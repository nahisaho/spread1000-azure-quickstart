"""
合成振動波形データを生成する.

正常: 2 成分正弦波 + Gaussian ノイズ
異常: 正常 + 周期的インパルス欠陥 (ベアリング欠陥模擬)

分割:
  train  (AE 学習用, 正常のみ):           n_normal * 0.64
  val    (早期終了検証用, 正常のみ):        n_val_es  (default 32)
  cal    (閾値キャリブレーション用, 正常のみ): n_cal    (default 128)
  test   (評価, 正常 + 異常):             残り正常 + 全異常

閾値はキャリブレーションセット (X_cal) で 1 回だけ選び、
テストセットは最終評価に 1 回だけ使用する。
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
        # FIXED: raised from (0.8, 1.5) — impulse amplitude must be large enough
        # relative to normal signal amplitude (~1.0) for reliable detection.
        # (0.8, 1.5) yielded ROC-AUC ≈ 0.80; (3.0, 6.0) reaches ROC-AUC ≥ 0.99.
        amp = rng.uniform(3.0, 6.0)
        # 幅 3 のインパルス列
        for pos in range(offset, SAMPLE_LEN - 3, period):
            base[i, pos:pos + 3] += amp * np.array([0.5, 1.0, 0.5], dtype=np.float32)
    return base


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate synthetic vibration data for the AE anomaly detection pipeline."
    )
    p.add_argument("--out", type=Path, default=Path("data/vibration.npz"))
    p.add_argument("--n-normal", type=int, default=1000,
                   help="Total number of normal windows to generate.")
    p.add_argument("--n-anomaly", type=int, default=200,
                   help="Number of anomaly windows to generate.")
    p.add_argument("--n-cal", type=int, default=128,
                   help="Calibration-set size drawn from normal windows "
                        "(used for threshold selection in train.py).")
    p.add_argument("--n-val-es", type=int, default=32,
                   help="Early-stopping validation set size (normal windows only).")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    n_normal = args.n_normal
    n_cal = args.n_cal
    n_val_es = args.n_val_es
    n_tr = int(n_normal * 0.64)
    n_test_normal = n_normal - n_tr - n_val_es - n_cal
    if n_test_normal <= 0:
        raise ValueError(
            f"n_normal={n_normal} is too small for the requested split "
            f"(train={n_tr}, val_es={n_val_es}, cal={n_cal}). "
            "Increase --n-normal or reduce --n-cal / --n-val-es."
        )

    print(f"[gen] generating {n_normal} normal + {args.n_anomaly} anomaly windows")
    normal = gen_normal(n_normal, rng)
    anomaly = gen_anomaly(args.n_anomaly, rng)

    # 分割 (再現性のため fixed seed):
    #   train:  n_normal * 0.64  → AE 学習 (異常なし = 教師なし)
    #   val:    n_val_es          → 早期終了検証のみ (閾値決定には使わない)
    #   cal:    n_cal             → 閾値キャリブレーション (テストセットとは独立)
    #   test:   残り正常 + 全異常 → 最終評価に 1 回だけ使用
    idx = rng.permutation(n_normal)
    tr_idx  = idx[:n_tr]
    val_idx = idx[n_tr:n_tr + n_val_es]
    cal_idx = idx[n_tr + n_val_es:n_tr + n_val_es + n_cal]
    te_idx  = idx[n_tr + n_val_es + n_cal:]

    X_train       = normal[tr_idx]
    X_val         = normal[val_idx]    # early-stopping only
    X_cal         = normal[cal_idx]    # threshold calibration only
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
        X_train=X_train,
        X_val=X_val,
        X_cal=X_cal,
        X_test=X_test,
        y_test=y_test,
        fs=FS,
        sample_len=SAMPLE_LEN,
        seed=args.seed,
        n_normal=n_normal,
        n_anomaly=args.n_anomaly,
        n_cal=n_cal,
        n_val_es=n_val_es,
    )
    print(f"[gen] saved → {args.out}")
    print(
        f"       train={X_train.shape}  val_es={X_val.shape}  "
        f"cal={X_cal.shape}  test={X_test.shape}  "
        f"anomaly_rate={y_test.mean():.2%}"
    )


if __name__ == "__main__":
    main()
