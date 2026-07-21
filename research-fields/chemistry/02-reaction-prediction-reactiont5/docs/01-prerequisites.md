# 01 — 事前準備

## シェル環境（重要）

このクイックスタートの `deploy.sh` は **Bash 前提**です。次のいずれかで実行してください：

- **Windows**: WSL2 (Ubuntu 22.04+ 推奨) — PowerShell では動きません
- **macOS**: 標準の zsh / bash で OK (`brew install jq` は不要、このシナリオでは jq を使いません)
- **Linux**: 標準の bash で OK
- **Azure Cloud Shell**: ブラウザで即実行可 (az CLI 全部入り)

## Azure CLI

```bash
az version
# azure-cli >= 2.60.0
# ml extension >= 2.30.0
```

インストール / 更新：

```bash
# CLI 本体
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash   # Ubuntu / WSL2

# ml v2 extension
az extension add -n ml
az extension update -n ml
```

## サインイン

```bash
az login
az account set --subscription "<Subscription 名 or ID>"
az account show -o table
```

## リージョン選定

T4 GPU (NCasT4_v3) は以下のリージョンで在庫が比較的安定しています：

| リージョン | 特徴 |
|---|---|
| `japaneast` | 日本国内、レイテンシ小 |
| `eastus` | 米国東部、在庫豊富 |
| `westeurope` | 欧州 |

デフォルトは `japaneast` で進めます。在庫が無い場合は `eastus` に切り替えてください（別 RG 名で再デプロイ）。

## Resource Provider の登録

```bash
az provider register --namespace Microsoft.MachineLearningServices --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.Storage --wait
az provider register --namespace Microsoft.KeyVault --wait
az provider register --namespace Microsoft.Insights --wait
az provider register --namespace Microsoft.OperationalInsights --wait
```

未登録のまま Bicep を実行すると `The subscription is not registered to use namespace ...` エラーで止まります。

## GPU クォータの確認

**AML Studio の GPU コンピュートは、通常の VM クォータとは別枠**です。両方を確認してください：

### 1. VM クォータ (概算・デプロイ前チェック)

```bash
az vm list-usage -l japaneast --query \
  "[?contains(name.value,'NCASv3_T4') || contains(name.value,'standardNCASv3T4Family')]" -o table
```

### 2. Azure ML Compute クォータ (実際に使う枠) — Workspace デプロイ後

Workspace デプロイ後 (`docs/02-provision-aml.md` の完了後) に：

```bash
az ml compute list-usage --location japaneast -o table 2>/dev/null | \
  grep -E "NCASv3|Total Cluster"
```

**次の 2 つが両方 4 以上**必要です：

- `Standard NCASv3_T4 Family Cluster Dedicated vCPUs` >= 4
- `Total Cluster Dedicated Regional vCPUs` >= 4

不足時は **Azure ML Studio → Manage → Quota → Request quota increase** から申請 (承認まで数時間〜1 営業日)。

## 検証スクリプト用の Python パッケージ (ローカル)

[`scripts/verify-output.py`](../scripts/verify-output.py) をローカルで実行するために、AML SDK と MLflow を含む Python 環境が必要です。

```bash
# Python 3.10+ を推奨
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

pip install \
  "azure-ai-ml>=1.20.0" \
  "azure-identity>=1.17.0" \
  "mlflow>=2.14.0" \
  "azureml-mlflow>=1.62.0"
```

> [!NOTE]
> このパッケージ群は**ローカルの verify-output.py 用**です。ジョブ側 (Azure ML コンピュート) の依存関係は `aml/conda.yml` で管理されており、こちらのローカル venv とは無関係です。

## 権限の確認

Bicep が Role Assignment を作成するため、以下のいずれかが必要です：

- **Owner** (推奨、最速)
- **Contributor + User Access Administrator**

```bash
az role assignment list --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --subscription "$(az account show --query id -o tsv)" \
  --query "[].roleDefinitionName" -o tsv
```

`Owner` または `Contributor` + `User Access Administrator` が含まれていれば OK。

次: [`02-provision-aml.md`](02-provision-aml.md)
