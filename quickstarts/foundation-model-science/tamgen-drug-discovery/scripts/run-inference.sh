#!/usr/bin/env bash
#
# TamGen 推論ラッパー (シェル)
# -----------------------------
# Compute Instance 上、conda env `TamGen` が有効な状態で実行してください。
#
# 例:
#   bash run-inference.sh 3wze
#   bash run-inference.sh 3wze 50   # 50 分子を生成
#
set -euo pipefail

PDB_ID="${1:-3wze}"
NUM_MOL="${2:-50}"
WORK_DIR="${HOME}/TamGen"
CONDA_ENV="TamGen"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${WORK_DIR}" ]]; then
  echo "❌ ${WORK_DIR} が存在しません。先に setup-tamgen.sh を実行してください。"
  exit 1
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

cd "${WORK_DIR}"

echo "==== TamGen 推論 (PDB=${PDB_ID}, N=${NUM_MOL}) ===="
python "${SCRIPT_DIR}/generate_from_pdb.py" \
  --pdb "${PDB_ID}" \
  --num-molecules "${NUM_MOL}" \
  --output-dir "output/${PDB_ID}"

echo ""
echo "結果を確認:"
echo "  cat ${WORK_DIR}/output/${PDB_ID}/generation_stats.json"
echo "  head -5 ${WORK_DIR}/output/${PDB_ID}/generated_molecules.csv"
