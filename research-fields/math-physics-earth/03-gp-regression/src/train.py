"""
Gaussian Process 回帰: 周期信号 + トレンド + ノイズ を fit し、
未観測領域も含めて予測平均・潜在関数 95% 区間・観測値 95% 区間を可視化する.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel, DotProduct, ExpSineSquared, Sum, WhiteKernel
)
from sklearn.metrics import mean_squared_error

# _argtypes is in the same src/ directory
sys.path.insert(0, str(Path(__file__).parent))
from _argtypes import bounded_int, bounded_float, finite_float  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


def true_fn(t: np.ndarray) -> np.ndarray:
    """Ground truth: 5 単位周期 + 弱いトレンド."""
    return np.sin(2 * np.pi * t / 5.0) + 0.1 * t


def extract_signal_kernel(kernel):
    """Return (signal_kernel, noise_level) with WhiteKernel stripped out (HIGH-1)."""
    if isinstance(kernel, WhiteKernel):
        return None, float(kernel.noise_level)
    if isinstance(kernel, Sum):
        lk, ln = extract_signal_kernel(kernel.k1)
        rk, rn = extract_signal_kernel(kernel.k2)
        noise = ln + rn
        if lk is None and rk is None:
            return None, noise
        if lk is None:
            return rk, noise
        if rk is None:
            return lk, noise
        return Sum(lk, rk), noise
    return kernel, 0.0


def get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def parse_args():
    p = argparse.ArgumentParser(
        description="GP regression quickstart — periodic + linear-trend toy signal"
    )
    # HIGH-3: validated argument types
    p.add_argument("--n-obs", type=bounded_int(10, 100_000), default=30,
                   metavar="N", help="observation count [10, 100000]")
    p.add_argument("--noise", type=finite_float(lo=0.0), default=0.15,
                   metavar="SIGMA", help="observation noise σ (finite, >= 0)")
    p.add_argument("--n-pred", type=bounded_int(10, 100_000), default=200,
                   metavar="N", help="prediction grid points [10, 100000]")
    p.add_argument("--t-min", type=finite_float(), default=0.0,
                   metavar="T", help="observation range lower bound (finite)")
    p.add_argument("--t-max", type=finite_float(), default=20.0,
                   metavar="T", help="observation range upper bound (finite)")
    p.add_argument("--seed", type=bounded_int(0, 2**32 - 1), default=42,
                   metavar="N", help="random seed [0, 4294967295]")
    # HIGH-2: extrapolation horizon
    p.add_argument("--extrap-horizon", type=finite_float(lo=0.0), default=5.0,
                   metavar="DT",
                   help="extrapolation window added to t_max (default 5.0). "
                        "For periodic kernels, uncertainty may NOT widen monotonically.")
    # MED-9: optimizer init / restarts
    p.add_argument("--init-period", type=finite_float(lo=0.1), default=3.0,
                   metavar="P",
                   help="initial periodicity for optimizer (default 3.0; true=5.0)")
    p.add_argument("--n-restarts", type=bounded_int(1, 100), default=8,
                   metavar="N", help="optimizer restarts for hyperparameter search")
    # MED-8: numerical stability
    p.add_argument("--jitter", type=bounded_float(0.0, 1e-2), default=1e-8,
                   metavar="EPS",
                   help="GP alpha (diagonal jitter) for numerical stability [0, 1e-2]")
    a = p.parse_args()
    # HIGH-3: post-parse cross-arg validation
    if a.t_min >= a.t_max:
        p.error(f"--t-min ({a.t_min}) must be strictly less than --t-max ({a.t_max})")
    return a


def main():
    a = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    # 観測データ
    t_obs = np.sort(rng.uniform(a.t_min, a.t_max, size=a.n_obs))
    y_true_obs = true_fn(t_obs)
    y_obs = y_true_obs + rng.normal(0.0, a.noise, size=a.n_obs)

    # 予測グリッド (外挿 extrap_horizon 分追加; HIGH-2)
    t_pred = np.linspace(a.t_min, a.t_max + a.extrap_horizon, a.n_pred)

    # ------------------------------------------------------------------ #
    # Kernel: 周期成分 (ExpSineSquared) +                                 #
    #         線形トレンド (DotProduct; MED-6: RBF は平均回帰的なので不可) +  #
    #         観測ノイズ (WhiteKernel)                                     #
    # MED-9: init_period=3.0 (true=5.0) でオプティマイザに発見させる         #
    # ------------------------------------------------------------------ #
    kernel = (
        ConstantKernel(1.0, (1e-2, 1e2))
        * ExpSineSquared(
            length_scale=1.0,
            periodicity=a.init_period,
            length_scale_bounds=(0.1, 10.0),
            periodicity_bounds=(1.0, 20.0),
        )
        + ConstantKernel(0.1, (1e-3, 1e1))
        * DotProduct(sigma_0=0.0, sigma_0_bounds="fixed")
        + WhiteKernel(noise_level=a.noise ** 2, noise_level_bounds=(1e-5, 1.0))
    )

    # MED-8: alpha=jitter で数値安定性; MED-9: n_restarts_optimizer=n_restarts
    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=a.n_restarts,
        normalize_y=True,
        alpha=a.jitter,
        random_state=a.seed,
    )
    print(f"[fit] observations={a.n_obs}  init_period={a.init_period}  restarts={a.n_restarts}")
    print(f"      initial kernel: {kernel}")
    gp.fit(t_obs.reshape(-1, 1), y_obs)
    print(f"[fit] optimized kernel: {gp.kernel_}")
    print(f"[fit] log-marginal-likelihood = {gp.log_marginal_likelihood_value_:.4f}")

    # ------------------------------------------------------------------ #
    # 数値安定性チェック (MED-8)                                            #
    # ------------------------------------------------------------------ #
    try:
        K_stab = gp.L_ @ gp.L_.T
        cond_num = float(np.linalg.cond(K_stab))
        print(f"[stability] condition number = {cond_num:.3e}")
        if cond_num > 1e14:
            raise RuntimeError(
                f"GP kernel matrix near-singular (cond={cond_num:.2e}). "
                "Increase --jitter or reduce --n-obs."
            )
        if cond_num > 1e10:
            warnings.warn(
                f"GP kernel matrix ill-conditioned (cond={cond_num:.2e}). "
                "Consider increasing --jitter.",
                RuntimeWarning,
                stacklevel=2,
            )
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(
            "Failed to compute condition number — kernel matrix may be singular. "
            "Increase --jitter."
        ) from exc

    # ------------------------------------------------------------------ #
    # 予測: 観測バンド (observation) + 潜在バンド (latent; HIGH-1)          #
    # ------------------------------------------------------------------ #
    y_mean, y_std_obs = gp.predict(t_pred.reshape(-1, 1), return_std=True)

    # HIGH-3: 有限チェック
    if not (np.all(np.isfinite(y_mean)) and np.all(np.isfinite(y_std_obs))):
        raise RuntimeError(
            "GP predictions contain non-finite values. "
            "Check inputs or increase --jitter."
        )

    # 潜在関数バンド: WhiteKernel を除いた signal-only kernel で再 fit (optimizer=None)
    signal_kernel, white_noise_level = extract_signal_kernel(gp.kernel_)
    if signal_kernel is not None:
        gp_latent = GaussianProcessRegressor(
            kernel=signal_kernel,
            alpha=white_noise_level + a.jitter,
            normalize_y=True,
            optimizer=None,
            random_state=a.seed,
        )
        gp_latent.fit(t_obs.reshape(-1, 1), y_obs)
        _, y_std_latent = gp_latent.predict(t_pred.reshape(-1, 1), return_std=True)
    else:
        y_std_latent = y_std_obs

    # ------------------------------------------------------------------ #
    # 評価: グリッド RMSE (内挿 / 外挿)                                    #
    # ------------------------------------------------------------------ #
    y_true_grid = true_fn(t_pred)
    mask_interp = t_pred <= a.t_max
    rmse_interp = float(
        np.sqrt(mean_squared_error(y_true_grid[mask_interp], y_mean[mask_interp]))
    )
    has_extrap = mask_interp.sum() < len(t_pred)
    rmse_extrap = (
        float(np.sqrt(mean_squared_error(y_true_grid[~mask_interp], y_mean[~mask_interp])))
        if has_extrap
        else None
    )
    print(f"[eval] RMSE (interpolation region) = {rmse_interp:.4f}")
    if rmse_extrap is not None:
        print(f"[eval] RMSE (extrapolation t>{a.t_max:.1f}) = {rmse_extrap:.4f}")

    # ------------------------------------------------------------------ #
    # Temporal holdout: 最後の 20% をテストセット (MED-7)                  #
    # ------------------------------------------------------------------ #
    holdout_n = max(1, int(0.2 * a.n_obs))
    t_train_h, t_test_h = t_obs[:-holdout_n], t_obs[-holdout_n:]
    y_train_h, y_test_h = y_obs[:-holdout_n], y_obs[-holdout_n:]

    gp_holdout = GaussianProcessRegressor(
        kernel=gp.kernel_,
        alpha=a.jitter,
        normalize_y=True,
        optimizer=None,
        random_state=a.seed,
    )
    gp_holdout.fit(t_train_h.reshape(-1, 1), y_train_h)
    y_pred_h, y_std_h = gp_holdout.predict(t_test_h.reshape(-1, 1), return_std=True)

    rmse_holdout = float(np.sqrt(mean_squared_error(y_test_h, y_pred_h)))
    # Log predictive density (Gaussian)
    lpd = float(np.mean(
        -0.5 * ((y_test_h - y_pred_h) / y_std_h) ** 2
        - np.log(y_std_h)
        - 0.5 * np.log(2 * np.pi)
    ))
    lower_h, upper_h = y_pred_h - 1.96 * y_std_h, y_pred_h + 1.96 * y_std_h
    coverage_h = float(np.mean((y_test_h >= lower_h) & (y_test_h <= upper_h)))

    print(f"[eval] Temporal holdout RMSE (last {holdout_n} pts) = {rmse_holdout:.4f}")
    print(f"[eval] Holdout log-predictive density = {lpd:.4f}")
    print(f"[eval] Holdout 95% coverage = {coverage_h:.3f}")

    # MED-9: 最適化済み周期を抽出してレポート
    optimized_period = None
    for pname, pval in gp.kernel_.get_params().items():
        if "periodicity" in pname and "bounds" not in pname:
            optimized_period = float(pval)
            break
    if optimized_period is not None:
        print(f"[fit] optimized_period = {optimized_period:.4f}  (init={a.init_period}, true=5.0)")

    # ------------------------------------------------------------------ #
    # プロット: gp_fit.png (HIGH-1: 2バンド表示)                           #
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t_pred, y_true_grid, "k-", alpha=0.5, label="true function")
    ax.plot(t_pred, y_mean, "b-", label="GP mean")
    # 観測値 95% 予測区間 (WhiteKernel を含む; 新しいノイズ観測に対する区間)
    ax.fill_between(
        t_pred,
        y_mean - 1.96 * y_std_obs,
        y_mean + 1.96 * y_std_obs,
        color="blue", alpha=0.12,
        label="95% pred. interval — new noisy obs. (plug-in MLE)",
    )
    # 潜在関数 95% 区間 (WhiteKernel を除く)
    ax.fill_between(
        t_pred,
        y_mean - 1.96 * y_std_latent,
        y_mean + 1.96 * y_std_latent,
        color="cyan", alpha=0.30,
        label="95% pred. interval — latent f (signal only)",
    )
    ax.errorbar(
        t_obs, y_obs, yerr=a.noise, fmt="o", color="red", markersize=4,
        label=f"observations (n={a.n_obs})", capsize=2,
    )
    ax.axvline(a.t_max, color="gray", linestyle=":", label="extrapolation boundary")
    ax.set_xlabel("t")
    ax.set_ylabel("y")
    ax.set_title(
        f"GP regression  |  interp RMSE={rmse_interp:.3f}"
        f"  holdout RMSE={rmse_holdout:.3f}"
    )
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "gp_fit.png", dpi=120)
    plt.close()

    # ------------------------------------------------------------------ #
    # プロット: residuals.png — in-sample (参考) + holdout (MED-7)        #
    # ------------------------------------------------------------------ #
    y_mean_obs, y_std_at_obs = gp.predict(t_obs.reshape(-1, 1), return_std=True)
    residuals_insample = y_obs - y_mean_obs

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))

    ax = axes[0]
    ax.errorbar(t_obs, residuals_insample, yerr=1.96 * y_std_at_obs,
                fmt="o", capsize=2, color="steelblue")
    ax.axhline(0.0, color="black", alpha=0.5)
    ax.set_xlabel("t")
    ax.set_ylabel("residual (y_obs − GP mean)")
    ax.set_title("In-sample residuals\n(fitted pts — misleadingly small; see holdout)")
    ax.grid(alpha=0.3)

    ax = axes[1]
    holdout_res = y_test_h - y_pred_h
    ax.errorbar(t_test_h, holdout_res, yerr=1.96 * y_std_h,
                fmt="s", capsize=2, color="darkorange")
    ax.axhline(0.0, color="black", alpha=0.5)
    ax.set_xlabel("t")
    ax.set_ylabel("residual (y_obs − GP mean)")
    ax.set_title(
        f"Temporal holdout residuals (last {holdout_n} pts)\n"
        f"coverage={coverage_h:.2f}  LPD={lpd:.3f}"
    )
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "residuals.png", dpi=120)
    plt.close()

    # ------------------------------------------------------------------ #
    # metrics.json (HIGH-3: allow_nan=False; HIGH-4: provenance)         #
    # ------------------------------------------------------------------ #
    train_py_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    metrics: dict = {
        "versions": {
            "python": sys.version,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "cli_args": vars(a),
        "generator_params": {
            "true_fn": "sin(2*pi*t/5) + 0.1*t",
            "t_min": a.t_min,
            "t_max": a.t_max,
            "n_obs": a.n_obs,
            "noise_sigma": a.noise,
            "seed": a.seed,
        },
        "n_obs": a.n_obs,
        "noise_true": a.noise,
        "rmse_interp": round(rmse_interp, 4),
        "rmse_extrap": round(rmse_extrap, 4) if rmse_extrap is not None else None,
        "log_marginal_likelihood": float(gp.log_marginal_likelihood_value_),
        "optimized_kernel": str(gp.kernel_),
        "optimized_period": round(optimized_period, 4) if optimized_period else None,
        "holdout_n": holdout_n,
        "holdout_rmse": round(rmse_holdout, 4),
        "holdout_log_predictive_density": round(lpd, 4),
        "holdout_95pct_coverage": round(coverage_h, 4),
        "seed": a.seed,
        "jitter": a.jitter,
        "condition_number": cond_num,
        "git_sha": get_git_sha(),
        "train_py_sha256": train_py_sha256,
    }
    with (OUT_DIR / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, allow_nan=False)

    print(f"[train] saved → {OUT_DIR}/gp_fit.png, residuals.png, metrics.json")


if __name__ == "__main__":
    main()
