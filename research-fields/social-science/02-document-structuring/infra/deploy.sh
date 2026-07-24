#!/usr/bin/env bash
# Document structuring infra deploy
# Usage: ./infra/deploy.sh <resource-group> [parameters-file]
set -euo pipefail

RG="${1:?Usage: ./infra/deploy.sh <resource-group> [parameters-file]}"
PARAMS="${2:-infra/parameters.json}"
LOC="${AZURE_LOCATION:-japaneast}"

if [[ ! -f "$PARAMS" ]]; then
  echo "ERROR: parameters file '$PARAMS' not found." >&2
  echo "       Copy 'infra/parameters.example.json' to 'infra/parameters.json' first." >&2
  exit 1
fi

# ── Preflight: provider registration ─────────────────────────────────────────
echo "==> Checking Microsoft.CognitiveServices provider registration..."
REG_STATE="$(az provider show -n Microsoft.CognitiveServices --query registrationState -o tsv 2>/dev/null || true)"
if [[ "$REG_STATE" != "Registered" ]]; then
  echo "    Registering Microsoft.CognitiveServices (this can take ~1 min)..."
  az provider register --namespace Microsoft.CognitiveServices --wait
fi
echo "    Microsoft.CognitiveServices: Registered"

# ── Preflight: quota check ────────────────────────────────────────────────────
echo "==> Cognitive Services quota in $LOC:"
az cognitiveservices usage list -l "$LOC" -o table 2>/dev/null || \
  echo "    (quota check not available for this subscription type)"

# ── Resource group: auto-create if missing ────────────────────────────────────
if ! az group show -n "$RG" >/dev/null 2>&1; then
  echo "==> Resource group '$RG' not found — creating in $LOC..."
  az group create -n "$RG" -l "$LOC"
fi

# ── Deployer identity ─────────────────────────────────────────────────────────
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

# ── Bicep deploy ──────────────────────────────────────────────────────────────
echo "==> Deploying Bicep (this takes 3-5 minutes)..."
OUTPUTS="$(az deployment group create \
  --resource-group "$RG" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters "@${PARAMS}" \
  --parameters deployerObjectId="${DEPLOYER_OID}" deployerPrincipalType="${DEPLOYER_PRINCIPAL_TYPE}" \
  --query "properties.outputs" -o json)"
echo "$OUTPUTS"

# ── Parse outputs ─────────────────────────────────────────────────────────────
DI_ENDPOINT="$(echo "$OUTPUTS"    | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['docIntelEndpoint']['value'])")"
DI_NAME="$(echo "$OUTPUTS"        | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['docIntelName']['value'])")"
AOAI_ENDPOINT="$(echo "$OUTPUTS"  | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['aoaiEndpoint']['value'])")"
AOAI_ACCOUNT="$(echo "$OUTPUTS"   | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['aoaiAccountName']['value'])")"
AOAI_DEPLOY="$(echo "$OUTPUTS"    | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['aoaiDeploymentName']['value'])")"
AOAI_MODEL="$(echo "$OUTPUTS"     | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['aoaiModelName']['value'])")"
AOAI_VERSION="$(echo "$OUTPUTS"   | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['aoaiModelVersion']['value'])")"
AOAI_LOC="$(echo "$OUTPUTS"       | python3 -c "import json,sys; o=json.load(sys.stdin); print(o['location']['value'])")"

# Deployment type: get from actual deployment SKU
AOAI_DTYPE="$(az cognitiveservices account deployment show \
  -g "$RG" -n "$AOAI_ACCOUNT" \
  --deployment-name "$AOAI_DEPLOY" \
  --query sku.name -o tsv 2>/dev/null || echo "Standard")"

# ── Preflight: verify the model+version is available ─────────────────────────
echo "==> Verifying model '$AOAI_MODEL' version '$AOAI_VERSION' is listed on the account..."
az cognitiveservices account list-models -g "$RG" -n "$AOAI_ACCOUNT" \
  --query "[?model.name=='$AOAI_MODEL' && model.version=='$AOAI_VERSION'].{name:model.name,version:model.version}" \
  -o table 2>/dev/null || echo "    (model listing not available; proceeding)"

# ── Write .env ────────────────────────────────────────────────────────────────
ENV_FILE=".env"
cat > "$ENV_FILE" <<EOF
DOC_RG=${RG}
DOC_INTEL_NAME=${DI_NAME}
AOAI_ACCOUNT_NAME=${AOAI_ACCOUNT}
AOAI_DEPLOYMENT_NAME=${AOAI_DEPLOY}
DOCUMENT_INTELLIGENCE_ENDPOINT=${DI_ENDPOINT}
AZURE_OPENAI_ENDPOINT=${AOAI_ENDPOINT}
AZURE_OPENAI_DEPLOYMENT=${AOAI_DEPLOY}
AZURE_OPENAI_LOCATION=${AOAI_LOC}
AZURE_OPENAI_DEPLOYMENT_TYPE=${AOAI_DTYPE}
AZURE_OPENAI_MODEL_NAME=${AOAI_MODEL}
AZURE_OPENAI_MODEL_VERSION=${AOAI_VERSION}
EOF
chmod 600 "$ENV_FILE"

echo
echo "==> Deployment complete. .env written (chmod 600)."
echo "    Next: docs/03-prepare-documents.md"
