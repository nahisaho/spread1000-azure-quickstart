# 07 — 倫理と限界

## クラスタリングの本質的限界

- **答えは 1 つではない**: resolution を変えれば違うクラスタ構造が得られる → 「正解」は生物学的コンテキストと annotation で決まる
- **UMAP 距離は無意味**: クラスタ間の距離、線の長さは topology のみ、絶対値解釈禁止
- **rank_genes は探索的マーカー候補**: `rank_genes_groups` の p-value はクラスタが同一データから導出 (double-dipping) されるため anti-conservative。単一ドナー由来のセルは統計的に独立ではない。確証的 DE 解析には独立ドナーの pseudobulk + カウントモデル (DESeq2, edgeR, muscat) を使用すること。

## Batch effect / confounding

- 由来サンプル、実験日、技術者、10x kit バージョン等が clustering を汚染しうる
- **UMAP でサンプル別に色分けして batch effect を確認**必須

## 少細胞クラスタの解釈

- < 20 細胞のクラスタは統計的に不安定 → 別実験での再現性確認
- 「Rare cell population 発見!」の前に doublet や artifact の可能性を除外

## Human data の場合

### 発現データ (counts / h5ad)

- 個人識別につながる遺伝子情報 (SNP 由来 variant) が RNA-seq にも含まれうる
- 公開時は de-identification と IRB 承認、GDPR / 個人情報保護法遵守が必須
- PBMC 3k は 10x Genomics が公開する健常人由来のオープンデータ (CC BY 4.0)

### 生データ (FASTQ / BAM) の取扱い — 特に重要

生リードには識別可能な胚細胞変異 (germline variant) が含まれうるため、以下を必ず遵守してください:

- **Git / 公開ストレージへの配置禁止**: FASTQ/BAM を GitHub や公開クラウドバケットに置かない
- **管理リポジトリを使用**: dbGaP (米国)、EGA (欧州)、JGA (日本) などの controlled-access リポジトリを利用する
- **同意書と DUA の確認**: データ受領前に被験者同意書 (informed consent) とデータ利用契約 (DUA) を確認する
- **アクセス制御**: RBAC (ロールベースアクセス制御) + 最小権限原則をストレージに適用する
- **暗号化**: 保管時 (at rest) および転送時 (in transit) の暗号化を徹底する
- **監査ログ**: ストレージおよび処理環境への全アクセスを記録する
- **保持と削除**: 保持期間ポリシーを定め、期限後は安全に削除する
- **データ所在地制約**: EU 居住者データは EU 内での処理が GDPR で求められる場合がある
- **法的フレームワーク**:
  - 米国: HIPAA (保護健康情報)
  - EU: GDPR Article 9 (特別カテゴリ個人データ)
  - 日本: 個人情報保護法の「要配慮個人情報」(遺伝情報)

## PBMC 3k データセット

- **ライセンス**: 10x Genomics PBMC3k — CC BY 4.0
- **出典**: https://support.10xgenomics.com/single-cell-gene-expression/datasets/1.1.0/pbmc3k
- **論文**: Zheng et al. (2017). *"Massively parallel digital transcriptional profiling of single cells"*, Nature Communications. DOI: [10.1038/ncomms14049](https://doi.org/10.1038/ncomms14049)
- **ダウンロード元**: Scanpy 1.10+ は `falexwolf.de/data/pbmc3k_raw.h5ad` から変換済み H5AD を取得 (10x 直接ではない)
- SHA-256 は初回実行後に `outputs/metrics.json` の `provenance.dataset_sha256` フィールドに記録されます

## 参考文献

- Luecken & Theis (2019). *"Current best practices in single-cell RNA-seq analysis: a tutorial"*, Mol. Syst. Biol.
- Heumos et al. (2023). *"Best practices for single-cell analysis across modalities"*, Nat. Rev. Genet.
