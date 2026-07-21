#!/usr/bin/env bash
# ローカル Task09_Spleen ディレクトリを AML workspace の default blobstore (Storage) にアップロード
# 使い方: ./upload-dataset.sh <ローカル Task09_Spleen ディレクトリ>
# 事前: AZURE_STORAGE_ACCOUNT を export し、az login 済み

set -euo pipefail

SRC_DIR="${1:-}"

: "${AZURE_STORAGE_ACCOUNT:?環境変数 AZURE_STORAGE_ACCOUNT を設定してください (infra/deploy.sh の出力参照)}"
: "${AZURE_RESOURCE_GROUP:?環境変数 AZURE_RESOURCE_GROUP を設定してください}"
: "${AZURE_WORKSPACE_NAME:?環境変数 AZURE_WORKSPACE_NAME を設定してください}"

if [[ -z "$SRC_DIR" ]] || [[ ! -d "$SRC_DIR" ]]; then
  echo "使い方: $0 <ローカル Task09_Spleen ディレクトリ>"
  echo "例:     $0 ./msd-data/Task09_Spleen"
  exit 1
fi

# workspaceblobstore の実体コンテナ名を動的に解決する。
# 実体は 'azureml-blobstore-<workspace-guid>' で workspace 作成時に auto-provision される。
# `azureml` という名前を直接使うと、Data Asset (azureml://datastores/workspaceblobstore/paths/...)
# が別コンテナを参照しているため Job から見えない。
CONTAINER=$(az ml datastore show \
  --name workspaceblobstore \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_WORKSPACE_NAME" \
  --query container_name -o tsv)

if [[ -z "$CONTAINER" ]]; then
  echo "❌ workspaceblobstore の container_name を取得できませんでした" >&2
  echo "   確認: az ml datastore list -g \$AZURE_RESOURCE_GROUP -w \$AZURE_WORKSPACE_NAME" >&2
  exit 1
fi

echo "==== Blob コンテナ確認 ===="
echo "  workspaceblobstore → $CONTAINER"
if ! az storage container show \
      --account-name "$AZURE_STORAGE_ACCOUNT" \
      --name "$CONTAINER" \
      --auth-mode login \
      --output none 2>/dev/null; then
  echo "  → $CONTAINER コンテナを作成"
  az storage container create \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --name "$CONTAINER" \
    --auth-mode login \
    --output none
fi
echo "  ✓ $CONTAINER"

DEST_PREFIX="datasets/Task09_Spleen"

FILE_COUNT=$(find "$SRC_DIR" -type f | wc -l)
TOTAL_MB=$(du -sm "$SRC_DIR" | cut -f1)

echo ""
echo "==== アップロード ===="
echo "  Source: $SRC_DIR"
echo "  Dest:   az://${CONTAINER}/${DEST_PREFIX}/"
echo "  Files:  $FILE_COUNT (${TOTAL_MB} MB)"
echo ""
read -rp "続行しますか？ [y/N] " ANS
[[ "$ANS" != "y" ]] && exit 0

az storage blob upload-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination "$CONTAINER" \
  --destination-path "$DEST_PREFIX" \
  --source "$SRC_DIR" \
  --overwrite \
  --output none

echo ""
echo "==== 検証 ===="
UPLOADED=$(az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name "$CONTAINER" \
  --prefix "$DEST_PREFIX/" \
  --query "length(@)" -o tsv)

echo "  Blob 上のファイル数: $UPLOADED (期待値: $FILE_COUNT)"

if [[ "$UPLOADED" != "$FILE_COUNT" ]]; then
  echo "  ❌ アップロード数が一致しません。再実行してください。" >&2
  exit 1
fi

echo ""
echo "==== 完了 ===="
echo "  次のステップ: aml/data-spleen.yml を登録"
echo "    az ml data create -f aml/data-spleen.yml \\"
echo "      -g \$AZURE_RESOURCE_GROUP -w \$AZURE_WORKSPACE_NAME"
