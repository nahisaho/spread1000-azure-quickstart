#!/usr/bin/env bash
# AML ワークスペース + 依存リソース (Storage/ACR/KeyVault/AppInsights) をデプロイ
# 使い方: ./deploy.sh
# 事前: docs/01-prerequisites.md の環境変数 (AZURE_LOCATION, AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME) を export

set -euo pipefail

: "${AZURE_LOCATION:?環境変数 AZURE_LOCATION を設定してください (例: japaneast)}"
: "${AZURE_RESOURCE_GROUP:?環境変数 AZURE_RESOURCE_GROUP を設定してください}"
: "${AZURE_WORKSPACE_NAME:?環境変数 AZURE_WORKSPACE_NAME を設定してください}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_NAME="monai-$(date +%Y%m%d-%H%M%S)"

echo "==== プロバイダー登録 ===="
for rp in Microsoft.MachineLearningServices \
          Microsoft.Storage \
          Microsoft.ContainerRegistry \
          Microsoft.KeyVault \
          Microsoft.Insights \
          Microsoft.OperationalInsights \
          Microsoft.Compute; do
  state=$(az provider show --namespace "$rp" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "$state" != "Registered" ]]; then
    echo "  → registering $rp ..."
    az provider register --namespace "$rp" --wait
  else
    echo "  ✓ $rp"
  fi
done

echo ""
echo "==== Resource Group 作成 ===="
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --tags scenario=monai-3d-seg project=spread1000 \
  --output none

echo "  ✓ $AZURE_RESOURCE_GROUP ($AZURE_LOCATION)"

echo ""
echo "==== 現在の Azure AD ユーザー ObjectId ===="
DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
echo "  ✓ $DEPLOYER_OID"

echo ""
echo "==== Bicep デプロイ ===="
OUTPUTS=$(az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters \
      workspaceName="$AZURE_WORKSPACE_NAME" \
      deployerObjectId="$DEPLOYER_OID" \
  --query properties.outputs \
  --output json)

WS_NAME=$(echo "$OUTPUTS" | jq -r '.workspaceName.value')
ST_NAME=$(echo "$OUTPUTS" | jq -r '.storageAccountName.value')
KV_NAME=$(echo "$OUTPUTS" | jq -r '.keyVaultName.value')
ACR_NAME=$(echo "$OUTPUTS" | jq -r '.acrName.value')
AI_NAME=$(echo "$OUTPUTS" | jq -r '.appInsightsName.value')

echo ""
echo "==== 作成されたリソース ===="
echo "  ML Workspace: $WS_NAME"
echo "  Storage:      $ST_NAME"
echo "  Key Vault:    $KV_NAME"
echo "  ACR:          $ACR_NAME"
echo "  App Insights: $AI_NAME"

echo ""
echo "==== ローカル環境変数 (以降のコマンドで使用) ===="
cat <<EOF

以下を bashrc または現在のシェルに追記してください:

export AZURE_LOCATION=$AZURE_LOCATION
export AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP
export AZURE_WORKSPACE_NAME=$WS_NAME
export AZURE_STORAGE_ACCOUNT=$ST_NAME

EOF

echo "==== 次のステップ ===="
echo "  1. scripts/download-data.sh で Task09_Spleen を取得"
echo "  2. scripts/upload-dataset.sh で Blob (datasets/Task09_Spleen/) に登録"
echo "  3. az ml data create -f aml/data-spleen.yml -g $AZURE_RESOURCE_GROUP -w $WS_NAME"
echo "  4. az ml environment create -f aml/environment.yml -g $AZURE_RESOURCE_GROUP -w $WS_NAME"
echo "  5. az ml compute create -f aml/compute-t4.yml -g $AZURE_RESOURCE_GROUP -w $WS_NAME"
echo "     (fine-tuning するなら aml/compute-a100.yml も)"
