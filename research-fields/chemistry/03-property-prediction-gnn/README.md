# 03 — 分子物性 GNN (ESOL 溶解度予測)

MoleculeNet の **ESOL** データセット（水溶解度 1128 分子、回帰）を **PyTorch Geometric (PyG)** の **GINE** モデルで学習し、Azure ML v2 の T4 GPU で **10〜25 分**で end-to-end 完走します。

> [!NOTE]
> このシナリオは **学習 + 評価** を含みます（B-1, B-2 は推論のみでした）。分子グラフを扱う GNN の基本を体験できます。

## 何を得られるか

- Azure ML Workspace + T4 GPU コンピュート (Standard_NC4as_T4_v3) を Bicep で構築
- PyG (MIT) + RDKit (BSD-3) で MoleculeNet ESOL を学習
- GINE (3 層) を train → validate → test → MLflow に RMSE / MAE / R² を記録
- MoleculeNet ESOL の CSV を Data Asset として登録 (再現性・データリネージ)

## コスト

| 項目 | 実行中 (30 分) | 停止中 |
|---|---:|---:|
| **Standard_NC4as_T4_v3** (T4 GPU) | $0.36 | $0 (min=0) |
| Storage / Log Analytics / App Insights | 月額 $1 未満 | 同左 |
| **ACR Basic** | $0.007 | **$5/月** (削除しない限り継続) |
| **合計 (1 回)** | **約 $0.20〜0.50 (¥30〜75)** | — |

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
| 01 | [事前準備](docs/01-prerequisites.md) — az login, クォータ確認 | 10 分 |
| 02 | [AML Workspace デプロイ](docs/02-provision-aml.md) — Bicep で一括 | 5 分 |
| 03 | [データセット準備](docs/03-prepare-data.md) — ESOL CSV を取得しアップロード | 5 分 |
| 04 | [学習ジョブの実行](docs/04-train-and-evaluate.md) — GPU で GINE 学習 → 精度確認 | 15〜25 分 |
| 05 | [クリーンアップ](docs/05-cleanup.md) — RG を削除 | 3 分 |

## モデルとデータ

- **モデル**: [PyG GINEConv](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.GINEConv.html) 3 層 + global mean pool + MLP head (隠れ次元 64)
- **データ**: [MoleculeNet ESOL](https://moleculenet.org/datasets-1) — Delaney (2004) の 1128 分子、目的変数 = log10(mol/L) 溶解度
- **分割**: 80/10/10 のシード固定ランダム分割 (seed=42)
- **標準化**: 学習データの平均・分散で y を正規化 (推論時に逆変換)

## 期待される精度

| 分割 | RMSE | MAE | R² |
|---|---:|---:|---:|
| **期待値**（シード固定ランダム） | 0.70〜0.95 | 0.50〜0.75 | 0.60〜0.85 |
| **合格ライン** | ≤ 1.0 | ≤ 0.8 | ≥ 0.5 |

参考: MoleculeNet 元論文 (Wu et al., 2018) は GraphConv でランダム分割 RMSE ~0.58 を報告。本クイックスタートはより簡易な GINE 実装なので若干低め。

## ライセンス

- **PyG** ([pyg-team/pytorch_geometric](https://github.com/pyg-team/pytorch_geometric)): MIT
- **RDKit** ([rdkit/rdkit](https://github.com/rdkit/rdkit)): BSD-3-Clause
- **DeepChem MoleculeNet loader** ([deepchem/deepchem](https://github.com/deepchem/deepchem)): MIT
- **ESOL データ**: 明示的な独立ライセンス無し。Delaney (2004) の論文 (DOI [10.1021/ci034243x](https://doi.org/10.1021/ci034243x)) を引用してください。
- **本ドキュメントと `src/`, `infra/`, `scripts/`**: MIT

## 学術引用

- Delaney J. S. *ESOL: Estimating Aqueous Solubility Directly from Molecular Structure.* J. Chem. Inf. Comput. Sci. **2004**, 44, 1000-1005. https://doi.org/10.1021/ci034243x
- Wu Z. et al. *MoleculeNet: a benchmark for molecular machine learning.* Chem. Sci. **2018**, 9, 513-530. https://doi.org/10.1039/C7SC02664A
- Hu W. et al. *Strategies for Pre-training Graph Neural Networks.* ICLR **2020** (GINE). https://arxiv.org/abs/1905.12265

## 次のシナリオ

化学分野の 3 シナリオはこれで完了です。他分野の学習を続ける場合は [ルート README](../../../README.md) を参照してください。

## トラブルシューティング

問題が起きたら [`troubleshooting.md`](troubleshooting.md) を参照してください。
