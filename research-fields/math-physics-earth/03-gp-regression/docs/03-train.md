# 03 — 学習と予測

```bash
python src/train.py --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--n-obs` | 30 | 観測点数 |
| `--noise` | 0.15 | 観測ノイズ σ |
| `--n-pred` | 200 | 予測グリッド点数 |
| `--t-min` | 0 | |
| `--t-max` | 20 | 観測範囲上限 (これを超えると外挿) |
| `--seed` | 42 | |

## 期待出力

```
[fit] optimized kernel:
      2.62**2 * ExpSineSquared(length_scale=4.22, periodicity=5.02)
      + 2.63**2 * RBF(length_scale=33.6) + WhiteKernel(noise_level=0.0118)
[fit] log-marginal-likelihood = 6.61
[eval] RMSE (interpolation region) = 0.09
[eval] RMSE (extrapolation region t>20.0) = 0.07
```

**要点**: `periodicity=5.02` と真値 (5.0) が一致 → GP が周期性を正しく発見。

## 実行時間

| CPU | n_obs=30 |
|---|---|
| 全プラットフォーム | < 1 秒 |
