# 01. 前提条件

## Azure サブスクリプション

- **Owner** ロール、または **Contributor + User Access Administrator (UAA)** の両方が必要
  - 理由: Resource Group 作成、Provider 登録、Managed Identity への role 割り当てを行うため
  - **サブスクリプションスコープ**の権限が必要 (RG スコープでは Provider 登録不可)
- サブスクリプション ID を控える

```bash
az login
az account show --query "{id:id,name:name,tenantId:tenantId}" -o jsonc
export AZURE_SUBSCRIPTION_ID=<上記 id>
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
```

## GPU クォータ

**Standard NC A100 v4 Family vCPUs** の quota が **24 以上** 必要 (`NC24ads_A100_v4` = 24 vCPU)。

> [!IMPORTANT]
> **AML compute の quota は VM の quota とは別枠**です (`Microsoft.MachineLearningServices` 側で管理)。`az vm list-usage` は Compute Provider の値しか返さないため、Job が Preparing で止まる原因になります。**必ず `az ml compute list-usage` (AML 側 quota) を確認してください**:

```bash
# AML 側 quota (Job Preparing で止まる原因はこちら)
az ml compute list-usage --location japaneast \
  --query "[?contains(name.localizedValue,'NCADSA100v4') || contains(name.value,'NCADSA100v4')].{Name:name.localizedValue, Current:currentValue, Limit:limit, Unit:unit}" \
  -o table

# 参考: VM Compute Provider 側 quota (dedicated / low_priority 別)
az vm list-usage --location japaneast \
  --query "[?contains(name.value,'NCADSA100v4') || contains(name.value,'lowPriorityCores')].{Name:localName,Current:currentValue,Limit:limit}" \
  -o table
```

**Spot (`low_priority`) を使う場合は `LowPriorityCores` (dedicated と別枠) も 24 以上必要**です。`Limit` が 0 の場合は Azure Portal → Subscription → Usage + quotas から「Standard NCADSA100v4 Family」+ 必要に応じて `Low-priority cores` を **24** ずつ申請 (通常 1〜24 時間で承認)。

> [!TIP]
> **A100 が枯渇していたら NCads H100 v5 (`Standard_NC40ads_H100_v5` 40 vCPU) が代替**として使えます。VRAM 80 GB は同じで、BioEmu では ~1.5x 速い実測があります。この場合 `aml/compute-a100.yml` の `size:` を差し替え、quota は `Standard NCadsH100v5 Family` を確認してください。

参考: <https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-quotas>

## Provider 登録

初回のみ:

```bash
az provider register --namespace Microsoft.MachineLearningServices
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerRegistry  # AML environment build に必須
```

登録完了 (Registered) を確認:

```bash
for NS in Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault \
          Microsoft.Insights Microsoft.OperationalInsights Microsoft.ContainerRegistry; do
  echo "$NS: $(az provider show --namespace $NS --query registrationState -o tsv)"
done
```

## ローカル環境

- **Azure CLI 2.65+** (`az --version`)
- **AML CLI (v2) 2.30+** 拡張

```bash
az extension add --name ml --upgrade
az extension show --name ml --query version -o tsv
```

- **Bicep CLI** (Azure CLI に同梱、`az bicep version` で確認)
- **Python 3.11+** (ローカル解析用、Job 内では AML 環境が使われる)
- **curl / jq / bash**

## リージョン選定

**Japan East** を推奨:

- A100 GPU (`NC24ads_A100_v4`) 在庫あり
- Retail Prices API に PAYG / Spot 両方の価格登録あり
- 学術ネットワークからの遅延が低い

## 環境変数の準備

以降のドキュメントで参照する変数を今のうちに export しておくと便利:

```bash
export AZURE_LOCATION=japaneast
export AZURE_RESOURCE_GROUP=rg-spread1000-bioemu
export AZURE_WORKSPACE_NAME=  # infra/deploy.sh 実行後に出力される名前を入れる
```

## 予算アラート (強く推奨)

デプロイ前に **月額 ¥3,000** 程度の予算アラートを設定してください:

```bash
az consumption budget create \
  --amount 20 \
  --budget-name "bioemu-quickstart" \
  --category cost \
  --time-grain monthly \
  --start-date $(date -u +%Y-%m-01) \
  --end-date $(date -u -d "+3 months" +%Y-%m-01) \
  --resource-group "$AZURE_RESOURCE_GROUP" 2>/dev/null || \
  echo "→ Portal → Cost Management → Budgets から作成してください"
```

## チェックリスト

- [ ] `az login` 済み
- [ ] Owner または Contributor+UAA を持つ Subscription を選択済み
- [ ] NCADSA100v4 quota ≥ 24 vCPU
- [ ] Provider 登録済み
- [ ] AML CLI 拡張インストール済み
- [ ] `AZURE_SUBSCRIPTION_ID` / `AZURE_LOCATION` / `AZURE_RESOURCE_GROUP` を export 済み
- [ ] 予算アラート設定済み

## 次のステップ

→ [02. AML workspace + A100 compute プロビジョニング](02-provision-aml.md)
