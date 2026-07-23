# 07 — 倫理と限界

## 信頼区間の過信は禁物

- GP の 95% CI は **kernel が真の関数族を含む** ときのみ意味を持つ
- 例: 真関数が周期を持たないのに ExpSineSquared kernel を使う → CI は意味なし
- 実装は必ず **残差診断** と **異なる kernel での LML 比較**をセットで行う

## 外挿の限界

- 学習範囲外での予測は本質的に不確実
- GP は「不確実性が増す」ことを教えてくれるが、**外挿値そのものは kernel の事前仮定に強く依存**
- 気候予測、金融予測などで GP のポイント予測を絶対視しない

## スケール制約による選択バイアス

- n が大きい問題では sparse GP や別モデルを選択せざるを得ない
- 「使えるモデルの範囲でデータをサブサンプルした結果」がバイアスを生む可能性

## 参考文献

- Rasmussen, C. E. & Williams, C. K. I. (2006). *"Gaussian Processes for Machine Learning"*, MIT Press. (無料 PDF: https://gaussianprocess.org/gpml/)
- Foreman-Mackey et al. (2017). *"celerite: Scalable 1D Gaussian Processes in astronomy"*, AJ 154
- Duvenaud (2014). *"Automatic Model Construction with Gaussian Processes"*, PhD thesis (kernel selection ガイド)
