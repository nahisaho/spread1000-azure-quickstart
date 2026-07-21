# トラブルシューティング

## 1. Bicep デプロイエラー

### `The Resource 'Microsoft.KeyVault/vaults/kv-ecg-xxx' already exists but has been soft-deleted`

**原因**: 過去に同名の Key Vault が作成され、soft-delete 期間 (7 日) 中

**対処**: 削除済み KV を purge するか、リソース名を変更します:

```bash
# 削除済み KV を確認
az keyvault list-deleted --query "[?name=='kv-ecg-<hash>']" -o table
# purge (即時完全削除)
az keyvault purge --name "kv-ecg-<hash>"
```

または `infra/main.bicep` で `keyVaultName` を明示的に別名に変更してください。

### `The subscription is not registered to use namespace 'Microsoft.MachineLearningServices'`

`deploy.sh` で自動登録していますが、遅延する場合があります:

```bash
az provider register --namespace Microsoft.MachineLearningServices --wait
```

## 2. GPU quota エラー

### `Operation results in exceeding quota limits of Core. Additional details - Deployment Model: Standard, Location: japaneast, Current Limit: 0`

**原因**: NCasT4_v3 family の quota が 0

**対処**:
1. `../../../docs/02-gpu-quota.md` の手順で quota を申請
2. または CPU フォールバック (`aml/compute-cpu.yml`) を使う:

```bash
az ml compute create -f aml/compute-cpu.yml -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
# job YAML はそのまま。--set で compute のみ差し替え
az ml job create -f aml/job-train.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" \
  --set compute=azureml:ecg-cpu --web
```

## 3. PhysioNet ダウンロード

### `wget` が途中で失敗する / SSL エラー

- 組織 proxy 経由の場合: `export https_proxy=http://<proxy>:<port>` を設定
- SSL エラーが出る場合、まず `--no-check-certificate` は使わずに wget のバージョンを更新
- 代替として **AWS Open Data ミラー** を使えます:

```bash
mkdir -p data/mitdb-1.0.0 && cd data/mitdb-1.0.0
aws s3 sync --no-sign-request s3://physionet-open/mitdb/1.0.0/ ./
```

### `.dat` ファイル数が 48 に満たない

- ネットワーク断で不完全ダウンロード。`bash scripts/download-data.sh` を再実行（`-c` continue オプションが効くので途中再開可）

## 4. Blob アップロード

### `AuthorizationPermissionMismatch`

**原因**: 実行ユーザーに `Storage Blob Data Contributor` が付いていない

**対処**: `deploy.sh` の Bicep デプロイで自動付与されますが、伝播に 1〜2 分かかることがあります。1 分待って再実行してください。

手動で確認:

```bash
DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
az role assignment list \
  --assignee "$DEPLOYER_OID" \
  --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT" \
  -o table
```

## 5. AML Job

### ジョブが `Failed` になり、`std_log.txt` に `ModuleNotFoundError: No module named 'wfdb'`

**原因**: Environment に `wfdb` が含まれていない

**対処**: `aml/conda.yml` に `wfdb==4.3.1` があることを確認。Environment version は immutable のため、依存を変更した場合は `aml/environment.yml` の `version:` をインクリメント（例: `1` → `2`）してから再作成し、ジョブの参照バージョンを明示します:

```bash
# 1) aml/environment.yml の version を "2" に上げる
# 2) 新バージョンを登録
az ml environment create -f aml/environment.yml -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"

# 3) ジョブ送信時にそのバージョンを明示 (`@latest` はキャッシュ挙動に依存するので非推奨)
az ml job create -f aml/job-train.yml \
  --set environment=azureml:ecg-pytorch-2-4:2 \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

### ジョブが `Preparing` から進まない (10 分以上)

**原因**: Environment image build 中（初回のみ 5〜10 分）

**対処**: AML Studio のジョブ画面 → Outputs + logs → `20_image_build_log.txt` で build 進行を確認。build ログでエラーが出ていなければ待つ。

### `RuntimeError: No usable records found in <path>`

**原因**: prepare_data.py がデータフォルダに `*.dat` を見つけられない

**対処**:
- `az ml data show` で登録された data asset の path を確認
- Blob 上のファイル配置を確認: `az storage blob list --account-name ... --container-name datasets --prefix mitdb-1.0.0/`
- prepare_data.py は `rglob('*.dat')` でサブフォルダも探すので、余計なネストがあっても動くはず

### Training が nan / 0 の loss で止まる

**原因**: バッチが極端に偏っている、または正規化失敗

**対処**:
- prep_manifest.json で各 split の class 分布を確認
- `--seed` を変えて再実行
- `--lr` を 5e-4 に下げる

## 6. コスト関連

### 想定より請求が高い

- **AML compute が 0 台に scale-down していない** → `az ml compute show --name ecg-t4` で `min_instances`, `current_node_count` を確認
- **ACR image storage** → 使い終わったら `az acr repository list -n $ACR_NAME` で不要 image を削除
- **Log Analytics** → 30 日保持で最低限、大量ログでもコスト影響は数百円/月未満

## 参照

- [`../../../docs/00-azure-account-setup.md`](../../../docs/00-azure-account-setup.md)
- [`../../../docs/01-cost-management.md`](../../../docs/01-cost-management.md)
- [`../../../docs/02-gpu-quota.md`](../../../docs/02-gpu-quota.md)
