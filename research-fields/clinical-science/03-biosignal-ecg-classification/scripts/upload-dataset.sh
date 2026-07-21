#!/usr/bin/env bash
# ローカルの MIT-BIH データを Storage Blob (datasets コンテナ) にアップロード
# AAD 認証を使用 (Shared Key は不要)
set -Eeuo pipefail

: "${AZURE_STORAGE_ACCOUNT:?環境変数 AZURE_STORAGE_ACCOUNT を設定してください}"

LOCAL_DIR="${1:-./data/mitdb-1.0.0}"
DEST_PATH="datasets/mitdb-1.0.0"

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "🛑 $LOCAL_DIR が存在しません。先に bash scripts/download-data.sh を実行してください。" >&2
  exit 1
fi

DAT_COUNT=$(find "$LOCAL_DIR" -maxdepth 1 -name '*.dat' | wc -l)
if [[ "$DAT_COUNT" -lt 48 ]]; then
  echo "🛑 $LOCAL_DIR に .dat が $DAT_COUNT 個 (期待 48)。ダウンロードが不完全です。" >&2
  exit 1
fi

echo "==== Blob upload: $LOCAL_DIR → $AZURE_STORAGE_ACCOUNT/$DEST_PATH ===="
az storage blob upload-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --destination "datasets" \
  --destination-path "mitdb-1.0.0" \
  --source "$LOCAL_DIR" \
  --auth-mode login \
  --overwrite \
  --output none

echo "  ✓ アップロード完了"

echo ""
echo "==== 確認 ===="
az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --container-name datasets \
  --prefix "mitdb-1.0.0/" \
  --auth-mode login \
  --num-results 5 \
  --output table

echo ""
echo "==== 次のステップ ===="
echo "  az ml data create -f aml/data-mitbih.yml -g \$AZURE_RESOURCE_GROUP -w \$AZURE_WORKSPACE_NAME"
