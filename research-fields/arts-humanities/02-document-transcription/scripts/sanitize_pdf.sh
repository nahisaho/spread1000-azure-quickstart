#!/usr/bin/env bash
# sanitize_pdf.sh — Strip PDF metadata before Document Intelligence submission.
#
# Usage: bash scripts/sanitize_pdf.sh <input.pdf> <output.pdf>
#
# For images (JPEG/PNG/TIFF):
#   exiftool -all= --icc_profile:all= image.jpg
#
# Note: exiftool edits alone may not remove metadata embedded in PDF object streams;
# qpdf --linearize rewrites the PDF structure to remove residual objects.
#
# Dependencies:
#   apt install libimage-exiftool-perl qpdf
set -euo pipefail

IN="${1:-}"
OUT="${2:-}"

if [[ -z "$IN" || -z "$OUT" ]]; then
  echo "Usage: $0 <input.pdf> <output.pdf>" >&2
  exit 1
fi

command -v exiftool >/dev/null || {
  echo "[error] exiftool not found. Install: apt install libimage-exiftool-perl" >&2
  exit 1
}
command -v qpdf >/dev/null || {
  echo "[error] qpdf not found. Install: apt install qpdf" >&2
  exit 1
}

TMP_PDF="${OUT%.pdf}.sanitize_tmp.pdf"

# Step 1: strip all metadata with exiftool
exiftool -overwrite_original -all= "$IN" -o "$TMP_PDF"

# Step 2: rewrite PDF structure to eliminate residual metadata objects
qpdf --linearize --object-streams=generate --remove-unreferenced-resources=yes "$TMP_PDF" "$OUT"

# Step 3: verify no sensitive fields remain
REMAINING=$(exiftool "$OUT" | grep -E "Author|Creator|Producer|GPS|Modify Date" || true)
if [[ -n "$REMAINING" ]]; then
  echo "[warn] residual metadata detected in output:" >&2
  echo "$REMAINING" >&2
  rm -f "$TMP_PDF"
  exit 2
fi

rm -f "$TMP_PDF"
echo "[done] Sanitized: $OUT"
