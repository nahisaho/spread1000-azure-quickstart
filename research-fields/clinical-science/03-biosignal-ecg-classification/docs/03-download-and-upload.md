# 03. MIT-BIH ダウンロード + Blob へアップロード

## 1. PhysioNet から MIT-BIH v1.0.0 をダウンロード

```bash
cd research-fields/clinical-science/03-biosignal-ecg-classification
bash scripts/download-data.sh
```

デフォルトの保存先は `./data/mitdb-1.0.0/`。約 104 MB、3〜5 分で完了します。

> [!NOTE]
> **ライセンス**: MIT-BIH Arrhythmia Database v1.0.0 は [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) で公開されています。再配布や派生データを公開する場合は、Moody & Mark (2001) 論文の引用と PhysioNet の標準引用（[こちら](https://physionet.org/content/mitdb/1.0.0/)）を明記してください。

**確認**:

```bash
ls data/mitdb-1.0.0/*.dat | wc -l   # → 48
```

## 2. Blob Storage にアップロード

**AAD 認証**でアップロードします（Shared Key 不要）:

```bash
bash scripts/upload-dataset.sh
```

内部で以下を実行:

```bash
az storage blob upload-batch \
  --account-name $AZURE_STORAGE_ACCOUNT \
  --destination datasets \
  --destination-path mitdb-1.0.0 \
  --source ./data/mitdb-1.0.0 \
  --auth-mode login \
  --overwrite
```

## 3. AML datastore として `datasets` コンテナを登録

Bicep で作成した `datasets` コンテナ（`workspaceblobstore` とは別）を AML datastore として登録します:

```bash
sed "s/STORAGE_ACCOUNT_PLACEHOLDER/$AZURE_STORAGE_ACCOUNT/" aml/datastore-datasets.yml \
  | az ml datastore create -f /dev/stdin \
      -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

## 4. AML data asset として登録

```bash
az ml data create \
  -f aml/data-mitbih.yml \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME"
```

登録確認:

```bash
az ml data show \
  --name mitbih-1.0.0 \
  --version 1 \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --query '{name:name, version:version, path:path}' -o table
```

## 次

[04-train-and-evaluate.md](04-train-and-evaluate.md) で 1D CNN を学習します。
