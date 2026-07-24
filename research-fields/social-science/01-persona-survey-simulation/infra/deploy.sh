#!/usr/bin/env bash
# Persona survey simulation infra deploy
# Usage: ./infra/deploy.sh <resource-group> [parameters-file]
set -euo pipefail

RG="${1:?Usage: ./infra/deploy.sh <resource-group> [parameters-file]}"
PARAMS="${2:-infra/parameters.json}"

if [[ ! -f "$PARAMS" ]]; then
  echo "ERROR: parameters file '$PARAMS' not found." >&2
  echo "       Copy 'infra/parameters.example.json' to 'infra/parameters.json' first." >&2
  exit 1
fi

# Model lifecycle preflight: reject deprecated/near-retirement models before
# calling ARM. This catches the common case where a copied parameters file
# still points at a retired version (e.g., gpt-4.1-mini 2025-04-14).
MODEL_NAME="$(python3 -c "import json,sys;print(json.load(open('$PARAMS'))['parameters']['modelName']['value'])")"
MODEL_VERSION="$(python3 -c "import json,sys;print(json.load(open('$PARAMS'))['parameters'].get('modelVersion',{}).get('value',''))")"
LOCATION="$(python3 -c "import json,sys;print(json.load(open('$PARAMS'))['parameters']['location']['value'])")"
if [[ -z "$MODEL_VERSION" || "$MODEL_VERSION" == "REPLACE_ME" ]]; then
  echo "ERROR: modelVersion is unset in $PARAMS. Discover a currently GA version with:" >&2
  echo "  az cognitiveservices model list -l $LOCATION \\" >&2
  echo "    --query \"[?model.name=='$MODEL_NAME' && model.lifecycleStatus=='generallyAvailable' && (model.deprecation.inference==null || model.deprecation.inference > '2026-12-31')].{version:model.version, deprecation:model.deprecation.inference}\" \\" >&2
  echo "    -o table" >&2
  echo "Set the chosen value in $PARAMS." >&2
  exit 1
fi
echo "==> Preflight: verifying $MODEL_NAME $MODEL_VERSION lifecycle in $LOCATION..."
MODEL_META="$(az cognitiveservices model list -l "$LOCATION" \
  --query "[?model.name=='$MODEL_NAME' && model.version=='$MODEL_VERSION']|[0].{status:model.lifecycleStatus, retire:model.deprecation.inference}" \
  -o json 2>/dev/null || echo '{}')"
LIFECYCLE="$(echo "$MODEL_META" | python3 -c "import json,sys;d=json.load(sys.stdin) or {};print(d.get('status') or '')")"
RETIRE="$(echo "$MODEL_META" | python3 -c "import json,sys;d=json.load(sys.stdin) or {};print(d.get('retire') or '')")"
if [[ "$LIFECYCLE" != "generallyAvailable" ]]; then
  echo "ERROR: $MODEL_NAME $MODEL_VERSION is '$LIFECYCLE' (expected generallyAvailable) in $LOCATION." >&2
  echo "  Deprecated versions cannot be newly deployed. Pick a currently GA version and update $PARAMS." >&2
  exit 2
fi
if [[ -n "$RETIRE" && "$RETIRE" < "2026-12-31" ]]; then
  echo "ERROR: $MODEL_NAME $MODEL_VERSION retires $RETIRE (< 2026-12-31 threshold)." >&2
  echo "  Pick a version whose retirement is further out and update $PARAMS." >&2
  exit 3
fi
echo "  [ok] $MODEL_NAME $MODEL_VERSION is GA${RETIRE:+ (retires $RETIRE)}."

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
echo "    Next: docs/03-prepare-personas.md"
