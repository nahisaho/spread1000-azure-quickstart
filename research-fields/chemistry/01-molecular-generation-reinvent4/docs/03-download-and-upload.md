# 03. Prior のダウンロードと Blob へのアップロード

REINVENT4 の pretrained priors は Zenodo (Apache-2.0) で公開されています。ローカルで一度取得し、AML data asset として登録します。

## 1. ダウンロード

```bash
cd research-fields/chemistry/01-molecular-generation-reinvent4
bash scripts/download-priors.sh
```

`priors/` ディレクトリに以下が保存されます (Zenodo API から md5 + size を取得して検証):

- `libinvent.prior` — scaffold decoration
- `reinvent_pubchem.prior` — de novo generation (本 quickstart では未使用)

Zenodo record: <https://zenodo.org/records/20701824>

> [!NOTE]
> このスクリプトは `jq` と md5 コマンド (`md5sum` / `gmd5sum` / macOS 標準 `md5`) を使用します。macOS の場合は `brew install jq` を実行してください（`md5` は macOS 標準で入っています）。Ubuntu/WSL2 は `sudo apt-get install -y jq` で jq のみ導入で OK。

## 2. AML Workspace のデフォルト datastore にアップロード

REINVENT4 の prior は 100 MB 未満と小さいため、`workspaceblobstore` (Bicep 作成の Storage 上に AML が自動作成) に格納します。

```bash
az storage blob upload-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --destination "azureml-blobstore-$(az ml datastore show \
      -n workspaceblobstore \
      -g $AZURE_RESOURCE_GROUP -w $AZURE_WORKSPACE_NAME \
      --query 'container_name' -o tsv | sed 's/azureml-blobstore-//')" \
  --destination-path "reinvent4-priors/v4.8/" \
  --source ./priors \
  --pattern "*.prior" \
  --auth-mode login
```

> [!TIP]
> 上のコマンドは datastore の実 container 名を動的に取得します。

## 3. AML data asset として登録

```bash
az ml data create \
  -f aml/data-priors.yml \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"
```

登録確認:

```bash
az ml data show \
  --name reinvent4-priors \
  --version 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --query '{name:name, version:version, path:path}' -o table
```
