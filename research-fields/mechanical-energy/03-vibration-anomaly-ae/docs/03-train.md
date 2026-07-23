# 03 — 学習

## 実行

```bash
python src/train.py --data data/vibration.npz --epochs 30 --device cpu --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--data` | (必須) | `generate_data.py` の出力 npz |
| `--device` | cpu | cuda 指定可 |
| `--epochs` | 30 | エポック数 |
| `--lr` | 1e-3 | Adam 学習率 |
| `--batch-size` | 32 | ミニバッチ |
| `--latent-dim` | 32 | AE ボトルネック次元 |
| `--seed` | 42 | |

## モデル

**Conv1D AE** (src/model.py):
- Encoder: `Conv1d(1→16→32→64)` + MaxPool ×3 → `Linear(→32)`
- Decoder: `Linear(32→)` → `Upsample + Conv1d(64→32→16→1)` ×3
- 総 params: ~ 200K (受容野広め、実装重視のシンプル設計)

## 期待される進行

```
[data] train=(640, 2048) val=(160, 2048) seq_len=2048
[model] Conv1D AE latent=32: 211,633 params
[epoch   1/30] train_mse=0.34112  val_mse=0.20128  *best*
[epoch  10/30] train_mse=0.00812  val_mse=0.00857  *best*
[epoch  30/30] train_mse=0.00214  val_mse=0.00226  *best*
[threshold] val MSE p99 = 0.003841  (min=0.001824, max=0.003912)
```

## 実行時間

| CPU | epochs=30 |
|---|---|
| Apple M1 | ~2 分 |
| Intel i5 (8th gen) | ~4 分 |

## 出力

- `outputs/best_ae.pt` — 最良検証誤差モデル + `mu`, `sigma`, `threshold` を含む dict
- `outputs/loss_curve.png` — 学習/検証 MSE 曲線
- `outputs/train_metrics.json` — 最終評価値
