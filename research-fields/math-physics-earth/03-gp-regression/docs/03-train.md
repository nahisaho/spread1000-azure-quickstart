# 03 — 学習と予測

```bash
cd "$(git rev-parse --show-toplevel)/research-fields/math-physics-earth/03-gp-regression"
python src/train.py --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--n-obs` | 30 | 観測点数 [10, 100000] |
| `--noise` | 0.15 | 観測ノイズ σ (finite, >= 0) |
| `--n-pred` | 200 | 予測グリッド点数 [10, 100000] |
| `--t-min` | 0 | 観測範囲下限 (finite) |
| `--t-max` | 20 | 観測範囲上限 (finite) |
| `--seed` | 42 | 乱数シード [0, 4294967295] |
| `--extrap-horizon` | 5.0 | 外挿区間幅 (t_max に加算) |
| `--init-period` | 3.0 | 周期初期値 (真値 5.0 とは意図的にずらす) |
| `--n-restarts` | 8 | ハイパラ最適化の再起動回数 |
| `--jitter` | 1e-8 | GP 対角ジッタ (数値安定性) [0, 0.01] |

## 外挿例

```bash
# 1 周期先外挿 (ExtrapHorizon=5): 周期カーネルなので帯はほぼ広がらない
python src/train.py --extrap-horizon 5

# 10 周期先外挿 + 初期周期を大きくずらす: 帯の乱れや収束失敗を確認
python src/train.py --extrap-horizon 50 --init-period 7 --n-restarts 3
```

## 期待出力

```
[fit] observations=30  init_period=3.0  restarts=8
[fit] optimized kernel: 2.62**2 * ExpSineSquared(..., periodicity=5.02) + ...
[fit] log-marginal-likelihood = 6.61
[stability] condition number = 1.23e+03
[eval] RMSE (interpolation region) = 0.09
[eval] Temporal holdout RMSE (last 6 pts) = 0.11
[eval] Holdout 95% coverage = 0.83
[fit] optimized_period = 5.0241  (init=3.0, true=5.0)
```

**要点 (MED-9)**: `init_period=3.0` (真値 5.0 とは離れた初期値) から出発し、オプティマイザが `periodicity ≈ 5.0` に収束する。8 回の再起動のうち多くが 5.0 付近に収束すれば周期発見は頑健。初期値が真値から離れているほど発見難易度が上がる。

## 実行時間

| CPU | n_obs=30 |
|---|---|
| 全プラットフォーム | < 5 秒 (restarts=8) |
