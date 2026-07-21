# 01. 前提条件

## 1. Azure サブスクリプション

| 項目 | 内容 |
|---|---|
| Azure サブスクリプション | 有効。**必ず `../../../../docs/00-azure-account-setup.md` を先に読み**、Cost 予算アラート設定済み |
| 権限 | Resource Group を作成できる Owner または Contributor + User Access Administrator |
| リージョン | `japaneast` 推奨（`eastus2` でも動作） |

## 2. ローカル CLI

本 quickstart のシェルコマンドは **Bash** 前提です。以下のいずれかの環境で実行してください:

- **WSL2** (Windows) — Ubuntu 22.04 推奨
- **Linux / macOS** ネイティブ
- **[Azure Cloud Shell](https://shell.azure.com/)** — ブラウザだけで完結、`az` CLI 済み

PowerShell からのコピペは `curl` / `sed` / `stat` などの差異で動きません。

```bash
az version    # >= 2.65 推奨
az extension add --name ml --upgrade
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

## 3. 環境変数

以下を `~/.bashrc` などに追加、または現在のシェルで export します:

```bash
export AZURE_SUBSCRIPTION_ID="<sub-id>"
export AZURE_LOCATION="japaneast"
export AZURE_RESOURCE_GROUP="rg-spread-chem-molgen"
export AZURE_WORKSPACE_NAME="mlw-chem-molgen"
```

## 4. GPU quota は不要（ただし vCPU quota は確認）

本 quickstart は **CPU (`Standard_D4as_v5`, 4 vCPU)** で完結します。GPU quota の申請は不要ですが、**AML compute quota** は VM quota とは別枠なので Workspace デプロイ後に必ず確認してください:

```bash
export AZURE_LOCATION=japaneast   # または eastus2

# Workspace デプロイ後 (docs/02 実行後) に実行
az ml compute list-usage \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  -o table
```

以下 2 行が **`Limit - CurrentValue >= 4`** であることを確認:

- `Standard DASv5 Family Cluster Dedicated vCPUs`
- `Total Cluster Dedicated Regional vCPUs`

どちらかが不足している場合は Azure ML Studio → Workspace → **Manage → Quota** から `Standard DASv5 Family Cluster Dedicated vCPUs` の増加リクエストを送信してください（承認まで数時間〜1営業日）。

**すぐに動かしたい場合**は別リージョンで再構築するのが最速です。既存の Resource Group はそのリージョンに固定されているため、以下のように**新しい RG と Workspace 名**を設定して `docs/02-provision-aml.md` から再実行してください:

```bash
export AZURE_LOCATION="eastus2"
export AZURE_RESOURCE_GROUP="rg-spread-chem-molgen-eastus2"
export AZURE_WORKSPACE_NAME="mlw-chem-molgen-eastus2"
```

参考として Workspace デプロイ**前**にサブスクリプション全体の VM quota を確認する場合:

```bash
az vm list-usage --location "$AZURE_LOCATION" -o table \
  | grep -Ei "Total Regional vCPUs|Standard DASv5 Family"
```

> [!NOTE]
> Subscription の VM quota (`Standard DASv5 Family vCPUs`) と AML の Cluster Dedicated quota は**別枠**です。AML compute cluster を作れるかどうかは後者で決まります。

## 5. ローカル Python 環境（オプション、推奨）

`scripts/verify-output.py` を実行する場合や、生成結果をローカルで再スコアリングしたい場合:

```bash
python -m venv .venv && source .venv/bin/activate
pip install "rdkit==2026.3.4" \
            "azure-ai-ml==1.34.1" "azure-identity>=1.19.0" \
            "mlflow==2.16.2" "azureml-mlflow==1.57.0" \
            "pandas>=2.2"
```

> [!NOTE]
> RDKit は 2025 以降 pip wheel (Linux/macOS/Windows CPython 3.10/3.11/3.12) が公式に提供されるようになったため、conda は不要です。
