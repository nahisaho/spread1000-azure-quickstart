# 05 — 自前病理画像への適用

## MedMNIST 内の他データセット

`medmnist` パッケージには他にも:

| データセット | 内容 | 用途 |
|---|---|---|
| PneumoniaMNIST | 胸部 X 線 (2 class) | 感染症スクリーニング |
| DermaMNIST | 皮膚病変 (7 class) | 皮膚科補助診断 |
| BloodMNIST | 血液細胞 (8 class) | 血液学 |
| BreastMNIST | 乳腺超音波 (2 class) | 悪性度判定 |
| RetinaMNIST | 網膜眼底 (5 class) | 糖尿病網膜症 |
| ChestMNIST | 胸部 X 線 (14 multi-label) | 多疾患検出 |

`src/train.py` の `PathMNIST` を `PneumoniaMNIST` 等に差し替え + `CLASS_NAMES` を更新するだけ。

## 実 WSI (Whole Slide Image) への拡張

Camelyon16, PANDA, TCGA 等の実 WSI で運用する場合:

1. **OpenSlide** で `.svs`/`.mrxs` を読み込み
2. **染色正規化**: Macenko (`torchstain`) や Vahadane
3. **タイル分割**: 224×224 or 256×256 パッチ + Otsu で組織検出
4. **転移学習**: ImageNet 事前学習 ResNet50/EfficientNet or 病理特化 foundation model (**HIPT, CTransPath, UNI, Virchow**) を backbone
5. **MIL アグリゲーション**: パッチ予測 → CLAM, TransMIL で WSI レベル予測

## Foundation Model の活用

2023-2024 の病理特化 foundation model:
- **UNI** (Chen et al. 2024, Nat Med) — ViT-Large、100K WSI で学習
- **Virchow** (Vorontsov 2024, Nat Med) — Paige.AI 提供
- **CTransPath** (Wang 2022, Med Image Anal) — Swin Transformer

これらを backbone にすれば、少数ラベル (< 100 スライド) で高精度が可能。

## Azure での GPU 学習

大規模学習は Azure ML の Compute Cluster (Standard_NC4as_T4_v3, A100) を推奨:
- 参考: [../../electrical-informatics/01-llm-lora/](../../electrical-informatics/01-llm-lora/) の Azure ML CLI v2 設定

## クラス不均衡対策

病理データセットは典型的に:
- 正常組織 >> 病変組織 (画像枚数)
- 早期病変 << 進行病変
- 対策: `WeightedRandomSampler` or `nn.CrossEntropyLoss(weight=class_weights)`

## 参考文献

- Chen, R.J. et al. (2024). *"Towards a general-purpose foundation model for computational pathology"* (UNI), Nature Medicine
- Wang, X. et al. (2022). *"Transformer-based unsupervised contrastive learning for histopathological image classification"* (CTransPath)
- Lu, M.Y. et al. (2021). *"Data-efficient and weakly supervised computational pathology on whole-slide images"* (CLAM), Nat. Biomed. Eng.
