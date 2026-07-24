"""
Conv1D AE を正常データのみで学習し、キャリブレーションセットの 99 分位で閾値を決める.

閾値決定には X_cal (generate_data.py で分離された専用セット) のみを使用する。
テストセットは evaluate.py による最終評価に 1 回だけ使用する。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info() -> tuple[str, bool]:
    """Return (commit_sha, is_dirty). Falls back to 'unknown' on error."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
        ).decode().strip()
        return commit, bool(status)
    except Exception:
        return "unknown", False


def _collect_provenance(args: argparse.Namespace, data: np.lib.npyio.NpzFile,
                        seq_len: int) -> dict:
    import scipy
    import sklearn
    git_commit, git_dirty = _git_info()
    try:
        import torch as _torch
        cuda_ver = _torch.version.cuda or "n/a"
    except Exception:
        cuda_ver = "n/a"

    gen_params: dict = {
        "sample_len": seq_len,
        "fs": float(data.get("fs", 5000.0)),
    }
    for key in ("seed", "n_normal", "n_anomaly", "n_cal", "n_val_es"):
        val = data.get(key)
        if val is not None:
            gen_params[key] = int(val)

    return {
        "schema_version": 1,
        "data_sha256": _sha256_file(args.data),
        "fs": float(data.get("fs", 5000.0)),
        "generator_params": gen_params,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "python": sys.version,
        "torch": str(torch.__version__),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "platform": platform.platform(),
        "torch_cuda": cuda_ver,
    }


def _bootstrap_p99_ci(samples: np.ndarray, n_resamples: int = 1000,
                       alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """95% bootstrap CI for the 99th percentile."""
    rng = np.random.default_rng(seed)
    qs = [float(np.quantile(rng.choice(samples, size=len(samples), replace=True), 0.99))
          for _ in range(n_resamples)]
    return float(np.percentile(qs, 100 * alpha / 2)), float(np.percentile(qs, 100 * (1 - alpha / 2)))


def _validate_data(X_train: np.ndarray, X_val: np.ndarray, X_cal: np.ndarray,
                   seq_len: int, batch_size: int, epochs: int) -> None:
    """Raise ValueError/RuntimeError with descriptive messages on invalid inputs."""
    for name, arr in [("X_train", X_train), ("X_val", X_val), ("X_cal", X_cal)]:
        if arr.ndim != 2:
            raise ValueError(f"{name} must be 2-D, got shape {arr.shape}")
        if arr.shape[0] == 0:
            raise ValueError(f"{name} is empty (0 windows)")
        if arr.shape[1] != seq_len:
            raise ValueError(
                f"{name} has seq_len={arr.shape[1]}, expected {seq_len} from NPZ sample_len"
            )
        t = torch.from_numpy(arr)
        if not torch.isfinite(t).all():
            raise ValueError(f"{name} contains NaN or Inf values")
        if float(arr.std()) < 1e-8:
            raise ValueError(f"{name} has near-zero standard deviation (constant signal?)")
    if seq_len % 8 != 0:
        raise ValueError(
            f"seq_len={seq_len} is not divisible by 8. "
            "The Conv1D AE encoder uses 3× MaxPool1d(2), requiring seq_len % 8 == 0."
        )
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")
    if epochs <= 0:
        raise ValueError(f"epochs must be > 0, got {epochs}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train Conv1D AE on normal-only data. "
                    "Threshold is set on the calibration set (X_cal), not the test set."
    )
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument(
        "--epochs", type=int, default=30,
        help="Number of training epochs [1, 200]. Use --allow-long-run for > 100.",
    )
    p.add_argument(
        "--allow-long-run", action="store_true",
        help="Required when --epochs > 100 to prevent accidental long runs.",
    )
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--latent-dim", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Epochs bounds guard (MED 9)
    if args.epochs < 1 or args.epochs > 200:
        raise ValueError(f"--epochs must be in [1, 200], got {args.epochs}")
    if args.epochs > 100 and not args.allow_long_run:
        raise SystemExit(
            f"--epochs {args.epochs} > 100. Pass --allow-long-run to confirm "
            "you intend a long training run."
        )
    est_min = args.epochs * 2 / 60
    print(f"[train] epochs={args.epochs}  estimated runtime ≈ {est_min:.0f} min "
          "(~2 sec/epoch on CPU)")

    # CUDA determinism (MED 7)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    det_active = torch.are_deterministic_algorithms_enabled()

    if args.device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))
    set_seed(args.seed)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)

    data = np.load(args.data)
    X_train = data["X_train"].astype(np.float32)
    X_val   = data["X_val"].astype(np.float32)   # early-stopping validation only
    seq_len = int(data["sample_len"])

    # Calibration set for threshold determination (separate from val / test)
    if "X_cal" in data:
        X_cal = data["X_cal"].astype(np.float32)
        print("[data] using X_cal from NPZ for threshold calibration")
    else:
        # Graceful fallback for NPZ files generated before the calibration-split update
        X_cal = X_val
        print("[data] WARNING: X_cal not found in NPZ — falling back to X_val for "
              "threshold calibration. Re-run generate_data.py to get a proper "
              "calibration set.")

    # Data validation (MED 8)
    _validate_data(X_train, X_val, X_cal, seq_len, args.batch_size, args.epochs)

    print(f"[data] train={X_train.shape}  val_es={X_val.shape}  "
          f"cal={X_cal.shape}  seq_len={seq_len}")

    # 正規化: train セットのグローバル mean/std
    mu    = float(X_train.mean())
    sigma = float(X_train.std() + 1e-8)
    X_train_n = (X_train - mu) / sigma
    X_val_n   = (X_val   - mu) / sigma
    X_cal_n   = (X_cal   - mu) / sigma

    tr_tensor  = torch.from_numpy(X_train_n).unsqueeze(1)  # (N, 1, L)
    val_tensor = torch.from_numpy(X_val_n).unsqueeze(1)
    cal_tensor = torch.from_numpy(X_cal_n).unsqueeze(1)

    tr_loader = DataLoader(
        TensorDataset(tr_tensor), batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        TensorDataset(val_tensor), batch_size=args.batch_size, shuffle=False, num_workers=0
    )
    cal_loader = DataLoader(
        TensorDataset(cal_tensor), batch_size=args.batch_size, shuffle=False, num_workers=0
    )

    model = Conv1DAE(latent_dim=args.latent_dim, seq_len=seq_len).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[model] Conv1D AE latent={args.latent_dim}: {n_params:,} params")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()

    best_val = float("inf")
    history  = {"train": [], "val": []}
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
            # Save placeholder checkpoint (provenance added after training)
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
        print(f"[epoch {epoch:3d}/{args.epochs}] train_mse={tr_loss:.5f}  "
              f"val_mse={val_loss:.5f}{marker}")

    # Threshold on calibration set (not val, not test) — MED 15 / HIGH 3
    ck = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ck["model_state_dict"])
    model.eval()
    cal_errors = []
    with torch.no_grad():
        for (xb,) in cal_loader:
            xb = xb.to(device)
            xr = model(xb)
            err = ((xr - xb) ** 2).mean(dim=(1, 2)).cpu().numpy()
            cal_errors.extend(err.tolist())
    cal_errors_arr = np.array(cal_errors)
    thr = float(np.quantile(cal_errors_arr, 0.99))
    ci_lo, ci_hi = _bootstrap_p99_ci(cal_errors_arr, n_resamples=1000)
    print(f"[threshold] cal MSE p99 = {thr:.6f}  "
          f"95% CI [{ci_lo:.6f}, {ci_hi:.6f}]  "
          f"(cal_n={len(cal_errors_arr)}, "
          f"min={cal_errors_arr.min():.6f}, max={cal_errors_arr.max():.6f})")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.plot(history["train"], label="train")
    plt.plot(history["val"], label="val (early-stop)")
    plt.xlabel("epoch")
    plt.ylabel("MSE")
    plt.title("Conv1D AE — reconstruction MSE")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "loss_curve.png", dpi=120)
    plt.close()

    # Full checkpoint provenance (HIGH 6)
    provenance = _collect_provenance(args, data, seq_len)
    provenance["deterministic_algorithms_enabled"] = det_active  # MED 7

    final_ckpt = {
        **ck,
        "threshold": thr,
        "calibration_set_size": len(cal_errors_arr),
        "p99_threshold_ci": [round(ci_lo, 8), round(ci_hi, 8)],
        **provenance,
    }
    torch.save(final_ckpt, ckpt_path)

    with (out_dir / "train_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "best_val_mse": round(best_val, 6),
                "threshold_p99": round(thr, 6),
                "p99_threshold_ci_95": [round(ci_lo, 8), round(ci_hi, 8)],
                "calibration_set_size": len(cal_errors_arr),
                "mu": round(mu, 6),
                "sigma": round(sigma, 6),
                "epochs": args.epochs,
                "latent_dim": args.latent_dim,
                "seed": args.seed,
                "params": n_params,
                "deterministic_algorithms_enabled": det_active,
                "data_sha256": provenance["data_sha256"],
            },
            f,
            indent=2,
        )
    print(f"[train] saved → {ckpt_path}, {out_dir}/loss_curve.png, train_metrics.json")


if __name__ == "__main__":
    main()
