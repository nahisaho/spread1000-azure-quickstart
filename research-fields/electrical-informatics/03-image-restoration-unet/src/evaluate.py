"""Denoiser の val セットでの詳細評価.

- 保存済み best_model.pt を読み込み
- val 全 40 サンプルで PSNR/SSIM を再計算
- baseline (noisy vs clean 素) と復元後を並べて改善量を報告
- outputs/metrics.json, outputs/test_samples.png (8 サンプル比較)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader
from torchmetrics.image import (
    PeakSignalNoiseRatio,
    StructuralSimilarityIndexMeasure,
)

from model import MiniUNet
from train import NoisyCleanDataset

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir or DATA_DIR
    out_dir = args.output_dir or OUT_DIR
    ckpt_path = out_dir / "best_model.pt"

    if not ckpt_path.exists():
        raise FileNotFoundError(f"{ckpt_path} が見つかりません。先に train.py を実行してください。")

    device = torch.device(args.device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model = MiniUNet(
        in_channels=ckpt.get("in_channels", 1),
        out_channels=ckpt.get("out_channels", 1),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    val_ds = NoisyCleanDataset(data_dir / "val")
    loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    print(f"[eval] val samples = {len(val_ds)}")

    psnr_noisy = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim_noisy = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)
    psnr_pred = PeakSignalNoiseRatio(data_range=1.0).to(device)
    ssim_pred = StructuralSimilarityIndexMeasure(data_range=1.0).to(device)

    with torch.no_grad():
        for noisy, clean in loader:
            noisy, clean = noisy.to(device), clean.to(device)
            pred = model(noisy).clamp(0.0, 1.0)
            noisy_c = noisy.clamp(0.0, 1.0)
            psnr_noisy.update(noisy_c, clean)
            ssim_noisy.update(noisy_c, clean)
            psnr_pred.update(pred, clean)
            ssim_pred.update(pred, clean)

    metrics = {
        "baseline_noisy": {
            "psnr_db": round(float(psnr_noisy.compute()), 4),
            "ssim": round(float(ssim_noisy.compute()), 4),
        },
        "restored": {
            "psnr_db": round(float(psnr_pred.compute()), 4),
            "ssim": round(float(ssim_pred.compute()), 4),
        },
        "improvement": {
            "psnr_db": round(
                float(psnr_pred.compute()) - float(psnr_noisy.compute()), 4
            ),
            "ssim": round(
                float(ssim_pred.compute()) - float(ssim_noisy.compute()), 4
            ),
        },
        "checkpoint_epoch": int(ckpt.get("epoch", -1)),
        "n_val": len(val_ds),
    }
    with (out_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(
        "[eval] noisy vs clean : PSNR = {:.2f} dB, SSIM = {:.4f}".format(
            metrics["baseline_noisy"]["psnr_db"],
            metrics["baseline_noisy"]["ssim"],
        )
    )
    print(
        "[eval] pred  vs clean : PSNR = {:.2f} dB, SSIM = {:.4f}".format(
            metrics["restored"]["psnr_db"],
            metrics["restored"]["ssim"],
        )
    )
    print(
        "[eval] improvement    : PSNR + {:.2f} dB, SSIM + {:.4f}".format(
            metrics["improvement"]["psnr_db"],
            metrics["improvement"]["ssim"],
        )
    )

    # 8 サンプルの比較画像
    n_show = min(8, len(val_ds))
    fig, axes = plt.subplots(n_show, 3, figsize=(9, 3 * n_show))
    if n_show == 1:
        axes = axes[None, :]
    got = 0
    with torch.no_grad():
        for noisy, clean in loader:
            for i in range(noisy.size(0)):
                if got >= n_show:
                    break
                pred = model(noisy[i : i + 1].to(device)).clamp(0.0, 1.0).cpu()
                for col, (arr, title) in enumerate(
                    [
                        (noisy[i, 0].numpy(), "noisy"),
                        (pred[0, 0].numpy(), "denoised"),
                        (clean[i, 0].numpy(), "clean"),
                    ]
                ):
                    axes[got, col].imshow(arr, cmap="gray", vmin=0, vmax=1)
                    axes[got, col].set_title(title)
                    axes[got, col].axis("off")
                got += 1
            if got >= n_show:
                break
    plt.tight_layout()
    plt.savefig(out_dir / "test_samples.png", dpi=100)
    plt.close()

    print(f"[eval] saved → {out_dir}/metrics.json, test_samples.png")


if __name__ == "__main__":
    main()
