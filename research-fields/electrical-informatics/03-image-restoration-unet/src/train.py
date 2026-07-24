"""U-Net denoiser 学習スクリプト.

- data/train, data/val の (clean, noisy) NPZ ペアを読む
- L1 損失で clean を直接予測
- val PSNR で早期停止 (patience=4)
- outputs/best_model.pt, train_history.json, loss_curve.png, comparison.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchmetrics.image import (
    PeakSignalNoiseRatio,
    StructuralSimilarityIndexMeasure,
)

from model import MiniUNet, count_parameters

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"

MAX_TRAINING_HOURS_HARD_LIMIT = 2.0  # require --allow-long-run above this


# ── Argparse validators ───────────────────────────────────────────────────────

def _positive_int(value: str) -> int:
    v = int(value)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value!r}")
    return v


def _positive_float(value: str) -> float:
    v = float(value)
    if v <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive float, got {value!r}")
    return v


# ── Dataset ───────────────────────────────────────────────────────────────────

class NoisyCleanDataset(Dataset):
    def __init__(self, split_dir: Path) -> None:
        self.paths = sorted(split_dir.glob("*.npz"))
        if not self.paths:
            raise FileNotFoundError(
                f"{split_dir} に .npz が見つかりません。先に generate_data.py を実行してください。"
            )

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        path = self.paths[idx]
        with np.load(path, allow_pickle=False) as d:
            if "clean" not in d or "noisy" not in d:
                raise KeyError(f"Missing keys 'clean'/'noisy' in {path}")
            clean: np.ndarray = d["clean"]
            noisy: np.ndarray = d["noisy"]

        if clean.shape != noisy.shape:
            raise ValueError(f"Shape mismatch clean={clean.shape} noisy={noisy.shape} in {path}")
        if clean.dtype != np.float32 or noisy.dtype != np.float32:
            raise ValueError(f"Expected float32, got clean={clean.dtype} noisy={noisy.dtype} in {path}")
        if not (np.all(clean >= 0.0) and np.all(clean <= 1.0)):
            raise ValueError(f"clean values out of [0,1] in {path}")
        if not (np.all(noisy >= 0.0) and np.all(noisy <= 1.0)):
            raise ValueError(f"noisy values out of [0,1] in {path}")
        if not np.isfinite(clean).all() or not np.isfinite(noisy).all():
            raise ValueError(f"Non-finite values in {path}")

        return torch.from_numpy(noisy.copy()), torch.from_numpy(clean.copy())


# ── Seed / determinism ────────────────────────────────────────────────────────

def set_seed(seed: int) -> torch.Generator:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    return torch.Generator().manual_seed(seed)


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    criterion: nn.Module,
    context: str = "eval",
) -> tuple[float, float, float]:
    """Returns (mean_loss, psnr_db, ssim). Raises SystemExit on non-finite values."""
    model.eval()
    psnr_m = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim_m = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)
    losses, n = 0.0, 0
    with torch.no_grad():
        for noisy, clean in loader:
            noisy, clean = noisy.to(device), clean.to(device)
            pred = model(noisy)
            pred_c = pred.clamp(0.0, 1.0)
            loss = criterion(pred, clean)
            if not torch.isfinite(loss):
                raise SystemExit(f"[abort] non-finite loss in {context}: {loss.item()}")
            losses += loss.item() * clean.size(0)
            n += clean.size(0)
            psnr_m.update(pred_c, clean)
            ssim_m.update(pred_c, clean)
    mean_loss = losses / n
    val_psnr = float(psnr_m.compute())
    val_ssim = float(ssim_m.compute())
    if not math.isfinite(val_psnr):
        raise SystemExit(f"[abort] non-finite PSNR in {context}: {val_psnr}")
    if not math.isfinite(val_ssim):
        raise SystemExit(f"[abort] non-finite SSIM in {context}: {val_ssim}")
    return mean_loss, val_psnr, val_ssim


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train MiniUNet denoiser.")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=_positive_int, default=20,
                   help="Maximum training epochs (default: 20)")
    p.add_argument("--batch-size", type=_positive_int, default=16)
    p.add_argument("--lr", type=_positive_float, default=1e-3)
    p.add_argument("--weight-decay", type=_positive_float, default=1e-4)
    p.add_argument("--patience", type=_positive_int, default=4)
    p.add_argument("--seed", type=_positive_int, default=42)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--max-training-hours", type=_positive_float, default=1.0,
                   help="Wall-clock budget in hours (default: 1.0). "
                        f"Values > {MAX_TRAINING_HOURS_HARD_LIMIT} require --allow-long-run.")
    p.add_argument("--allow-long-run", action="store_true",
                   help=f"Required when --max-training-hours > {MAX_TRAINING_HOURS_HARD_LIMIT}")
    return p.parse_args()


# ── Comparison figure ─────────────────────────────────────────────────────────

def _save_comparison(model: nn.Module, loader: DataLoader,
                     device: torch.device, out_path: Path, n: int = 4) -> None:
    model.eval()
    fig, axes = plt.subplots(n, 3, figsize=(9, 3 * n))
    if n == 1:
        axes = axes[None, :]
    got = 0
    with torch.no_grad():
        for noisy, clean in loader:
            for i in range(noisy.size(0)):
                if got >= n:
                    break
                pred = model(noisy[i: i + 1].to(device)).clamp(0.0, 1.0).cpu()
                for col, (arr, title) in enumerate(
                    [
                        (noisy[i, 0].numpy(), "noisy input"),
                        (pred[0, 0].numpy(), "denoised (model)"),
                        (clean[i, 0].numpy(), "clean target"),
                    ]
                ):
                    axes[got, col].imshow(arr, cmap="gray", vmin=0, vmax=1)
                    axes[got, col].set_title(title)
                    axes[got, col].axis("off")
                got += 1
            if got >= n:
                break
    plt.tight_layout()
    plt.savefig(out_path, dpi=100)
    plt.close()


# ── Reproducibility helpers ───────────────────────────────────────────────────

def _get_versions() -> dict[str, str]:
    import importlib
    import sys as _sys
    versions: dict[str, str] = {"python": _sys.version}
    for pkg in ("torch", "torchvision", "torchmetrics", "skimage", "numpy"):
        try:
            mod = importlib.import_module(pkg)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not installed"
    return versions


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    except Exception:
        return "unavailable"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if args.max_training_hours > MAX_TRAINING_HOURS_HARD_LIMIT and not args.allow_long_run:
        raise SystemExit(
            f"[abort] --max-training-hours {args.max_training_hours} > "
            f"{MAX_TRAINING_HOURS_HARD_LIMIT} h. Pass --allow-long-run to proceed."
        )

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(
            "[abort] --device cuda requested but torch.cuda.is_available() is False."
        )

    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    generator = set_seed(args.seed)

    data_dir = args.data_dir or DATA_DIR
    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean stale artifacts
    for stale in ["best_model.pt", "train_history.json", "loss_curve.png", "comparison.png"]:
        stale_path = out_dir / stale
        if stale_path.exists():
            stale_path.unlink()

    train_ds = NoisyCleanDataset(data_dir / "train")
    val_ds = NoisyCleanDataset(data_dir / "val")
    print(f"[data] train={len(train_ds)}, val={len(val_ds)}")

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=0, generator=generator,
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device(args.device)
    model = MiniUNet(in_channels=1, out_channels=1).to(device)
    print(f"[model] MiniUNet, trainable params = {count_parameters(model):,}")

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.L1Loss()

    # Baseline PSNR/SSIM (noisy vs clean)
    psnr_bl = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim_bl = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)
    with torch.no_grad():
        for noisy, clean in val_loader:
            noisy, clean = noisy.to(device), clean.to(device)
            psnr_bl.update(noisy.clamp(0.0, 1.0), clean)
            ssim_bl.update(noisy.clamp(0.0, 1.0), clean)
    baseline_psnr = float(psnr_bl.compute())
    baseline_ssim = float(ssim_bl.compute())
    if not math.isfinite(baseline_psnr) or not math.isfinite(baseline_ssim):
        raise SystemExit(
            f"[abort] non-finite baseline metrics: PSNR={baseline_psnr}, SSIM={baseline_ssim}"
        )
    print(f"[baseline] val noisy vs clean: PSNR={baseline_psnr:.2f} dB, SSIM={baseline_ssim:.4f}")

    history: dict[str, list[float]] = {
        "train_loss": [], "val_loss": [], "val_psnr": [], "val_ssim": []
    }
    best_psnr, best_epoch, patience_left = -1.0, 0, args.patience
    best_ckpt = out_dir / "best_model.pt"
    run_start = time.monotonic()

    for epoch in range(1, args.epochs + 1):
        elapsed_h = (time.monotonic() - run_start) / 3600.0
        if elapsed_h >= args.max_training_hours:
            print(
                f"[wall-clock] {elapsed_h:.2f} h >= --max-training-hours "
                f"{args.max_training_hours} h; stopping before epoch {epoch}."
            )
            break

        model.train()
        total_loss, n = 0.0, 0
        for noisy, clean in train_loader:
            noisy, clean = noisy.to(device), clean.to(device)
            optimizer.zero_grad()
            pred = model(noisy)
            loss = criterion(pred, clean)
            if not torch.isfinite(loss):
                raise SystemExit(
                    f"[abort] non-finite train loss at epoch {epoch}: {loss.item()}"
                )
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * clean.size(0)
            n += clean.size(0)
        train_loss = total_loss / n
        if not math.isfinite(train_loss):
            raise SystemExit(
                f"[abort] non-finite mean train loss at epoch {epoch}: {train_loss}"
            )

        val_loss, val_psnr, val_ssim = evaluate(
            model, val_loader, device, criterion, context=f"epoch {epoch} val"
        )
        scheduler.step()

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_psnr"].append(val_psnr)
        history["val_ssim"].append(val_ssim)

        marker = ""
        if val_psnr > best_psnr:
            best_psnr, best_epoch, patience_left = val_psnr, epoch, args.patience
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_psnr": val_psnr,
                    "val_ssim": val_ssim,
                    "in_channels": 1,
                    "out_channels": 1,
                },
                best_ckpt,
            )
            marker = "  ★ (best, saved)"
        else:
            patience_left -= 1
        print(
            f"[epoch {epoch:2d}/{args.epochs}] train_loss={train_loss:.4f} "
            f"val_loss={val_loss:.4f} val_PSNR={val_psnr:.2f} val_SSIM={val_ssim:.4f}{marker}"
        )
        if patience_left <= 0:
            print(f"[early-stop] no val PSNR improvement for {args.patience} epochs")
            break

    total_elapsed_h = (time.monotonic() - run_start) / 3600.0
    print(
        f"[train] best val PSNR = {best_psnr:.2f} dB (epoch {best_epoch}), "
        f"elapsed {total_elapsed_h:.3f} h"
    )

    # Loss / PSNR curves
    fig, ax1 = plt.subplots(figsize=(7, 4))
    epochs_x = range(1, len(history["train_loss"]) + 1)
    ax1.plot(epochs_x, history["train_loss"], label="train loss (L1)", color="tab:blue")
    ax1.plot(epochs_x, history["val_loss"], label="val loss (L1)", color="tab:orange")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("L1 loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(epochs_x, history["val_psnr"], label="val PSNR", color="tab:green", linestyle="--")
    ax2.axhline(baseline_psnr, color="tab:red", linestyle=":", label="baseline PSNR (noisy)")
    ax2.set_ylabel("PSNR (dB)")
    ax2.legend(loc="lower right")
    plt.title("MiniUNet Denoiser — train/val curves")
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    # Reload best weights for comparison image
    ckpt = torch.load(best_ckpt, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    _save_comparison(model, val_loader, device, out_dir / "comparison.png", n=4)

    # Full reproducibility manifest
    ckpt_sha256 = _sha256_file(best_ckpt)
    pkg_versions = _get_versions()
    cuda_version = getattr(torch.version, "cuda", None)
    cudnn_version: int | None = None
    try:
        cudnn_version = torch.backends.cudnn.version()
    except Exception:
        pass
    gpu_name: str | None = None
    if torch.cuda.is_available():
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            pass

    manifest: dict = {
        "history": history,
        "baseline_val_psnr": baseline_psnr,
        "baseline_val_ssim": baseline_ssim,
        "best_val_psnr": best_psnr,
        "best_epoch": best_epoch,
        "trained_epochs": len(history["train_loss"]),
        "total_elapsed_hours": round(total_elapsed_h, 6),
        "n_train": len(train_ds),
        "n_val": len(val_ds),
        "cli_args": vars(args),
        "seed": args.seed,
        "device": args.device,
        "checkpoint_sha256": ckpt_sha256,
        "git_commit": _git_head(),
        "package_versions": pkg_versions,
        "cuda_version": cuda_version,
        "cudnn_version": cudnn_version,
        "gpu_name": gpu_name,
        "deterministic_algorithms": True,
        "cudnn_deterministic": True,
        "cudnn_benchmark": False,
    }
    history_path = out_dir / "train_history.json"
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, allow_nan=False)

    print(
        f"[train] saved → {best_ckpt}, {out_dir}/loss_curve.png, "
        f"comparison.png, train_history.json"
    )
    print(f"[train] checkpoint SHA-256: {ckpt_sha256}")


if __name__ == "__main__":
    main()
