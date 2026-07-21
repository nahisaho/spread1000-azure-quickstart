# 01. 前提条件と GPU クォータ

## 1. ソフトウェア

ローカル PC (Bash / WSL / macOS) で以下をインストール:

```bash
# Azure CLI 2.60 以上
az version

# ml extension (v2)
az extension add --name ml --upgrade

az extension show --name ml --query version -o tsv
# → 2.30.0 以上を想定
```

その他:
- `jq` (JSON 整形): `sudo apt install jq` / `brew install jq`
- `curl`, `tar` (Task09 ダウンロード用)
- ローカルで NIfTI を可視化したい場合: **3D Slicer** または **ITK-SNAP** (任意)

## 2. サブスクリプション権限

初期プロビジョニングを実行するアカウントには、**Subscription スコープで** 以下のいずれかが必要です:

- **Owner** (Subscription スコープ)
- または **Contributor + User Access Administrator** (Subscription スコープ、Bicep が Storage への RBAC 割り当てを行うため)

Subscription スコープの権限が必要な理由:
- 新規 Resource Group の作成
- リソースプロバイダー登録 (`Microsoft.MachineLearningServices` など)
- Storage/ACR へのユーザー RBAC 割り当て

既存 Resource Group を利用する場合は、以下でも可能ですが、リソースプロバイダー登録は**サブスクリプション管理者**に事前依頼してください:
- **RG スコープの Owner** (or Contributor + User Access Administrator) + プロバイダー登録済み

```bash
# 現在の割り当てを確認 (ローカル PC で)
az account show --query "{sub:name,tenant:tenantId,user:user.name}" -o jsonc

# 自身のロール
az role assignment list \
  --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --scope "/subscriptions/$(az account show --query id -o tsv)" \
  --query "[].{role:roleDefinitionName,scope:scope}" \
  -o table
```

## 3. リージョン選定

**推奨: Japan East** (レイテンシ + データ主権)。Southeast Asia もフォールバックとして利用可。

環境変数を設定:

```bash
export AZURE_LOCATION=japaneast
export AZURE_RESOURCE_GROUP=rg-monai-quickstart
export AZURE_WORKSPACE_NAME=ml-monai-$(date +%m%d)
```

## 4. GPU SKU の在庫確認 (最重要)

A100/T4 は Subscription/リージョンごとに在庫が異なります。**必ずデプロイ前に確認**してください:

```bash
# A100 (推奨: fine-tuning 用)
az vm list-skus \
  --location "$AZURE_LOCATION" \
  --size Standard_NC24ads_A100_v4 \
  --query "[].{name:name,restrictions:restrictions[].reasonCode}" \
  -o table

# T4 (推奨: inference/デモ用、安価)
az vm list-skus \
  --location "$AZURE_LOCATION" \
  --size Standard_NC4as_T4_v3 \
  --query "[].{name:name,restrictions:restrictions[].reasonCode}" \
  -o table
```

**`restrictions` が空** → 利用可能。
**`NotAvailableForSubscription`** → この Subscription/リージョンでは使えない → Southeast Asia を試すか、Subscription ownership を確認。

## 5. GPU クォータ

新規サブスクリプションでは A100 family のクォータが **0** の場合が多いです。

```bash
# NCADSA100v4 Family (A100) のクォータを確認
az vm list-usage \
  --location "$AZURE_LOCATION" \
  --query "[?contains(name.value, 'NCADSA100v4')].{name:name.value,current:currentValue,limit:limit}" \
  -o table

# NCASv3_T4 Family (T4) のクォータを確認
az vm list-usage \
  --location "$AZURE_LOCATION" \
  --query "[?contains(name.value, 'NCASv3') || contains(name.value, 'T4')].{name:name.value,current:currentValue,limit:limit}" \
  -o table
```

必要量:

| SKU | Family | 必要 vCPU quota |
|---|---|---:|
| `Standard_NC24ads_A100_v4` × 1 node | `standardNCADSA100v4Family` | 24 |
| `Standard_NC48ads_A100_v4` × 1 node | `standardNCADSA100v4Family` | 48 |
| `Standard_NC4as_T4_v3` × 1 node | `standardNCASv3_T4Family` | 4 |

**quota が 0 または不足していれば申請** (無料、1〜3 営業日):

Azure Portal → **クォータ** → **Compute** → リージョン選択 → 家族名で検索 → **クォータの引き上げを要求**

参考: https://learn.microsoft.com/azure/quotas/per-vm-quota-requests

> [!IMPORTANT]
> Quota 未承認のまま Job を投入すると `Queued` のまま数時間戻ってこないか `Allocation failed` になります。**必ず承認を待ってから Compute Cluster を作成**してください。

## 6. Storage クォータと帯域

Task09_Spleen は約 1.5 GB。Fine-tuning artifact (checkpoint, tensorboard, prediction) を含めても **50 GB あれば十分**。標準 Storage Account の上限 (5 PB) をはるかに下回るため考慮不要です。

## 7. リソースプロバイダー登録

初回のみ以下を登録:

```bash
for rp in Microsoft.MachineLearningServices \
          Microsoft.Storage \
          Microsoft.ContainerRegistry \
          Microsoft.KeyVault \
          Microsoft.Insights \
          Microsoft.OperationalInsights \
          Microsoft.Compute; do
  az provider register --namespace $rp --wait
done
```

## 8. コスト予算 (推奨)

初回 Quickstart 用に月 ¥10,000 の Budget を作成しておくと安心:

```bash
# Resource Group 作成 (次の docs/02 で行うが、Budget 用に先行してもよい)
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --tags scenario=monai-3d-seg project=spread1000
```

Budget 作成は Portal → **コスト管理 + 請求** → **予算** から。**メール通知先を必ず設定**してください (Budget alert は自動停止ではなく通知のみです)。

## チェックリスト

- [ ] `az --version` 2.60 以上、`az extension show -n ml` インストール済み
- [ ] `az account show` で目的の Subscription にログイン
- [ ] Owner または (Contributor + User Access Administrator) 権限を保有
- [ ] `AZURE_LOCATION`, `AZURE_RESOURCE_GROUP`, `AZURE_WORKSPACE_NAME` を export 済み
- [ ] `az vm list-skus` で A100/T4 が `NotAvailableForSubscription` でない
- [ ] `az vm list-usage` で `NCADSA100v4` (または T4) family の quota 残枠が必要量 ≥
- [ ] リソースプロバイダー登録完了

## 次のステップ

→ [`docs/02-provision-aml.md`](02-provision-aml.md) — Bicep で AML + Storage + ACR を作成し、Compute Cluster と Environment を登録
