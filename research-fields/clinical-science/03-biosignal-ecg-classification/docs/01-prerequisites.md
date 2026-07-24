# 01. 事前準備

## 必要なもの

| 項目 | 内容 |
|---|---|
| Azure サブスクリプション | 有効。**必ず `../../../../docs/00-azure-account-setup.md` を先に読み**、Cost 予算アラート設定済み |
| Azure サブスクリプション権限 | **Owner** / **User Access Administrator** / **Role Based Access Control Administrator** のいずれか (Bicep が `Microsoft.Authorization/roleAssignments/write` を必要とするため、`Contributor` のみでは失敗します)。組織で権限が下りない場合は、docs/02 の RBAC 節を管理者に代行依頼するパスを利用してください |
| OS | Linux / WSL2 / macOS (bash + wget + jq が動作すること) |
| Azure CLI | 2.65+ + `az extension add -n ml` (Azure ML CLI v2 extension) |
| Python | 3.10 以上（ローカルでの事前検証用。AML 実行環境は別途構築） |

## 1. Azure CLI + ML extension

```bash
az --version                   # 2.65+
az extension add -n ml -y      # v2
az extension update -n ml
az ml -h                       # 動作確認
```

## 2. ログイン

```bash
az login
az account set --subscription "<subscription-id>"
```

## 3. GPU quota チェック

本 quickstart は **`Standard_NC4as_T4_v3`** (T4, 4 vCPU) を使います。新規サブスクリプションでは GPU quota は **通常 0** なので、事前に確認・申請してください。

> [!IMPORTANT]
> Azure ML compute cluster の quota は **サブスクリプション VM quota とは別枠** です。事前チェックは Workspace デプロイ**後**に AML CLI で行うのが確実です:
>
> ```bash
> export AZURE_LOCATION=japaneast   # または eastus2
>
> az ml compute list-usage \
>   -g "$AZURE_RESOURCE_GROUP" \
>   -w "$AZURE_WORKSPACE_NAME" \
>   -o table
> ```
>
> 以下の 2 行を確認し、**`Limit - CurrentValue >= 4`** であることを検証します:
> - `NCASv3_T4 Family Cluster Dedicated vCPUs`
> - `Total Cluster Dedicated Regional vCPUs`
>
> どちらかが不足している場合は quota 増加リクエストを送信してください（承認まで数時間〜1営業日）。**AML 用の cluster quota は Azure Portal からは以下の 2 経路のいずれか**から申請します:
>
> - **推奨**: Azure ML Studio → Workspace → **Manage → Quota**（または Azure Portal の Workspace → **Support + troubleshooting → Usage + quotas**） → `Standard NCASv3_T4 Family Cluster Dedicated vCPUs` と `Total Cluster Dedicated Regional vCPUs` の Request quota
> - **代替**: `az ml compute list-usage` で `usage-id` を確認 → 同じサブスクリプション内で AML Studio から申請
>
> Subscription 全体の "Usage + quotas" ページから申請する **VM (Standard NCASv3_T4 Family) vCPUs は直接 VM 作成用**の別枠なので、AML compute の quota 不足解消にはなりません。詳しくは [`../../../../docs/02-gpu-quota.md`](../../../../docs/02-gpu-quota.md)。

Workspace デプロイ**前**にざっと目安を見るだけであれば、参考として `az vm list-usage --location $AZURE_LOCATION` の `NCASv3_T4` 行も見られますが、これは直接 VM 作成用の quota なので AML 実行可否の判定には使えません。

> [!TIP]
> **GPU quota が 0 のままでも学習は可能**です。`aml/compute-cpu.yml` (`Standard_D4as_v5`) を使えば CPU で 60〜90 分で完走します（想定コスト $0.3 未満）。この場合は quota 申請が承認されるまで CPU で続行できます。

## 4. AML Workspace 用の環境変数

以下を bashrc に追加、または現在のシェルに export します:

```bash
export AZURE_LOCATION=japaneast
export AZURE_RESOURCE_GROUP=rg-spread1000-ecg
export AZURE_WORKSPACE_NAME=ml-ecg-quickstart

# 現在サブスクリプション ID
export AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

`AZURE_WORKSPACE_NAME` は **同リージョン内でユニーク**である必要があります。既存名と衝突する場合は変更してください。

## 5. ローカル Python 環境（オプション、推奨）

`src/prepare_data.py` を AML 送信前にローカル検証したい場合、および `scripts/verify-output.py` を実行する場合:

```bash
python -m venv .venv && source .venv/bin/activate
pip install "wfdb==4.3.1" "numpy==1.26.4" "scikit-learn==1.5.2" \
            "azure-ai-ml==1.34.1" "azure-identity>=1.19.0" \
            "mlflow==2.16.2" "azureml-mlflow==1.57.0"
```

## 次

[02-provision-aml.md](02-provision-aml.md) で Bicep デプロイに進みます。
