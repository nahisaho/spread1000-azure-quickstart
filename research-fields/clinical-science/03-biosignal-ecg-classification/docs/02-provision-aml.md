# 02. AML Workspace + 依存リソースをデプロイ (Bicep)

## デプロイされるもの

| リソース | 用途 |
|---|---|
| Storage Account (LRS, Hot) | MIT-BIH データ格納 + AML workspace 既定 datastore |
| Key Vault (Standard, RBAC 認可) | AML workspace の secrets storage |
| Log Analytics Workspace | Application Insights のバックエンド (30 日保持) |
| Application Insights (workspace-based) | AML run のテレメトリー |
| Container Registry (Basic) | Environment image build 先 |
| Machine Learning Workspace (system-assigned MI) | AML の中核 |

## デプロイ

`infra/deploy.sh` を実行します（`docs/01-prerequisites.md` の環境変数が export 済みであること）:

```bash
cd research-fields/clinical-science/03-biosignal-ecg-classification
bash infra/deploy.sh
```

初回は **5〜8 分** かかります。完了すると出力に:

```
==== 作成されたリソース ====
  ML Workspace: ml-ecg-quickstart
  Storage:      stecg<hash>
  Key Vault:    kv-ecg-<hash>
  ACR:          crecg<hash>
  App Insights: ai-ecg-<hash>
```

## 環境変数のセット (デプロイ後)

deploy.sh 出力の指示に従って以下を export:

```bash
export AZURE_LOCATION=japaneast
export AZURE_RESOURCE_GROUP=rg-spread1000-ecg
export AZURE_WORKSPACE_NAME=ml-ecg-quickstart
export AZURE_STORAGE_ACCOUNT=stecg<hash>   # deploy.sh 出力を参照
export AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

## 動作確認

```bash
# Workspace が見えること
az ml workspace show \
  -g "$AZURE_RESOURCE_GROUP" \
  -n "$AZURE_WORKSPACE_NAME" \
  --query '{name:name, location:location, identity:identity.principalId}' \
  -o table

# Storage RBAC (Blob Data Contributor) が付いていること
DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment list \
  --assignee "$DEPLOYER_OID" \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT" \
  --query "[?roleDefinitionName=='Storage Blob Data Contributor'].{role:roleDefinitionName, scope:scope}" \
  -o table
```

## 次

[03-download-and-upload.md](03-download-and-upload.md) で MIT-BIH をダウンロード → Blob に登録します。
