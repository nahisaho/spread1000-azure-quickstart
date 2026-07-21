#!/usr/bin/env bash
# 実データ (FASTQ ファイル) を Blob にアップロード
# 使い方: ./upload-data.sh <ローカルディレクトリ> <blob サブパス>
#   例:   ./upload-data.sh ~/raw-fastq project-001
set -euo pipefail

LOCAL_DIR="${1:-}"
BLOB_SUBPATH="${2:-project-001}"

if [[ -z "$LOCAL_DIR" ]] || [[ ! -d "$LOCAL_DIR" ]]; then
  echo "使い方: $0 <ローカルディレクトリ> [blob サブパス]"
  echo "例:     $0 ~/raw-fastq project-001"
  exit 1
fi

: "${AZURE_STORAGE_ACCOUNT:?環境変数 AZURE_STORAGE_ACCOUNT を設定してください}"

FASTQ_FILES=("$LOCAL_DIR"/*.fastq.gz)
if [[ ${#FASTQ_FILES[@]} -eq 0 ]] || [[ ! -f "${FASTQ_FILES[0]}" ]]; then
  echo "❌ *.fastq.gz が $LOCAL_DIR に見つかりません"
  exit 1
fi

echo "==== ${#FASTQ_FILES[@]} ファイルをアップロード ===="
echo "  Storage: ${AZURE_STORAGE_ACCOUNT}"
echo "  Prefix:  raw-fastq/${BLOB_SUBPATH}/"
echo ""
read -rp "続行しますか？ [y/N] " ANS
[[ "$ANS" != "y" ]] && exit 0

# 並列アップロード (最大 8 並列、失敗を集計)
JOBS=0
MAX_JOBS=8
PIDS=()
for f in "${FASTQ_FILES[@]}"; do
  base=$(basename "$f")
  echo "  → raw-fastq/${BLOB_SUBPATH}/${base}"
  az storage blob upload \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --container-name omics \
    --name "raw-fastq/${BLOB_SUBPATH}/${base}" \
    --file "$f" \
    --overwrite \
    --output none &
  PIDS+=($!)

  ((JOBS+=1))
  if [[ $JOBS -ge $MAX_JOBS ]]; then
    wait -n || true
    ((JOBS-=1))
  fi
done

FAIL=0
for pid in "${PIDS[@]}"; do
  wait "$pid" || FAIL=$((FAIL + 1))
done
if [[ $FAIL -gt 0 ]]; then
  echo "❌ $FAIL 件のアップロードが失敗しました。再実行してください。" >&2
  exit 1
fi

echo "==== 完了 ===="
az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --container-name omics \
  --prefix "raw-fastq/${BLOB_SUBPATH}/" \
  --query "[].{name:name,sizeGB:properties.contentLength}" \
  -o table
