# 医用画像 3D セグメンテーション (MONAI + Azure Machine Learning)

> 分野: **臨床科学 (medical-imaging)** — SPReAD-1000

**Project MONAI** の Model Zoo Bundle (`spleen_ct_segmentation` v0.6.1) を Azure Machine Learning (AML) の GPU 上で動かし、公開 CT データセット **Medical Segmentation Decathlon Task09_Spleen** に対して事前学習モデルの推論 → fine-tuning → 評価を行うクイックスタート。

## このクイックスタートで得られるもの

- **1〜2 時間で最初の予測 mask** (NIfTI `.nii.gz`) を生成
- Bundle 公称 mean Dice **0.961** (validation) を Azure 上で再現
- 事前学習重みを起点にした fine-tuning ジョブのテンプレート
- AML の Compute Cluster、Data Asset、Environment、Command Job の実装パターン
- **NC24ads_A100_v4** (1×A100 80GB) または **NC4as_T4_v3** (1×T4 16GB) の 2 パス選択

## 対象読者

- MONAI/PyTorch は触ったことがあるが Azure は初めての PI・研究員
- 施設の CT/MRI データを使ってセグメンテーションモデルを試したい
- GPU クォータ申請・データ資産管理・コスト管理まで含めて 1 通り理解したい

## 何をやるか

1. Bicep で AML ワークスペース + Storage + ACR + Key Vault + App Insights を作る
2. GPU Compute Cluster (autoscale, `min_instances=0`) を登録
3. MONAI 1.4.0 + PyTorch 2.4.0 のカスタム Environment を登録
4. MSD Task09_Spleen (公開 CC-BY-SA 4.0) をダウンロードして Blob に登録
5. **推論 Job** で事前学習 Bundle を実行 → 予測 mask 生成
6. **Fine-tuning Job** で 100 epoch の再学習 → validation Dice 確認
7. Cluster を 0 ノードに縮小 → 課金停止

> [!WARNING]
> **GPU Cluster の `min_instances` を 0 に戻し忘れると 1 日あたり数千〜数万円の課金が続きます。**
> クリーンアップは `docs/05-cleanup.md` を必ず参照してください。

> [!IMPORTANT]
> 本 Bundle は **研究用途** で、`spleen_ct_segmentation` のライセンスファイルに "not to be used for diagnostic purposes" と明記されています。臨床診断・意思決定には使用しないでください。

## 前提条件

- Azure サブスクリプション (Owner または Contributor + User Access Administrator)
- Azure CLI 2.60 以上 + `ml` extension (`az extension add -n ml`)
- **NCADSA100v4 Family クォータ 24 以上** (A100 パス) または **NCASv3_T4 Family クォータ 4 以上** (T4 パス)
- Bash / WSL 環境
- リージョン: **Japan East** 推奨 (`az vm list-skus` で SKU 空きを事前確認)

## 標準ワークフロー (推奨リージョン: Japan East)

| # | ステップ | 所要時間 | 目安コスト (JPY, 東日本) |
|---|---|---:|---:|
| 1 | AML ワークスペース + 依存リソース作成 | 5〜10 分 | 初期費用 0 (idle) |
| 2 | GPU クォータ確認・申請 | 即時〜1 営業日 | 0 |
| 3 | Task09_Spleen ダウンロード + Blob 登録 | 5〜10 分 | ¥5/月 (ストレージ) |
| 4 | Environment 登録 (初回のみ ACR ビルド) | 10〜20 分 | 数十円 (ACR ビルド) |
| 5 | 推論 Job (T4, pretrained inference) | 15〜25 分 | 約 ¥50〜100 |
| 6 | Fine-tuning Job (A100, 100 epoch) | 2〜3 時間 | Dedicated 約 ¥1,700〜2,600 / Spot 約 ¥320〜480 |
| 7 | Cluster を 0 ノードに縮小 | 即時 | 以後 idle 無料 |

> [!NOTE]
> A100 の Japan East PAYG (Pay-As-You-Go) は約 **¥861/h** です (2026-07 Retail Prices API 実測値)。Spot は約 ¥160/h ですが、eviction される可能性があるため checkpoint を頻繁に保存するジョブ以外では推奨しません。

## 主要リソース

| リソース | 用途 | 課金 |
|---|---|---|
| Azure Machine Learning Workspace | ジョブ・データ・環境管理 | 無料 (関連リソースのみ課金) |
| Storage Account (LRS Hot) | データセット + Job artifacts | ¥3.23/GB/月 |
| Azure Container Registry (Basic) | カスタム Environment image | ¥600/月 |
| Key Vault (Standard) | Workspace secret | ¥30/月 |
| Application Insights | ジョブログ | 5 GB まで無料 |
| Compute Cluster A100 (idle) | GPU 計算 | idle は 0 (min_instances=0) |
| Compute Cluster T4 (idle) | 低コスト推論 | idle は 0 |

> [!TIP]
> **AML Workspace 単体を削除しても、Storage/ACR/Key Vault/App Insights は残ります。**
> 完全に消したいときはクイックスタート専用 Resource Group ごと `az group delete` するのが確実です。

## 手順

1. [`docs/01-prerequisites.md`](docs/01-prerequisites.md) — Azure CLI, ml extension, クォータ, サブスクリプション確認
2. [`docs/02-provision-aml.md`](docs/02-provision-aml.md) — Bicep で AML + 依存リソース作成、Compute Cluster & Environment 登録
3. [`docs/03-run-inference.md`](docs/03-run-inference.md) — 事前学習 Bundle で推論 (T4, 15〜25 分)
4. [`docs/04-fine-tuning.md`](docs/04-fine-tuning.md) — A100 で 100 epoch fine-tuning、Dice 評価
5. [`docs/05-cleanup.md`](docs/05-cleanup.md) — Cluster 縮小 & 全リソース削除
6. [`docs/troubleshooting.md`](docs/troubleshooting.md) — GPU quota 拒否、OOM、Bundle download 失敗 など

## ライセンス

| コンポーネント | ライセンス |
|---|---|
| MONAI 1.4.0 (Core) | Apache 2.0 |
| Bundle `spleen_ct_segmentation` v0.6.1 | Apache 2.0 |
| Medical Segmentation Decathlon Task09_Spleen | **CC BY-SA 4.0** (出典明示・派生条件を確認) |
| 本テンプレート (Bicep/YAML/Bash) | 本リポジトリの LICENSE に準拠 |

## 引用

論文で MSD Task09 を利用した場合は以下を引用してください:

- Antonelli, M. et al. *The Medical Segmentation Decathlon.* Nat. Commun. 13, 4128 (2022). https://doi.org/10.1038/s41467-022-30695-9
