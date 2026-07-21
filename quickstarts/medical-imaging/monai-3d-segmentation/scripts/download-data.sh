#!/usr/bin/env bash
# MSD Task09_Spleen (~1.5 GB) をローカルに取得
# 出典: http://medicaldecathlon.com/
# ライセンス: CC BY-SA 4.0
# 使い方: ./download-data.sh [保存先ディレクトリ]

set -euo pipefail

DEST_DIR="${1:-./msd-data}"
# 一次ソース: AWS Open Data Registry (MSD ミラー、CC-BY-SA 4.0)
#   https://registry.opendata.aws/msd/
# medicaldecathlon.com の直接 URL は 2025 年以降不安定なため、
# AWS S3 ミラーを既定ソースとして採用。
URL="${MSD_URL:-https://msd-for-monai.s3-us-west-2.amazonaws.com/Task09_Spleen.tar}"

mkdir -p "$DEST_DIR"
cd "$DEST_DIR"

# 展開済みディレクトリの整合性チェック
check_integrity() {
  local dir="$1"
  local imagesTr labelsTr imagesTs dsjson
  imagesTr=$(find "$dir/imagesTr" -maxdepth 1 -name '*.nii.gz' 2>/dev/null | wc -l)
  labelsTr=$(find "$dir/labelsTr" -maxdepth 1 -name '*.nii.gz' 2>/dev/null | wc -l)
  imagesTs=$(find "$dir/imagesTs" -maxdepth 1 -name '*.nii.gz' 2>/dev/null | wc -l)
  dsjson=$([[ -f "$dir/dataset.json" ]] && echo 1 || echo 0)
  # 期待値: 41 imagesTr / 41 labelsTr / 20 imagesTs / dataset.json
  [[ "$imagesTr" -eq 41 && "$labelsTr" -eq 41 && "$imagesTs" -eq 20 && "$dsjson" -eq 1 ]]
}

if [[ -d "Task09_Spleen" ]]; then
  if check_integrity "Task09_Spleen"; then
    echo "  ✓ Task09_Spleen が既に存在し整合性 OK: $(pwd)/Task09_Spleen"
    exit 0
  fi
  echo "  ⚠ Task09_Spleen が不完全です。削除して再取得します。"
  rm -rf "Task09_Spleen"
fi

echo "==== Task09_Spleen (~1.5 GB) をダウンロード ===="
echo "  URL:  $URL"
echo "  Dest: $(pwd)/Task09_Spleen.tar"
echo ""

# 一次ソース (medicaldecathlon.com) は 2025 年以降不安定なため、
# AWS Open Data Registry (msd-for-monai) を既定として使用。
# 元サイトを試す場合は次を実行:
#   MSD_URL=http://medicaldecathlon.com/files/Task09_Spleen.tar ./download-data.sh
curl -fL --retry 3 --retry-delay 5 -o Task09_Spleen.tar "$URL"

echo ""
echo "==== 展開 (一時ディレクトリ経由で原子的に配置) ===="
STAGING=".stage-$$"
mkdir -p "$STAGING"
tar -xf Task09_Spleen.tar -C "$STAGING"

# `tar` の内容は `Task09_Spleen/` を1階層目に含む
if [[ ! -d "$STAGING/Task09_Spleen" ]]; then
  echo "❌ アーカイブに Task09_Spleen/ が含まれません" >&2
  rm -rf "$STAGING" Task09_Spleen.tar
  exit 1
fi

if ! check_integrity "$STAGING/Task09_Spleen"; then
  echo "❌ 展開後の整合性チェック失敗 (期待: 41+41+20+dataset.json)" >&2
  rm -rf "$STAGING" Task09_Spleen.tar
  exit 1
fi

mv "$STAGING/Task09_Spleen" ./Task09_Spleen
rm -rf "$STAGING"
rm -f Task09_Spleen.tar

echo ""
echo "==== 内容確認 ===="
ls -la Task09_Spleen/
echo ""
echo "  imagesTr: $(find Task09_Spleen/imagesTr -name '*.nii.gz' | wc -l) files"
echo "  labelsTr: $(find Task09_Spleen/labelsTr -name '*.nii.gz' | wc -l) files"
echo "  imagesTs: $(find Task09_Spleen/imagesTs -name '*.nii.gz' | wc -l) files"

echo ""
echo "==== 完了 ===="
echo "  次のステップ: ./scripts/upload-dataset.sh $(pwd)/Task09_Spleen"
