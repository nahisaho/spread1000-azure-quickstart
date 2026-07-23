#!/usr/bin/env bash
# GraphRAG エンドツーエンド実行スクリプト
# ------------------------------------------------
# 1. `graphrag init` で ./ragtest 配下に設定ファイル雛形を作る
# 2. data/input/*.txt を ./ragtest/input/ にコピー
# 3. settings.yaml を Azure OpenAI 用に上書き
# 4. `graphrag index` でエンティティ・関係・コミュニティ抽出
# 5. サンプル local / global クエリを実行

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

if [[ ! -f .env ]]; then
    echo "[error] .env が見つかりません。cp .env.example .env で作成して編集してください。" >&2
    exit 1
fi

# .env を読み込む (GRAPHRAG_API_KEY 等)
set -a
# shellcheck disable=SC1091
source .env
set +a

RAGDIR="${ROOT}/ragtest"

# --- Step 1: init ----------------------------------------------------
if [[ ! -f "${RAGDIR}/settings.yaml" ]]; then
    echo "[1/5] graphrag init --root ${RAGDIR}"
    python -m graphrag init --root "${RAGDIR}"
else
    echo "[1/5] ${RAGDIR}/settings.yaml は既に存在。skip"
fi

# --- Step 2: input -----------------------------------------------------
echo "[2/5] コーパスを ${RAGDIR}/input/ にコピー"
mkdir -p "${RAGDIR}/input"
cp "${ROOT}/data/input/"*.txt "${RAGDIR}/input/"

# --- Step 3: settings.yaml を Azure OpenAI 用に置換 -----------------
echo "[3/5] settings.yaml を Azure OpenAI 設定で上書き"
cp "${ROOT}/src/settings.yaml" "${RAGDIR}/settings.yaml"

# --- Step 4: index -----------------------------------------------------
echo "[4/5] graphrag index (数分〜十数分、\$1〜\$5 程度のコストがかかります)"
python -m graphrag index --root "${RAGDIR}"

# --- Step 5: sample queries -------------------------------------------
echo "[5/5] サンプルクエリ"
echo
echo "--- GLOBAL: Who were the main intellectuals of Meiji-era Japan and how are they connected?"
python -m graphrag query --root "${RAGDIR}" --method global \
    --query "Who were the main intellectuals connecting Rangaku and the Meiji Restoration, and how were they related?"

echo
echo "--- LOCAL: What did Sugita Genpaku translate and with whom?"
python -m graphrag query --root "${RAGDIR}" --method local \
    --query "What did Sugita Genpaku translate and who were his collaborators?"

echo
echo "[done] エンティティ・関係・コミュニティは ${RAGDIR}/output/ に parquet 形式で保存されました。"
