# 03 — 学習

```bash
python src/train.py --epochs 8 --n-classes 5 --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--epochs` | 8 | |
| `--lr` | 1e-3 | fc head の学習率 |
| `--batch-size` | 16 | |
| `--n-classes` | 5 | Flowers102 の先頭 N クラスを使用 |
| `--seed` | 42 | |

## 期待進行

```
[data] downloading Flowers102 (~330MB, only first time)
[data] classes=[0, 1, 2, 3, 4] train=50 val=50 test=200
[model] ResNet18 (backbone frozen) | trainable=2,565 / total=11,178,181
[epoch  1/8] train_loss=1.5921 val_loss=1.3812 val_acc=0.480 *best*
[epoch  4/8] train_loss=0.6244 val_loss=0.5311 val_acc=0.820 *best*
[epoch  8/8] train_loss=0.3811 val_loss=0.4128 val_acc=0.880 *best*
```

## 実行時間

| CPU | epochs=8 |
|---|---|
| Apple M1 | ~5 分 |
| Intel i5 | ~10 分 |
| GPU (T4 or M2 MPS) | 1 分未満 |

## 出力

- `outputs/best_model.pt` — head + backbone state dict
- `outputs/loss_acc.png`
- `outputs/train_metrics.json`

## Evaluate

```bash
python src/evaluate.py --model outputs/best_model.pt
```

出力: test accuracy, precision/recall/F1, `confusion_matrix.png`, `eval_metrics.json`.
