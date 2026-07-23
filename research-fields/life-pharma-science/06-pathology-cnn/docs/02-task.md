# 02 — PathMNIST とタスク

## MedMNIST とは

- MedMNIST v2 (Yang et al., 2023) は 12 の 2D + 6 の 3D 医用画像ベンチマーク
- 各データセットは 28×28 (小) / 224×224 (大) にリサイズ済み
- **ライセンス**: `medmnist` **Python パッケージ (コード) は Apache-2.0**。各**データセットのライセンスは個別**で、PathMNIST は元データ (Kather 2019) の **CC BY 4.0** を継承。DermaMNIST は元データが **CC BY-NC 4.0** (非営利利用のみ)。データセットごとに [MedMNIST 公式サイト](https://medmnist.com/) で個別確認してください。

## PathMNIST の中身

- 出典: Kather et al. (2019) NCT-CRC-HE 100K データセット (H&E 染色大腸組織)
- **107,180 パッチ** (train 89,996 / val 10,004 / test 7,180)
- **9 クラス**:

| ID | ラベル | 病理学的意味 |
|---|---|---|
| 0 | adipose | 脂肪組織 |
| 1 | background | 背景 (無組織) |
| 2 | debris | 崩壊組織 |
| 3 | lymphocytes | リンパ球 |
| 4 | mucus | 粘液 |
| 5 | smooth_muscle | 平滑筋 |
| 6 | normal_colon | 正常大腸粘膜 |
| 7 | cancer_stroma | 癌関連間質 |
| 8 | adenocarcinoma_epi | 大腸腺癌上皮 |

## モデル: PathoCNN

```
Input (B, 3, 28, 28)
   │
Conv2d(3→32, k=3) → BN → ReLU → MaxPool(2)   → (B, 32, 14, 14)
Conv2d(32→64, k=3) → BN → ReLU → MaxPool(2)  → (B, 64, 7, 7)
Conv2d(64→128, k=3) → BN → ReLU              → (B, 128, 7, 7)
AdaptiveAvgPool2d(1)                          → (B, 128)
Dropout(0.3) → Linear(128 → 9)
```

パラメータ数: **~95K** (超軽量、CPU で数分)

## なぜ ImageNet 転移学習ではないか

- 28×28 という小解像度なので、ImageNet 事前学習 ResNet はオーバースペック
- **from scratch でも十分**な精度が出る (PathMNIST 論文でも同様の結果)
- 実 WSI (256×256+) を使う場合は転移学習 (H-1 を参照)

## 参考文献

- Yang, J. et al. (2023). *"MedMNIST v2: A large-scale lightweight benchmark for 2D and 3D biomedical image classification"*, Scientific Data
- Kather, J.N. et al. (2019). *"Predicting survival from colorectal cancer histology slides using deep learning"*, PLOS Medicine
