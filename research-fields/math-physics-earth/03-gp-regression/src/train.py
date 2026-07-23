"""
Gaussian Process 回帰: 周期信号 + トレンド + ノイズ を fit し、
未観測領域も含めて予測平均と 95% 信頼区間を可視化する.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel, ExpSineSquared, RBF, WhiteKernel
)
from sklearn.metrics import mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def true_fn(t: np.ndarray) -> np.ndarray:
    """Ground truth: 5 単位周期 + 弱いトレンド."""
    return np.sin(2 * np.pi * t / 5.0) + 0.1 * t


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n-obs", type=int, default=30)
    p.add_argument("--noise", type=float, default=0.15)
    p.add_argument("--n-pred", type=int, default=200)
    p.add_argument("--t-min", type=float, default=0.0)
    p.add_argument("--t-max", type=float, default=20.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    a = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    # 観測データ
    t_obs = np.sort(rng.uniform(a.t_min, a.t_max, size=a.n_obs))
    y_true_obs = true_fn(t_obs)
    y_obs = y_true_obs + rng.normal(0.0, a.noise, size=a.n_obs)

    # 予測グリッド
    t_pred = np.linspace(a.t_min, a.t_max + 5.0, a.n_pred)  # 少し外挿

    # Kernel: 周期成分 + トレンドを吸収する RBF + ノイズ
    kernel = (
        ConstantKernel(1.0, (1e-2, 1e2))
        * ExpSineSquared(length_scale=1.0, periodicity=5.0,
                         length_scale_bounds=(0.1, 10.0),
                         periodicity_bounds=(1.0, 20.0))
        + ConstantKernel(0.1, (1e-3, 1e1)) * RBF(length_scale=10.0, length_scale_bounds=(1.0, 50.0))
        + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-3, 1.0))
    )

    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=5,
        normalize_y=True,
        random_state=a.seed,
    )
    print(f"[fit] observations={a.n_obs}  initial kernel:")
    print(f"      {kernel}")
    gp.fit(t_obs.reshape(-1, 1), y_obs)
    print(f"[fit] optimized kernel:")
    print(f"      {gp.kernel_}")
    print(f"[fit] log-marginal-likelihood = {gp.log_marginal_likelihood_value_:.4f}")

    # 予測
    y_mean, y_std = gp.predict(t_pred.reshape(-1, 1), return_std=True)

    # 評価: 観測点 (in-sample) と内挿部分での RMSE
    y_true_grid = true_fn(t_pred)
    mask_interp = t_pred <= a.t_max
    rmse_interp = float(np.sqrt(mean_squared_error(y_true_grid[mask_interp], y_mean[mask_interp])))
    rmse_extrap = float(np.sqrt(mean_squared_error(y_true_grid[~mask_interp], y_mean[~mask_interp])))
    print(f"[eval] RMSE (interpolation region) = {rmse_interp:.4f}")
    print(f"[eval] RMSE (extrapolation region t>{a.t_max}) = {rmse_extrap:.4f}")

    # プロット
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t_pred, y_true_grid, "k-", alpha=0.5, label="true function")
    ax.plot(t_pred, y_mean, "b-", label="GP mean")
    ax.fill_between(t_pred, y_mean - 1.96 * y_std, y_mean + 1.96 * y_std,
                    color="blue", alpha=0.2, label="95% CI")
    ax.errorbar(t_obs, y_obs, yerr=a.noise, fmt="o", color="red", markersize=4,
                label=f"observations (n={a.n_obs})", capsize=2)
    ax.axvline(a.t_max, color="gray", linestyle=":", label="extrapolation boundary")
    ax.set_xlabel("t"); ax.set_ylabel("y")
    ax.set_title(f"GP regression  |  interp RMSE = {rmse_interp:.3f}")
    ax.legend(loc="upper left"); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "gp_fit.png", dpi=120); plt.close()

    # 残差
    y_mean_at_obs, y_std_at_obs = gp.predict(t_obs.reshape(-1, 1), return_std=True)
    residuals = y_obs - y_mean_at_obs
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.errorbar(t_obs, residuals, yerr=1.96 * y_std_at_obs, fmt="o", capsize=2)
    ax.axhline(0.0, color="black", alpha=0.5)
    ax.set_xlabel("t"); ax.set_ylabel("residual (y_obs - GP mean)")
    ax.set_title("Residuals with 95% predictive interval")
    ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(OUT_DIR / "residuals.png", dpi=120); plt.close()

    with (OUT_DIR / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump({
            "n_obs": a.n_obs,
            "noise_true": a.noise,
            "rmse_interp": round(rmse_interp, 4),
            "rmse_extrap": round(rmse_extrap, 4),
            "log_marginal_likelihood": float(gp.log_marginal_likelihood_value_),
            "optimized_kernel": str(gp.kernel_),
            "seed": a.seed,
        }, f, indent=2)
    print(f"[train] saved → {OUT_DIR}/gp_fit.png, residuals.png, metrics.json")


if __name__ == "__main__":
    main()
