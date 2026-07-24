# 04 — 結果の解釈

## loss_acc.png

- 左軸: train/val loss
- 右軸: val accuracy (緑破線)
- train_loss が val_loss より **極端に低い** → overfitting
- val_acc が 5-6 epoch で頭打ち → epochs 増やしても伸びない

## confusion_matrix.png

- 対角線に集中していれば良好
- 特定クラス間で誤分類が集中 (例: クラス 1↔3) → **クラス間類似度**が高いか、学習データ不足

## 精度目安 (Flowers102 5 クラス)

| val_acc | 意味 |
|---|---|
| > 0.90 | 素晴らしい (**本ベンチマーク上の性能**。実運用には現場光条件・栽培品種・地域・季節・撮影機器ごとの独立検証が必要) |
| 0.80 - 0.90 | 良好 |
| 0.60 - 0.80 | 頭打ち、fine-tuning 検討 |
| < 0.60 | データ / 前処理 / lr の見直し |

## precision, recall, F1

- **precision (適合率)**: 「病害」と判定した中で本当に病害だった割合
- **recall (再現率)**: 実際の病害のうち検出できた割合
- 農業応用: 未検出 (recall 低い) が経済的損失に直結するケースも多いが、**閾値の調整による recall 優先は誤診率増加とトレードオフ**である
- 推奨: 低信頼度の予測は「判断保留 (abstention)」として専門家に回す運用を設計し、自動判定の範囲を明示的に制限すること
- `train.py --best-metric val_macro_f1` でクラス不均衡時のマクロ F1 を最適化できる

## Overfitting 対策 (発生した場合)

- Data augmentation を追加 (`ColorJitter(brightness=0.2)` 等)
- `Dropout` を fc head に追加
- Early stopping (val_acc 3 epoch 更新なしで停止)
- Learning rate を下げる (`--lr 5e-4`)
