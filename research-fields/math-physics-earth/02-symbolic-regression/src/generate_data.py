"""合成観測データを生成: y = 2 x0 sin(x1) + 0.5 x0^2 + noise."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/obs.npz"))
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--noise", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def true_fn(x0: np.ndarray, x1: np.ndarray) -> np.ndarray:
    return 2.0 * x0 * np.sin(x1) + 0.5 * x0 ** 2


def main():
    a = parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    X = rng.uniform(-3.0, 3.0, size=(a.n, 2)).astype(np.float32)
    y_clean = true_fn(X[:, 0], X[:, 1])
    y = y_clean + rng.normal(0.0, a.noise, size=a.n).astype(np.float32)
    np.savez_compressed(a.out, X=X.astype(np.float32), y=y.astype(np.float32),
                        y_clean=y_clean.astype(np.float32), seed=a.seed)
    print(f"[gen] saved → {a.out}  X={X.shape}  y range=[{y.min():.2f}, {y.max():.2f}]")


if __name__ == "__main__":
    main()
