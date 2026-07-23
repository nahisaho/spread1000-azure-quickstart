# 07 — 倫理と限界

## 合成データの本質的限界

- 本教材の合成スペクトルは Gaussian ピークで簡略化しており、実 HSI の
  **大気補正残差、隣接効果、水吸収帯 (~1400/1900 nm) 欠損**を模していない
- 「動く」ことは確認できるが、**論文級の精度評価には実データ必須**

## Hyperspectral 実データの落とし穴

- **チャネル正規化欠如**: 反射率スケールがバンドで大きく違うと学習破綻
- **同一 flight/scene からのみ学習**: 別日・別センサーで精度急落 (domain shift)
- **クラス不均衡**: Indian Pines では最小クラス 20 サンプル、最大 2455 → 不均衡対応必須

## リモートセンシング応用の倫理

- **プライバシー**: 高分解能 HSI は個人の私有地/庭を識別可能 → 分解能規制
- **軍事転用**: HSI 分類技術は camouflage 検出等の軍事応用の歴史 → デュアルユース
- **土地利用政策への影響**: 誤分類が土地税/補助金判定に使われると不利益発生
- **先住民の土地・農地権**: 遠隔地の土地利用マッピングは合意なき情報収集になりうる

## 説明可能性

- 「なぜこのバンドが判定根拠か」を示すのが重要
- 手法: **Saliency / SHAP を band 次元に適用**、重要バンドを可視化
- 実装例: `captum.attr.IntegratedGradients` を Conv1d モデルに適用

## 参考文献

- Roy et al. (2020). *"HybridSN"*, IEEE GRSL — 実 Indian Pines 精度の参照
- Camps-Valls et al. (2020). *"Advances in Hyperspectral Image and Signal Processing"*, IEEE Signal Process. Mag.
