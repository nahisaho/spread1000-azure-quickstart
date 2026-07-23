# 05 — 自前データへの適用

## ディレクトリ構造

`torchvision.datasets.ImageFolder` に準拠すれば、`src/train.py` のデータ読み込みを差し替えるだけで学習可能:

```
my_plants/
├── train/
│   ├── healthy/          # class 0
│   │   ├── 001.jpg
│   │   └── ...
│   ├── rust/             # class 1
│   └── blight/           # class 2
└── val/
    ├── healthy/
    ├── rust/
    └── blight/
```

## train.py の書き換え箇所

```python
from torchvision.datasets import ImageFolder
train_ds = ImageFolder("my_plants/train", transform=build_transforms(train=True))
val_ds = ImageFolder("my_plants/val", transform=build_transforms(train=False))
# filter_by_classes 部分は不要 (すでにクラス分割済み)
n_classes = len(train_ds.classes)
```

## 公開データセット候補

| データセット | 用途 | サイズ | ライセンス |
|---|---|---|---|
| **PlantVillage** | 葉病害 38 種 | ~1.5GB | Kaggle 経由、CC-BY |
| **DeepWeeds** | オーストラリアの雑草 8 種 | ~1GB | CC-BY |
| **iNaturalist Species** | 動植物 8000+ 種 | 30GB+ | CC-BY-NC |
| **CropDeep** | 稲作害虫 | ~500MB | 論文リポジトリ経由 |

## クラス不均衡対策

- 各クラスのサンプル数が偏っている場合 (例: 健全 900, 病害 100):
  - `WeightedRandomSampler` で minority class を oversample
  - `nn.CrossEntropyLoss(weight=...)` に class weight を渡す
  - F1 マクロ平均で評価する (accuracy は misleading)

## 精度を上げるコツ (順番に試す)

1. Data augmentation を強化: `TrivialAugmentWide()` を追加
2. Epochs を 15-20 に増やす + LR scheduler (`CosineAnnealingLR`)
3. Backbone の最終ブロック (`model.layer4`) だけ unfreeze して低い lr で fine-tune
4. より大きなモデル (ResNet50, EfficientNet-B0) に切り替え
5. 最後に **より多くの学習データ**を集める (最もインパクト大)
