#!/usr/bin/env bash
# Download MoleculeNet ESOL raw CSV from DeepChem S3 bucket
set -euo pipefail

URL="https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="${SCRIPT_DIR}/../data"
mkdir -p "$DEST_DIR"
DEST_DIR="$(cd "$DEST_DIR" && pwd)"
DEST="${DEST_DIR}/delaney-processed.csv"
EXPECTED_ROWS=1129   # header + 1128 molecules

echo "==> Downloading ESOL CSV from ${URL}"
curl -fSL --retry 3 --retry-delay 5 -o "${DEST}.part" "$URL"

# Verify row count
ACTUAL_ROWS="$(wc -l < "${DEST}.part" | tr -d ' ')"
if [[ "$ACTUAL_ROWS" -ne "$EXPECTED_ROWS" ]]; then
  echo "ERROR: expected ${EXPECTED_ROWS} lines, got ${ACTUAL_ROWS}" >&2
  rm -f "${DEST}.part"
  exit 1
fi

mv "${DEST}.part" "$DEST"
echo "==> Saved ${DEST} (${ACTUAL_ROWS} rows)"
