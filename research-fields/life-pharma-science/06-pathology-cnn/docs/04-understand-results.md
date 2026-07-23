# 04 — 結果の解釈

> [!IMPORTANT]
> 本教材のモデルは **研究・教育目的の実装例**であり、診断に用いてはいけません。臨床適用には多施設臨床試験、PMDA/FDA 等の薬事承認、SaMD としてのリスク管理が必須です。以下の解釈もあくまで学習結果の見方の説明であって、臨床性能の主張ではありません。

## confusion_matrix.png のポイント (学習結果の読み方)

- **cancer_stroma (7) と adenocarcinoma_epi (8)** の相互誤分類はデータ上よく起きる (両者とも癌領域で組織像が類似)
- **normal_colon (6) → adenocarcinoma (8)** の誤判定は False Positive (仮に臨床応用したなら過剰生検につながる例)
- **adenocarcinoma (8) → normal (6)** の誤判定は False Negative (仮に臨床応用したなら見逃しにつながる例)
- **背景 (1) とデブリ (2)** は前処理段階での混同でよくある

## precision/recall の見方 (病理応用**を検討する際の一般論**)

- **癌クラスの recall (再現率) を優先**するのが一般的: 見逃しの臨床影響が大きいため
- 検診応用なら **precision も重視** (不要な精密検査を減らすため)
- ただし本モデルはパッチ単位・単一施設データ・臨床検証なしのため、これらの数値を根拠に臨床運用してはいけない

## 精度目安 (**MedMNIST ベンチマーク上の**目安)

| val_acc | 意味 (ベンチマーク上のみ) |
|---|---|
| > 0.90 | 論文級 (ResNet50 fine-tune で 0.95 も可能) |
| 0.85-0.90 | ベンチマーク上の高スコア (臨床性能の指標ではない) |
| 0.75-0.85 | 学習曲線がまだ登り途中、epoch 増やす |
| < 0.75 | データ量 or モデル容量不足 |

> [!WARNING]
> 検証データ (`val`) は元データセット `NCT-CRC-HE 100K` から**パッチ単位でランダム分割**されたもので、患者単位・スライド単位の分割ではありません。同一スライドのパッチが train と val に混入する **data leakage** が起きうるため、val_acc は臨床データに対する期待精度より楽観的な可能性があります。真の汎化性能は **独立の外部テストセット** (CRC-VAL-HE-7K など) で評価します。

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
