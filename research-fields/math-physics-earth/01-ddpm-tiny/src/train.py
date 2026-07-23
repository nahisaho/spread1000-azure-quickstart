"""Train tiny DDPM on Fashion-MNIST resized to 16x16."""
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
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import TinyUNet, DDPMScheduler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--T", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-subset", type=int, default=4000, help="Fashion-MNIST サブサンプル数 (CPU 前提)")
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))
    set_seed(args.seed)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)

    tfm = transforms.Compose([
        transforms.Resize(16),
        transforms.ToTensor(),                   # [0, 1]
        transforms.Normalize((0.5,), (0.5,)),    # [-1, 1] DDPM 標準
    ])
    print(f"[data] downloading Fashion-MNIST to {DATA_DIR} (~30MB)")
    ds = datasets.FashionMNIST(str(DATA_DIR), train=True, download=True, transform=tfm)
    if args.n_subset < len(ds):
        idx = torch.randperm(len(ds))[: args.n_subset].tolist()
        ds = torch.utils.data.Subset(ds, idx)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=True)
    print(f"[data] using {len(ds)} training images (16x16 grayscale)")

    model = TinyUNet().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] TinyUNet: {n_params:,} params")

    scheduler = DDPMScheduler(T=args.T, device=device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()

    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        n = 0
        for x, _ in loader:
            x = x.to(device)
            b = x.size(0)
            t = torch.randint(0, args.T, (b,), device=device)
            noise = torch.randn_like(x)
            xt = scheduler.q_sample(x, t, noise)
            eps_pred = model(xt, t)
            loss = mse(eps_pred, noise)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item() * b
            n += b
        avg = total_loss / n
        history.append(avg)
        print(f"[epoch {epoch:3d}/{args.epochs}] loss={avg:.5f}")

    ckpt_path = out_dir / "ddpm_model.pt"
    torch.save(
        {"model_state_dict": model.state_dict(), "T": args.T, "history": history},
        ckpt_path,
    )

    # loss curve
    plt.figure(figsize=(6, 4))
    plt.plot(history, marker="o")
    plt.xlabel("epoch"); plt.ylabel("MSE loss"); plt.grid(alpha=0.3)
    plt.title("DDPM training loss")
    plt.tight_layout(); plt.savefig(out_dir / "loss_curve.png", dpi=120); plt.close()

    # sample 16 images
    print("[sample] generating 16 images by reverse diffusion (T steps)")
    model.eval()
    samples = scheduler.p_sample_loop(model, (16, 1, 16, 16), device=device)
    samples = (samples.clamp(-1, 1) + 1.0) / 2.0  # -> [0, 1]

    fig, axes = plt.subplots(4, 4, figsize=(6, 6))
    for i, ax in enumerate(axes.flatten()):
        ax.imshow(samples[i, 0].cpu().numpy(), cmap="gray", vmin=0, vmax=1)
        ax.axis("off")
    plt.suptitle(f"DDPM samples after {args.epochs} epochs")
    plt.tight_layout()
    plt.savefig(out_dir / "samples.png", dpi=120)
    plt.close()

    with (out_dir / "train_metrics.json").open("w") as f:
        json.dump({"final_loss": history[-1], "epochs": args.epochs, "T": args.T,
                   "params": n_params, "seed": args.seed}, f, indent=2)
    print(f"[train] saved → {ckpt_path}, samples.png, loss_curve.png")


if __name__ == "__main__":
    main()
