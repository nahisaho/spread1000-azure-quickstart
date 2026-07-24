"""Verify a checkpoint before deployment or publication.

Checks performed (exit 0 iff ALL pass):
  1. SHA-256 of .pth file matches --checkpoint-sha256 (if provided)
  2. torch.load with weights_only=True succeeds
  3. Model output shape matches expected  [1, 1, H, W]
  4. All output logits are finite
  5. Dice on test split >= --min-dice  (default 0.60)
  6. If --baseline-metrics provided: dice improvement > 5% relative

Usage:
    python src/verify.py \
        --checkpoint data/checkpoints/best_model.pth \
        --checkpoint-sha256 <sha256hex> \
        --test-metrics data/predictions/test_metrics.json \
        --min-dice 0.70

    # With baseline comparison:
    python src/verify.py \
        --checkpoint data/checkpoints/best_model.pth \
        --test-metrics data/predictions/test_metrics.json \
        --baseline-metrics baseline/test_metrics.json \
        --min-dice 0.70
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument(
        "--checkpoint-sha256",
        default=None,
        help="Expected SHA-256 hex; omit to skip hash check",
    )
    p.add_argument(
        "--test-metrics", type=Path, required=True,
        help="Path to test_metrics.json produced by evaluate.py",
    )
    p.add_argument(
        "--min-dice", type=float, default=0.60,
        help="Minimum acceptable test Dice (default: 0.60)",
    )
    p.add_argument(
        "--baseline-metrics", type=Path, default=None,
        help="Optional baseline test_metrics.json for regression check",
    )
    p.add_argument("--image-size", type=int, default=128)
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    return p.parse_args()


def _row(name: str, status: str, detail: str = "") -> str:
    icon = "✓" if status == "PASS" else "✗"
    return f"  {icon} {status:<4}  {name:<35} {detail}"


def main() -> int:
    args = parse_args()
    results: list[tuple[str, bool, str]] = []

    import torch
    sys.path.insert(0, str(Path(__file__).parent))
    from model import build_model

    # ── 1. SHA-256 check ──────────────────────────────────────────────────
    if not args.checkpoint.exists():
        print(f"ERROR: checkpoint not found: {args.checkpoint}", file=sys.stderr)
        return 1

    actual_sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    if args.checkpoint_sha256:
        sha_ok = actual_sha == args.checkpoint_sha256.lower()
        results.append((
            "SHA-256 matches",
            sha_ok,
            f"expected {args.checkpoint_sha256[:16]}... got {actual_sha[:16]}...",
        ))
    else:
        results.append(("SHA-256 check", True, f"skipped (actual: {actual_sha[:16]}...)"))

    # ── 2. Load checkpoint ────────────────────────────────────────────────
    device = torch.device(args.device)
    try:
        state = torch.load(args.checkpoint, weights_only=True, map_location=device)
        load_ok = True
        load_detail = "weights_only=True"
    except Exception as exc:
        load_ok = False
        load_detail = str(exc)
        state = None
    results.append(("torch.load weights_only=True", load_ok, load_detail))

    # ── 3. Output shape check ─────────────────────────────────────────────
    shape_ok = False
    shape_detail = "load failed"
    if load_ok and state is not None:
        try:
            model = build_model(in_channels=1, out_channels=1).to(device)
            model.load_state_dict(state)
            model.eval()
            dummy = torch.zeros(1, 1, args.image_size, args.image_size, device=device)
            with torch.no_grad():
                out = model(dummy)
            expected_shape = (1, 1, args.image_size, args.image_size)
            shape_ok = tuple(out.shape) == expected_shape
            shape_detail = f"got {tuple(out.shape)}, expected {expected_shape}"
        except Exception as exc:
            shape_detail = str(exc)
    results.append(("Output shape", shape_ok, shape_detail))

    # ── 4. Finite output check ────────────────────────────────────────────
    finite_ok = False
    finite_detail = "shape check failed"
    if shape_ok:
        finite_ok = bool(torch.isfinite(out).all())
        finite_detail = (
            "all finite" if finite_ok
            else f"non-finite count: {(~torch.isfinite(out)).sum().item()}"
        )
    results.append(("All logits finite", finite_ok, finite_detail))

    # ── 5. Dice threshold check ───────────────────────────────────────────
    dice_ok = False
    dice_detail = "test_metrics.json not loaded"
    test_dice = None
    if args.test_metrics.exists():
        try:
            m = json.loads(args.test_metrics.read_text())
            test_dice = float(m["test_dice"])
            dice_ok = test_dice >= args.min_dice
            dice_detail = f"dice={test_dice:.4f}, threshold={args.min_dice:.4f}"
        except Exception as exc:
            dice_detail = str(exc)
    else:
        dice_detail = f"not found: {args.test_metrics}"
    results.append((f"Dice >= {args.min_dice:.2f}", dice_ok, dice_detail))

    # ── 6. Baseline regression check ─────────────────────────────────────
    if args.baseline_metrics is not None:
        regress_ok = False
        regress_detail = "baseline not loaded"
        if args.baseline_metrics.exists() and test_dice is not None:
            try:
                bm = json.loads(args.baseline_metrics.read_text())
                baseline_dice = float(bm["test_dice"])
                improvement = (test_dice - baseline_dice) / max(abs(baseline_dice), 1e-9)
                regress_ok = improvement > 0.05
                regress_detail = (
                    f"new={test_dice:.4f} baseline={baseline_dice:.4f} "
                    f"Δ={improvement:+.2%}"
                )
            except Exception as exc:
                regress_detail = str(exc)
        results.append(("Dice > baseline + 5%", regress_ok, regress_detail))

    # ── Print summary table ───────────────────────────────────────────────
    print("\n── Checkpoint verification ───────────────────────────────────")
    for name, ok, detail in results:
        print(_row(name, "PASS" if ok else "FAIL", detail))

    all_pass = all(ok for _, ok, _ in results)
    print("──────────────────────────────────────────────────────────────")
    if all_pass:
        print("  RESULT: ALL PASS ✓")
    else:
        n_fail = sum(1 for _, ok, _ in results if not ok)
        print(f"  RESULT: {n_fail} FAIL(S) — checkpoint NOT safe to deploy ✗")
    print()
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
