# トラブルシューティング

## セットアップ / RBAC

### `deploy.sh` が `AuthorizationFailed` で止まる
Bicep が Role Assignment を作成する権限は **User Access Administrator** または **Owner** が必要です。Contributor だけでは不足です。

### `The subscription is not registered to use namespace 'Microsoft.MachineLearningServices'`
Resource Provider が未登録です。[`docs/01-prerequisites.md`](docs/01-prerequisites.md) の**プロバイダー登録**手順を実行してください。

## クォータ

### `Operation could not be completed as it results in exceeding approved <Region> Cores quota`
Standard_NC4as_T4_v3 は **NCASv3_T4 Family Cluster Dedicated vCPUs** と **Total Cluster Dedicated Regional vCPUs** の両方の枠を消費します。両方が 4 以上あるか [`docs/01-prerequisites.md`](docs/01-prerequisites.md) で確認し、不足時はポータル (AML Studio → Manage → Quota) から Request quota increase を送信してください。

### 別リージョンで再デプロイしたい
既存 RG のリージョンは変更できません。**新しい RG 名 (例: `spread-chem-gnn-eastus-rg`)** と Workspace 名で `deploy.sh` を再実行してください。

## ジョブ実行

### `azureml-mlflow` のプラグインが認識されない / conda.yml を変更した
Environment version は immutable です。conda.yml を編集したら `environment.yml` の `version:` を上げ (例: `1` → `2`)、`az ml environment create -f aml/environment.yml` を再実行し、ジョブ送信時に `--set environment=azureml:molecule-gnn:2` で明示してください。

### `torch-scatter` / `torch-sparse` の wheel が無いエラー
本シナリオでは PyG 2.7 の**純 Python 実装**のみを使用しています。`torch-scatter` などの拡張は不要です。conda.yml に追加しないでください。もし独自に必要になった場合は、Torch 2.6 + CUDA 12.4 用 wheel を `https://data.pyg.org/whl/torch-2.6.0+cu124.html` からインストールしてください。

### RDKit がインストール中に固まる
`rdkit-pypi` (旧パッケージ) は非推奨です。conda.yml では `rdkit==2024.3.6` (新パッケージ) を指定しています。書き換えないでください。

### `CUDA out of memory`
ESOL は非常に小さい (1128 分子) ため、T4 (16 GB) で溢れることはほぼありません。他プロセスが GPU を掴んでいる可能性があるので、ジョブを再送してください。

## 学習結果

### `test_rmse` が 1.5 以上になる
ランダム分割の分割によっては起こり得ますが、`aml/job-train.yml` の `--seed` を変えて再実行してください。1.5 以上が続く場合：
- `--hidden 128` に増やす
- `--epochs 300 --patience 40` に伸ばす
- `--lr 5e-4` に下げる

### 逆に `test_r2` がとても高い (0.99+)
train / val / test の分割にリークがあるか、`y` の標準化を test にも適用してしまっている可能性があります。`src/train.py` の `mu`, `sd` は **train のみ**から計算しているか確認してください。

### `data.pt` を再利用したい
PyG は初回に `esol/processed/data.pt` を作成します。この pickle は PyG / RDKit のバージョンに依存するので、**Data Asset には登録しないでください**。生 CSV (`delaney-processed.csv`) だけを Asset に登録しています。

## クリーンアップ

### `az group delete` で `Cannot delete resource ... because it has resources`
削除ロックまたは Managed Identity の依存が残っている可能性があります。ポータルで RG を開き依存関係タブから孤立リソースを個別削除してから再実行してください。

### `--max-instances 0` が拒否される
AML CLI の `--max-instances` の最小値は 1 です。**課金停止には `min_instances: 0` (デフォルト) のままで十分**です。完全削除するなら `az ml compute delete -n gpu-cluster -y`。
