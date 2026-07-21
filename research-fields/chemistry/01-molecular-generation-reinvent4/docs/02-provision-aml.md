# 02. AML Workspace のプロビジョニング (Bicep)

## 1. リソースプロバイダー登録 (初回のみ)

```bash
az provider register --namespace Microsoft.MachineLearningServices --wait
az provider register --namespace Microsoft.Storage --wait
az provider register --namespace Microsoft.KeyVault --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.Insights --wait
```

## 2. Bicep 実行

```bash
cd research-fields/chemistry/01-molecular-generation-reinvent4
bash infra/deploy.sh
```

`deploy.sh` は以下を行います:

1. Resource Group 作成
2. Bicep デプロイ (Workspace + Storage + Key Vault + Log Analytics + App Insights + ACR Basic)
3. デプロイ実行ユーザーに **Storage Blob Data Contributor** を付与 (prior をアップロードするため)
4. Workspace 名 / Storage 名 / 次に流すコマンドを標準出力

## 3. 出力の確認

コマンドが終わると、以下が表示されます:

```
=== Deployment successful ===
Resource Group: rg-spread-chem-molgen
Workspace:      mlw-chem-molgen-...
Storage:        stmolgen...

Next steps (copy-paste):
  export AZURE_WORKSPACE_NAME=mlw-chem-molgen-...
  export AZURE_STORAGE_ACCOUNT=stmolgen...

Then follow docs/03-download-and-upload.md
```

## 4. Studio で確認

```bash
az ml workspace show \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --query 'discoveryUrl' -o tsv
```

ブラウザで [Azure ML Studio](https://ml.azure.com/) を開き、Workspace が一覧に出れば OK。
