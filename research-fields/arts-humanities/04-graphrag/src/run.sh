#!/usr/bin/env bash
# GraphRAG エンドツーエンド実行スクリプト
# ------------------------------------------------
# 1. `graphrag init` で ./ragtest 配下に設定ファイル雛形を作る
# 2. data/input/*.txt を ./ragtest/input/ にコピー (既存ファイルは削除して同期)
# 3. settings.yaml を Azure OpenAI 用に上書き
# 4. コーパスサイズを推定してユーザー確認 (大規模ならスキップ)
# 5. `graphrag index --dry-run` で設定検証 → 本番 `graphrag index`
# 6. サンプル local / global クエリを実行

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
    echo "[1/6] graphrag init --root ${RAGDIR}"
    python -m graphrag init --root "${RAGDIR}"
else
    echo "[1/6] ${RAGDIR}/settings.yaml は既に存在。skip"
fi

# --- Step 2: input (削除 → コピーで同期。古い入力の残留を防ぐ) ------
echo "[2/6] コーパスを ${RAGDIR}/input/ に同期 (古いファイル削除 + 新規コピー)"
mkdir -p "${RAGDIR}/input"
find "${RAGDIR}/input" -type f -name '*.txt' -delete
cp "${ROOT}/data/input/"*.txt "${RAGDIR}/input/"

# --- Step 3: settings.yaml を Azure OpenAI 用に置換 -----------------
echo "[3/6] settings.yaml を Azure OpenAI 設定で上書き"
cp "${ROOT}/src/settings.yaml" "${RAGDIR}/settings.yaml"
# ragtest/.env にも同期 (graphrag CLI が ragtest ディレクトリで env を探すため)
cp "${ROOT}/.env" "${RAGDIR}/.env"

# --- Step 4: コーパスサイズ推定 + 確認 ---------------------------------
TOTAL_BYTES=$(du -sb "${RAGDIR}/input" | awk '{print $1}')
# 概算: 1 word ≈ 5 bytes, tokens ≈ words × 1.3
EST_TOKENS=$(( TOTAL_BYTES * 13 / 50 ))
# GraphRAG は入力の 3-5x のトークンを LLM 呼び出しで消費
EST_LLM_CALLS_TOKENS=$(( EST_TOKENS * 4 ))
# gpt-4o-mini: 入力 $0.15/1M + 出力 $0.60/1M ≈ 実効 $0.30/1M
EST_COST_USD=$(awk "BEGIN {printf \"%.2f\", $EST_LLM_CALLS_TOKENS / 1000000.0 * 0.30}")
echo "[4/6] 入力サイズ: $((TOTAL_BYTES / 1024)) KB, 推定入力トークン: ${EST_TOKENS}, gpt-4o-mini 想定コスト: \$${EST_COST_USD}"
BUDGET_LIMIT="${GRAPHRAG_BUDGET_USD:-10}"
if awk "BEGIN {exit !($EST_COST_USD > $BUDGET_LIMIT)}"; then
    echo "[warn] 推定コストが上限 \$${BUDGET_LIMIT} を超えています。"
    echo "       続行するには GRAPHRAG_BUDGET_USD=<予算上限> を明示的に設定してください。"
    exit 2
fi

# --- Step 5: dry-run + 本番 index ---------------------------------
echo "[5/6] graphrag index --dry-run で設定検証"
python -m graphrag index --root "${RAGDIR}" --dry-run

echo "[5/6] graphrag index (本番。LLM 呼び出しでコストが発生します)"
python -m graphrag index --root "${RAGDIR}"

# --- Step 6: sample queries -------------------------------------------
echo "[6/6] サンプルクエリ"
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
