#!/usr/bin/env bash
#
# ESMFold クイックスタート — Azure ML ワークスペースと GPU コンピュートをデプロイ
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
# (環境変数 YOUR_NAME / LOCATION / OWNER_EMAIL / COMPUTE_SIZE で上書き可能)
# ==========================================================================
YOUR_NAME="${YOUR_NAME:-taro}"                          # 半角小文字英数字のみ(3-8文字). 衝突回避用
LOCATION="${LOCATION:-japaneast}"                       # 既定: japaneast
OWNER_EMAIL="${OWNER_EMAIL:-taro@example.ac.jp}"        # 課金追跡タグ用
COMPUTE_SIZE="${COMPUTE_SIZE:-Standard_NC8as_T4_v3}"    # T4 16GB (推奨・低コスト). 長鎖・バッチ用は Standard_NC24ads_A100_v4
# ==========================================================================
# ▲▲▲ 変更するのはここまで ▲▲▲
# ==========================================================================

# --- 派生変数（変更不要） -------------------------------------------------
PROJECT="spread1000"
FIELD="life-pharma-science"
CATEGORY="molecular-gnn"
SCENARIO="esmfold-structure-prediction"

# サブスクリプションから決定論的なユニーク接尾辞を生成 (5 文字)
SUB_ID=$(az account show --query id -o tsv)
UNIQ=$(printf "%s|%s|%s" "${SUB_ID}" "${YOUR_NAME}" "${SCENARIO}" | md5sum | cut -c1-5)

RG="rg-${PROJECT}-${SCENARIO}-${YOUR_NAME}"
WS="mlw-esmfold-${YOUR_NAME}"                     # 33 文字以内
WS="${WS:0:33}"
CI_NAME="ci-esmfold-${YOUR_NAME}-${UNIQ}"         # 24 文字以内、リージョン内で一意
CI_NAME="${CI_NAME:0:24}"

TAGS=(
  "project=${PROJECT}"
  "field=${FIELD}"
  "category=${CATEGORY}"
  "scenario=${SCENARIO}"
  "owner=${OWNER_EMAIL}"
)

echo "==================================================================="
echo " ESMFold クイックスタート — Azure リソース作成"
echo "==================================================================="
echo " サブスクリプション : $(az account show --query name -o tsv)"
echo " リソースグループ   : ${RG}"
echo " リージョン        : ${LOCATION}"
echo " Workspace         : ${WS}"
echo " Compute (GPU)     : ${CI_NAME} (${COMPUTE_SIZE})"
echo " Owner             : ${OWNER_EMAIL}"
echo "==================================================================="
read -rp "この内容で作成しますか? [y/N]: " ANS
[[ "${ANS,,}" != "y" ]] && { echo "中止しました"; exit 1; }

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
idle_time_before_shutdown_minutes: 30
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
echo " 次のクリーンアップに使う変数 (メモしておいてください):"
echo "   RG=${RG}"
echo "   WS=${WS}"
echo "   CI=${CI_NAME}"
echo ""
echo " Workspace URL:"
echo "   https://ml.azure.com/?wsid=/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.MachineLearningServices/workspaces/${WS}"
echo ""
echo " 次のステップ (docs/03-run-esmfold.md):"
echo "   1) 上記 URL を開き、左メニュー 'コンピューティング' → '${CI_NAME}' の 'ターミナル' を起動"
echo "   2) ターミナルで以下を実行:"
echo "        cd ~ && git clone --branch main --depth 1 https://github.com/nahisaho/spread1000-azure-quickstart.git"
echo "        bash spread1000-azure-quickstart/research-fields/life-pharma-science/02-protein-structure-esmfold/scripts/setup-esmfold.sh"
echo "      (curl | bash は避け、必ずスクリプトを目で確認してから実行してください)"
echo ""
echo " ⚠️  作業終了後は必ず停止してください (課金対策):"
echo "      az ml compute stop --name ${CI_NAME} \\"
echo "        --resource-group ${RG} --workspace-name ${WS}"
echo ""

