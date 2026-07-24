# 07 — 倫理と限界

## 信頼区間の過信は禁物

- GP の 95% CI は **kernel が真の関数族を含む** ときのみ意味を持つ
- 例: 真関数が周期を持たないのに ExpSineSquared kernel を使う → CI は意味なし
- 実装は必ず **残差診断** と **異なる kernel での LML 比較**をセットで行う

## 外挿の限界

- 学習範囲外での予測は本質的に不確実
- 周期カーネルは同位相の点に自信を持ち続けるため、「外挿で帯が広がる」とは限らない (docs/02-gp-concept.md 参照)
- **外挿値そのものは kernel の事前仮定に強く依存** — ポイント予測を絶対視しない

## スケール制約による選択バイアス

- n が大きい問題では sparse GP や別モデルを選択せざるを得ない
- 「使えるモデルの範囲でデータをサブサンプルした結果」がバイアスを生む可能性

## 高リスク用途の禁止事項

このシナリオのコードは **教育・研究プロトタイプ用途** のものです。以下の用途での使用は、必ず**独立した検証・専門家によるレビュー・説明責任の枠組み**を伴わない限り行わないでください:

- **気候・環境意思決定**: 行政判断に直結する予測 (排出規制、洪水リスク評価 等)
- **金融意思決定**: 投資・融資・保険の自動承認などリスクを伴う判断
- **地理空間鉱物資源探査**: 土地使用権・採掘許可に影響する分布推定
- **医療・安全システム**: 患者状態予測、機器異常検知等の生命に関わる用途

**センシティブな位置情報の取り扱い**: 地理座標・住所・個人の移動履歴等を含む実データに GP を適用する場合は、プライバシー影響評価を実施し、関連法令 (個人情報保護法, GDPR 等) に準拠してください。

## 参考文献

- Rasmussen, C. E. & Williams, C. K. I. (2006). *"Gaussian Processes for Machine Learning"*, MIT Press. (無料 PDF: https://gaussianprocess.org/gpml/)
- Foreman-Mackey et al. (2017). *"celerite: Scalable 1D Gaussian Processes in astronomy"*, AJ 154
- Duvenaud (2014). *"Automatic Model Construction with Gaussian Processes"*, PhD thesis (kernel selection ガイド)
