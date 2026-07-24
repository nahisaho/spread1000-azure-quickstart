# 分子生成 (REINVENT4) — SPReAD-1000 Azure Quickstart

Azure ML v2 command job で **REINVENT4 v4.8** を実行し、**LibInvent scaffold decoration** を体験する **CPU で完結**する最短ルート。

> [!IMPORTANT]
> **ライセンスの適用範囲について**: REINVENT4 コード、公開 prior、Azure Bicep テンプレート等は Apache-2.0 で提供されますが、これは**ソフトウェア/モデル成果物の利用条件**に限られます。生成された化学構造の**特許自由度 (Freedom-to-Operate)、化学的安全性、規制遵守 (医薬品医療機器法・PIC/S GMP・化管法など)、実験・治験での適法性**については一切保証されません。生成物を実物質として合成・使用する前に、必ず所属機関の**知財部門・EHS 部門・IRB 等**へ相談し、患者・環境への影響評価と関連法規のレビューを実施してください。

## 想定ユーザー

- 化学分野の SPReAD-1000 採択者で、AI-for-Chemistry と Azure の両方が初めて
- ローカルには Docker/GPU 不要。**WSL2 / Linux / macOS / Azure Cloud Shell** のいずれかの Bash 環境と `az` CLI があれば OK（PowerShell からの直接コピペは非対応）
- 目標: 30 分以内に「scaffold → 100 分子生成 → RDKit で物性スコアリング → QED top-20 を可視化」まで一気通貫

## シナリオ概要

| 項目 | 内容 |
|---|---|
| モデル | REINVENT4 v4.8 (Apache-2.0) + LibInvent scaffold decoration prior |
| Priors | Zenodo record 20701824 (`libinvent.prior`, `reinvent_pubchem.prior`) — Apache-2.0 |
| 計算 | Azure ML `Standard_D4as_v5` (4 vCPU, 16 GB, CPU) — `min_instances=0` |
| 想定コスト | **$0.10〜0.50 / 1 run** |
| 想定所要時間 | 初回 40〜60 分（Bicep デプロイ + image build + 生成ラン） |

## ステップ

1. [前提条件](docs/01-prerequisites.md) — Azure サブスク、CLI、ml 拡張
2. [インフラ deployment](docs/02-provision-aml.md) — Bicep で AML Workspace + 依存リソース
3. [Prior のダウンロードとアップロード](docs/03-download-and-upload.md) — Zenodo priors を Blob に格納
4. [生成ジョブ実行と評価](docs/04-generate-and-evaluate.md) — LibInvent サンプリング → RDKit スコアリング
5. [クリーンアップ](docs/05-cleanup.md) — Compute 停止、RG 削除

## コスト内訳

| 項目 | 目安 |
|---|---|
| 初回デプロイ (Bicep) | 3〜5 分 |
| Environment build (初回のみ) | 5〜10 分 |
| Prior ダウンロード + Blob 登録 | 1〜2 分 |
| 生成ラン (CPU, 100〜1000 分子) | 5〜15 分 |
| **合計初回** | 約 20〜40 分 |
| **VM 料金 (D4as_v5 Japan East, 15 分)** | **約 $0.04** |
| ACR Basic (固定) | 約 $5/月 (0.167 USD/日) |
| Storage / Log Analytics / App Insights | 月額 $1 未満（本チュートリアル規模） |
| **想定 1 run 総コスト** | **$0.10〜0.50** |

> [!TIP]
> `compute-cpu.yml` の `min_instances: 0` により、ジョブが完了すればノードは自動的にスケールダウンし compute VM 課金は 0 になります。ACR Basic は月 $5 程度発生するため、長期的に使わない場合は Resource Group ごと削除してください。

## 生成 = 何が得られるのか

1. `outputs.molecules/sampled.csv` — REINVENT が生成した SMILES + NLL (RAW; 無効/重複を含む)
2. `outputs.molecules/scored.csv` — RDKit で MW / LogP / QED / TPSA を付与。**RDKit がパースできた有効分子のみ**。生成された全 SMILES 数 (`n_total`) と有効数 (`n_valid`) は MLflow メトリクスと `scored.csv` のヘッダで確認できます。
3. `outputs.molecules/top20.png` — QED でソートした top-20 の 2D 分子構造画像
4. MLflow メトリクス: `n_total`, `n_valid`, `n_unique`, `valid_ratio`, `unique_ratio`, `mean_qed`, `mean_mw`, `mean_logp`

## データセット

| 項目 | 内容 |
|---|---|
| Prior 種 | REINVENT4 official priors (Zenodo [record 20701824](https://zenodo.org/records/20701824)) |
| ライセンス | Apache-2.0 |
| 出典 | Loeffler et al. *J. Cheminform.* 16:20, 2024 — REINVENT4 |

> [!NOTE]
> 本 quickstart は生成のみ扱い、外部データセットとの新規性比較 (MOSES/ZINC novelty) は含まれません。novelty を評価したい場合は生成後に自前で `moses.metrics.novelty` を回すか、SPReAD-1000 内部データセットとの重複を RDKit で確認する追加ジョブを別途作成してください。

## 共有ドキュメント

- [../../../docs/00-azure-account-setup.md](../../../docs/00-azure-account-setup.md)
- [../../../docs/01-cost-management.md](../../../docs/01-cost-management.md)
- [../../../docs/02-gpu-quota.md](../../../docs/02-gpu-quota.md) — 本 quickstart は CPU のみのため GPU quota は不要

## トラブルシュート

問題が起きたら [troubleshooting.md](troubleshooting.md) を参照。
