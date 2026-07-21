# 02. AML ワークスペース + 依存リソースのプロビジョン

このステップで作成するもの:
- Resource Group (東日本など)
- Storage Account (LRS, Hot, public access 無効)
- Key Vault (Standard, RBAC 認可)
- Application Insights
- Azure Container Registry (Basic)
- **Azure Machine Learning Workspace** (system-assigned MI)
- 実行ユーザーへの Storage Blob Data Contributor 割り当て

所要時間: 5〜10 分

## 1. 環境変数の確認

```bash
env | grep AZURE_
# AZURE_LOCATION=japaneast
# AZURE_RESOURCE_GROUP=rg-monai-quickstart
# AZURE_WORKSPACE_NAME=ml-monai-XXXX
```

## 2. Bicep デプロイ

```bash
cd quickstarts/medical-imaging/monai-3d-segmentation

./infra/deploy.sh
```

`deploy.sh` の中で以下が実行されます:

1. リソースプロバイダー登録 (`Microsoft.MachineLearningServices` など 6 個)
2. Resource Group 作成
3. `az ad signed-in-user show --query id` で自分の Azure AD ObjectId を取得
4. `az deployment group create` で `main.bicep` を実行

完了後、以下のような出力が表示されます:

```
==== 作成されたリソース ====
  ML Workspace: ml-monai-0721
  Storage:      stmonaiabcdef123456
  Key Vault:    kv-monai-abcdef123456
  ACR:          crmonaiabcdef123456
  App Insights: ai-monai-abcdef123456
```

**Storage Account 名を必ず環境変数に保存**してください (Blob アップロードに `AZURE_STORAGE_ACCOUNT`、コンテナ名解決に `AZURE_RESOURCE_GROUP` と `AZURE_WORKSPACE_NAME` が必要):

```bash
export AZURE_STORAGE_ACCOUNT=stmonaiabcdef123456
# 冒頭 (§0-1) で export した AZURE_RESOURCE_GROUP / AZURE_WORKSPACE_NAME もこのシェルで有効なままにしておく
```

## 3. データセットの取得と Blob 登録

Task09_Spleen (~1.5 GB, CC-BY-SA 4.0) をローカルに取得し、AML の default blobstore にアップロードします。

```bash
# 3-1. ダウンロード (5〜10 分)
./scripts/download-data.sh ./msd-data

# 3-2. Blob にアップロード (~2 分, 帯域による)
./scripts/upload-dataset.sh ./msd-data/Task09_Spleen
```

> [!NOTE]
> `upload-dataset.sh` は `az ml datastore show` で **workspaceblobstore の実体コンテナ名** (`azureml-blobstore-<workspace-guid>`) を解決してからそこに書き込みます。Data Asset (`aml/data-spleen.yml`) の path `azureml://datastores/workspaceblobstore/paths/datasets/Task09_Spleen/` と正しく整合します。

## 4. Data Asset の登録

Bundle が参照できる URI Folder として登録:

```bash
az ml data create \
  --file aml/data-spleen.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME"

# 確認
az ml data show \
  --name task09-spleen \
  --version 1 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "{name:name,version:version,path:path,type:type}" \
  -o jsonc
```

## 5. Environment 登録

MONAI 1.4.0 + PyTorch 2.4.0 のカスタム Environment を登録 (初回は ACR ビルドで 10〜15 分):

```bash
cd aml
az ml environment create \
  --file environment.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME"
cd ..
```

> [!IMPORTANT]
> `environment.yml` はベースイメージに `mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:latest` を指定しています。**再現性を最優先する場合**は `latest` を最新の日付タグ (例: `20260715.v1`) に固定してください。利用可能タグは以下で確認:
> ```bash
> curl -s https://mcr.microsoft.com/v2/azureml/openmpi5.0-cuda12.4-ubuntu22.04/tags/list | jq -r '.tags[]' | sort -r | head -10
> ```

初回のみビルドと ACR プッシュが走り、次回以降 Job 起動時にはキャッシュ image が pull されます。

## 6. Compute Cluster 登録

### 6-1. T4 クラスター (推論・軽量デモ用)

```bash
az ml compute create \
  --file aml/compute-t4.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME"
```

### 6-2. A100 クラスター (fine-tuning 用)

**先に GPU quota が承認済みか必ず確認** (docs/01 §5):

```bash
az vm list-usage \
  --location "$AZURE_LOCATION" \
  --query "[?contains(name.value, 'NCADSA100v4')].{name:name.value,current:currentValue,limit:limit}" \
  -o table
```

`limit` が 24 以上であることを確認してから:

```bash
az ml compute create \
  --file aml/compute-a100.yml \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME"
```

### 6-3. 状態確認

```bash
az ml compute list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "[].{name:name,type:type,size:size,state:provisioning_state,min:min_instances,max:max_instances}" \
  -o table
```

`state: Succeeded` かつ `min: 0` であればアイドル時課金 0 です。

## 7. RBAC 確認

Workspace の system-assigned MI は自動的に Storage/ACR へのアクセスが付与されますが、手動確認しておくと安心:

```bash
# Workspace MI の principalId
WS_PRINCIPAL_ID=$(az ml workspace show \
  --name "$AZURE_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query identity.principal_id -o tsv)

echo "Workspace MI: $WS_PRINCIPAL_ID"

# Storage への role 割り当て確認
STORAGE_ID=$(az storage account show \
  --name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query id -o tsv)

az role assignment list \
  --assignee "$WS_PRINCIPAL_ID" \
  --scope "$STORAGE_ID" \
  --query "[].{role:roleDefinitionName,scope:scope}" \
  -o table
```

想定される role: `Storage Blob Data Contributor` (AzureML が自動付与)。

## チェックリスト

- [ ] Bicep デプロイ成功、outputs にすべてのリソース名が出力された
- [ ] `AZURE_STORAGE_ACCOUNT` を export 済み
- [ ] Task09_Spleen が Blob (`datasets/Task09_Spleen/`) にアップロード済み
- [ ] `az ml data show task09-spleen` が成功
- [ ] `az ml environment show monai-spleen-1-4` が成功
- [ ] `az ml compute list` で `monai-t4` (と必要なら `monai-a100`) が Succeeded, min=0
- [ ] Workspace MI に `Storage Blob Data Contributor` が Storage スコープで付与済み

## 次のステップ

→ [`docs/03-run-inference.md`](03-run-inference.md) — T4 で事前学習 Bundle を実行して予測 mask を生成 (15〜25 分)
