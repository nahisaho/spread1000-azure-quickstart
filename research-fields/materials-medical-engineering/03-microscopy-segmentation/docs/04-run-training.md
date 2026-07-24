# 04 — 学習の詳細と実データへの拡張

`src/train.py` の内部動作と、自分の顕微鏡画像で学習する方法を解説します。

## パイプライン

```
[generate_data.generate_batch()] → MONAI CacheDataset → MONAI DataLoader
   → [MONAI UNet forward → DiceCELoss(sigmoid=True, ce_weight=pos_weight)]
   → Adam(lr=1e-3) で 10 epochs
   → 毎エポック validation → DiceMetric (MONAI) & IoU (torchmetrics)
   → best_val_iou を更新したエポックの重みを保存
   → 最終エポックで [入力 | 正解 | 予測] のモンタージュ生成
   → metrics.json に再現性メタデータ・チェックポイント SHA-256 を記録
```

## 主要な CLI オプション

| オプション | 既定 | 意味 |
|---|---|---|
| `--task` | `grains` | `grains` (Voronoi 粒界) / `particles` (円粒子) |
| `--image-size` | `128` | 4 の倍数必須 (2 段の stride-2 conv のため) |
| `--n-train` / `--n-val` | 200 / 50 | 生成する合成画像枚数 |
| `--batch-size` | `8` | CPU では 4〜16 が目安 |
| `--epochs` | `10` | 10 で十分学習曲線が見える。>50 には `--allow-long-run` が必要 |
| `--lr` | `1e-3` | Adam の学習率 |
| `--device` | `cpu` | `cpu` / `cuda` |
| `--num-workers` | `0` | WSL2/Windows は 0 のまま、Linux/Compute Instance は 2〜4 |
| `--pos-weight` | `9.0` | BCE の陽性クラス重み。DiceCELoss の ce_weight として渡す |
| `--max-training-hours` | `2.0` | ウォールクロック上限 (時間)。>4.0 h には `--allow-long-run` が必要 |
| `--allow-long-run` | (flag) | `--epochs>50` または `--max-training-hours>4.0` を許可 |
| `--n-montage` | `6` | 最終モンタージュに含める検証画像数 |
| `--output` | `data/` | 出力先ディレクトリ |

## 損失関数のなぜ

**DiceCELoss(sigmoid=True, ce_weight=pos_weight)** を選んだ理由:
- 粒界マスクは全ピクセルの ~12% しか陽性 (境界) が無い強い不均衡データ
- Dice 項: 陽性・陰性ピクセルのオーバーラップを最大化（不均衡に頑健）
- CE 項 + ce_weight=9.0: 細い境界の再現率を優先（陰性/陽性比 ~7.3 より少し高め）
- MONAI の `DiceCELoss` はシグモイドを内部で適用し数値的に安定

実データで陽性率が違うなら `[data] positive pixel fraction (train)` の出力を見て `pos_weight = (1 - p) / p` に調整してください。

## 実データを使う場合

`src/train.py` の `_make_loaders()` を差し替えるか、以下のような `Dataset` を書いてください:

```python
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

class MicroscopyDataset(Dataset):
    """Load grayscale image + binary mask pairs from disk."""
    def __init__(self, image_dir: str, mask_dir: str, size: int = 256):
        self.imgs  = sorted(Path(image_dir).glob("*.png"))
        self.masks = sorted(Path(mask_dir).glob("*.png"))
        assert len(self.imgs) == len(self.masks), "画像とマスクの数が一致しません"
        self.size = size

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, i):
        img  = Image.open(self.imgs[i]).convert("L").resize((self.size, self.size))
        mask = Image.open(self.masks[i]).convert("L").resize((self.size, self.size))
        x = torch.from_numpy(np.array(img,  dtype=np.float32) / 255.0).unsqueeze(0)   # (1,H,W)
        # 二値化 (mask ピクセルが 0 or 255 前提)。マスクは float32 で BCE に渡す
        y = torch.from_numpy((np.array(mask) > 127).astype(np.float32)).unsqueeze(0)
        return x, y
```

そして `train.py` の `_make_loaders()` 冒頭を書き換え:
```python
train_ds = MicroscopyDataset("data/real_train/images", "data/real_train/masks", size=args.image_size)
val_ds   = MicroscopyDataset("data/real_val/images",   "data/real_val/masks",   size=args.image_size)
train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, ...)
val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, ...)
```

**重要**:
- マスクは **float32**、`BCEWithLogitsLoss` は `bool`/`uint8` を受け付けません
- モデルは **logits を返す** (`sigmoid` を最後に付けない)。予測時のみ `torch.sigmoid()` してから閾値 0.5

## モデルを大きくする

MONAI UNet のチャンネル数を変更することで大きくなります:

```python
from monai.networks.nets import UNet
model = UNet(
    spatial_dims=2, in_channels=1, out_channels=1,
    channels=(32, 64, 128),  # 基本 16/32/64 → 32/64/128 で ~4 倍のパラメータ
    strides=(2, 2),
    num_res_units=2,
)
```

より本格的には MONAI Model Zoo の事前学習モデルを活用できます:
https://monai.io/model-zoo.html

## 参考リンク

- U-Net 論文: Ronneberger et al., MICCAI 2015 https://arxiv.org/abs/1505.04597
- PyTorch DataLoader: https://pytorch.org/docs/stable/data.html
- torchmetrics classification: https://lightning.ai/docs/torchmetrics/stable/
