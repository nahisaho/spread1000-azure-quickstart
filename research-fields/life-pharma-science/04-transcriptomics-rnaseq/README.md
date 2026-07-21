# RNA-Seq on Azure Batch (nf-core/rnaseq) クイックスタート

> **対象読者**: SPReAD-1000 採択者のうち、RNA-Seq (トランスクリプトーム定量) を Azure 上で流したいバイオインフォマティクス初心者。Azure・Nextflow のどちらも未経験を想定。

## 概要 / このシナリオで学べること

- **Azure Batch** (バッチジョブの管理サービス) + **Nextflow** (再現性の高いワークフロー実行エンジン) + **Blob Storage** (`az://` プロトコルで Nextflow から直接読み書きできるオブジェクトストレージ) を組み合わせ、**nf-core/rnaseq** パイプラインをフルマネージドで実行します。
- 標準ルート: **STAR** でリファレンスにアラインメント → **Salmon** で転写産物定量 → **MultiQC** で QC レポート集約。
- **6 サンプル × 40M paired-end reads** クラスの標準解析を、CPU only の autoscale プールで並列実行します。GPU 不要です。
- 完走後は **pool を自動で 0 ノードに縮小**し、無駄な課金を止めます。

> [!WARNING]
> **プールを 0 に縮小し忘れると 1 日あたり数万円の課金が続きます。**
> 最低: `az batch pool delete` または autoscale で `$TargetDedicatedNodes = 0; $TargetLowPriorityNodes = 0` (Spot 使用時は両方必須)
> クリーンアップの詳細は必ず `docs/05-cleanup.md` を参照してください。

> [!IMPORTANT]
> **本パイプラインは発現量マトリクス (counts / TPM) を作りますが、差次的発現解析 (DE)  の p 値・FDR・log2FC は生成しません**。DE 解析は
> `nf-core/differentialabundance` や自作 R/DESeq2 スクリプトで別途実行してください ([docs/04-real-data.md#8-差次的発現解析-de-を続ける場合](docs/04-real-data.md#8-差次的発現解析-de-を続ける場合) に概略あり)。

## 前提条件

- Azure サブスクリプション (Owner または Contributor + User Access Administrator)
- Azure CLI 2.60 以上、Bash / WSL 環境
- **Batch アカウントの dedicated core quota が 0 でないこと** (新規サブスクリプションでは 0 の場合あり — `docs/01-prerequisites.md` の手順で申請)
- Standard_D8ds_v5 (デモ) / Standard_E16ds_v5 (本番) SKU が対象リージョンで利用可能
- Blob Storage 用に 30 GB (デモ) 〜 300 GB (本番) の空き容量

**推奨リージョン**: Japan East → Japan West → East US 2

## 所要時間の目安

| ステップ | 時間 |
|---|---:|
| Azure リソースの Bicep デプロイ | 10〜15 分 |
| Controller VM への Nextflow インストール | 5 分 |
| Blob へのデータアップロード (デモ) | 5 分未満 |
| **nf-core/rnaseq test プロファイル実行** | 20〜40 分 (pool 起動 + コンテナ pull 含む) |
| 本番 6 サンプル解析 | 2〜4 時間 (E16ds_v5 × 6 dedicated) |
| クリーンアップ | 5〜10 分 |

## 想定コスト (Japan East, 2026-07 Azure Retail Prices API 目安)

以下は **代表的な実行シナリオでの試算** です。`config/nextflow.azure.config` の `machineType = 'Standard_D*ds_v5,Standard_E*ds_v5'` により、Nextflow は工程ごとに複数のプールを作ることがあり、そのたびに Batch service が最適な SKU を選びます。したがって「E16ds_v5 × 6」は上限ではなく想定平均であり、実際は数プール分の合計が課金対象になる点にご注意ください (`maxVmCount=10` は **プールごとの上限** です)。

| 項目 | 単価 | デモ (30 分実行) | 本番 6 サンプル (3 時間実行) |
|---|---:|---:|---:|
| **Batch 基盤料金** | ¥0 | ¥0 | ¥0 |
| Batch ノード: D8ds_v5 (デモ) | ¥94.45/h | 2 × 0.5h = ¥95 | — |
| Batch ノード: E16ds_v5 (本番, dedicated) | ¥225.14/h | — | 6 × 3h = ¥4,053 |
| Batch ノード: E16ds_v5 (本番, Spot) | ¥41.61/h | — | 6 × 3h = ¥749 (eviction リスクあり) |
| Controller VM: Standard_B2s (常時) | ¥8.80/h | ¥8.80 | ¥26.40 (3h) |
| Controller VM OS ディスク: Standard SSD 64GB | ¥770/月 | ¥26 (1日按分) | ¥26 (1日按分) |
| Public IP (Standard, static) | ¥590/月 | ¥20 (1日按分) | ¥20 (1日按分) |
| Blob Storage Hot LRS | ¥3.23/GB/月 | 30GB × 1日 = ¥3 | 270GB × 1日 = ¥29 |
| **完走時合計** | | **約 ¥153** | **約 ¥4,154 (dedicated) / ¥850 (Spot)** |

> [!NOTE]
> VNet 自体は無料。OS ディスクと Public IP は月額課金のため、実行時間に関わらず月末まで発生します。上表は 1 日按分の目安。使わない期間は Controller VM を `deallocate` してもディスク・IP 課金は継続する点にご注意ください (完全に止めるにはリソースグループ削除)。

> [!WARNING]
> **プールを縮小せず 1 週間放置すると: E16ds_v5 × 6 dedicated = 6 × 168h × ¥225.14 ≈ ¥227,000**
> 必ず `deploy.sh` が設定する **autoscale (idle 15 分で 0 ノード)** が有効か `docs/05-cleanup.md` で確認してください。

## 次のステップ

1. [docs/01-prerequisites.md](docs/01-prerequisites.md) — Azure サブスクリプション準備、Batch quota 確認・申請
2. [docs/02-provision-batch.md](docs/02-provision-batch.md) — Bicep で Batch + Storage + Controller VM をデプロイ
3. [docs/03-run-demo.md](docs/03-run-demo.md) — nf-core/rnaseq の test プロファイルでスモーク実行
4. [docs/04-real-data.md](docs/04-real-data.md) — 実データ (Human GRCh38 + GENCODE v50) で本番解析
5. [docs/05-cleanup.md](docs/05-cleanup.md) — プール停止、Blob ライフサイクル、リソースグループ削除
6. [docs/troubleshooting.md](docs/troubleshooting.md) — 頻出エラーと対処

## 関連クイックスタート

- **タンパク質構造予測**: [ESMFold](../../molecular-gnn/esmfold-structure-prediction/) / [AlphaFold 3](../../molecular-gnn/alphafold3-structure-prediction/)
- **薬剤設計 (基盤モデル)**: [TamGen](../../foundation-model-science/tamgen-drug-discovery/)

## 参考

- nf-core/rnaseq 3.26.0 (MIT): https://nf-co.re/rnaseq/3.26.0/
- Nextflow 26.04.6 (Apache 2.0): https://docs.seqera.io/nextflow/
- Nextflow Azure Batch executor: https://docs.seqera.io/nextflow/azure
- Azure Batch: https://learn.microsoft.com/en-us/azure/batch/batch-technical-overview

## サポート

- **Azure 側の問題**: Microsoft Q&A / サポートリクエスト
- **nf-core/rnaseq 側の問題**: [nf-core Slack #rnaseq](https://nf-co.re/join) / [GitHub Issues](https://github.com/nf-core/rnaseq/issues)
- **このクイックスタート自体の問題**: [Issues](https://github.com/nahisaho/spread1000-azure-quickstart/issues) で報告してください
