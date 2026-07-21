#!/usr/bin/env bash
# Download REINVENT4 v4.8 pretrained priors from Zenodo (Apache-2.0)
# Source: https://zenodo.org/records/20701824
#
# Uses the Zenodo REST API to fetch canonical md5 + size for each file, then
# downloads to *.part, verifies, and atomically renames. Existing files are
# re-verified on every run so a corrupted rerun repairs itself.
set -Eeuo pipefail

TARGET_DIR="$(dirname "$0")/../priors"
mkdir -p "$TARGET_DIR"

ZENODO_RECORD="20701824"
API_URL="https://zenodo.org/api/records/${ZENODO_RECORD}"

FILES=(
  "libinvent.prior"
  "reinvent_pubchem.prior"
)

command -v jq >/dev/null 2>&1 || {
  echo "🛑 jq が必要です。'sudo apt-get install -y jq' (Debian/Ubuntu/WSL2)、'brew install jq' (macOS) などでインストールしてください。" >&2
  exit 1
}

# Detect an md5 command that works on Linux (md5sum, coreutils gmd5sum) and macOS (md5 -q).
if command -v md5sum >/dev/null 2>&1; then
  MD5CMD=(md5sum)
  MD5_PARSE='awk "{print \$1}"'
elif command -v gmd5sum >/dev/null 2>&1; then
  MD5CMD=(gmd5sum)
  MD5_PARSE='awk "{print \$1}"'
elif command -v md5 >/dev/null 2>&1; then
  # macOS BSD md5: `md5 -q <file>` prints only the digest
  MD5CMD=(md5 -q)
  MD5_PARSE='cat'
else
  echo "🛑 md5sum / gmd5sum / md5 のいずれも見つかりません (Linux: coreutils, macOS: builtin md5)。" >&2
  exit 1
fi

echo "==> Fetching Zenodo file manifest"
MANIFEST=$(curl -fsSL "$API_URL")

verify_file() {
  local path="$1" expected_md5="$2" expected_size="$3"
  local actual_size actual_md5
  actual_size=$(wc -c < "$path")
  if [ "$actual_size" -ne "$expected_size" ]; then
    echo "  size mismatch: expected=$expected_size actual=$actual_size" >&2
    return 1
  fi
  actual_md5=$("${MD5CMD[@]}" "$path" | eval "$MD5_PARSE")
  if [ "$actual_md5" != "$expected_md5" ]; then
    echo "  md5 mismatch: expected=$expected_md5 actual=$actual_md5" >&2
    return 1
  fi
  return 0
}

for f in "${FILES[@]}"; do
  entry=$(printf '%s' "$MANIFEST" | jq -c --arg key "$f" '.files[] | select(.key == $key)')
  if [ -z "$entry" ] || [ "$entry" = "null" ]; then
    echo "🛑 Zenodo manifest に $f が見つかりません。record ID または filename を確認してください。" >&2
    exit 1
  fi
  url=$(printf '%s' "$entry" | jq -r '.links.self')
  # checksum is either "md5:xxxx" or a bare hex string depending on Zenodo API version
  raw_ck=$(printf '%s' "$entry" | jq -r '.checksum')
  md5="${raw_ck#md5:}"
  size=$(printf '%s' "$entry" | jq -r '.size')
  human=$(awk -v s="$size" 'BEGIN{printf "%.1f MB", s/1048576}')

  if [ -f "$TARGET_DIR/$f" ]; then
    if verify_file "$TARGET_DIR/$f" "$md5" "$size" 2>/dev/null; then
      echo "  ✓ already have (verified): $f (${human})"
      continue
    fi
    echo "  ! existing $f failed verification, re-downloading"
    rm -f "$TARGET_DIR/$f"
  fi

  echo "  ↓ downloading: $f (${human})"
  curl -fSL --retry 3 --retry-delay 5 \
    -o "$TARGET_DIR/${f}.part" \
    "$url"

  if verify_file "$TARGET_DIR/${f}.part" "$md5" "$size"; then
    mv "$TARGET_DIR/${f}.part" "$TARGET_DIR/$f"
    echo "  ✓ verified: $f"
  else
    echo "🛑 $f の検証に失敗しました。もう一度スクリプトを実行してください。" >&2
    rm -f "$TARGET_DIR/${f}.part"
    exit 1
  fi
done

echo ""
echo "Downloaded files:"
ls -lh "$TARGET_DIR"
echo "✅ Prior download successful."
