# 03 — 学習

```bash
python src/train.py --epochs 15 --n-per-class 200
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--epochs` | 20 | |
| `--batch-size` | 32 | |
| `--lr` | 1e-3 | Adam |
| `--n-per-class` | 200 | 合成データのクラスごとサンプル数 |
| `--seed` | 42 | |

## 期待進行

```
[data] generating synthetic HSI: 200/class × 6 classes × 200 bands
[data] X.shape=(1200, 200) y.shape=(1200,)
[data] train=720 val=240 test=240
[model] HSI-CNN | params=9,542
[epoch  1/15] train_loss=1.5535 val_loss=1.7088 val_acc=0.188 *best*
[epoch  5/15] train_loss=0.8763 val_loss=0.8099 val_acc=0.938 *best*
[epoch 10/15] train_loss=0.4722 val_loss=0.4178 val_acc=0.988 *best*
[epoch 15/15] train_loss=0.2812 val_loss=0.2369 val_acc=0.988
[test] acc=0.963
```

## 実行時間

| CPU | 15 epoch × 720 samples |
|---|---|
| Apple M1 | ~1 分 |
| Intel i5 | ~2 分 |

## 出力

- `outputs/best_model.pt`
- `outputs/loss_acc.png`
- `outputs/confusion_matrix.png`
- `outputs/sample_spectra.png` — 6 クラスの典型スペクトル
- `outputs/metrics.json`
