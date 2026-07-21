#!/usr/bin/env bash
# Bicep deploy script for chemistry molecular generation quickstart
set -Eeuo pipefail

# Required env vars
: "${AZURE_SUBSCRIPTION_ID:?export AZURE_SUBSCRIPTION_ID first}"
: "${AZURE_LOCATION:?export AZURE_LOCATION first (e.g. japaneast)}"
: "${AZURE_RESOURCE_GROUP:?export AZURE_RESOURCE_GROUP first (e.g. rg-spread-chem-molgen)}"
: "${AZURE_WORKSPACE_NAME:?export AZURE_WORKSPACE_NAME first (e.g. mlw-chem-molgen)}"

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

echo "==> Registering resource providers (idempotent)"
for ns in Microsoft.MachineLearningServices Microsoft.Storage Microsoft.KeyVault \
          Microsoft.ContainerRegistry Microsoft.Insights Microsoft.OperationalInsights; do
  az provider register --namespace "$ns" --wait
done

echo "==> Creating resource group: $AZURE_RESOURCE_GROUP"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" -o none

DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
echo "==> Deployer objectId: $DEPLOYER_OID"

echo "==> Running Bicep deployment (5-10 min)"
DEPLOYMENT_NAME="chem-molgen-$(date +%Y%m%d-%H%M%S)"
az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters \
      workspaceName="$AZURE_WORKSPACE_NAME" \
      deployerObjectId="$DEPLOYER_OID" \
  -o none

WS_NAME=$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" \
  --query 'properties.outputs.workspaceName.value' -o tsv)
STORAGE=$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" \
  --query 'properties.outputs.storageAccountName.value' -o tsv)

cat <<EOF

=== Deployment successful ===
Resource Group: $AZURE_RESOURCE_GROUP
Workspace:      $WS_NAME
Storage:        $STORAGE

Next steps (copy-paste):
  export AZURE_WORKSPACE_NAME=$WS_NAME
  export AZURE_STORAGE_ACCOUNT=$STORAGE

Then follow docs/03-download-and-upload.md
EOF
