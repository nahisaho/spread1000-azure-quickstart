#!/usr/bin/env bash
# Deploy EHR-NLP RAG quickstart infrastructure.
#
# Usage:
#   cd research-fields/clinical-science/02-ehr-nlp-rag
#   # 1. Copy env template and edit
#   cp inputs/.env.example .env  &&  $EDITOR .env
#   # 2. Load env
#   set -a && source .env && set +a
#   # 3. Deploy
#   bash infra/deploy.sh

set -euo pipefail

: "${LOCATION:?Set LOCATION in .env (e.g. japaneast)}"
: "${RG:?Set RG in .env (e.g. spread1000-ehr-nlp)}"
: "${UNIQUE_SUFFIX:?Set UNIQUE_SUFFIX in .env (3-8 hex chars). Generate with: openssl rand -hex 3}"

# Reject the placeholder that ships with inputs/.env.example
if [[ "$UNIQUE_SUFFIX" == "REPLACE_ME_6HEX" ]]; then
  echo "ERROR: UNIQUE_SUFFIX is still the placeholder REPLACE_ME_6HEX." >&2
  echo "       Set a real value in .env, e.g. UNIQUE_SUFFIX=\$(openssl rand -hex 3)" >&2
  exit 1
fi
if ! [[ "$UNIQUE_SUFFIX" =~ ^[a-z0-9]{3,8}$ ]]; then
  echo "ERROR: UNIQUE_SUFFIX must be 3-8 lowercase hex chars, got: $UNIQUE_SUFFIX" >&2
  exit 1
fi

: "${PROJECT_TAG:=spread1000}"
: "${SCENARIO_TAG:=ehr-nlp}"
: "${PI_TAG:=unknown}"

# Helper: assign role but only tolerate "already exists" (RoleAssignmentExists / already assigned).
assign_role() {
  local principal_id="$1" principal_type="$2" role_name="$3" scope="$4"
  local err
  if ! err=$(az role assignment create \
      --assignee-object-id "$principal_id" \
      --assignee-principal-type "$principal_type" \
      --role "$role_name" \
      --scope "$scope" \
      -o none 2>&1); then
    if echo "$err" | grep -qiE 'RoleAssignmentExists|already exists'; then
      echo "  [ok] '$role_name' already assigned to $principal_id"
    else
      echo "ERROR assigning '$role_name' to $principal_id at scope $scope" >&2
      echo "$err" >&2
      exit 1
    fi
  else
    echo "  [ok] assigned '$role_name' to $principal_id"
  fi
}

# --- Preflight ---
echo "==> Checking Azure CLI login..."
az account show --query "{name:name, id:id}" -o table

echo "==> Confirming resource providers are registered..."
for RP in Microsoft.CognitiveServices Microsoft.Search Microsoft.Storage \
          Microsoft.KeyVault Microsoft.OperationalInsights Microsoft.Insights; do
  STATE=$(az provider show --namespace "$RP" --query registrationState -o tsv)
  if [[ "$STATE" != "Registered" ]]; then
    echo "  Registering $RP (currently $STATE)..."
    az provider register --namespace "$RP" --wait
  else
    echo "  $RP already Registered"
  fi
done

# --- Resource group ---
echo "==> Creating resource group $RG in $LOCATION..."
az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --tags project="$PROJECT_TAG" scenario="$SCENARIO_TAG" pi="$PI_TAG" \
  -o table

# --- Deploy ---
echo "==> Deploying Bicep template (this takes ~10 minutes)..."
DEPLOYMENT_NAME="ehr-nlp-$(date -u +%Y%m%d-%H%M%S)"

# Build parameters. Model overrides are optional; if unset, Bicep defaults apply.
BICEP_PARAMS=(
  uniqueSuffix="$UNIQUE_SUFFIX"
  projectTag="$PROJECT_TAG"
  scenarioTag="$SCENARIO_TAG"
  piTag="$PI_TAG"
)
[[ -n "${CHAT_MODEL_NAME:-}" ]] && BICEP_PARAMS+=(chatModelName="$CHAT_MODEL_NAME")
[[ -n "${CHAT_MODEL_VERSION:-}" ]] && BICEP_PARAMS+=(chatModelVersion="$CHAT_MODEL_VERSION")
[[ -n "${CHAT_DEPLOYMENT_NAME:-}" ]] && BICEP_PARAMS+=(chatDeploymentName="$CHAT_DEPLOYMENT_NAME")
[[ -n "${EMBEDDING_MODEL_NAME:-}" ]] && BICEP_PARAMS+=(embeddingModelName="$EMBEDDING_MODEL_NAME")
[[ -n "${EMBEDDING_MODEL_VERSION:-}" ]] && BICEP_PARAMS+=(embeddingModelVersion="$EMBEDDING_MODEL_VERSION")
[[ -n "${EMBEDDING_DEPLOYMENT_NAME:-}" ]] && BICEP_PARAMS+=(embeddingDeploymentName="$EMBEDDING_DEPLOYMENT_NAME")

az deployment group create \
  --resource-group "$RG" \
  --name "$DEPLOYMENT_NAME" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters "${BICEP_PARAMS[@]}" \
  -o table

# --- Post-deploy: grant caller RBAC on Search + Storage + OpenAI ---
CALLER_OID=$(az ad signed-in-user show --query id -o tsv)
SUB_ID=$(az account show --query id -o tsv)
SEARCH_NAME=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" --query properties.outputs.searchName.value -o tsv)
OPENAI_NAME=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" --query properties.outputs.openAiName.value -o tsv)
STORAGE_NAME=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" --query properties.outputs.storageAccountName.value -o tsv)
SEARCH_PRINCIPAL_ID=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" --query properties.outputs.searchPrincipalId.value -o tsv)

echo "==> Granting caller ($CALLER_OID) least-privilege data-plane roles..."

# Search: Search Index Data Contributor + Search Service Contributor
assign_role "$CALLER_OID" User "Search Index Data Contributor" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Search/searchServices/$SEARCH_NAME"

assign_role "$CALLER_OID" User "Search Service Contributor" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Search/searchServices/$SEARCH_NAME"

# OpenAI: Cognitive Services OpenAI User
assign_role "$CALLER_OID" User "Cognitive Services OpenAI User" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$OPENAI_NAME"

# Storage: Blob Data Contributor
assign_role "$CALLER_OID" User "Storage Blob Data Contributor" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME"

# Grant AI Search's managed identity access to OpenAI and Storage (for skillsets/indexers)
echo "==> Granting AI Search's managed identity access to OpenAI and Storage..."
assign_role "$SEARCH_PRINCIPAL_ID" ServicePrincipal "Cognitive Services OpenAI User" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$OPENAI_NAME"

assign_role "$SEARCH_PRINCIPAL_ID" ServicePrincipal "Storage Blob Data Reader" \
  "/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME"

echo ""
echo "==============================================================="
echo "✅ Deployment complete."
echo "==============================================================="
az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" --query properties.outputs -o json

# Persist the deployment name so downstream docs can retrieve outputs deterministically.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "$DEPLOYMENT_NAME" > "$SCRIPT_DIR/../.last-deployment-name"
echo ""
echo "Deployment name recorded to .last-deployment-name: $DEPLOYMENT_NAME"
echo "Next: docs/03-index-documents.md"
