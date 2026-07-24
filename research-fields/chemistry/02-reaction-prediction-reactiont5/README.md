# 02 — 反応予測 (ReactionT5v2 forward)

反応物 (reactants) から生成物 (product) を予測する Seq2Seq モデル **ReactionT5v2** ([sagawa/ReactionT5v2-forward](https://huggingface.co/sagawa/ReactionT5v2-forward)) を Azure Machine Learning v2 の T4 GPU で動かします。日本人研究者 (Sagawa & Kojima) による T5 ベースモデルで、USPTO-MIT で top-1 92.8% を達成しています。

> [!NOTE]
> このシナリオは **推論のみ** です（学習は行いません）。事前学習済みチェックポイント (~0.8 GB, MIT ライセンス) を Hugging Face から取得し、5〜10 反応を予測して精度を確認します。

## 何を得られるか

- Azure ML Workspace + T4 GPU コンピュート (Standard_NC4as_T4_v3) を Bicep で構築
- Hugging Face から MIT ライセンスのチェックポイントを取得 (revision pin 済み)
- 5 反応のデモを 15〜30 分で完走 (top-1 一致率 / 有効 SMILES 率を MLflow ログ)
- 独自の反応 CSV に差し替えて自分の反応を予測可能

## コスト

| 項目 | 実行中 (30 分) | 停止中 |
|---|---:|---:|
| **Standard_NC4as_T4_v3** (T4 GPU) | $0.36 | $0 (min=0) |
| Storage / Log Analytics / App Insights | 月額 $1 未満 | 同左 |
| **ACR Basic** | $0.007 | **$5/月** (削除しない限り継続) |
| **合計 (1 回)** | **約 $0.18〜0.50 (¥30〜75)** | — |

> [!IMPORTANT]
> ACR Basic は停止不可の固定課金です。使い終わったら [`docs/05-cleanup.md`](docs/05-cleanup.md) の**リソースグループごと削除**を必ず実施してください。

## 前提

- Azure サブスクリプション (Owner または Contributor + User Access Administrator)
- **NCasT4_v3 系 GPU クォータが 4 vCPU 以上** ([`docs/01-prerequisites.md`](docs/01-prerequisites.md) で確認)
- **Bash 環境** (WSL2 / Linux / macOS / Cloud Shell) — PowerShell では動きません
- az CLI v2.60+, ml extension v2.30+

## 実行順序

| # | 手順 | 所要 |
|---:|---|---:|
| 01 | [事前準備](docs/01-prerequisites.md) — az login, クォータ確認, リージョン選定 | 10 分 |
| 02 | [AML Workspace デプロイ](docs/02-provision-aml.md) — Bicep で一括 | 5 分 |
| 03 | [反応データの準備](docs/03-prepare-data.md) — デモ CSV をアップロード | 5 分 |
| 04 | [予測ジョブの実行](docs/04-predict-and-evaluate.md) — GPU で推論 → 精度確認 | 15〜30 分 |
| 05 | [クリーンアップ](docs/05-cleanup.md) — RG を削除 | 3 分 |

## ライセンス

- **モデル** ([sagawa/ReactionT5v2-forward](https://huggingface.co/sagawa/ReactionT5v2-forward)): MIT。学習は Open Reaction Database (ORD) で行われ、USPTO-MIT ベンチマークで top-1 92.8% を達成（[モデルカード参照](https://huggingface.co/sagawa/ReactionT5v2-forward)）。
- **コード** ([sagawatatsuya/ReactionT5v2](https://github.com/sagawatatsuya/ReactionT5v2)): MIT
- **学習データ** (Open Reaction Database, ORD): CC BY-SA 4.0
- **同梱デモ CSV (`data/demo-reactions.csv`)**: ORD (CC BY-SA 4.0) から抽出・改変した 5 反応レコードを含みます。試薬列 (`reagents`) は溶媒/触媒等を人が抜粋しており、元 ORD レコードの完全再現ではありません。**継承ライセンス: CC BY-SA 4.0**。改変履歴は `data/demo-reactions.csv` のコメント行と `docs/03-prepare-data.md` に記載。個別レコードの ORD ID (`ord-...`) が失われているため、独自データで実験する際は `docs/03-prepare-data.md` の手順で ORD から直接取得することを推奨します。
- **本ドキュメントと `src/`, `infra/`, `scripts/`**: 親リポジトリ (SPReAD-1000 Azure Quickstart) と同じライセンス。ライセンスファイルが未整備の場合は「All rights reserved (研究利用に限る)」として扱ってください。

## 学術引用

Sagawa T., Kojima R. *ReactionT5: a pre-trained transformer model for accurate chemical reaction prediction with limited data*. Journal of Cheminformatics (2025). https://doi.org/10.1186/s13321-025-01075-4

## 次のシナリオ

- **[03 — 分子物性 GNN (予定)](../03-molecular-property-gnn/)** — MoleculeNet トキシシティ/溶解度予測

## トラブルシューティング

問題が起きたら [`troubleshooting.md`](troubleshooting.md) を参照してください。
