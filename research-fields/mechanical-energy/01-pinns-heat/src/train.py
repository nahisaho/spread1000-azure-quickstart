"""
1D 熱伝導方程式 u_t = alpha u_xx を PINN で解く.

- 座標入力 (x, t) → スカラー u の MLP (tanh activations)
- 損失 = PDE 残差 (autograd で u_xx, u_t 計算) + IC + BC
- 学習: Adam 2500 epoch + L-BFGS 500 epoch
- 評価: 解析解 u = exp(-pi^2 alpha t) sin(pi x) との L2 相対誤差
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"

ALPHA = 0.05  # 熱拡散係数


class PINN(nn.Module):
    """MLP: (x, t) -> u.  4 hidden layers of width 32, tanh activation."""

    def __init__(self, hidden: int = 32, depth: int = 4):
        super().__init__()
        layers: list[nn.Module] = []
        in_dim = 2
        for _ in range(depth):
            layers.append(nn.Linear(in_dim, hidden))
            layers.append(nn.Tanh())
            in_dim = hidden
        layers.append(nn.Linear(hidden, 1))
        self.net = nn.Sequential(*layers)
        # Xavier init は tanh MLP に相性が良い
        for m in self.net:
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([x, t], dim=-1))


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def compute_pde_residual(
    model: PINN, x: torch.Tensor, t: torch.Tensor, alpha: float
) -> torch.Tensor:
    """r = u_t - alpha * u_xx via double autograd."""
    x = x.clone().requires_grad_(True)
    t = t.clone().requires_grad_(True)
    u = model(x, t)
    grad_u = torch.autograd.grad(
        u, [x, t], grad_outputs=torch.ones_like(u), create_graph=True
    )
    u_x, u_t = grad_u[0], grad_u[1]
    u_xx = torch.autograd.grad(
        u_x, x, grad_outputs=torch.ones_like(u_x), create_graph=True
    )[0]
    return u_t - alpha * u_xx


def sample_points(n_pde: int, n_ic: int, n_bc: int, device: torch.device):
    """Latin-hypercube 風の一様サンプリング (簡易版で一様乱数を使用)."""
    x_pde = torch.rand(n_pde, 1, device=device)
    t_pde = torch.rand(n_pde, 1, device=device)

    x_ic = torch.rand(n_ic, 1, device=device)
    t_ic = torch.zeros_like(x_ic)
    u_ic_true = torch.sin(math.pi * x_ic)

    t_bc = torch.rand(n_bc, 1, device=device)
    x_bc_left = torch.zeros_like(t_bc)
    x_bc_right = torch.ones_like(t_bc)

    return {
        "x_pde": x_pde,
        "t_pde": t_pde,
        "x_ic": x_ic,
        "t_ic": t_ic,
        "u_ic_true": u_ic_true,
        "t_bc": t_bc,
        "x_bc_left": x_bc_left,
        "x_bc_right": x_bc_right,
    }


def analytic_solution(x: torch.Tensor, t: torch.Tensor, alpha: float) -> torch.Tensor:
    return torch.exp(-(math.pi**2) * alpha * t) * torch.sin(math.pi * x)


def evaluate_l2(model: PINN, alpha: float, device: torch.device) -> float:
    """Test grid 200 x 200 で解析解との相対 L2 誤差を計算 (percentage)."""
    model.eval()
    xs = torch.linspace(0, 1, 200, device=device)
    ts = torch.linspace(0, 1, 200, device=device)
    xx, tt = torch.meshgrid(xs, ts, indexing="ij")
    x_flat = xx.reshape(-1, 1)
    t_flat = tt.reshape(-1, 1)
    with torch.no_grad():
        u_pred = model(x_flat, t_flat).cpu().numpy().reshape(200, 200)
    u_true = analytic_solution(x_flat, t_flat, alpha).cpu().numpy().reshape(200, 200)
    err = np.sqrt(np.mean((u_pred - u_true) ** 2)) / np.sqrt(np.mean(u_true**2))
    return float(err * 100.0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--epochs", type=int, default=3000, help="Adam epochs (L-BFGS が +500 追加)")
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--n-pde", type=int, default=5000)
    p.add_argument("--n-ic", type=int, default=200)
    p.add_argument("--n-bc", type=int, default=200)
    p.add_argument("--w-ic", type=float, default=10.0, help="IC 損失重み")
    p.add_argument("--w-bc", type=float, default=10.0, help="BC 損失重み")
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
    model = PINN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] PINN MLP: {n_params:,} params")

    pts = sample_points(args.n_pde, args.n_ic, args.n_bc, device)
    print(f"[data] collocation: PDE={args.n_pde}, IC={args.n_ic}, BC={args.n_bc}")

    mse = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    def total_loss() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        r = compute_pde_residual(model, pts["x_pde"], pts["t_pde"], ALPHA)
        l_pde = mse(r, torch.zeros_like(r))
        u_ic_pred = model(pts["x_ic"], pts["t_ic"])
        l_ic = mse(u_ic_pred, pts["u_ic_true"])
        u_bc_l = model(pts["x_bc_left"], pts["t_bc"])
        u_bc_r = model(pts["x_bc_right"], pts["t_bc"])
        l_bc = mse(u_bc_l, torch.zeros_like(u_bc_l)) + mse(u_bc_r, torch.zeros_like(u_bc_r))
        return l_pde + args.w_ic * l_ic + args.w_bc * l_bc, l_pde, l_ic, l_bc

    history = {"total": [], "pde": [], "ic": [], "bc": [], "l2_percent": []}

    print("[train] phase 1: Adam")
    for epoch in range(1, args.epochs + 1):
        optimizer.zero_grad()
        loss, l_pde, l_ic, l_bc = total_loss()
        loss.backward()
        optimizer.step()
        if epoch % 100 == 0 or epoch == 1:
            l2 = evaluate_l2(model, ALPHA, device)
            history["total"].append(loss.item())
            history["pde"].append(l_pde.item())
            history["ic"].append(l_ic.item())
            history["bc"].append(l_bc.item())
            history["l2_percent"].append(l2)
            print(
                f"[Adam {epoch:5d}/{args.epochs}] "
                f"total={loss.item():.3e}  pde={l_pde.item():.3e}  "
                f"ic={l_ic.item():.3e}  bc={l_bc.item():.3e}  L2={l2:.2f}%"
            )

    # Phase 2: L-BFGS refinement (500 iterations)
    print("[train] phase 2: L-BFGS refinement (max 500 iter)")
    lbfgs = torch.optim.LBFGS(
        model.parameters(),
        lr=1.0,
        max_iter=500,
        history_size=50,
        line_search_fn="strong_wolfe",
        tolerance_grad=1e-8,
        tolerance_change=1e-10,
    )
    iter_counter = [0]

    def closure():
        lbfgs.zero_grad()
        loss, l_pde, l_ic, l_bc = total_loss()
        loss.backward()
        iter_counter[0] += 1
        if iter_counter[0] % 50 == 0:
            l2 = evaluate_l2(model, ALPHA, device)
            print(
                f"[L-BFGS {iter_counter[0]:4d}] total={loss.item():.3e}  L2={l2:.2f}%"
            )
        return loss

    lbfgs.step(closure)

    final_l2 = evaluate_l2(model, ALPHA, device)
    print(f"[train] final L2 relative error = {final_l2:.3f}%")

    # 保存
    ckpt_path = out_dir / "best_model.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "alpha": ALPHA,
            "final_l2_percent": final_l2,
        },
        ckpt_path,
    )

    # 学習曲線
    epochs_x = list(range(1, len(history["total"]) * 100, 100))
    if len(epochs_x) != len(history["total"]):
        epochs_x = [1] + list(range(100, len(history["total"]) * 100, 100))
        epochs_x = epochs_x[: len(history["total"])]
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.semilogy(epochs_x, history["total"], label="total", color="tab:blue")
    ax1.semilogy(epochs_x, history["pde"], label="pde", color="tab:green")
    ax1.semilogy(epochs_x, history["ic"], label="ic", color="tab:orange")
    ax1.semilogy(epochs_x, history["bc"], label="bc", color="tab:red")
    ax1.set_xlabel("Adam epoch")
    ax1.set_ylabel("loss (log)")
    ax1.legend(loc="upper right")
    ax2 = ax1.twinx()
    ax2.plot(epochs_x, history["l2_percent"], label="L2 err (%)", color="tab:purple", linestyle="--")
    ax2.set_ylabel("L2 relative error (%)")
    ax2.legend(loc="upper left")
    plt.title("PINN — 1D heat equation (Adam phase)")
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    # 解の可視化: 3 時刻での u(x, t)
    xs_plot = torch.linspace(0, 1, 200, device=device).reshape(-1, 1)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for ax, t_val in zip(axes, [0.0, 0.25, 0.75]):
        t_plot = torch.full_like(xs_plot, t_val)
        with torch.no_grad():
            u_pred = model(xs_plot, t_plot).cpu().numpy().flatten()
        u_true = analytic_solution(xs_plot, t_plot, ALPHA).cpu().numpy().flatten()
        ax.plot(xs_plot.cpu().numpy().flatten(), u_true, "k-", label="analytic", linewidth=2)
        ax.plot(xs_plot.cpu().numpy().flatten(), u_pred, "r--", label="PINN", linewidth=2)
        ax.set_xlabel("x")
        ax.set_ylabel("u")
        ax.set_title(f"t = {t_val:.2f}")
        ax.legend()
        ax.grid(alpha=0.3)
    plt.suptitle(f"1D heat u_t = {ALPHA} u_xx  —  final L2 = {final_l2:.2f}%")
    plt.tight_layout()
    plt.savefig(out_dir / "solution.png", dpi=120)
    plt.close()

    with (out_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "l2_relative_error_percent": round(final_l2, 4),
                "alpha": ALPHA,
                "adam_epochs": args.epochs,
                "lbfgs_iters": iter_counter[0],
                "n_pde": args.n_pde,
                "n_ic": args.n_ic,
                "n_bc": args.n_bc,
                "seed": args.seed,
                "device": args.device,
                "params": n_params,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"[train] saved → {ckpt_path}, {out_dir}/loss_curve.png, solution.png, metrics.json")


if __name__ == "__main__":
    main()
