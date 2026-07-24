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
| `--epochs` | 30 | エポック数 [1, 200] |
| `--allow-long-run` | — | epochs > 100 の場合に必要 |
| `--lr` | 1e-3 | Adam 学習率 |
| `--batch-size` | 32 | ミニバッチ |
| `--latent-dim` | 32 | AE ボトルネック次元 |
| `--seed` | 42 | |

## モデル

**Conv1D AE** (src/model.py):
- Encoder: `Conv1d(1→16→32→64)` + MaxPool1d(2) ×3 → `Linear(16384→32)`
  - 特徴マップサイズ: 2048 → 1024 → 512 → 256 → (flatten) → 32 latent
- Decoder: `Linear(32→16384)` → `Upsample + Conv1d(64→32→16→1)` ×3
  - 特徴マップサイズ: 256 → 512 → 1024 → 2048
- 総 params: **1,083,105**

## キャリブレーションセットと閾値決定

学習後、`X_cal` (generate_data.py が生成した 128 窓の専用セット) を使って
再構成 MSE の 99 分位を閾値として決定します。

```
閾値 = np.quantile(cal_reconstruction_mse, 0.99)
```

`train.py` は 95% ブートストラップ CI も算出し `train_metrics.json` に記録します。
テストセットは閾値決定に一切使用しません。

## 期待される進行

```
[train] epochs=30  estimated runtime ≈ 1 min (~2 sec/epoch on CPU)
[data] using X_cal from NPZ for threshold calibration
[data] train=(640, 2048)  val_es=(32, 2048)  cal=(128, 2048)  seq_len=2048
[model] Conv1D AE latent=32: 1,083,105 params
[epoch   1/30] train_mse=1.01825  val_mse=0.99357  *best*
[epoch  10/30] train_mse=0.19564  val_mse=0.22732  *best*
[epoch  30/30] train_mse=0.12763  val_mse=0.26465
[threshold] cal MSE p99 = 0.318548  95% CI [0.258037, 0.334442]  (cal_n=128, ...)
```

## 実行時間

| CPU | epochs=30 |
|---|---|
| Apple M1 | ~2 分 |
| Intel i5 (8th gen) | ~4 分 |

## 出力

- `outputs/best_ae.pt` — 最良検証誤差モデル + `mu`, `sigma`, `threshold`, `data_sha256`, `fs`, `schema_version` などのプロベナンス情報を含む dict
- `outputs/loss_curve.png` — 学習/検証 MSE 曲線
- `outputs/train_metrics.json` — 最終評価値 (threshold, CI, calibration_set_size 含む)
