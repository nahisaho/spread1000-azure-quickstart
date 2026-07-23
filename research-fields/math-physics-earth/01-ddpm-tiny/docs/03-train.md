# 03 — 学習

```bash
python src/train.py --epochs 10 --device cpu --seed 42
```

## CLI

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--epochs` | 10 | エポック数 |
| `--lr` | 2e-4 | Adam 学習率 |
| `--batch-size` | 64 | |
| `--T` | 200 | 拡散ステップ数 |
| `--n-subset` | 4000 | Fashion-MNIST から使う枚数 |
| `--seed` | 42 | |

## 期待進行

```
[data] using 4000 training images (16x16 grayscale)
[model] TinyUNet: 495,393 params
[epoch   1/10] loss=0.32418
[epoch   5/10] loss=0.11207
[epoch  10/10] loss=0.09318
[sample] generating 16 images by reverse diffusion (T steps)
```

## 出力

- `outputs/ddpm_model.pt`
- `outputs/loss_curve.png`
- `outputs/samples.png` — 学習直後の生成 16 枚

## 追加サンプル生成

```bash
python src/sample.py --model outputs/ddpm_model.pt --n-samples 25 --out outputs/more_samples.png
```

## 実行時間

| CPU | 4000 img × 10 epoch |
|---|---|
| Apple M1 | ~5 分 |
| Intel i5 | ~10 分 |
