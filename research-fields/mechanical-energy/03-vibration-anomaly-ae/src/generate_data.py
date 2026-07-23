"""
合成振動波形データを生成する.

正常: 2 成分正弦波 + Gaussian ノイズ
異常: 正常 + 周期的インパルス欠陥 (ベアリング欠陥模擬)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

SAMPLE_LEN = 2048
FS = 5000.0  # sampling rate Hz


def gen_normal(n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(SAMPLE_LEN) / FS
    out = np.zeros((n, SAMPLE_LEN), dtype=np.float32)
    for i in range(n):
        f1 = rng.uniform(30.0, 60.0)
        f2 = rng.uniform(90.0, 180.0)
        phi1 = rng.uniform(0, 2 * np.pi)
        phi2 = rng.uniform(0, 2 * np.pi)
        sig = np.sin(2 * np.pi * f1 * t + phi1) + 0.5 * np.sin(2 * np.pi * f2 * t + phi2)
        sig += rng.normal(0.0, 0.05, size=SAMPLE_LEN)
        out[i] = sig.astype(np.float32)
    return out


def gen_anomaly(n: int, rng: np.random.Generator) -> np.ndarray:
    base = gen_normal(n, rng)
    for i in range(n):
        period = rng.integers(100, 301)   # 欠陥のインパルス間隔
        offset = rng.integers(0, period)
        amp = rng.uniform(0.8, 1.5)
        # 幅 3 のインパルス列
        for pos in range(offset, SAMPLE_LEN - 3, period):
            base[i, pos:pos + 3] += amp * np.array([0.5, 1.0, 0.5], dtype=np.float32)
    return base


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/vibration.npz"))
    p.add_argument("--n-normal", type=int, default=1000)
    p.add_argument("--n-anomaly", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    print(f"[gen] generating {args.n_normal} normal + {args.n_anomaly} anomaly windows")
    normal = gen_normal(args.n_normal, rng)
    anomaly = gen_anomaly(args.n_anomaly, rng)

    # 分割:
    #   train (AE 学習用, 正常のみ):    n_normal * 0.64
    #   val   (閾値決定, 正常のみ):     n_normal * 0.16
    #   test  (評価, 正常 + 異常):      残り正常 + 全異常
    idx = rng.permutation(args.n_normal)
    n_tr = int(args.n_normal * 0.64)
    n_val = int(args.n_normal * 0.16)
    tr_idx = idx[:n_tr]
    val_idx = idx[n_tr:n_tr + n_val]
    te_idx = idx[n_tr + n_val:]

    X_train = normal[tr_idx]
    X_val = normal[val_idx]
    X_test_normal = normal[te_idx]
    X_test = np.concatenate([X_test_normal, anomaly], axis=0)
    y_test = np.concatenate(
        [np.zeros(len(X_test_normal), dtype=np.int64),
         np.ones(len(anomaly), dtype=np.int64)],
        axis=0,
    )
    # test をシャッフル
    perm = rng.permutation(len(X_test))
    X_test = X_test[perm]
    y_test = y_test[perm]

    np.savez_compressed(
        args.out,
        X_train=X_train, X_val=X_val,
        X_test=X_test, y_test=y_test,
        fs=FS, sample_len=SAMPLE_LEN, seed=args.seed,
    )
    print(f"[gen] saved → {args.out}")
    print(f"       train={X_train.shape}  val={X_val.shape}  test={X_test.shape}  "
          f"anomaly_rate={y_test.mean():.2%}")


if __name__ == "__main__":
    main()
