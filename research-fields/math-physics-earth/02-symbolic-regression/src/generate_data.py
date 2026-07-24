"""合成観測データを生成: y = x0 * sin(x1) + x0**2 + noise."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import numpy as np

# TARGET_FORMULA is embedded here so provenance can be recorded in metrics.json.
TARGET_FORMULA = "x0 * sin(x1) + x0**2 + noise"


def _positive_float(value: str) -> float:
    """argparse type: finite float >= 0."""
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a number, got {value!r}")
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be finite, got {value!r}")
    if v < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {v}")
    return v


def _positive_int(value: str) -> int:
    """argparse type: int in [50, 100000]."""
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value!r}")
    if not (50 <= v <= 100_000):
        raise argparse.ArgumentTypeError(f"must be in [50, 100000], got {v}")
    return v


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate synthetic observations for symbolic regression."
    )
    p.add_argument("--out", type=Path, default=Path("data/obs.npz"))
    p.add_argument("--n", type=_positive_int, default=200,
                   help="Number of samples [50, 100000] (default: 200)")
    p.add_argument("--noise", type=_positive_float, default=0.1,
                   help="Noise std-dev, finite >= 0 (default: 0.1)")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def true_fn(x0: np.ndarray, x1: np.ndarray) -> np.ndarray:
    """Target: x0 * sin(x1) + x0**2  (recoverable by gplearn with default settings)."""
    return x0 * np.sin(x1) + x0 ** 2


def main():
    a = parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    X = rng.uniform(-3.0, 3.0, size=(a.n, 2)).astype(np.float64)
    y_clean = true_fn(X[:, 0], X[:, 1])
    noise_arr = rng.normal(0.0, a.noise, size=a.n).astype(np.float64)
    y = y_clean + noise_arr

    # Sanity assertions
    assert X.dtype == np.float64, "X must be float64"
    assert y.dtype == np.float64, "y must be float64"
    assert X.shape[0] == y.shape[0], "X and y length mismatch"
    assert np.isfinite(X).all(), "X contains NaN or Inf"
    assert np.isfinite(y).all(), "y contains NaN or Inf"

    np.savez_compressed(
        a.out,
        X=X, y=y, y_clean=y_clean,
        seed=np.int64(a.seed),
        noise=np.float64(a.noise),
        target_formula=TARGET_FORMULA,
    )
    print(
        f"[gen] saved → {a.out}  X={X.shape}  "
        f"y range=[{y.min():.2f}, {y.max():.2f}]  "
        f"target={TARGET_FORMULA}"
    )


if __name__ == "__main__":
    main()
