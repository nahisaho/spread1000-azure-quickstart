# 05. クリーンアップ

**GPU クラスターは idle でも課金対象になる場合があります**。使い終わったら必ずクラスターを 0 に縮小するか、リソース全体を削除してください。

> [!IMPORTANT]
> このドキュメントのコマンドは **ローカル PC (もしくは Cloud Shell)** で、Bicep デプロイに使ったのと同じ Owner / Contributor + User Access Administrator アカウントで実行してください。Compute Cluster の system-assigned MI にはリソース削除権限はありません。

## 1. クラスターの状態確認

```bash
env | grep AZURE_
# AZURE_RESOURCE_GROUP=rg-monai-quickstart
# AZURE_WORKSPACE_NAME=ml-monai-XXXX

az ml compute list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query "[].{name:name,state:provisioning_state,current:current_node_count,min:min_instances,max:max_instances}" \
  -o table
```

`current: 0` かつ `min: 0` であれば idle 課金は 0 です。

## 2. 部分クリーンアップ (プロジェクトを継続する場合)

### 2-1. Compute Cluster を最小構成に

Cluster 定義は残したまま、min/max ともに 0 にすると **新規 Job 投入も不可**になります (完全に停止):

```bash
az ml compute update \
  --name monai-a100 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --min-instances 0 \
  --max-instances 0

az ml compute update \
  --name monai-t4 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --min-instances 0 \
  --max-instances 0
```

> [!NOTE]
> 一部の CLI バージョンでは `--max-instances 0` が拒否されます。その場合は `--min-instances 0 --max-instances 1` に戻し、`idle_time_before_scale_down` 経過後に自動縮小されるのを待ってください。

再開時は同じコマンドで `--max-instances 1` に戻します。

### 2-2. Compute Cluster を削除

Cluster そのものを消す場合:

```bash
az ml compute delete \
  --name monai-a100 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --yes

az ml compute delete \
  --name monai-t4 \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --yes
```

## 3. 中間データのライフサイクル管理

Task09_Spleen (1.5 GB) や Job artifacts (fine-tuning で 数百 MB 〜 数 GB) を保持しつつストレージコストを抑えたい場合、Storage Account の **Blob ライフサイクル管理ポリシー** で自動 Tier 移行を設定します:

```bash
: "${AZURE_STORAGE_ACCOUNT:?環境変数 AZURE_STORAGE_ACCOUNT を設定してください}"

cat > lifecycle.json <<'JSON'
{
  "rules": [
    {
      "name": "monai-artifacts-cool-then-archive",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["azureml/ExperimentRun/", "azureml-blobstore-"]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": { "daysAfterModificationGreaterThan": 30 },
            "tierToArchive": { "daysAfterModificationGreaterThan": 90 }
          }
        }
      }
    }
  ]
}
JSON

az storage account management-policy create \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --policy @lifecycle.json

rm lifecycle.json
```

> [!IMPORTANT]
> 管理ポリシー作成は **management-plane 権限** (`Microsoft.Storage/storageAccounts/managementPolicies/write`) が必要で、`Storage Blob Data Contributor` (data-plane) では実行できません。**ローカル PC の Owner または Contributor アカウント**で実行してください。

## 4. 完全削除 (Resource Group ごと)

このクイックスタート用に **専用の Resource Group** を作った場合、以下 1 コマンドで全リソースを削除できます:

```bash
az group delete \
  --name "$AZURE_RESOURCE_GROUP" \
  --yes \
  --no-wait
```

削除対象:
- Storage Account (`stmonai*`) — Task09 データ、Job artifacts、モデル全消去
- Key Vault (`kv-monai-*`) — Soft delete 7 日間残る場合あり
- Application Insights (`ai-monai-*`)
- Container Registry (`crmonai*`) — カスタム Environment image
- AML Workspace (`ml-monai-*`)
- Compute Cluster (すべて)

> [!WARNING]
> **`az ml workspace delete` だけでは Storage/ACR/Key Vault/App Insights が残ります**。完全に消したい場合は必ず Resource Group ごと削除してください。

## 5. Soft-delete された Key Vault のパージ (必要な場合)

Key Vault は soft delete が有効で、削除後 7 日間 (本テンプレート設定) 名前が予約されます。同名で再作成したい場合はパージ:

```bash
KV_NAME=<削除した Key Vault 名>

az keyvault list-deleted \
  --query "[?name=='$KV_NAME'].{name:name,location:properties.location}" \
  -o table

az keyvault purge \
  --name "$KV_NAME" \
  --location "$AZURE_LOCATION"
```

パージ操作には `Microsoft.KeyVault/locations/deletedVaults/purge/action` が必要 (Owner または Contributor)。

## 6. コスト実測

Cost Management で `scenario=monai-3d-seg` タグの累計を確認:

```bash
az costmanagement query \
  --type ActualCost \
  --dataset-granularity Daily \
  --dataset-filter '{"tags": {"name": "scenario", "operator": "In", "values": ["monai-3d-seg"]}}' \
  --timeframe MonthToDate \
  --scope "/subscriptions/$(az account show --query id -o tsv)" \
  --query "properties.rows" \
  -o table
```

または Azure Portal → **コスト管理 + 請求** → **コスト分析** → タグフィルタ `scenario=monai-3d-seg`。

## チェックリスト (課金停止確認)

- [ ] すべての Compute Cluster が `current_node_count: 0` かつ `min_instances: 0`
- [ ] (完全削除する場合) Resource Group の削除ジョブが Portal で完了状態
- [ ] (継続する場合) Blob ライフサイクル管理が有効で cool tier に移行するように設定済み
- [ ] 課金レポートで `scenario=monai-3d-seg` タグの日次コストが想定内

## 次のステップ

- Bundle を差し替えて別タスクを試す (whole-body CT, brain tumor など) → docs/troubleshooting.md 参照
- 施設の DICOM で fine-tuning → `docs/04-fine-tuning.md` の epochs, split, spacing を調整
- MONAI Deploy App SDK で臨床パイプラインへ組み込む → 別クイックスタート予定
