#!/usr/bin/env bash
# Deploy AOAI account + 2 deployments + RBAC, then write .env for src/ scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP env var, e.g. export AZURE_RESOURCE_GROUP=rg-spread-social-03}"
: "${AZURE_LOCATION:=japaneast}"

# Ensure RG exists
az group show -n "$AZURE_RESOURCE_GROUP" >/dev/null 2>&1 || \
  az group create -n "$AZURE_RESOURCE_GROUP" -l "$AZURE_LOCATION" -o none

PRINCIPAL_ID="$(az ad signed-in-user show --query id -o tsv)"

PARAMS=(location="$AZURE_LOCATION" principalId="$PRINCIPAL_ID" principalType=User)
if [ -f parameters.json ]; then
  PARAM_FILE=(--parameters @parameters.json)
else
  PARAM_FILE=()
fi

echo "Deploying Bicep to resource group $AZURE_RESOURCE_GROUP ..."
DEPLOY_OUT="$(az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file main.bicep \
  "${PARAM_FILE[@]}" \
  --parameters "${PARAMS[@]}" \
  --query properties.outputs \
  -o json)"

AOAI_ENDPOINT="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["aoaiEndpoint"]["value"])')"
AOAI_NAME="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["aoaiName"]["value"])')"
EMBED_DEPLOYMENT="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["embedDeployment"]["value"])')"
EMBED_DEPLOYMENT_TYPE="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["embedDeploymentType"]["value"])')"
EMBED_MODEL_NAME="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["embedModelName"]["value"])')"
EMBED_MODEL_VERSION="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["embedModelVersion"]["value"])')"
LABEL_DEPLOYMENT="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["labelDeployment"]["value"])')"
LABEL_DEPLOYMENT_TYPE="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["labelDeploymentType"]["value"])')"
LABEL_MODEL_NAME="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["labelModelName"]["value"])')"
LABEL_MODEL_VERSION="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["labelModelVersion"]["value"])')"

cat > ../.env <<EOF
AZURE_OPENAI_ENDPOINT=$AOAI_ENDPOINT
AZURE_OPENAI_ACCOUNT_NAME=$AOAI_NAME
AZURE_OPENAI_EMBED_DEPLOYMENT=$EMBED_DEPLOYMENT
AZURE_OPENAI_EMBED_DEPLOYMENT_TYPE=$EMBED_DEPLOYMENT_TYPE
AZURE_OPENAI_EMBED_MODEL_NAME=$EMBED_MODEL_NAME
AZURE_OPENAI_EMBED_MODEL_VERSION=$EMBED_MODEL_VERSION
AZURE_OPENAI_LABEL_DEPLOYMENT=$LABEL_DEPLOYMENT
AZURE_OPENAI_LABEL_DEPLOYMENT_TYPE=$LABEL_DEPLOYMENT_TYPE
AZURE_OPENAI_LABEL_MODEL_NAME=$LABEL_MODEL_NAME
AZURE_OPENAI_LABEL_MODEL_VERSION=$LABEL_MODEL_VERSION
AZURE_OPENAI_LOCATION=$AZURE_LOCATION
AZURE_RESOURCE_GROUP=$AZURE_RESOURCE_GROUP
EOF

echo "Wrote ../.env with endpoint + deployment names + model versions from Bicep outputs."

# Poll for role assignment propagation (up to 90s) instead of blind sleep.
echo "Polling for role assignment propagation (up to 90s) ..."
for i in $(seq 1 18); do
  if az cognitiveservices account deployment show \
      -g "$AZURE_RESOURCE_GROUP" -n "$AOAI_NAME" \
      --deployment-name "$EMBED_DEPLOYMENT" \
      --query "properties.provisioningState" -o tsv 2>/dev/null | grep -q Succeeded; then
    echo "  [ok] deployment '$EMBED_DEPLOYMENT' visible on attempt $i"
    break
  fi
  sleep 5
done
echo "Done. Try: python ../src/embed.py --help"
