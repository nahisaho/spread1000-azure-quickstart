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
# SHA-256 of the currently served DeepChem ESOL CSV.
# If this changes upstream, verify the new bytes against a checked-in
# reference publication before updating (row count alone can mask silent
# schema/data drift and defeats the "reproducible dataset" claim).
EXPECTED_SHA256="8c06a76f0c6487d29ab0f903e6a7a7139f189ab3c1178f159c8be8964602f189"

echo "==> Downloading ESOL CSV from ${URL}"
curl -fSL --retry 3 --retry-delay 5 -o "${DEST}.part" "$URL"

# Verify row count
ACTUAL_ROWS="$(wc -l < "${DEST}.part" | tr -d ' ')"
if [[ "$ACTUAL_ROWS" -ne "$EXPECTED_ROWS" ]]; then
  echo "ERROR: expected ${EXPECTED_ROWS} lines, got ${ACTUAL_ROWS}" >&2
  rm -f "${DEST}.part"
  exit 1
fi

# Verify SHA-256 (portable: sha256sum on Linux, shasum -a 256 on macOS)
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL_SHA="$(sha256sum "${DEST}.part" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL_SHA="$(shasum -a 256 "${DEST}.part" | awk '{print $1}')"
else
  echo "ERROR: neither sha256sum nor shasum available for checksum verification" >&2
  rm -f "${DEST}.part"
  exit 1
fi
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA256" ]]; then
  echo "ERROR: SHA-256 mismatch." >&2
  echo "  expected: ${EXPECTED_SHA256}" >&2
  echo "  actual:   ${ACTUAL_SHA}" >&2
  echo "  Upstream DeepChem may have republished the file. Do NOT proceed until you verify" >&2
  echo "  the new bytes against a citable reference (Delaney 2004 J. Chem. Inf. Comput. Sci.)" >&2
  echo "  and then update EXPECTED_SHA256 in this script." >&2
  rm -f "${DEST}.part"
  exit 1
fi

mv "${DEST}.part" "$DEST"
echo "==> Saved ${DEST} (${ACTUAL_ROWS} rows)"
