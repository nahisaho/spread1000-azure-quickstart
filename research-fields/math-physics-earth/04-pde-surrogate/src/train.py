"""2D 移流拡散 PDE のニューラルサロゲート

- 教師データ: FD 解 (pde.py) の (u_t, u_{t+k}) ペア (k step 先)
- モデル: 小型 U-Net (~50K params), 入力/出力ともに 1 チャネル 64×64
- 損失: MSE, 評価: relative L2 error
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
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from pde import generate_trajectories


class TinyUNet(nn.Module):
    def __init__(self, base: int = 16):
        super().__init__()
        self.e1 = nn.Sequential(nn.Conv2d(1, base, 3, padding=1), nn.ReLU(),
                                nn.Conv2d(base, base, 3, padding=1), nn.ReLU())
        self.p1 = nn.MaxPool2d(2)
        self.e2 = nn.Sequential(nn.Conv2d(base, base*2, 3, padding=1), nn.ReLU(),
                                nn.Conv2d(base*2, base*2, 3, padding=1), nn.ReLU())
        self.p2 = nn.MaxPool2d(2)
        self.bott = nn.Sequential(nn.Conv2d(base*2, base*4, 3, padding=1), nn.ReLU(),
                                  nn.Conv2d(base*4, base*4, 3, padding=1), nn.ReLU())
        self.u2 = nn.ConvTranspose2d(base*4, base*2, 2, stride=2)
        self.d2 = nn.Sequential(nn.Conv2d(base*4, base*2, 3, padding=1), nn.ReLU(),
                                nn.Conv2d(base*2, base*2, 3, padding=1), nn.ReLU())
        self.u1 = nn.ConvTranspose2d(base*2, base, 2, stride=2)
        self.d1 = nn.Sequential(nn.Conv2d(base*2, base, 3, padding=1), nn.ReLU(),
                                nn.Conv2d(base, base, 3, padding=1), nn.ReLU())
        self.out = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(self.p1(e1))
        b  = self.bott(self.p2(e2))
        d2 = self.d2(torch.cat([self.u2(b), e2], 1))
        d1 = self.d1(torch.cat([self.u1(d2), e1], 1))
        # 残差学習: モデルは Δu を予測、u + Δu を返す
        return x + self.out(d1)


def rel_l2(pred: torch.Tensor, tgt: torch.Tensor) -> float:
    num = torch.linalg.norm((pred - tgt).flatten(1), dim=1)
    den = torch.linalg.norm(tgt.flatten(1), dim=1) + 1e-8
    return (num / den).mean().item()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-train", type=int, default=64)
    ap.add_argument("--n-val", type=int, default=16)
    ap.add_argument("--n-steps", type=int, default=40, help="FD trajectory length")
    ap.add_argument("--k-step", type=int, default=5, help="predict k steps ahead")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.k_step < 1:
        raise SystemExit(f"[error] --k-step must be >= 1 (got {args.k_step})")
    if args.k_step >= args.n_steps:
        raise SystemExit(f"[error] --k-step ({args.k_step}) must be < --n-steps ({args.n_steps})")
    if args.n_train < 1 or args.n_val < 1:
        raise SystemExit("[error] --n-train and --n-val must be >= 1")

    torch.manual_seed(args.seed); np.random.seed(args.seed)
    device = torch.device("cpu")
    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    print(f"[data] generating FD solutions: n_train={args.n_train} n_val={args.n_val} n_steps={args.n_steps}")
    train_trajs, dt = generate_trajectories(args.n_train, args.n_steps, seed=args.seed)
    val_trajs, _   = generate_trajectories(args.n_val, args.n_steps, seed=args.seed + 999)
    print(f"[data] dt={dt:.5f}, k-step prediction horizon = {args.k_step*dt:.4f}")

    def to_pairs(trajs: np.ndarray, k: int):
        # (n_traj, n_steps+1, H, W) → (samples, 1, H, W) x, y
        xs, ys = [], []
        for traj in trajs:
            for t in range(len(traj) - k):
                xs.append(traj[t]); ys.append(traj[t + k])
        return np.stack(xs)[:, None], np.stack(ys)[:, None]

    Xtr, Ytr = to_pairs(train_trajs, args.k_step)
    Xva, Yva = to_pairs(val_trajs, args.k_step)
    print(f"[data] train pairs={len(Xtr)} val pairs={len(Xva)}")

    tr_loader = DataLoader(TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(Ytr)),
                           batch_size=args.batch_size, shuffle=True)
    va_loader = DataLoader(TensorDataset(torch.from_numpy(Xva), torch.from_numpy(Yva)),
                           batch_size=args.batch_size, shuffle=False)

    model = TinyUNet(base=16).to(device)
    n_param = sum(p.numel() for p in model.parameters())
    print(f"[model] TinyUNet | params={n_param:,}")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()
    hist = {"train_loss": [], "val_loss": [], "val_relL2": []}
    best = float("inf")
    for ep in range(1, args.epochs + 1):
        model.train(); tl = 0.0
        for xb, yb in tr_loader:
            opt.zero_grad()
            loss = mse(model(xb), yb)
            loss.backward(); opt.step()
            tl += loss.item() * yb.size(0)
        tl /= len(tr_loader.dataset)

        model.eval(); vl = 0.0; vrel = 0.0; n_val = 0
        with torch.no_grad():
            for xb, yb in va_loader:
                p = model(xb)
                vl += mse(p, yb).item() * yb.size(0)
                vrel += rel_l2(p, yb) * yb.size(0)
                n_val += yb.size(0)
        vl /= n_val; vrel /= n_val
        hist["train_loss"].append(tl); hist["val_loss"].append(vl); hist["val_relL2"].append(vrel)
        mark = ""
        if vrel < best:
            best = vrel
            torch.save(model.state_dict(), outputs / "best_model.pt")
            mark = " *best*"
        print(f"[epoch {ep:2d}/{args.epochs}] train_mse={tl:.5f} val_mse={vl:.5f} val_relL2={vrel:.4f}{mark}")

    # rollout (自己回帰的に K ステップ先まで予測して FD 解と比較)
    print("\n[rollout] autoregressive multi-step forecast on 1 val trajectory")
    model.load_state_dict(torch.load(outputs / "best_model.pt", map_location=device))
    model.eval()
    traj = val_trajs[0]
    u = torch.from_numpy(traj[0])[None, None]
    preds = [u.squeeze().numpy()]
    n_rollout_k = min(6, (len(traj) - 1) // args.k_step)
    with torch.no_grad():
        for _ in range(n_rollout_k):
            u = model(u)
            preds.append(u.squeeze().numpy())
    gts = [traj[i * args.k_step] for i in range(n_rollout_k + 1)]

    fig, axes = plt.subplots(3, n_rollout_k + 1, figsize=(2.2 * (n_rollout_k + 1), 6.6))
    for j in range(n_rollout_k + 1):
        axes[0, j].imshow(gts[j], vmin=0, vmax=1.5, cmap="viridis")
        axes[0, j].set_title(f"t={j*args.k_step}\nFD"); axes[0, j].axis("off")
        axes[1, j].imshow(preds[j], vmin=0, vmax=1.5, cmap="viridis")
        axes[1, j].set_title("pred"); axes[1, j].axis("off")
        err = np.abs(preds[j] - gts[j])
        axes[2, j].imshow(err, vmin=0, vmax=0.3, cmap="Reds")
        axes[2, j].set_title(f"|err| max={err.max():.2f}"); axes[2, j].axis("off")
    fig.tight_layout(); fig.savefig(outputs / "rollout.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(hist["val_relL2"], "-o")
    ax.set_xlabel("epoch"); ax.set_ylabel("val relative L2")
    ax.set_title("Neural PDE surrogate accuracy")
    fig.tight_layout(); fig.savefig(outputs / "learning_curve.png", dpi=120); plt.close(fig)

    metrics = {"n_params": n_param, "dt_fd": dt, "k_step": args.k_step,
               "best_val_relL2": best,
               "rollout_final_err_max": float(np.abs(preds[-1] - gts[-1]).max())}
    (outputs / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"[done] best val relL2={best:.4f}, rollout final max err={metrics['rollout_final_err_max']:.3f}")


if __name__ == "__main__":
    main()
