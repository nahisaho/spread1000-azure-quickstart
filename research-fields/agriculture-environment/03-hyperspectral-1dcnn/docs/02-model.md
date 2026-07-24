# 02 — モデル設計

## 1D-CNN アーキテクチャ

```
Input (B, 1, 200)                 # 1 ピクセルの 200 バンドスペクトル
   │
Conv1d(1→16, k=7, pad=3) → BN → ReLU
MaxPool1d(2)                       → (B, 16, 100)
   │
Conv1d(16→32, k=5, pad=2) → BN → ReLU
MaxPool1d(2)                       → (B, 32, 50)
   │
Conv1d(32→64, k=3, pad=1) → BN → ReLU
AdaptiveAvgPool1d(1)               → (B, 64, 1) → (B, 64)
   │
Linear(64 → n_classes)
```

パラメータ数: **9,542** (synthetic 6-class / 200-band; n_classes 変更で変化)

## 設計判断

| 選択 | 理由 |
|---|---|
| kernel size 7→5→3 の減少 | 初期は広い受容野で連続バンドのパターン、後段で局所特徴 |
| BatchNorm | 各 Conv 層後の特徴チャネルを正規化して学習を安定化させる (最適化の安定化; 入力バンドの正規化は train.py の --norm-method が担当) |
| Global Average Pool (GAP) | Flatten より overfitting しにくく、可変長入力にも対応 |
| チャネル数 16→32→64 | 抽象度上昇に伴い特徴数を増加 |

## なぜ 2D-CNN や 3D-CNN でないか

- **ピクセル単位分類**: 空間コンテキストを使わず、スペクトルのみで判定
- **利点**: 少量ラベルで動く、任意形状の対象領域に適用可能
- **限界**: 空間的にまとまった対象では 2D/3D-CNN が上限精度で上回る

より高精度が必要なら:
- **2D-CNN**: 5×5 パッチ × バンド → HybridSN
- **3D-CNN**: 空間 × 空間 × バンド (計算量大)
- **Transformer**: SpectralFormer (2022) 等

## 参考文献

- Hu et al. (2015). *"Deep Convolutional Neural Networks for Hyperspectral Image Classification"*, J. Sensors
- Roy et al. (2020). *"HybridSN: Exploring 3-D-2-D CNN Feature Hierarchy for Hyperspectral Image Classification"*, IEEE GRSL
