# 04 — 結果の解釈

## confusion_matrix.png のポイント

- **cancer_stroma (7) と adenocarcinoma_epi (8)** の誤分類は臨床的に許容範囲 (両者とも癌領域)
- **normal_colon (6) を adenocarcinoma (8) と誤判定** は False Positive → 過剰診断
- **adenocarcinoma (8) を normal (6) と誤判定** は False Negative → 見逃し
- **背景 (1) とデブリ (2)** は前処理段階での混同でよくある

## precision/recall の見方

病理応用では:
- **癌クラスの recall (再現率) を優先**: 見逃しの臨床コストが大きい
- 一般成人検診なら **precision も重視** (無症状者への過剰生検を避ける)

## 精度目安

| val_acc | 意味 |
|---|---|
| > 0.90 | 論文級 (ResNet50 fine-tune で 0.95 も可能) |
| 0.85-0.90 | 実用途への基礎モデルとして OK |
| 0.75-0.85 | 学習曲線がまだ登り途中、epoch 増やす |
| < 0.75 | データ量 or モデル容量不足 |

## overfitting 対策

- Data augmentation (`RandomHorizontalFlip`, `ColorJitter(brightness=0.1, hue=0.05)` — H&E 染色向け)
- Dropout を増やす (0.3 → 0.5)
- Early stopping (val_acc 3 epoch 更新なしで停止)
- MedMNIST は各クラスの色調が似ているので、hue/saturation augmentation が特に有効

## 実 WSI との違い

- MedMNIST の 28×28 パッチは既に「関心領域が中央」に前処理済み
- 実 WSI (Whole Slide Image, gigapixel) では:
  - **前処理**: 組織検出 → タイル分割 → 染色正規化 (Macenko/Vahadane)
  - **アグリゲーション**: パッチ単位の予測を WSI レベルに集約 (MIL, attention pooling)
  - **推論**: 1 スライド 数万パッチ = GPU 必須
