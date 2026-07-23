"""U-Net denoiser 学習スクリプト.

- data/train, data/val の (clean, noisy) NPZ ペアを読む
- L1 損失で clean を直接予測
- val PSNR で早期停止 (patience=4)
- outputs/best_model.pt, train_history.json, loss_curve.png, comparison.png
"""
from __future__ import annotations

import argparse
import json
import os
import random
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


class NoisyCleanDataset(Dataset):
    def __init__(self, split_dir: Path):
        self.paths = sorted(split_dir.glob("*.npz"))
        if not self.paths:
            raise FileNotFoundError(
                f"{split_dir} に .npz が見つかりません。先に generate_data.py を実行してください。"
            )

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        d = np.load(self.paths[idx])
        clean = torch.from_numpy(d["clean"])  # (1, H, W) float32
        noisy = torch.from_numpy(d["noisy"])
        return noisy, clean


def set_seed(seed: int) -> torch.Generator:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    return torch.Generator().manual_seed(seed)


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    criterion: nn.Module,
) -> tuple[float, float, float]:
    """returns (mean_loss, psnr_db, ssim)."""
    model.eval()
    psnr = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)
    losses, n = 0.0, 0
    with torch.no_grad():
        for noisy, clean in loader:
            noisy, clean = noisy.to(device), clean.to(device)
            pred = model(noisy)
            pred_c = pred.clamp(0.0, 1.0)
            loss = criterion(pred, clean)
            losses += loss.item() * clean.size(0)
            n += clean.size(0)
            psnr.update(pred_c, clean)
            ssim.update(pred_c, clean)
    return losses / n, float(psnr.compute()), float(ssim.compute())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--patience", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def _save_comparison(model, loader, device, out_path: Path, n: int = 4) -> None:
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
                pred = model(noisy[i : i + 1].to(device)).clamp(0.0, 1.0).cpu()
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


def main() -> None:
    args = parse_args()
    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    generator = set_seed(args.seed)

    data_dir = args.data_dir or DATA_DIR
    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

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

    # baseline PSNR/SSIM (noisy vs clean, モデル無評価) を先に測っておく
    psnr_bl = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim_bl = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)
    with torch.no_grad():
        for noisy, clean in val_loader:
            noisy, clean = noisy.to(device), clean.to(device)
            psnr_bl.update(noisy.clamp(0.0, 1.0), clean)
            ssim_bl.update(noisy.clamp(0.0, 1.0), clean)
    baseline_psnr = float(psnr_bl.compute())
    baseline_ssim = float(ssim_bl.compute())
    print(f"[baseline] val noisy vs clean: PSNR={baseline_psnr:.2f} dB, SSIM={baseline_ssim:.4f}")

    history = {"train_loss": [], "val_loss": [], "val_psnr": [], "val_ssim": []}
    best_psnr, best_epoch, patience_left = -1.0, 0, args.patience
    best_ckpt = out_dir / "best_model.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for noisy, clean in train_loader:
            noisy, clean = noisy.to(device), clean.to(device)
            optimizer.zero_grad()
            pred = model(noisy)
            loss = criterion(pred, clean)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * clean.size(0)
            n += clean.size(0)
        train_loss = total_loss / n
        val_loss, val_psnr, val_ssim = evaluate(model, val_loader, device, criterion)
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

    print(f"[train] best val PSNR = {best_psnr:.2f} dB (epoch {best_epoch})")

    # 学習曲線
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

    # best 重みを読み直して比較画像 (train.py 終了時点でモデルは last epoch なので)
    ckpt = torch.load(best_ckpt, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    _save_comparison(model, val_loader, device, out_dir / "comparison.png", n=4)

    with (out_dir / "train_history.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "history": history,
                "baseline_val_psnr": baseline_psnr,
                "baseline_val_ssim": baseline_ssim,
                "best_val_psnr": best_psnr,
                "best_epoch": best_epoch,
                "trained_epochs": len(history["train_loss"]),
                "n_train": len(train_ds),
                "n_val": len(val_ds),
                "seed": args.seed,
                "device": args.device,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(
        f"[train] saved → {best_ckpt}, {out_dir}/loss_curve.png, comparison.png, train_history.json"
    )


if __name__ == "__main__":
    main()
