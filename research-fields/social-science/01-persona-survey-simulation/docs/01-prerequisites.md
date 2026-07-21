# 01 — 事前準備

## シェル環境

- **Windows**: WSL2 (Ubuntu 22.04+ 推奨) — PowerShell では動きません
- **macOS**: 標準の zsh / bash で OK
- **Linux**: 標準の bash で OK
- **Azure Cloud Shell**: ブラウザで即実行可

## Azure CLI

```bash
az version
# azure-cli >= 2.60.0
```

サインイン：

```bash
az login
az account set --subscription "<Subscription 名 or ID>"
az account show -o table
```

## リージョン選定

このシナリオは **`japaneast`** を既定にしています。gpt-4.1-mini の Regional（推論を Japan East 内で処理）デプロイが可能なリージョンです。

他リージョンの選択肢:

| リージョン | 特徴 |
|---|---|
| `japaneast` | 日本国内推論、レイテンシ小 |
| `eastus` | 最も多くのモデルが最速で利用可 |
| `swedencentral` | EU、多くの新モデルが早く利用可 |

## Azure OpenAI 利用登録

2026 年時点で新規サブスクリプションでは Azure OpenAI 利用登録が必要な場合があります：

- 申請先: <https://aka.ms/oai/access>
- 承認まで通常は数時間〜1 営業日

登録済みかは以下で確認できます：

```bash
az cognitiveservices account list-kinds -o table | grep OpenAI
```

## Resource Provider の登録

```bash
az provider register --namespace Microsoft.CognitiveServices --wait
az provider register --namespace Microsoft.Insights --wait
az provider register --namespace Microsoft.OperationalInsights --wait
```

## Python 環境

シミュレーションと分析はローカル (または Cloud Shell) の Python で実行します：

```bash
# Python 3.10+ を推奨
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

pip install \
  "openai>=1.50.0" \
  "azure-identity>=1.17.0" \
  "pydantic>=2.7.0" \
  "pandas>=2.2.0" \
  "scipy>=1.13.0" \
  "matplotlib>=3.8.0" \
  "python-dotenv>=1.0.0"
```

## 権限の確認

Bicep が Role Assignment を作成するため、以下のいずれかが必要です：

- **Owner** (推奨、最速)
- **Contributor + User Access Administrator**

```bash
az role assignment list --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --subscription "$(az account show --query id -o tsv)" \
  --query "[].roleDefinitionName" -o tsv
```

次: [`02-provision-aoai.md`](02-provision-aoai.md)
