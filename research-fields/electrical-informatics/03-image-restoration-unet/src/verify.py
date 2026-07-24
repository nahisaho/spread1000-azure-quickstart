"""src/verify.py — Checkpoint & metrics verification gate for E-3 U-Net denoiser.

Exits 0 only when ALL checks pass:
  1. SHA-256 of checkpoint file matches --checkpoint-sha256 (if provided)
  2. Checkpoint loads cleanly with weights_only=True + map_location='cpu'
  3. Model output shape matches input shape (B=1, C=1, H=128, W=128)
  4. All model outputs are finite
  5. Test metrics PSNR >= --min-psnr AND SSIM >= --min-ssim
  6. (Optional) Test PSNR beats baseline_metrics by at least --min-improvement-db

Usage:
  python src/verify.py \\
    --checkpoint outputs/best_model.pt \\
    --checkpoint-sha256 <hex> \\
    --test-metrics outputs/metrics.json \\
    --min-psnr 28.0 \\
    --min-ssim 0.85 \\
    --baseline-metrics outputs/baseline_metrics.json  # optional
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch

from model import MiniUNet


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _positive_float(value: str) -> float:
    v = float(value)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be positive, got {value}")
    return v


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Verify checkpoint integrity and assert metric thresholds."
    )
    p.add_argument("--checkpoint", type=Path, required=True,
                   help="Path to best_model.pt")
    p.add_argument("--checkpoint-sha256", type=str, default=None,
                   help="Expected SHA-256 hex digest of checkpoint file")
    p.add_argument("--test-metrics", type=Path, required=True,
                   help="Path to metrics.json produced by evaluate.py")
    p.add_argument("--min-psnr", type=_positive_float, default=28.0,
                   help="Minimum acceptable restored PSNR (dB). Default: 28.0")
    p.add_argument("--min-ssim", type=_positive_float, default=0.85,
                   help="Minimum acceptable restored SSIM. Default: 0.85")
    p.add_argument("--baseline-metrics", type=Path, default=None,
                   help="Path to baseline metrics.json; restored PSNR must beat "
                        "baseline by at least --min-improvement-db")
    p.add_argument("--min-improvement-db", type=_positive_float, default=3.0,
                   help="Required PSNR improvement over baseline (dB). Default: 3.0")
    return p.parse_args()


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def main() -> None:
    args = parse_args()

    # ── 1. SHA-256 verification ───────────────────────────────────────────────
    if not args.checkpoint.exists():
        _fail(f"Checkpoint not found: {args.checkpoint}")

    actual_sha256 = _compute_sha256(args.checkpoint)
    if args.checkpoint_sha256:
        if actual_sha256.lower() != args.checkpoint_sha256.lower():
            _fail(
                f"SHA-256 mismatch for {args.checkpoint}:\n"
                f"  expected: {args.checkpoint_sha256.lower()}\n"
                f"  actual:   {actual_sha256}"
            )
        _ok(f"SHA-256 verified: {actual_sha256}")
    else:
        _ok(f"SHA-256 (recorded, no expected value supplied): {actual_sha256}")

    # ── 2. Checkpoint loads cleanly ───────────────────────────────────────────
    try:
        ckpt = torch.load(args.checkpoint, weights_only=True, map_location="cpu")
    except Exception as exc:
        _fail(f"torch.load failed: {exc}")

    required_keys = {"model_state_dict", "epoch", "val_psnr", "val_ssim"}
    missing = required_keys - set(ckpt.keys())
    if missing:
        _fail(f"Checkpoint missing keys: {missing}")
    _ok(f"Checkpoint loaded (epoch={ckpt['epoch']}, val_PSNR={ckpt['val_psnr']:.2f})")

    # ── 3. Output-shape assertion ─────────────────────────────────────────────
    in_ch = ckpt.get("in_channels", 1)
    out_ch = ckpt.get("out_channels", 1)
    model = MiniUNet(in_channels=in_ch, out_channels=out_ch)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    dummy = torch.zeros(1, in_ch, 128, 128)
    with torch.no_grad():
        out = model(dummy)

    expected_shape = (1, out_ch, 128, 128)
    if tuple(out.shape) != expected_shape:
        _fail(
            f"Output shape mismatch: expected {expected_shape}, got {tuple(out.shape)}"
        )
    _ok(f"Output shape: {tuple(out.shape)} (matches input shape)")

    # ── 4. Finite output assertion ────────────────────────────────────────────
    if not torch.isfinite(out).all():
        _fail("Model output contains non-finite values (NaN or Inf)")
    _ok("All model outputs are finite")

    # ── 5. Metric threshold assertions ───────────────────────────────────────
    if not args.test_metrics.exists():
        _fail(f"Test metrics file not found: {args.test_metrics}")

    with args.test_metrics.open(encoding="utf-8") as f:
        metrics = json.load(f)

    # Support both flat and nested (evaluate.py) formats
    if "restored" in metrics:
        restored_psnr = float(metrics["restored"]["psnr_db"])
        restored_ssim = float(metrics["restored"]["ssim"])
    else:
        restored_psnr = float(metrics.get("psnr_db", float("nan")))
        restored_ssim = float(metrics.get("ssim", float("nan")))

    if not (restored_psnr == restored_psnr):  # NaN check
        _fail(f"PSNR in metrics is NaN")
    if not (restored_ssim == restored_ssim):
        _fail(f"SSIM in metrics is NaN")

    if restored_psnr < args.min_psnr:
        _fail(
            f"PSNR {restored_psnr:.2f} dB < threshold {args.min_psnr:.2f} dB"
        )
    _ok(f"PSNR {restored_psnr:.2f} dB >= {args.min_psnr:.2f} dB")

    if restored_ssim < args.min_ssim:
        _fail(
            f"SSIM {restored_ssim:.4f} < threshold {args.min_ssim:.4f}"
        )
    _ok(f"SSIM {restored_ssim:.4f} >= {args.min_ssim:.4f}")

    # ── 6. Baseline improvement assertion ────────────────────────────────────
    if args.baseline_metrics is not None:
        if not args.baseline_metrics.exists():
            _fail(f"Baseline metrics file not found: {args.baseline_metrics}")
        with args.baseline_metrics.open(encoding="utf-8") as f:
            baseline = json.load(f)

        if "baseline_noisy" in baseline:
            baseline_psnr = float(baseline["baseline_noisy"]["psnr_db"])
        elif "restored" in baseline:
            baseline_psnr = float(baseline["restored"]["psnr_db"])
        else:
            baseline_psnr = float(baseline.get("psnr_db", float("nan")))

        improvement = restored_psnr - baseline_psnr
        if improvement < args.min_improvement_db:
            _fail(
                f"PSNR improvement {improvement:.2f} dB < required "
                f"{args.min_improvement_db:.2f} dB "
                f"(restored={restored_psnr:.2f}, baseline={baseline_psnr:.2f})"
            )
        _ok(
            f"PSNR improvement {improvement:.2f} dB >= {args.min_improvement_db:.2f} dB "
            f"(restored={restored_psnr:.2f}, baseline={baseline_psnr:.2f})"
        )

    print("\n[PASS] All verification checks passed.")


if __name__ == "__main__":
    main()
