#!/usr/bin/env bash
# 解析結果を Blob からローカルに一括ダウンロード
# 使い方: ./download-results.sh <RUN_ID> [ローカル保存先]
set -euo pipefail

RUN_ID="${1:-}"
LOCAL_DIR="${2:-./results-$(date +%Y%m%d)}"

: "${AZURE_STORAGE_ACCOUNT:?環境変数 AZURE_STORAGE_ACCOUNT を設定してください}"

if [[ -z "$RUN_ID" ]]; then
  echo "使い方: $0 <RUN_ID> [ローカル保存先]"
  echo "例:     $0 project-001-20260721-120000 ./my-results"
  echo ""
  echo "利用可能な RUN_ID:"
  az storage blob list \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --container-name omics \
    --prefix "results/" \
    --delimiter "/" \
    --query "[].{name:name}" -o tsv | sed 's|results/||' | sed 's|/$||' | sort -u | head -20
  exit 1
fi

mkdir -p "$LOCAL_DIR"

echo "==== 結果をダウンロード ===="
echo "  Blob:  az://omics/results/${RUN_ID}/"
echo "  Local: ${LOCAL_DIR}/"

# azcopy が使える場合は速い
if command -v azcopy >/dev/null 2>&1; then
  # ログイン方式を環境で切り替え:
  #   - Azure VM (Controller) 上では Managed Identity
  #   - ローカル PC / Cloud Shell では az login のトークンを再利用
  if ! azcopy login status >/dev/null 2>&1; then
    if curl -s -f -m 2 -H "Metadata:true" \
         "http://169.254.169.254/metadata/instance?api-version=2021-02-01" \
         >/dev/null 2>&1; then
      azcopy login --identity
    else
      export AZCOPY_AUTO_LOGIN_TYPE=AZCLI
    fi
  fi
  azcopy copy \
    "https://${AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/omics/results/${RUN_ID}/*" \
    "$LOCAL_DIR/" \
    --recursive
else
  # azcopy がなければ az CLI で個別 download
  az storage blob download-batch \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --source omics \
    --pattern "results/${RUN_ID}/*" \
    --destination "$LOCAL_DIR"
fi

echo "==== 完了 ===="
echo "MultiQC report を確認:"
find "$LOCAL_DIR" -name "multiqc_report.html" | head -3

echo ""
echo "主要な出力ファイル:"
find "$LOCAL_DIR" -name "salmon.merged.gene_counts*.tsv" | head -3
find "$LOCAL_DIR" -name "salmon.merged.gene_tpm*.tsv" | head -3
