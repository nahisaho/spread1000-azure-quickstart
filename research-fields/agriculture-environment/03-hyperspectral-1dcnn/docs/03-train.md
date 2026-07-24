# 03 — 学習

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/03-hyperspectral-1dcnn"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "abort: wrong directory"; exit 1; }

python src/train.py --mode synthetic --epochs 15 --n-per-class 200
```

## CLI 主要フラグ

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--mode` | `synthetic` | `synthetic` / `indianpines` / `custom` |
| `--data-root` | `data/` | .mat または X.npy の場所 (synthetic 不要) |
| `--epochs` | 20 | 1–1000 |
| `--batch-size` | 32 | 1–65536 |
| `--lr` | 1e-3 | Adam 学習率 (0 < lr ≤ 1) |
| `--n-per-class` | 200 | 合成モード: クラスごとサンプル数 (≥5) |
| `--seed` | 42 | |
| `--split-strategy` | `disjoint_patch` | `random_pixel` / `disjoint_patch` (実データ推奨) |
| `--exclusion-radius` | 5 | パッチ境界の除外ピクセル半径 |
| `--allow-random-pixel-split` | off | random_pixel の空間リーク警告を抑制 |
| `--norm-method` | `per_band_zscore` | `per_band_zscore` / `per_spectrum_snv` / `none` |
| `--balance` | `weighted_ce` | `none` / `weighted_ce` / `weighted_sampler` / `focal` |
| `--best-metric` | `macro_f1` | `macro_f1` / `val_acc` / `balanced_acc` |
| `--device` | `auto` | `cpu` / `cuda` / `mps` / `auto` |
| `--amp` | off | CUDA のみ有効; CPU/MPS では自動無効化 |
| `--deterministic` | off | 決定論的アルゴリズム有効化 (再現性) |

## 合成データ実行例

```
[ep  1/15] loss=1.6124|1.7001  acc=0.156  mF1=0.082 *best*
[ep  5/15] loss=0.9012|0.8312  acc=0.921  mF1=0.921 *best*
[ep 10/15] loss=0.4801|0.4201  acc=0.983  mF1=0.983 *best*
[ep 15/15] loss=0.2914|0.2450  acc=0.983  mF1=0.983
[test] acc=0.962  mF1=0.962  bal_acc=0.962  kappa=0.954  best_ep=14
```

> ⚠ **合成データの精度はベンチマークではありません。** 実 Indian Pines では
> typical acc ≈ 0.80–0.90 (disjoint_patch split)。

## 実 Indian Pines (初回のみインターネット必要)

```bash
python src/train.py --mode indianpines \
    --split-strategy disjoint_patch \
    --balance weighted_ce \
    --epochs 30 --lr 5e-4
```

## カスタムデータ

```
data-root/
  X.npy           # (N, B) float32
  y.npy           # (N,) int64  0-indexed
  class_names.txt # クラス名 1 行 1 名
  coords.npy      # (N, 2) int32 [row, col]  ← disjoint_patch に必要
```

```bash
python src/train.py --mode custom --data-root path/to/data-root
```

## 出力

- `outputs/best_model.pt` — チェックポイント (正規化 stats, class_names 含む)
- `outputs/loss_acc.png`
- `outputs/confusion_matrix.png` + `outputs/confusion_matrix.csv`
- `outputs/sample_spectra.png`
- `outputs/prediction_map.png` — 実データのみ
- `outputs/metrics.json` — 完全メトリクス (git SHA, torch version, etc.)
