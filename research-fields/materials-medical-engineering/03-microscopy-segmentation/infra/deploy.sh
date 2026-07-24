#!/usr/bin/env bash
# infra/deploy.sh — Deploy 03-microscopy-segmentation Azure infrastructure
#
# Usage:
#   export RG="rg-microseg-dev"
#   export LOC="japaneast"
#   export NAME_PREFIX="microseg"
#   [export DEPLOYER_OID_OVERRIDE="<oid>"]       # skip signed-in-user lookup
#   [export DEPLOYER_PRINCIPAL_TYPE="User"]       # default: User
#   [export WHAT_IF=1]                            # dry-run only
#   bash infra/deploy.sh
set -euo pipefail
set -o errtrace
trap 'echo "ERROR at line $LINENO (exit $?)" >&2' ERR

# ── Required env vars ────────────────────────────────────────────────────────
: "${RG:?Set RG to the target resource group name}"
: "${LOC:?Set LOC to the Azure region (e.g. japaneast)}"
: "${NAME_PREFIX:=microseg}"

WHAT_IF="${WHAT_IF:-0}"
DEPLOYMENT_NAME="microseg-$(date -u +%Y%m%dT%H%M%S)"

# ── Pre-flight: verify az login & subscription ───────────────────────────────
echo "==> Verifying Azure CLI login ..."
az account show --query '{name:name, id:id}' -o table

echo "==> Confirming subscription (press Ctrl-C within 5 s to abort) ..."
sleep 5

# ── Register required Resource Providers ────────────────────────────────────
PROVIDERS=(
  Microsoft.MachineLearningServices
  Microsoft.Storage
  Microsoft.KeyVault
  Microsoft.ContainerRegistry
  Microsoft.OperationalInsights
  Microsoft.Insights
)
for rp in "${PROVIDERS[@]}"; do
  state=$(az provider show -n "$rp" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "$state" != "Registered" ]]; then
    echo "==> Registering $rp ..."
    az provider register --namespace "$rp"
  fi
done
echo "==> Waiting for all providers to be Registered ..."
for rp in "${PROVIDERS[@]}"; do
  for i in $(seq 1 30); do
    state=$(az provider show -n "$rp" --query registrationState -o tsv)
    [[ "$state" == "Registered" ]] && break
    echo "    $rp: $state (attempt $i/30) — waiting 10 s ..."
    sleep 10
  done
  state=$(az provider show -n "$rp" --query registrationState -o tsv)
  if [[ "$state" != "Registered" ]]; then
    echo "ERROR: $rp did not reach Registered in time (state: $state)" >&2
    exit 1
  fi
  echo "    $rp: Registered ✓"
done

# ── Ensure resource group exists (do NOT bail on missing RG) ─────────────────
if ! az group show -n "$RG" --query name -o tsv &>/dev/null; then
  echo "==> Creating resource group $RG in $LOC ..."
  az group create -n "$RG" -l "$LOC" -o table
else
  echo "==> Resource group $RG already exists."
fi

# ── Resolve deployer Object ID ────────────────────────────────────────────────
if [[ -n "${DEPLOYER_OID_OVERRIDE:-}" ]]; then
  DEPLOYER_OID="$DEPLOYER_OID_OVERRIDE"
  DEPLOYER_PRINCIPAL_TYPE="${DEPLOYER_PRINCIPAL_TYPE:-User}"
  echo "==> Using DEPLOYER_OID_OVERRIDE: $DEPLOYER_OID ($DEPLOYER_PRINCIPAL_TYPE)"
else
  echo "==> Resolving signed-in user Object ID ..."
  DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv)
  DEPLOYER_PRINCIPAL_TYPE="${DEPLOYER_PRINCIPAL_TYPE:-User}"
  echo "    OID: $DEPLOYER_OID ($DEPLOYER_PRINCIPAL_TYPE)"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Deploy Bicep ──────────────────────────────────────────────────────────────
DEPLOY_ARGS=(
  --resource-group "$RG"
  --name "$DEPLOYMENT_NAME"
  --template-file "$SCRIPT_DIR/main.bicep"
  --parameters
    namePrefix="$NAME_PREFIX"
    location="$LOC"
    deployerObjectId="$DEPLOYER_OID"
    deployerPrincipalType="$DEPLOYER_PRINCIPAL_TYPE"
)

if [[ "${WHAT_IF:-0}" == "1" ]]; then
  echo "==> WHAT-IF deployment (dry run) ..."
  az deployment group what-if "${DEPLOY_ARGS[@]}" -o table
  echo "==> What-if complete. Re-run without WHAT_IF=1 to deploy."
  exit 0
fi

echo "==> Deploying Bicep template (deployment: $DEPLOYMENT_NAME) ..."
az deployment group create "${DEPLOY_ARGS[@]}" -o table

# ── Retrieve outputs ──────────────────────────────────────────────────────────
echo "==> Retrieving deployment outputs ..."
OUTPUTS=$(az deployment group show \
  -g "$RG" -n "$DEPLOYMENT_NAME" \
  --query properties.outputs -o json)

WS_NAME=$(echo "$OUTPUTS"       | python3 -c "import sys,json; print(json.load(sys.stdin)['workspaceName']['value'])")
ST_NAME=$(echo "$OUTPUTS"       | python3 -c "import sys,json; print(json.load(sys.stdin)['storageName']['value'])")
KV_NAME=$(echo "$OUTPUTS"       | python3 -c "import sys,json; print(json.load(sys.stdin)['keyVaultName']['value'])")
ACR_SERVER=$(echo "$OUTPUTS"    | python3 -c "import sys,json; print(json.load(sys.stdin)['acrLoginServer']['value'])")
LA_ID=$(echo "$OUTPUTS"         | python3 -c "import sys,json; print(json.load(sys.stdin)['logAnalyticsWorkspaceId']['value'])")

# ── AML quota check ───────────────────────────────────────────────────────────
echo "==> AML compute quota in $LOC ..."
az ml compute list-usage -g "$RG" -w "$WS_NAME" -l "$LOC" -o table || \
  echo "    (quota check unavailable — ML extension may need: az extension add -n ml)"

# ── Write .env ────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"

SUB_ID=$(az account show --query id -o tsv)

cat > "$ENV_FILE" <<ENV
AZURE_SUBSCRIPTION_ID=$SUB_ID
AZURE_RESOURCE_GROUP=$RG
AZURE_LOCATION=$LOC
AML_WORKSPACE_NAME=$WS_NAME
AML_STORAGE_NAME=$ST_NAME
AML_KEY_VAULT_NAME=$KV_NAME
AML_ACR_LOGIN_SERVER=$ACR_SERVER
AML_LOG_ANALYTICS_ID=$LA_ID
ENV

chmod 600 "$ENV_FILE"
echo "==> Wrote $ENV_FILE (chmod 600)"
echo
echo "==> Next steps:"
echo "    source .env"
echo "    az ml compute create --type amlcompute --name gpu-cluster-nc4t4 \\"
echo "      --size Standard_NC4as_T4_v3 --min-instances 0 --max-instances 1 \\"
echo "      --tier low_priority --idle-time-before-scale-down 300 \\"
echo "      -g \"\$AZURE_RESOURCE_GROUP\" -w \"\$AML_WORKSPACE_NAME\""
