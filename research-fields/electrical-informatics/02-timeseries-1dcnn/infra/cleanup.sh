#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "[cleanup] ERROR: $ENV_FILE not found. Run ./infra/deploy.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

COMPUTE_NAME="${COMPUTE_NAME:-gpu-t4}"
WS="${WS:-${WORKSPACENAME:-}}"
KV_NAME="${KV_NAME:-${KEYVAULTNAME:-}}"

az ml compute delete --name "$COMPUTE_NAME" -g "$RG" -w "$WS" --yes --no-wait 2>/dev/null || true
az deployment group delete -g "$RG" -n "spread-timeseries-1dcnn-deploy" --no-wait 2>/dev/null || true
az group delete -n "$RG" --yes --no-wait && az group wait --name "$RG" --deleted

KV_EXISTS=$(az keyvault list-deleted --query "[?name=='$KV_NAME'].name | [0]" -o tsv 2>/dev/null || echo "")
if [ -n "$KV_EXISTS" ]; then
  PURGE_PROTECTED=$(az keyvault show-deleted --name "$KV_NAME" --location "$LOC" --query properties.purgeProtectionEnabled -o tsv 2>/dev/null || echo "false")
  if [ "$PURGE_PROTECTED" = "true" ]; then
    echo "[cleanup] Key Vault $KV_NAME has purge protection enabled. Immediate purge is blocked until retention period ($KV_SOFT_DELETE_DAYS days) expires."
  else
    az keyvault purge --name "$KV_NAME" --location "$LOC"
  fi
fi

echo "[cleanup] cleanup complete"
