#!/usr/bin/env bash
# infra/deploy.sh — E-3 Image-Restoration U-Net Azure infrastructure deployment
# Usage:
#   RG=my-rg LOC=japaneast PREFIX=e3unet SUB_ID=<uuid> bash infra/deploy.sh
# Dry-run (what-if only, no deployment):
#   DRY_RUN=1 RG=... bash infra/deploy.sh
# Override deployer OID (e.g. for service principal):
#   DEPLOYER_OID_OVERRIDE=<oid> bash infra/deploy.sh
set -euo pipefail
set -o errtrace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

# ── Required env vars ─────────────────────────────────────────────────────────
RG="${RG:?Set RG to the target resource group name}"
LOC="${LOC:?Set LOC to the Azure region, e.g. japaneast}"
PREFIX="${PREFIX:?Set PREFIX to the name prefix, e.g. e3unet}"
SUB_ID="${SUB_ID:?Set SUB_ID to your Azure subscription ID}"
DRY_RUN="${DRY_RUN:-0}"

# ── Verify az login ───────────────────────────────────────────────────────────
echo "==> Verifying az login..."
SIGNED_IN_USER=$(az account show --query user.name -o tsv 2>/dev/null || true)
if [[ -z "$SIGNED_IN_USER" ]]; then
  echo "ERROR: Not logged in. Run: az login" >&2
  exit 1
fi
echo "    Signed in as: ${SIGNED_IN_USER}"

echo "==> Setting active subscription to ${SUB_ID}..."
az account set --subscription "${SUB_ID}"
CURRENT_SUB=$(az account show --query id -o tsv)
if [[ "${CURRENT_SUB}" != "${SUB_ID}" ]]; then
  echo "ERROR: Failed to switch to subscription ${SUB_ID}" >&2
  exit 1
fi
echo "    Active subscription: ${CURRENT_SUB}"

# ── Pin ML CLI extension ──────────────────────────────────────────────────────
echo "==> Pinning Azure ML CLI extension to version 2.29.0..."
if az extension show -n ml &>/dev/null; then
  CURRENT_ML_VER=$(az extension show -n ml --query version -o tsv)
  if [[ "${CURRENT_ML_VER}" != "2.29.0" ]]; then
    az extension update -n ml --version 2.29.0 2>/dev/null \
      || az extension add -n ml --version 2.29.0
  else
    echo "    ml extension already at 2.29.0"
  fi
else
  az extension add -n ml --version 2.29.0
fi

# ── Register resource providers ───────────────────────────────────────────────
PROVIDERS=(
  Microsoft.MachineLearningServices
  Microsoft.Storage
  Microsoft.KeyVault
  Microsoft.ContainerRegistry
  Microsoft.OperationalInsights
  Microsoft.Insights
)
echo "==> Registering resource providers..."
for PROVIDER in "${PROVIDERS[@]}"; do
  STATE=$(az provider show -n "${PROVIDER}" --query registrationState -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "${STATE}" != "Registered" ]]; then
    echo "    Registering ${PROVIDER}..."
    az provider register -n "${PROVIDER}"
  fi
done

echo "    Waiting for all providers to reach Registered..."
for PROVIDER in "${PROVIDERS[@]}"; do
  for i in $(seq 1 30); do
    STATE=$(az provider show -n "${PROVIDER}" --query registrationState -o tsv)
    if [[ "${STATE}" == "Registered" ]]; then
      echo "    ${PROVIDER}: Registered"
      break
    fi
    echo "    ${PROVIDER}: ${STATE} (attempt ${i}/30, retrying in 10s...)"
    sleep 10
  done
  if [[ "${STATE}" != "Registered" ]]; then
    echo "ERROR: ${PROVIDER} did not reach Registered state" >&2
    exit 1
  fi
done

# ── Create resource group if missing ─────────────────────────────────────────
echo "==> Ensuring resource group ${RG} exists in ${LOC}..."
if ! az group show -n "${RG}" &>/dev/null; then
  az group create -n "${RG}" -l "${LOC}"
  echo "    Resource group created."
else
  echo "    Resource group already exists."
fi

# ── Resolve deployer object ID ────────────────────────────────────────────────
echo "==> Resolving deployer object ID..."
if [[ -n "${DEPLOYER_OID_OVERRIDE:-}" ]]; then
  DEPLOYER_OID="${DEPLOYER_OID_OVERRIDE}"
  echo "    Using DEPLOYER_OID_OVERRIDE: ${DEPLOYER_OID}"
else
  DEPLOYER_OID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null \
    || az account show --query user.name -o tsv | xargs -I{} az ad user show --id {} --query id -o tsv 2>/dev/null \
    || true)
  if [[ -z "${DEPLOYER_OID}" ]]; then
    echo "ERROR: Could not resolve deployer OID. Set DEPLOYER_OID_OVERRIDE." >&2
    exit 1
  fi
  echo "    Deployer OID: ${DEPLOYER_OID}"
fi

# ── What-if / deploy ──────────────────────────────────────────────────────────
BICEP_FILE="${SCRIPT_DIR}/main.bicep"
PARAMS=(
  "namePrefix=${PREFIX}"
  "location=${LOC}"
  "deployerObjectId=${DEPLOYER_OID}"
  "deployerPrincipalType=User"
)

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "==> DRY_RUN=1: running what-if only (no deployment)..."
  az deployment group what-if \
    --resource-group "${RG}" \
    --template-file "${BICEP_FILE}" \
    $(printf -- "--parameters %s " "${PARAMS[@]}")
  echo "==> What-if complete. Set DRY_RUN=0 to deploy."
  exit 0
fi

echo "==> Deploying Bicep template..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "${RG}" \
  --template-file "${BICEP_FILE}" \
  $(printf -- "--parameters %s " "${PARAMS[@]}") \
  --query properties.outputs \
  -o json)

echo "==> Deployment outputs:"
echo "${DEPLOY_OUTPUT}" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
for k, v in outputs.items():
    print(f'    {k} = {v[\"value\"]}')
"

# ── Extract outputs ───────────────────────────────────────────────────────────
WS=$(echo "${DEPLOY_OUTPUT}" | python3 -c "import json,sys; print(json.load(sys.stdin)['workspaceName']['value'])")
ST=$(echo "${DEPLOY_OUTPUT}" | python3 -c "import json,sys; print(json.load(sys.stdin)['storageAccountName']['value'])")
KV=$(echo "${DEPLOY_OUTPUT}" | python3 -c "import json,sys; print(json.load(sys.stdin)['keyVaultName']['value'])")
ACR=$(echo "${DEPLOY_OUTPUT}" | python3 -c "import json,sys; print(json.load(sys.stdin)['acrLoginServer']['value'])")

# ── Show AML quota and compute sizes ─────────────────────────────────────────
echo ""
echo "==> AML compute quota (az ml compute list-usage):"
az ml compute list-usage -g "${RG}" -w "${WS}" -l "${LOC}" -o table 2>/dev/null || \
  echo "    (quota check skipped — workspace may need a moment to provision)"

echo ""
echo "==> Available GPU compute sizes (first 20 rows):"
az ml compute list-sizes -l "${LOC}" -o table 2>/dev/null | head -20 || \
  echo "    (size listing skipped)"

# ── Write .env (chmod 600) ────────────────────────────────────────────────────
echo ""
echo "==> Writing ${ENV_FILE}..."
cat > "${ENV_FILE}" <<EOF
# E-3 Image-Restoration U-Net — generated by infra/deploy.sh
# $(date -u +"%Y-%m-%dT%H:%M:%SZ")
AML_SUBSCRIPTION_ID=${SUB_ID}
AML_RESOURCE_GROUP=${RG}
AML_WORKSPACE_NAME=${WS}
AML_STORAGE_ACCOUNT=${ST}
AML_KEY_VAULT_NAME=${KV}
AML_ACR_LOGIN_SERVER=${ACR}
AML_LOCATION=${LOC}
EOF
chmod 600 "${ENV_FILE}"
echo "    .env written (chmod 600)."

echo ""
echo "==> Deployment complete."
echo "    Source the .env with:  source .env"
echo "    Submit a training job: az ml job create -f azureml/train_job.yml -g \$AML_RESOURCE_GROUP -w \$AML_WORKSPACE_NAME"
