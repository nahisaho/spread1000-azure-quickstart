# 04 — 結果の解釈

## sample_spectra.png

- 各クラスの反射率スペクトル (合成データの典型パターン)
- **植生系** (corn, soybean, wheat, grass, woods): NIR (100-150 band) 領域に高い反射
- **裸地** (bare_soil): 長波長側に緩やかな上昇、明確なピークなし
- 実データ植生でも同様のパターン (red edge, NIR plateau) が現れる

## confusion_matrix.png

- 対角線が濃い青 → 高精度
- 誤分類が集中する pair があれば **スペクトル形状が類似**しているクラス
  - 合成データでは corn-soybean 間、wheat-grass 間が接近することがある
- 実データでは同種の農作物 (季節/成長段階) で分離が難しい

## loss_acc.png

- val_loss が train_loss より高いのは通常
- 両者の差が急拡大 → overfitting (data augmentation か epoch を減らす)
- val_acc の頭打ちが早い → モデル容量不足 (チャネル数増やす)

## metrics.json の見方

各クラスの precision/recall/F1 を確認:
- **precision 低い**: 誤って当てクラスに分類 (false positive)
- **recall 低い**: そのクラスを見逃し (false negative)
- 農業/環境応用では、リスク大きい方の recall を優先することが多い
