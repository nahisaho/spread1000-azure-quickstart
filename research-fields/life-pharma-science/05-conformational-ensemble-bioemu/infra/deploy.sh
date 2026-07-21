#!/usr/bin/env bash
# BioEmu AML workspace ワンショットデプロイ
#
# 事前:
#   export AZURE_SUBSCRIPTION_ID=<subscription id>
#   export AZURE_LOCATION=japaneast
#   export AZURE_RESOURCE_GROUP=rg-spread1000-bioemu
#
# 実行:
#   bash infra/deploy.sh
#
# 出力 (workspace 名など) は最後に echo される。

set -euo pipefail

: "${AZURE_SUBSCRIPTION_ID:?AZURE_SUBSCRIPTION_ID を export してください}"
: "${AZURE_LOCATION:=japaneast}"
: "${AZURE_RESOURCE_GROUP:=rg-spread1000-bioemu}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==== BioEmu AML workspace デプロイ ===="
echo "  Subscription: $AZURE_SUBSCRIPTION_ID"
echo "  Location:     $AZURE_LOCATION"
echo "  RG:           $AZURE_RESOURCE_GROUP"
echo ""

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

DEPLOY_NAME="bioemu-$(date -u +%Y%m%d%H%M%S)"

echo "==== Bicep デプロイ開始 (5〜10 分) ===="
DEPLOY_JSON=$(az deployment sub create \
  --name "$DEPLOY_NAME" \
  --location "$AZURE_LOCATION" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters location="$AZURE_LOCATION" resourceGroupName="$AZURE_RESOURCE_GROUP" \
  --output json)

WORKSPACE_NAME=$(echo "$DEPLOY_JSON" | jq -r '.properties.outputs.workspaceName.value')
STORAGE_NAME=$(echo "$DEPLOY_JSON" | jq -r '.properties.outputs.storageAccountName.value')
KV_NAME=$(echo "$DEPLOY_JSON" | jq -r '.properties.outputs.keyVaultName.value')

cat <<EOF

==== デプロイ完了 ====
  Workspace:       $WORKSPACE_NAME
  Storage Account: $STORAGE_NAME
  Key Vault:       $KV_NAME

次のコマンドで環境変数を設定してください:

  export AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP
  export AZURE_WORKSPACE_NAME=$WORKSPACE_NAME
  export AZURE_STORAGE_ACCOUNT=$STORAGE_NAME

  az configure --defaults group=\$AZURE_RESOURCE_GROUP workspace=\$AZURE_WORKSPACE_NAME

続いて: docs/02-provision-aml.md §3〜§5 (custom environment + A100 compute の作成)
EOF
