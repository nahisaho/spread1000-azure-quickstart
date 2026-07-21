#!/usr/bin/env bash
# MIT-BIH Arrhythmia Database v1.0.0 をローカルにダウンロード
# 公開データ (ODC-By 1.0)、48 レコード、~104MB
set -Eeuo pipefail

DATA_DIR="${1:-./data/mitdb-1.0.0}"
mkdir -p "$DATA_DIR"

echo "==== MIT-BIH v1.0.0 ダウンロード先: $DATA_DIR ===="
cd "$DATA_DIR"

# PhysioNet 公式手順 (再帰・タイムスタンプ・continue・parent禁止)
# 参考: https://physionet.org/content/mitdb/1.0.0/#files
wget -q --show-progress -r -N -c -np -nH --cut-dirs=4 \
     -R "index.html*" \
     "https://physionet.org/files/mitdb/1.0.0/"

DAT_COUNT=$(find . -maxdepth 1 -name '*.dat' | wc -l)
echo ""
echo "  ✓ .dat files: $DAT_COUNT (期待値: 48)"

if [[ "$DAT_COUNT" -lt 48 ]]; then
  echo "  ⚠️ ダウンロード不完全の可能性。ネットワーク/プロキシを確認して再実行してください。"
  exit 1
fi

echo ""
echo "==== 次のステップ ===="
echo "  bash scripts/upload-dataset.sh"
