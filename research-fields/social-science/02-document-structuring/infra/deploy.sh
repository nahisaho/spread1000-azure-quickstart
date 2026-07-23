#!/usr/bin/env bash
# Document structuring infra deploy
# Usage: ./infra/deploy.sh <resource-group> [parameters-file]
set -euo pipefail

RG="${1:?Usage: ./infra/deploy.sh <resource-group> [parameters-file]}"
PARAMS="${2:-infra/parameters.json}"

if [[ ! -f "$PARAMS" ]]; then
  echo "ERROR: parameters file '$PARAMS' not found." >&2
  echo "       Copy 'infra/parameters.example.json' to 'infra/parameters.json' first." >&2
  exit 1
fi

if ! az group show -n "$RG" >/dev/null 2>&1; then
  echo "ERROR: resource group '$RG' does not exist. Create it first:" >&2
  echo "       az group create -n $RG -l japaneast" >&2
  exit 1
fi

DEPLOYER_OID="${DEPLOYER_OID_OVERRIDE:-}"
DEPLOYER_PRINCIPAL_TYPE="${DEPLOYER_PRINCIPAL_TYPE:-User}"
if [[ -z "$DEPLOYER_OID" ]]; then
  DEPLOYER_OID="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
fi
if [[ -z "$DEPLOYER_OID" ]]; then
  echo "ERROR: could not resolve deployer object ID." >&2
  echo "       Interactive users: run 'az login' first." >&2
  echo "       Service principals / managed identities must set:" >&2
  echo "         DEPLOYER_OID_OVERRIDE=<oid> DEPLOYER_PRINCIPAL_TYPE=ServicePrincipal ./infra/deploy.sh ..." >&2
  exit 1
fi

echo "==> Deploying Bicep (this takes 3-5 minutes)..."
az deployment group create \
  --resource-group "$RG" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters "@${PARAMS}" \
  --parameters deployerObjectId="${DEPLOYER_OID}" deployerPrincipalType="${DEPLOYER_PRINCIPAL_TYPE}" \
  --query "properties.outputs" -o json

echo
echo "==> Deployment complete."
echo "    Next: docs/03-prepare-documents.md"
