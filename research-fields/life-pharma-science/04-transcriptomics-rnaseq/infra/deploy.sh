#!/usr/bin/env bash
# SPReAD-1000 RNA-Seq on Azure Batch — 対話デプロイスクリプト
#
# 使い方:
#   ./deploy.sh              # 対話モード
#   ./deploy.sh --yes        # 全てデフォルト、確認プロンプトなし (CI/CD 向け)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NON_INTERACTIVE=false
if [[ "${1:-}" == "--yes" ]] || [[ "${1:-}" == "-y" ]]; then
  NON_INTERACTIVE=true
fi

# ----- ユーティリティ -----
prompt() {
  local msg="$1"
  local default="${2:-}"
  local var
  if [[ "$NON_INTERACTIVE" == true ]]; then
    echo "$default"
    return
  fi
  if [[ -n "$default" ]]; then
    read -rp "$msg [$default]: " var
    echo "${var:-$default}"
  else
    read -rp "$msg: " var
    echo "$var"
  fi
}

confirm() {
  local msg="$1"
  if [[ "$NON_INTERACTIVE" == true ]]; then
    return 0
  fi
  local ans
  read -rp "$msg [y/N]: " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

echo "==== SPReAD-1000 RNA-Seq デプロイ ===="

# ----- Azure CLI 存在チェック -----
if ! command -v az >/dev/null 2>&1; then
  echo "❌ Azure CLI (az) が見つかりません。https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

# ----- サブスクリプション -----
CURRENT_SUB=$(az account show --query id -o tsv 2>/dev/null || echo "")
if [[ -z "$CURRENT_SUB" ]]; then
  echo "az login を実行してください。"
  az login
  CURRENT_SUB=$(az account show --query id -o tsv)
fi
SUBSCRIPTION_ID=$(prompt "サブスクリプション ID" "$CURRENT_SUB")
az account set --subscription "$SUBSCRIPTION_ID"

echo "現在のサブスクリプション: $(az account show --query name -o tsv)"

# ----- リージョン -----
LOCATION=$(prompt "リージョン (japaneast / japanwest / eastus2)" "japaneast")

# ----- リソースグループ -----
DEFAULT_RG="rg-spread1000-rnaseq-${USER}"
RG=$(prompt "リソースグループ名" "$DEFAULT_RG")

# ----- 命名プレフィクス (英小文字数字のみ、Storage/Batch アカウント名に使用) -----
DEFAULT_PREFIX=$(echo "rnaseq${USER}" | tr -cd 'a-z0-9' | cut -c1-15)
NAME_PREFIX=$(prompt "リソース名プレフィクス (3-15 文字、英小文字数字のみ)" "$DEFAULT_PREFIX")
if [[ ! "$NAME_PREFIX" =~ ^[a-z0-9]{3,15}$ ]]; then
  echo "❌ プレフィクスは英小文字数字 3-15 文字で指定してください: $NAME_PREFIX"
  exit 1
fi

# ----- SSH 公開鍵 -----
DEFAULT_SSH_KEY="$HOME/.ssh/id_ed25519.pub"
if [[ ! -f "$DEFAULT_SSH_KEY" ]]; then
  DEFAULT_SSH_KEY="$HOME/.ssh/id_rsa.pub"
fi
if [[ ! -f "$DEFAULT_SSH_KEY" ]]; then
  echo "⚠️  SSH 公開鍵が見つかりません。ed25519 鍵を生成します..."
  ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519"
  DEFAULT_SSH_KEY="$HOME/.ssh/id_ed25519.pub"
fi
SSH_KEY_PATH=$(prompt "SSH 公開鍵ファイル" "$DEFAULT_SSH_KEY")
if [[ ! -f "$SSH_KEY_PATH" ]]; then
  echo "❌ SSH 公開鍵ファイルが見つかりません: $SSH_KEY_PATH"
  exit 1
fi
SSH_PUBKEY=$(cat "$SSH_KEY_PATH")

# ----- 確認 -----
cat <<EOF

==== デプロイ内容 ====
サブスクリプション:  $(az account show --query name -o tsv)
リージョン:          ${LOCATION}
リソースグループ:    ${RG}
命名プレフィクス:    ${NAME_PREFIX}
SSH 公開鍵:          ${SSH_KEY_PATH}
テンプレート:        ${SCRIPT_DIR}/main.bicep

想定リソース:
  - Storage account (LRS, Hot)
  - Blob container 'omics'
  - Batch account (Batch service allocation mode)
  - Controller VM (Standard_B2s, Ubuntu 24.04) + OS ディスク (Standard SSD 64 GB)
  - Public IP (Standard, static)
  - VNet + NSG (SSH 22 のみ公開)
  - RBAC assignments (Storage Blob Data Contributor + Azure Batch Data Contributor)

想定コスト (待機時):
  - Controller VM (B2s):        ¥8.80/h = 月 ¥6,336 (常時起動時、deallocate で停止可)
  - OS ディスク (Std SSD 64GB): 月 ¥770 (deallocate しても発生)
  - Public IP (Standard):        月 ¥590 (deallocate しても発生)
  - Storage (30 GB Hot):        月 ¥97
  - Batch account:              ¥0 (基盤料金なし)

EOF

if ! confirm "このリソースをデプロイしますか？"; then
  echo "キャンセルしました。"
  exit 0
fi

# ----- リソースプロバイダー登録 -----
echo "==== リソースプロバイダーを登録中 (完了まで待機) ===="
REG_PIDS=()
for RP in Microsoft.Batch Microsoft.Storage Microsoft.Compute Microsoft.Network Microsoft.ManagedIdentity; do
  STATE=$(az provider show --namespace "$RP" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "$STATE" != "Registered" ]]; then
    echo "  $RP を登録中..."
    az provider register --namespace "$RP" --wait &
    REG_PIDS+=($!)
  fi
done
for PID in "${REG_PIDS[@]:-}"; do
  wait "$PID" || true
done
# 最終確認
for RP in Microsoft.Batch Microsoft.Storage Microsoft.Compute Microsoft.Network Microsoft.ManagedIdentity; do
  STATE=$(az provider show --namespace "$RP" --query registrationState -o tsv)
  if [[ "$STATE" != "Registered" ]]; then
    echo "❌ プロバイダー $RP の登録が完了しませんでした (state=$STATE)。しばらく待って再実行してください。"
    exit 1
  fi
done

# ----- リソースグループ作成 -----
echo "==== リソースグループ作成 ===="
az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --tags project=spread1000 field=life-pharma-science scenario=rnaseq-nextflow \
  -o none

# ----- what-if -----
echo "==== what-if で差分確認 ===="
az deployment group what-if \
  --resource-group "$RG" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters namePrefix="$NAME_PREFIX" \
               location="$LOCATION" \
               adminSshPublicKey="$SSH_PUBKEY" \
  || true

if ! confirm "上記の変更を実行しますか？"; then
  echo "キャンセルしました。"
  exit 0
fi

# ----- 本番デプロイ -----
echo "==== Bicep デプロイ実行 (10-15 分) ===="
DEPLOY_NAME="rnaseq-$(date +%Y%m%d-%H%M%S)"
az deployment group create \
  --resource-group "$RG" \
  --name "$DEPLOY_NAME" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters namePrefix="$NAME_PREFIX" \
               location="$LOCATION" \
               adminSshPublicKey="$SSH_PUBKEY" \
  -o none

# ----- 出力の取得と表示 -----
echo "==== デプロイ完了 ===="
OUTPUTS=$(az deployment group show \
  --resource-group "$RG" \
  --name "$DEPLOY_NAME" \
  --query properties.outputs)

echo "$OUTPUTS" | jq -r '
"  Resource Group:       \(.resourceGroupName.value)
  Batch Account:        \(.batchAccountName.value)
  Batch Endpoint:       \(.batchAccountEndpoint.value)
  Storage Account:      \(.storageAccountName.value)
  Blob Container:       \(.blobContainerName.value)
  Controller VM:        \(.controllerVmName.value)
  Controller Public IP: \(.controllerVmPublicIp.value)"'

CONTROLLER_IP=$(echo "$OUTPUTS" | jq -r '.controllerVmPublicIp.value')
BATCH_ACCT=$(echo "$OUTPUTS" | jq -r '.batchAccountName.value')
STORAGE_ACCT=$(echo "$OUTPUTS" | jq -r '.storageAccountName.value')

cat <<EOF

==== 次のステップ ====
1. Controller VM に SSH:
   ssh azureuser@${CONTROLLER_IP}

2. Controller VM 上で Nextflow をインストール:
   curl -sSL https://raw.githubusercontent.com/nahisaho/spread1000-azure-quickstart/main/research-fields/life-pharma-science/04-transcriptomics-rnaseq/scripts/install-nextflow.sh | bash

3. 環境変数を設定 (~/.bashrc に追加):
   export AZURE_LOCATION=${LOCATION}
   export AZURE_RESOURCE_GROUP=${RG}
   export AZURE_BATCH_ACCOUNT=${BATCH_ACCT}
   export AZURE_STORAGE_ACCOUNT=${STORAGE_ACCT}
   export NXF_VER=26.04.6

4. docs/03-run-demo.md に従い、nf-core/rnaseq test プロファイルを実行

⚠️  忘れずに: 使用後は docs/05-cleanup.md でプールを 0 に縮小してください
EOF
