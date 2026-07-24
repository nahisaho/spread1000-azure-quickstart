# 03 — 学習

```bash
cd research-fields/math-physics-earth/02-symbolic-regression
python src/generate_data.py --out data/obs.npz --seed 42
python src/train.py --data data/obs.npz --generations 30 --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--population` | 2000 | 集団サイズ [10, 2000] |
| `--generations` | 30 | 進化世代数 [1, 200] |
| `--parsimony` | 0.001 | 式長ペナルティ |
| `--test-size` | 0.15 | テストホールドアウト |
| `--val-size` | 0.15 | 検証ホールドアウト |
| `--seed` | 42 | |
| `--allow-long-run` | (なし) | population × generations > 60,000 の場合に必要 |

## 期待進行

```
    |   Population Average    |             Best Individual              |
---- ------------------------- ------------------------------------------
Gen  Length     Fitness        Length     Fitness       OOB Fitness    Time
   0    12.85      3.72        5          0.85          0.92          1.5s
  10     9.30      1.20        8          0.24          0.28          0.8s
  29     8.60      0.60        9          0.09          0.11          0.4s
```

(Fitness は生の MAE。世代番号は 0 始まり: Gen 0 〜 Gen 29)

## 出力

- `outputs/best_program.txt` — 発見された式 (S 式表現)
- `outputs/fitness_curve.png`
- `outputs/pred_vs_true.png`
- `outputs/metrics.json`

## 実行時間目安

| CPU | pop=2000, gen=30 |
|---|---|
| Apple M1 | ~1 分 |
| Intel i5 | ~3 分 |
