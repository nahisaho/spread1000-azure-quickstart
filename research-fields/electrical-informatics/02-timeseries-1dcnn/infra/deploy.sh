#!/usr/bin/env bash
# chmod +x infra/deploy.sh
set -euo pipefail
set -o errtrace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCENARIO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
DEPLOY_NAME="spread-timeseries-1dcnn-deploy"
COMPUTE_NAME="gpu-t4"
WHAT_IF=false

if [ "${1:-}" = "--what-if" ]; then
  WHAT_IF=true
  shift
fi

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

RG="${RG:-${AZURE_RESOURCE_GROUP:-}}"
WS="${WS:-${AZUREML_WORKSPACE_NAME:-}}"
LOC="${LOC:-${AZURE_LOCATION:-}}"
NAME_PREFIX="${NAME_PREFIX:-spread-ts}"
DEPLOYER_OBJECT_ID="${DEPLOYER_OBJECT_ID:-}"
DEPLOYER_PRINCIPAL_TYPE="${DEPLOYER_PRINCIPAL_TYPE:-User}"
KV_SOFT_DELETE_DAYS="${KV_SOFT_DELETE_DAYS:-7}"
ENABLE_PUBLIC_NETWORK_ACCESS="${ENABLE_PUBLIC_NETWORK_ACCESS:-true}"

if [ -z "$RG" ] || [ -z "$LOC" ] || [ -z "$NAME_PREFIX" ] || [ -z "$DEPLOYER_OBJECT_ID" ]; then
  echo "[deploy] ERROR: RG, LOC, NAME_PREFIX, and DEPLOYER_OBJECT_ID must be set via infra/.env or environment variables." >&2
  exit 1
fi

az account show >/dev/null
SUBSCRIPTION_NAME="$(az account show --query name -o tsv)"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
echo "[deploy] subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

az extension add -n ml --allow-preview false 2>/dev/null || az extension update -n ml

for provider in \
  Microsoft.MachineLearningServices \
  Microsoft.Storage \
  Microsoft.KeyVault \
  Microsoft.ContainerRegistry \
  Microsoft.OperationalInsights \
  Microsoft.Insights
do
  echo "[deploy] registering provider: $provider"
  az provider register --namespace "$provider" --wait >/dev/null
done

az group create -n "$RG" -l "$LOC" --tags scenario=spread-timeseries-1dcnn >/dev/null

echo "[deploy] AML quota snapshot (may fail before workspace exists)"
az ml compute list-usage -g "$RG" -w "${WS:-pending-workspace}" -l "$LOC" -o table || true

COMMON_ARGS=(
  --resource-group "$RG"
  --name "$DEPLOY_NAME"
  --template-file "$SCRIPT_DIR/main.bicep"
  --parameters
  namePrefix="$NAME_PREFIX"
  location="$LOC"
  kvSoftDeleteDays="$KV_SOFT_DELETE_DAYS"
  deployerObjectId="$DEPLOYER_OBJECT_ID"
  deployerPrincipalType="$DEPLOYER_PRINCIPAL_TYPE"
  enablePublicNetworkAccess="$ENABLE_PUBLIC_NETWORK_ACCESS"
)

if [ "$WHAT_IF" = true ]; then
  echo "[deploy] running what-if"
  az deployment group what-if "${COMMON_ARGS[@]}"
  echo "[deploy] what-if complete"
  exit 0
fi

echo "[deploy] creating resource group deployment: $DEPLOY_NAME"
az deployment group create "${COMMON_ARGS[@]}" >/dev/null

OUTPUTS_JSON="$(az deployment group show -g "$RG" -n "$DEPLOY_NAME" --query properties.outputs -o json)"
export OUTPUTS_JSON ENV_FILE RG LOC NAME_PREFIX DEPLOYER_OBJECT_ID DEPLOYER_PRINCIPAL_TYPE KV_SOFT_DELETE_DAYS DEPLOY_NAME COMPUTE_NAME ENABLE_PUBLIC_NETWORK_ACCESS
python - <<'PY'
import json
import os
from pathlib import Path

outputs = json.loads(os.environ["OUTPUTS_JSON"])
values = {key: value.get("value") for key, value in outputs.items()}
env_path = Path(os.environ["ENV_FILE"])
lines = [
    f"RG={os.environ['RG']}",
    f"LOC={os.environ['LOC']}",
    f"NAME_PREFIX={os.environ['NAME_PREFIX']}",
    f"DEPLOYER_OBJECT_ID={os.environ['DEPLOYER_OBJECT_ID']}",
    f"DEPLOYER_PRINCIPAL_TYPE={os.environ['DEPLOYER_PRINCIPAL_TYPE']}",
    f"KV_SOFT_DELETE_DAYS={os.environ['KV_SOFT_DELETE_DAYS']}",
    f"DEPLOY_NAME={os.environ['DEPLOY_NAME']}",
    f"COMPUTE_NAME={os.environ['COMPUTE_NAME']}",
    f"ENABLE_PUBLIC_NETWORK_ACCESS={os.environ['ENABLE_PUBLIC_NETWORK_ACCESS']}",
]
for key, value in sorted(values.items()):
    if value is None:
        continue
    escaped = str(value).replace('"', '\\"')
    lines.append(f'{key.upper()}="{escaped}"')

if "workspaceName" in values:
    lines.append(f'WS="{values["workspaceName"]}"')
if "workspaceLocation" in values:
    lines.append(f'WORKSPACE_LOCATION="{values["workspaceLocation"]}"')
if "workspaceIdentityPrincipalId" in values and values["workspaceIdentityPrincipalId"] is not None:
    lines.append(f'WORKSPACE_PRINCIPAL_ID="{values["workspaceIdentityPrincipalId"]}"')
if "keyVaultName" in values:
    lines.append(f'KV_NAME="{values["keyVaultName"]}"')
if "storageAccountName" in values:
    lines.append(f'STORAGE_ACCOUNT_NAME="{values["storageAccountName"]}"')
if "containerRegistryName" in values:
    lines.append(f'ACR_NAME="{values["containerRegistryName"]}"')

env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
chmod 600 "$ENV_FILE"

echo "[deploy] wrote $ENV_FILE"
echo "[deploy] workspace: $(az deployment group show -g "$RG" -n "$DEPLOY_NAME" --query properties.outputs.workspaceName.value -o tsv)"
echo "[deploy] deployment complete"
