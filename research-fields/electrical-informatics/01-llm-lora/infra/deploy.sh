#!/usr/bin/env bash
# infra/deploy.sh — Provision the E-1 LLM LoRA quickstart infrastructure
# Usage: bash infra/deploy.sh [--prefix spread] [--location japaneast] [--rg rg-spread1000-e1]
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────
PREFIX="spread"
LOCATION="japaneast"
RG="rg-spread1000-e1"
DEPLOYMENT_NAME="spread1000-e1-$(date +%Y%m%d%H%M%S)"

# ── Parse optional overrides ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)    PREFIX="$2";   shift 2 ;;
    --location)  LOCATION="$2"; shift 2 ;;
    --rg)        RG="$2";       shift 2 ;;
    *) echo "[error] Unknown argument: $1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

# ── Preflight: CLI tools ───────────────────────────────────────────────────
echo "[preflight] checking required CLI tools …"
for cmd in az git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "[error] '$cmd' not found. Install it and re-run." >&2; exit 1
  fi
done

AZ_VER=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "0")
echo "[preflight] az CLI version: $AZ_VER"

# Ensure ml extension
if ! az extension show --name ml &>/dev/null 2>&1; then
  echo "[preflight] installing az ml extension …"
  az extension add --name ml --yes
fi

# ── Preflight: subscription ────────────────────────────────────────────────
SUB_ID=$(az account show --query id -o tsv 2>/dev/null || true)
if [[ -z "$SUB_ID" ]]; then
  echo "[error] not logged in. Run: az login" >&2; exit 1
fi
echo "[preflight] subscription: $SUB_ID"

# ── Preflight: RP registration ────────────────────────────────────────────
echo "[preflight] registering resource providers …"
for rp in \
  Microsoft.MachineLearningServices \
  Microsoft.Storage \
  Microsoft.KeyVault \
  Microsoft.Insights \
  Microsoft.OperationalInsights \
  Microsoft.ContainerRegistry; do
  state=$(az provider show --namespace "$rp" --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "$state" != "Registered" ]]; then
    echo "[preflight]   registering $rp …"
    az provider register --namespace "$rp" --wait
  else
    echo "[preflight]   $rp — already Registered"
  fi
done

# ── Resource group ────────────────────────────────────────────────────────
echo "[deploy] creating resource group $RG in $LOCATION …"
az group create --name "$RG" --location "$LOCATION" --output none

# ── Name collision detection ──────────────────────────────────────────────
echo "[deploy] checking for existing AML workspace in $RG …"
existing=$(az ml workspace list -g "$RG" --query "[].name" -o tsv 2>/dev/null || true)
if [[ -n "$existing" ]]; then
  echo "[warn] existing AML workspaces in $RG: $existing"
  echo "[warn] Bicep will update in-place (idempotent). Press Ctrl+C within 10s to abort."
  sleep 10
fi

# ── Bicep deployment ──────────────────────────────────────────────────────
echo "[deploy] deploying infra/main.bicep …"
az deployment group create \
  --resource-group "$RG" \
  --template-file "$SCRIPT_DIR/main.bicep" \
  --parameters prefix="$PREFIX" location="$LOCATION" \
  --name "$DEPLOYMENT_NAME" \
  --output none

# ── Extract outputs ────────────────────────────────────────────────────────
echo "[deploy] reading deployment outputs …"
WS=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" \
  --query "properties.outputs.workspaceName.value" -o tsv)
KV=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" \
  --query "properties.outputs.keyVaultName.value" -o tsv)
SA=$(az deployment group show -g "$RG" -n "$DEPLOYMENT_NAME" \
  --query "properties.outputs.storageAccountName.value" -o tsv)

echo "[deploy] workspace:      $WS"
echo "[deploy] key vault:      $KV"
echo "[deploy] storage:        $SA"

# ── Quota check ──────────────────────────────────────────────────────────
echo "[quota] listing GPU compute usage …"
az ml compute list-usage -g "$RG" -w "$WS" -l "$LOCATION" -o table || \
  echo "[quota] (list-usage not available for this workspace yet)"

echo "[quota] checking NCasT4_v3 availability in $LOCATION …"
t4_count=$(az ml compute list-sizes -g "$RG" -w "$WS" -l "$LOCATION" \
  --query "[?name=='STANDARD_NC4AS_T4_V3'] | length(@)" -o tsv 2>/dev/null || echo "0")
if [[ "$t4_count" -eq 0 ]]; then
  echo "[warn] Standard_NC4as_T4_v3 not listed in $LOCATION — you may need to request quota."
else
  echo "[quota] Standard_NC4as_T4_v3 available: $t4_count SKU(s)"
fi

# ── Register custom AML environment ──────────────────────────────────────
echo "[env] registering spread-lora-gpu:1 environment …"
az ml environment create \
  -g "$RG" -w "$WS" \
  --file "$SCRIPT_DIR/environments/gpu/environment.yml" \
  --output none || \
  echo "[env] (environment may already exist — skipping)"

# ── Write .env (no secrets) ───────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
cat > "$ENV_FILE" << ENVEOF
# Generated by infra/deploy.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Do NOT commit this file to Git.
RG=${RG}
WS=${WS}
LOC=${LOCATION}
KV_NAME=${KV}
STORAGE_ACCOUNT=${SA}
ENVEOF
chmod 600 "$ENV_FILE"
echo "[deploy] wrote $ENV_FILE (chmod 600)"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " Deployment complete!"
echo " Workspace: $WS  (resource group: $RG)"
echo " Source .env with:  source .env"
echo " Submit training:   az ml job create --file train_job.yml -g \$RG -w \$WS --stream"
echo "════════════════════════════════════════════════════════════════"
