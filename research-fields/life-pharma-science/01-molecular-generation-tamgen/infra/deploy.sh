#!/usr/bin/env bash
#
# TamGen クイックスタート — Azure ML ワークスペースと GPU コンピュートをデプロイ
#
# 使い方:
#   1) 下の「変更するのはここだけ」ブロックを編集
#   2) chmod +x deploy.sh
#   3) ./deploy.sh
#
# 前提: az login 済み、正しい subscription が選択済み、Azure ML GPU クォータ確保済み
#       ( ../docs/01-prerequisites.md を参照 )
#
set -euo pipefail

# ==========================================================================
# ▼▼▼ 変更するのはここだけ ▼▼▼
# ==========================================================================
YOUR_NAME="taro"                          # 半角小文字英数字のみ(3-8文字). 衝突回避用
LOCATION="japaneast"                       # 既定: japaneast
OWNER_EMAIL="taro@example.ac.jp"          # 課金追跡タグ用
COMPUTE_SIZE="Standard_NC24ads_A100_v4"   # A100 80GB (推奨). 予算重視なら Standard_NC8as_T4_v3
# ==========================================================================
# ▲▲▲ 変更するのはここまで ▲▲▲
# ==========================================================================

# --- 派生変数（変更不要） -------------------------------------------------
PROJECT="spread1000"
FIELD="life-pharma-science"
CATEGORY="foundation-model-science"
SCENARIO="tamgen-drug-discovery"

# サブスクリプションから決定論的なユニーク接尾辞を生成 (5 文字)
SUB_ID=$(az account show --query id -o tsv)
# macOS の stock 環境には md5sum も coreutils も無いため portable なハッシュを使用
if command -v md5sum >/dev/null 2>&1; then
  UNIQ=$(printf "%s|%s|%s" "${SUB_ID}" "${YOUR_NAME}" "${SCENARIO}" | md5sum | cut -c1-5)
elif command -v md5 >/dev/null 2>&1; then
  # macOS/BSD の md5 (-q は quiet)
  UNIQ=$(printf "%s|%s|%s" "${SUB_ID}" "${YOUR_NAME}" "${SCENARIO}" | md5 -q | cut -c1-5)
else
  # 最後の手段: Python (どの環境にも通常入っている)
  UNIQ=$(printf "%s|%s|%s" "${SUB_ID}" "${YOUR_NAME}" "${SCENARIO}" \
    | python3 -c 'import hashlib,sys; print(hashlib.md5(sys.stdin.read().encode()).hexdigest()[:5])')
fi

RG="rg-${PROJECT}-${SCENARIO}-${YOUR_NAME}"
WS="mlw-${SCENARIO:0:12}-${YOUR_NAME}"           # 33 文字以内
WS="${WS:0:33}"
CI_NAME="ci-tamgen-${YOUR_NAME}-${UNIQ}"          # 24 文字以内、リージョン内で一意
CI_NAME="${CI_NAME:0:24}"

TAGS=(
  "project=${PROJECT}"
  "field=${FIELD}"
  "category=${CATEGORY}"
  "scenario=${SCENARIO}"
  "owner=${OWNER_EMAIL}"
)

echo "==================================================================="
echo " TamGen クイックスタート — Azure リソース作成"
echo "==================================================================="
echo " サブスクリプション : $(az account show --query name -o tsv)"
echo " リソースグループ   : ${RG}"
echo " リージョン        : ${LOCATION}"
echo " Workspace         : ${WS}"
echo " Compute (GPU)     : ${CI_NAME} (${COMPUTE_SIZE})"
echo " Owner             : ${OWNER_EMAIL}"
echo "==================================================================="
read -rp "この内容で作成しますか? [y/N]: " ANS
# ${var,,} は Bash 4+ 依存 (macOS の stock Bash 3.2 では syntax error)。portable な case 文で判定
case "${ANS}" in
  y|Y|yes|Yes|YES) ;;
  *) echo "中止しました"; exit 1 ;;
esac

# --- 0. Azure ML 拡張機能 ------------------------------------------------
echo "[0/5] Azure ML 拡張機能を確認..."
az extension add --name ml --upgrade --yes --only-show-errors

# --- 1. リソースプロバイダー登録 -----------------------------------------
echo "[1/5] リソースプロバイダー登録..."
REQUIRED_RPS=(Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault
              Microsoft.Insights Microsoft.ContainerRegistry Microsoft.Network Microsoft.Compute)

# まずは全プロバイダーを並行登録キック (--wait を付けない)
for RP in "${REQUIRED_RPS[@]}"; do
  STATE=$(az provider show --namespace "${RP}" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "${STATE}" != "Registered" ]]; then
    echo "  → ${RP} 登録キック (state=${STATE})"
    az provider register --namespace "${RP}" --only-show-errors >/dev/null || true
  fi
done

# ワークスペース作成に必須の 3 つだけをポーリング (最大 5 分)
CRITICAL_RPS=(Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault)
DEADLINE=$(( $(date +%s) + 300 ))
for RP in "${CRITICAL_RPS[@]}"; do
  while :; do
    STATE=$(az provider show --namespace "${RP}" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
    [[ "${STATE}" == "Registered" ]] && { echo "  ✓ ${RP} Registered"; break; }
    if (( $(date +%s) > DEADLINE )); then
      echo "  ✗ ${RP} が 5 分以内に Registered になりませんでした (現在 ${STATE})。" >&2
      echo "    しばらく待ってから再実行するか、Portal から手動登録してください。" >&2
      exit 1
    fi
    sleep 15
  done
done

# --- 2. リソースグループ -------------------------------------------------
echo "[2/5] リソースグループ作成..."
az group create \
  --name "${RG}" \
  --location "${LOCATION}" \
  --tags "${TAGS[@]}" \
  --output none

# --- 3. Azure ML Workspace ----------------------------------------------
echo "[3/5] Azure ML Workspace 作成 (5-8 分)..."
az ml workspace create \
  --resource-group "${RG}" \
  --name "${WS}" \
  --location "${LOCATION}" \
  --tags "${TAGS[@]}" \
  --output none

# --- 3.5 依存リソースにもタグを伝播 (az ml workspace create は本体しか付けないため) --
echo "[3.5/5] 依存リソースにタグを伝播..."
DEP_IDS=$(az resource list --resource-group "${RG}" --query "[?type != 'Microsoft.MachineLearningServices/workspaces'].id" -o tsv)
if [[ -n "${DEP_IDS}" ]]; then
  while IFS= read -r RID; do
    az tag update --resource-id "${RID}" --operation merge \
      --tags "${TAGS[@]}" --output none 2>/dev/null || true
  done <<< "${DEP_IDS}"
fi

# --- 4. GPU Compute Instance --------------------------------------------
echo "[4/5] GPU Compute Instance 作成 (3-5 分)..."

# サインイン中のユーザーを assignedUser として設定 (CLI 経由なら自動割当だが明示)
MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)

cat > /tmp/ci-${YOUR_NAME}-${UNIQ}.yml <<EOF
\$schema: https://azuremlschemas.azureedge.net/latest/computeInstance.schema.json
name: ${CI_NAME}
type: computeinstance
size: ${COMPUTE_SIZE}
idle_time_before_shutdown_minutes: 60
tags:
  project: ${PROJECT}
  field: ${FIELD}
  category: ${CATEGORY}
  scenario: ${SCENARIO}
  owner: ${OWNER_EMAIL}
EOF

az ml compute create \
  --file /tmp/ci-${YOUR_NAME}-${UNIQ}.yml \
  --resource-group "${RG}" \
  --workspace-name "${WS}" \
  --output none

rm -f /tmp/ci-${YOUR_NAME}-${UNIQ}.yml

# --- 5. 完了 -------------------------------------------------------------
echo ""
echo "==================================================================="
echo " ✅ デプロイ完了"
echo "==================================================================="
echo ""
echo " Workspace URL:"
echo "   https://ml.azure.com/?wsid=/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.MachineLearningServices/workspaces/${WS}"
echo ""
echo " 次のステップ (docs/03-run-tamgen.md):"
echo "   1) 上記 URL を開き、左メニュー 'コンピューティング' → '${CI_NAME}' の 'ターミナル' を起動"
echo "   2) ターミナルで以下を実行:"
echo "        cd ~ && git clone --branch main --depth 1 https://github.com/nahisaho/spread1000-azure-quickstart.git"
echo "        bash spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh"
echo "      (curl | bash は避け、必ずスクリプトを目で確認してから実行してください)"
echo ""
echo " ⚠️  作業終了後は必ず停止してください (課金対策):"
echo "      az ml compute stop --name ${CI_NAME} \\"
echo "        --resource-group ${RG} --workspace-name ${WS}"
echo ""

