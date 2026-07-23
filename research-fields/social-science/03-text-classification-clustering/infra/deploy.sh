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
EMBED_DEPLOYMENT="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["embedDeployment"]["value"])')"
LABEL_DEPLOYMENT="$(echo "$DEPLOY_OUT" | python -c 'import sys,json;print(json.load(sys.stdin)["labelDeployment"]["value"])')"

cat > ../.env <<EOF
AZURE_OPENAI_ENDPOINT=$AOAI_ENDPOINT
AZURE_OPENAI_EMBED_DEPLOYMENT=$EMBED_DEPLOYMENT
AZURE_OPENAI_LABEL_DEPLOYMENT=$LABEL_DEPLOYMENT
AZURE_OPENAI_LOCATION=$AZURE_LOCATION
AZURE_OPENAI_EMBED_DEPLOYMENT_TYPE=Standard
AZURE_OPENAI_LABEL_DEPLOYMENT_TYPE=GlobalStandard
EOF

echo "Wrote ../.env with endpoint + deployment names."
echo "Waiting up to 60s for role assignment to propagate ..."
sleep 30
echo "Done. Try: python ../src/embed.py --help"
