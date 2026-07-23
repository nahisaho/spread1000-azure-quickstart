# 02 — CPU / WSL2 クイックスタート

Azure を使わず、手元のマシンで顕微鏡セグメンテーションの全体像を体験します。128×128 の合成データ 200 枚を 10 エポック学習して、1〜3 分で結果が出ます。

## 前提

[01-prerequisites.md](01-prerequisites.md) の手順で以下が完了していること:
- Python 3.12 の venv (`.venv`) が有効
- `torch==2.7.1 torchvision==0.22.1` (CPU 版) と `requirements.txt` がインストール済み
- `python src/generate_data.py --task grains --n 4 --output data/samples/` が成功

## Step 1: 合成データを目視確認 (任意)

```bash
python src/generate_data.py --task grains --n 4 --output data/samples/
```

`data/samples/grains_00.png` ... `grains_03.png` を開いて、Voronoi 多角形の粒に薄い境界線が引かれていることを確認します。

粒子タスクを試す場合:
```bash
python src/generate_data.py --task particles --n 4 --output data/samples/
```

## Step 2: 学習 & 検証 (Voronoi 粒界)

```bash
python src/train.py --task grains --image-size 128 \
  --n-train 200 --n-val 50 --epochs 10 \
  --device cpu --output data/
```

**期待される出力**:
```
[data] generating 200 train / 50 val 128×128 images for task=grains ...
[data] boundary/positive pixel fraction (train): 0.1217
[model] MiniUNet: 117,073 parameters, device=cpu
[epoch   1/10] train=0.7203  val=0.6104  IoU=0.2841  Dice=0.4423 *best*
[epoch   2/10] train=0.5112  val=0.4923  IoU=0.4218  Dice=0.5931 *best*
...
[epoch  10/10] train=0.2001  val=0.2178  IoU=0.6864  Dice=0.8130 *best*
[done] best val IoU = 0.6864 at epoch 10
[done] wrote data/metrics.json, data/predictions/montage_epoch010.png,
       data/predictions/per_image_metrics.json,
       data/checkpoints/best_model.pth
```

> ⚠️ **数値は目安です**。シード・CPU アーキ・PyTorch ビルドで ±0.05 程度変動します。**IoU が 0.55 以上、Dice が 0.70 以上、学習損失が単調減少** していれば成功と判定できます。

## Step 3: 結果を確認

**モンタージュを開く**（6 枚の検証画像 × [入力 | 正解 | 予測]）:
```bash
xdg-open data/predictions/montage_epoch010.png   # Linux
open data/predictions/montage_epoch010.png       # macOS
```

**学習曲線をプロット**:
```python
import json, matplotlib.pyplot as plt
m = json.load(open("data/metrics.json"))
fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3))
a.plot(m["train_loss"], label="train"); a.plot(m["val_loss"], label="val")
a.set_xlabel("epoch"); a.set_ylabel("BCE loss"); a.legend()
b.plot(m["val_iou"], label="IoU"); b.plot(m["val_dice"], label="Dice")
b.set_xlabel("epoch"); b.set_ylabel("metric"); b.legend()
plt.tight_layout(); plt.savefig("data/loss_curve.png", dpi=120)
```

**検証画像ごとの IoU をランキング**:
```python
import json
rows = json.load(open("data/predictions/per_image_metrics.json"))
rows.sort(key=lambda r: r["iou"])
for r in rows[:5]:  print("worst:", r)
for r in rows[-5:]: print("best :", r)
```

## Step 4: 粒子タスクに切り替え

粒界検出よりも簡単な、粒子セグメンテーションでも試せます:
```bash
python src/train.py --task particles --epochs 10 --output data/particles/
```

粒子タスクは IoU 0.75〜0.90 程度と、粒界（0.55〜0.75）よりずっと高くなります（塊状オブジェクトは境界より学習しやすいため）。

## 実行時間の目安 (CPU, 4 コア)

| 設定 | 時間 |
|---|---:|
| データ生成 (200+50 枚, 128×128) | 5〜15 秒 |
| 1 エポック (25 バッチ, batch=8) | 3〜8 秒 |
| **10 エポック合計** | **1〜3 分** |
| モンタージュ + JSON 出力 | < 5 秒 |

**256×256 × 500 枚 × 20 epochs にすると 15〜40 分** になり、GPU の恩恵が出始めます。

## 次のステップ

- 自分の顕微鏡画像を試したい → `Dataset` を差し替える例は [04-run-training.md](04-run-training.md)
- 大きなサイズ・多数枚で速く回したい → [03-aml-gpu.md](03-aml-gpu.md)
- 結果の意味を深く理解したい → [05-understand-results.md](05-understand-results.md)
