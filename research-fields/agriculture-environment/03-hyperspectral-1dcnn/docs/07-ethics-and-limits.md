# 07 — 倫理と限界

## 合成データの本質的限界

- 本教材の合成スペクトルは Gaussian ピーク + ノイズで生成した **教材用 toy データ** であり、
  「Indian Pines 相当」ではありません
- 実 HSI の大気補正残差・隣接効果・water-absorption bands 欠損・センサー応答を模倣していない
- **合成データで高精度が出ても、実データの性能は保証されません**
- 論文ベンチマーク目的には必ず実データ (Indian Pines / Salinas 等) を使用すること

## Indian Pines データの引用義務

Indian Pines データを使用・発表する場合は必ず引用してください:

> Landgrebe, D. (2003). *Signal Theory Methods in Multispectral Remote Sensing*.
> Wiley-Interscience.

関連する精度参照論文:
> Roy et al. (2020). "HybridSN", IEEE GRSL

`.mat` ファイルの正式なオープンライセンスは未文書化です。
研究・教育目的以外の利用は Purdue 大学に確認してください。

## 空間分割と精度の誇張

- **random_pixel split で Indian Pines を評価すると acc ~0.90 が出る場合があるが過大評価**
- 隣接ピクセルは高い空間相関を持つため、ランダム分割すると test セットが train と
  ほぼ同一の統計を持つ → `disjoint_patch` split を使うこと
- 単一シーン・単一日付のみで学習した場合、別日・別センサーで精度が急落する (domain shift)

## デュアルユース・悪用リスク

| 応用 | リスク |
|---|---|
| 精密農業・ドローン圃場モニタリング | プライバシー: 個人農地の植生/作付けが特定可能 |
| 衛星リモートセンシング | 国家地図規制・安全保障上の規制対象になり得る |
| 軍事 ISR (情報収集・偵察・監視) | カモフラージュ検出・施設識別への転用 |
| 野生生物追跡 | 密猟者による生息地・個体追跡への悪用 (ポーチングリスク) |
| 重要インフラ・標的識別 | 高分解能 HSI は軍事攻撃計画に利用可能 |
| 有人地上空の HSI 取得 | 各国の地図・航空写真規制・プライバシー法に抵触する可能性 |

## 追加注意事項

- **座標の集約リスク**: 高精度予測マップから人の行動パターンが推定可能な場合、
  公開前に座標の一般化・遅延公開・アクセス制御を検討すること
- **農業診断への過信**: 小規模ピクセル分類器を生産現場の収量予測・病害診断に
  直接適用しないこと; 現場検証なしの意思決定に使ってはならない
- **土地利用・農地権**: 合意なく他者の土地をマッピングすることは
  先住民の土地権・農地権の観点から倫理的問題を生じさせる可能性がある

## 説明可能性

- モデルがどのバンドを根拠に分類したかを示すことが重要
- 手法: **Saliency / SHAP / Integrated Gradients を band 次元に適用**
- 実装例: `captum.attr.IntegratedGradients` を Conv1d モデルに適用

## 参考文献

- Roy et al. (2020). *"HybridSN"*, IEEE GRSL
- Camps-Valls et al. (2020). *"Advances in Hyperspectral Image and Signal Processing"*,
  IEEE Signal Process. Mag.
- Landgrebe, D. (2003). *Signal Theory Methods in Multispectral Remote Sensing*. Wiley.
