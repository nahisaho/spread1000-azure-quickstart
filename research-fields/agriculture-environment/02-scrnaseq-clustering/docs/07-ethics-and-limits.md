# 07 — 倫理と限界

## クラスタリングの本質的限界

- **答えは 1 つではない**: resolution を変えれば違うクラスタ構造が得られる → 「正解」は生物学的コンテキストと annotation で決まる
- **UMAP 距離は無意味**: クラスタ間の距離、線の長さは topology のみ、絶対値解釈禁止
- **rank_genes は多重検定**: p-value をそのまま解釈しない、必ず fold change と一緒に見る

## Batch effect / confounding

- 由来サンプル、実験日、技術者、10x kit バージョン等が clustering を汚染しうる
- **UMAP でサンプル別に色分けして batch effect を確認**必須

## 少細胞クラスタの解釈

- < 20 細胞のクラスタは統計的に不安定 → 別実験での再現性確認
- 「Rare cell population 発見!」の前に doublet や artifact の可能性を除外

## Human data の場合

- 個人識別につながる遺伝子情報 (SNP 由来 variant) が RNA-seq にも含まれうる
- 公開時は de-identification と IRB 承認、GDPR / 個人情報保護法遵守が必須
- PBMC 3k は 10x Genomics が公開する健常人由来のオープンデータ

## 参考文献

- Luecken & Theis (2019). *"Current best practices in single-cell RNA-seq analysis: a tutorial"*, Mol. Syst. Biol.
- Heumos et al. (2023). *"Best practices for single-cell analysis across modalities"*, Nat. Rev. Genet.
