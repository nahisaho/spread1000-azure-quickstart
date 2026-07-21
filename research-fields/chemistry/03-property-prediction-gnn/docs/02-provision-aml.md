# 02 — Azure ML Workspace のプロビジョニング

Bicep で AML Workspace + Storage + Key Vault + Log Analytics + App Insights + ACR Basic を一括作成します。

## 事前確認

[`docs/01-prerequisites.md`](01-prerequisites.md) の Resource Provider 登録と GPU クォータ確認が済んでいることを確認してください。

## パラメータファイルを作成

```bash
cd research-fields/chemistry/03-property-prediction-gnn
cp infra/parameters.example.json infra/parameters.json
```

`infra/parameters.json` を編集し、以下の値を確認 / 変更します：

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "workspaceName": { "value": "spread-chem-gnn-ws" },
    "location":      { "value": "japaneast" }
  }
}
```

## デプロイ

```bash
# サブスクリプションを再確認
az account show --query "{name:name, id:id}" -o table

# リソースグループを作成
az group create -n spread-chem-gnn-rg -l japaneast

# Bicep をデプロイ
./infra/deploy.sh spread-chem-gnn-rg infra/parameters.json
```

`deploy.sh` の中身：
- 現ユーザーの Object ID を取得し `deployerObjectId` として渡す (対話ユーザーは自動、SP/MI は `DEPLOYER_OID_OVERRIDE` env で明示)
- `az deployment group create` で Bicep 適用 (5〜7 分)
- 作成された Workspace / Storage / ACR / Key Vault 名を最後に表示
- 現ユーザーに **Storage Blob Data Contributor** を付与 (data upload 用)

## デプロイの確認

```bash
# Workspace が作成されたか
az ml workspace show -g spread-chem-gnn-rg -n spread-chem-gnn-ws -o table

# 既定の datastore を確認
az ml datastore list -g spread-chem-gnn-rg -w spread-chem-gnn-ws -o table
```

## デフォルトのリソースグループ / Workspace を設定

```bash
az configure --defaults group=spread-chem-gnn-rg workspace=spread-chem-gnn-ws
```

## トラブル

- `AuthorizationFailed`: Owner または User Access Administrator が必要 → [`troubleshooting.md`](../troubleshooting.md#deploy-sh-が-authorizationfailed-で止まる)
- `subscription is not registered`: RP 未登録 → [`docs/01-prerequisites.md`](01-prerequisites.md) の RP 登録

次: [`03-prepare-data.md`](03-prepare-data.md)
