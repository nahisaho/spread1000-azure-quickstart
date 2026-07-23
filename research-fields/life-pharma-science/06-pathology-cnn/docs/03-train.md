# 03 — 学習

```bash
# 高速スモーク (3 分)
python src/train.py --epochs 3 --train-frac 0.1

# 実用精度 (10-15 分)
python src/train.py --epochs 8 --train-frac 0.5

# 論文級精度 (30 分〜)
python src/train.py --epochs 15 --train-frac 1.0
```

## CLI

| フラグ | 既定 | 説明 |
|---|---|---|
| `--epochs` | 5 | |
| `--batch-size` | 128 | |
| `--lr` | 1e-3 | Adam |
| `--train-frac` | 0.2 | train データ縮小率 (0-1) |
| `--seed` | 42 | |

## 期待進行 (フル 90K, 8 epoch)

```
[data] loading MedMNIST PathMNIST (~205MB, 初回のみ)
[data] train=89996 val=10004 test=7180
[model] PathoCNN | params=94,857
[epoch 1/8] train_loss=0.7211 val_loss=0.5432 val_acc=0.802 *best*
[epoch 4/8] train_loss=0.3054 val_loss=0.3812 val_acc=0.867 *best*
[epoch 8/8] train_loss=0.2011 val_loss=0.3221 val_acc=0.892 *best*
[test] acc=0.883
```
