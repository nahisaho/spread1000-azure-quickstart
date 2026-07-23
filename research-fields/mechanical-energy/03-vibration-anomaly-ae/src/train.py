"""
Conv1D AE を正常データのみで学習し、検証セットの 99 分位で閾値を決める.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from model import Conv1DAE

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))
    set_seed(args.seed)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)

    data = np.load(args.data)
    X_train = data["X_train"].astype(np.float32)
    X_val = data["X_val"].astype(np.float32)
    seq_len = int(data["sample_len"])
    print(f"[data] train={X_train.shape} val={X_val.shape} seq_len={seq_len}")

    # 正規化: train セットのグローバル mean/std
    mu = float(X_train.mean())
    sigma = float(X_train.std() + 1e-8)
    X_train_n = (X_train - mu) / sigma
    X_val_n = (X_val - mu) / sigma

    tr_tensor = torch.from_numpy(X_train_n).unsqueeze(1)  # (N, 1, L)
    val_tensor = torch.from_numpy(X_val_n).unsqueeze(1)

    tr_loader = DataLoader(
        TensorDataset(tr_tensor), batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor), batch_size=args.batch_size, shuffle=False, num_workers=0
    )

    model = Conv1DAE(latent_dim=args.latent_dim, seq_len=seq_len).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] Conv1D AE latent={args.latent_dim}: {n_params:,} params")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()

    best_val = float("inf")
    history = {"train": [], "val": []}
    ckpt_path = out_dir / "best_ae.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        tr_loss = 0.0
        n = 0
        for (xb,) in tr_loader:
            xb = xb.to(device)
            opt.zero_grad()
            xr = model(xb)
            loss = mse(xr, xb)
            loss.backward()
            opt.step()
            tr_loss += loss.item() * xb.size(0)
            n += xb.size(0)
        tr_loss /= n

        model.eval()
        val_loss = 0.0
        n = 0
        with torch.no_grad():
            for (xb,) in val_loader:
                xb = xb.to(device)
                xr = model(xb)
                val_loss += mse(xr, xb).item() * xb.size(0)
                n += xb.size(0)
        val_loss /= n

        history["train"].append(tr_loss)
        history["val"].append(val_loss)

        marker = ""
        if val_loss < best_val:
            best_val = val_loss
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "latent_dim": args.latent_dim,
                    "seq_len": seq_len,
                    "mu": mu,
                    "sigma": sigma,
                },
                ckpt_path,
            )
            marker = "  *best*"
        print(f"[epoch {epoch:3d}/{args.epochs}] train_mse={tr_loss:.5f}  val_mse={val_loss:.5f}{marker}")

    # 閾値決定: best model を load して val セットの per-sample 再構成 MSE の 99 分位
    ck = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ck["model_state_dict"])
    model.eval()
    per_sample = []
    with torch.no_grad():
        for (xb,) in val_loader:
            xb = xb.to(device)
            xr = model(xb)
            err = ((xr - xb) ** 2).mean(dim=(1, 2)).cpu().numpy()
            per_sample.extend(err.tolist())
    per_sample = np.array(per_sample)
    thr = float(np.quantile(per_sample, 0.99))
    print(f"[threshold] val MSE p99 = {thr:.6f}  (min={per_sample.min():.6f}, "
          f"max={per_sample.max():.6f})")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.plot(history["train"], label="train")
    plt.plot(history["val"], label="val")
    plt.xlabel("epoch")
    plt.ylabel("MSE")
    plt.title("Conv1D AE — reconstruction MSE")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    with (out_dir / "train_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "best_val_mse": round(best_val, 6),
                "threshold_p99": round(thr, 6),
                "mu": round(mu, 6),
                "sigma": round(sigma, 6),
                "epochs": args.epochs,
                "latent_dim": args.latent_dim,
                "seed": args.seed,
                "params": n_params,
            },
            f,
            indent=2,
        )
    # threshold を model checkpoint にも保存
    ck["threshold"] = thr
    torch.save(ck, ckpt_path)
    print(f"[train] saved → {ckpt_path}, {out_dir}/loss_curve.png, train_metrics.json")


if __name__ == "__main__":
    main()
