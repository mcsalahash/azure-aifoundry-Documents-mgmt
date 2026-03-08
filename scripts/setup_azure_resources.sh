#!/bin/bash
# =============================================================================
# Azure AI Foundry - Provision all required Azure AI resources
# AI-102 Lab Setup Script
# =============================================================================
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Sufficient permissions to create resources
# Usage:
#   chmod +x scripts/setup_azure_resources.sh
#   ./scripts/setup_azure_resources.sh
#
# Idempotent: safe to re-run — existing resources are skipped, not recreated.
# =============================================================================

set -uo pipefail   # -e removed intentionally: individual failures are handled per-resource

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "   ${GREEN}✅ $*${NC}"; }
skip() { echo -e "   ${YELLOW}⏭  $* (already exists)${NC}"; }
fail() { echo -e "   ${RED}❌ $*${NC}"; }
info() { echo -e "${CYAN}$*${NC}"; }

# ── Configuration ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-LABAI}"
LOCATION="${AZURE_LOCATION:-francecentral}"
PREFIX="${AZURE_PREFIX:-ai102lab}"

SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || echo "")

info "=== Azure AI Foundry Lab — Resource Provisioning ==="
echo  "Resource Group : $RESOURCE_GROUP"
echo  "Location       : $LOCATION"
echo  "Subscription   : ${SUBSCRIPTION_ID:-<not detected>}"
echo  ""

# ── Helper: create or skip a Cognitive Services account ───────────────────────
create_cognitive() {
  local name="$1" kind="$2" sku="$3" loc="${4:-$LOCATION}"
  if az cognitiveservices account show --name "$name" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    skip "$name ($kind)"
  else
    az cognitiveservices account create \
      --name "$name" \
      --resource-group "$RESOURCE_GROUP" \
      --kind "$kind" \
      --sku "$sku" \
      --location "$loc" \
      --custom-domain "$name" \
      --yes \
      --output none \
    && ok "$name ($kind)" \
    || { fail "Failed to create $name ($kind)"; return 1; }
  fi
}

# ── Helper: ensure custom subdomain is set (needed for DNS resolution) ────────
# Without a custom domain, Azure returns a generic regional endpoint
# (francecentral.api.cognitive.microsoft.com) which the SDKs reject.
ensure_custom_domain() {
  local name="$1"
  local current
  current=$(az cognitiveservices account show \
    --name "$name" --resource-group "$RESOURCE_GROUP" \
    --query "properties.customSubDomainName" -o tsv 2>/dev/null || echo "")
  if [[ -z "$current" || "$current" == "None" || "$current" == "null" ]]; then
    az cognitiveservices account update \
      --name "$name" --resource-group "$RESOURCE_GROUP" \
      --custom-domain "$name" \
      --output none 2>/dev/null \
    && ok "  Custom domain set: ${name}.cognitiveservices.azure.com" \
    || fail "  Could not set custom domain for $name (may require recreating the resource)"
  else
    ok "  Custom domain: ${current}.cognitiveservices.azure.com"
  fi
}

# ── Verify Resource Group exists ─────────────────────────────────────────────
if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  fail "Resource Group '$RESOURCE_GROUP' introuvable. Créez-le d'abord ou définissez AZURE_RESOURCE_GROUP."
  exit 1
fi
ok "Resource Group: $RESOURCE_GROUP (trouvé)"
echo ""

# ── 1. Azure AI Services (multi-service — covers Vision + Language fallback) ──
info "1. Azure AI Services (multi-service)..."
AI_SERVICES_NAME="${PREFIX}-ai-services"
create_cognitive "$AI_SERVICES_NAME" "CognitiveServices" "S0"
ensure_custom_domain "$AI_SERVICES_NAME"
AI_KEY=$(az cognitiveservices account keys list \
  --name "$AI_SERVICES_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")

# ── 2. Document Intelligence ──────────────────────────────────────────────────
info "2. Document Intelligence..."
DOC_INT_NAME="${PREFIX}-doc-intel"
create_cognitive "$DOC_INT_NAME" "FormRecognizer" "S0"
ensure_custom_domain "$DOC_INT_NAME"
DOC_INT_ENDPOINT="https://${DOC_INT_NAME}.cognitiveservices.azure.com/"
DOC_INT_KEY=$(az cognitiveservices account keys list \
  --name "$DOC_INT_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")

# ── 3. Azure AI Language (Text Analytics) ─────────────────────────────────────
info "3. Azure AI Language..."
LANGUAGE_NAME="${PREFIX}-language"
create_cognitive "$LANGUAGE_NAME" "TextAnalytics" "S"
ensure_custom_domain "$LANGUAGE_NAME"
LANGUAGE_ENDPOINT="https://${LANGUAGE_NAME}.cognitiveservices.azure.com/"
LANGUAGE_KEY=$(az cognitiveservices account keys list \
  --name "$LANGUAGE_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")
LANGUAGE_KEY="${LANGUAGE_KEY:-$AI_KEY}"

# ── 4. Azure AI Vision (Computer Vision) ──────────────────────────────────────
info "4. Azure AI Vision..."
VISION_NAME="${PREFIX}-vision"
create_cognitive "$VISION_NAME" "ComputerVision" "S1"
ensure_custom_domain "$VISION_NAME"
VISION_ENDPOINT="https://${VISION_NAME}.cognitiveservices.azure.com/"
VISION_KEY=$(az cognitiveservices account keys list \
  --name "$VISION_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")
VISION_KEY="${VISION_KEY:-$AI_KEY}"

# ── 5. Azure OpenAI ───────────────────────────────────────────────────────────
info "5. Azure OpenAI..."
OPENAI_NAME="${PREFIX}-openai"
create_cognitive "$OPENAI_NAME" "OpenAI" "S0"
# OpenAI uses openai.azure.com domain, not cognitiveservices — no custom domain needed
OPENAI_ENDPOINT="https://${OPENAI_NAME}.openai.azure.com/"
OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")

# Deploy GPT-4o — essaie plusieurs versions/SKU selon la disponibilité régionale
CHAT_DEPLOYMENT_NAME="gpt-4o"
if az cognitiveservices account deployment show \
    --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
    --deployment-name "$CHAT_DEPLOYMENT_NAME" &>/dev/null; then
  skip "  $CHAT_DEPLOYMENT_NAME deployment"
else
  deployed=false
  for version in "2024-08-06" "2024-11-20" "2024-05-13"; do
    for sku in "GlobalStandard" "Standard"; do
      if az cognitiveservices account deployment create \
          --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
          --deployment-name "$CHAT_DEPLOYMENT_NAME" \
          --model-name "gpt-4o" --model-version "$version" \
          --model-format OpenAI \
          --sku-capacity 10 --sku-name "$sku" \
          --output none 2>/dev/null; then
        ok "  $CHAT_DEPLOYMENT_NAME deployment (version=$version, sku=$sku)"
        deployed=true
        break 2
      fi
    done
  done
  if [[ "$deployed" == "false" ]]; then
    CHAT_DEPLOYMENT_NAME="gpt-4o-mini"
    if az cognitiveservices account deployment create \
        --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
        --deployment-name "$CHAT_DEPLOYMENT_NAME" \
        --model-name "gpt-4o-mini" --model-version "2024-07-18" \
        --model-format OpenAI \
        --sku-capacity 10 --sku-name "GlobalStandard" \
        --output none 2>/dev/null; then
      ok "  $CHAT_DEPLOYMENT_NAME deployment (fallback gpt-4o-mini)"
    else
      fail "  Aucun déploiement GPT disponible en $LOCATION — vérifiez les quotas Azure"
    fi
  fi
fi

# Deploy text-embedding-ada-002 (idempotent)
if az cognitiveservices account deployment show \
    --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
    --deployment-name "text-embedding-ada-002" &>/dev/null; then
  skip "  text-embedding-ada-002 deployment"
else
  az cognitiveservices account deployment create \
    --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
    --deployment-name "text-embedding-ada-002" \
    --model-name "text-embedding-ada-002" --model-version "2" \
    --model-format OpenAI \
    --sku-capacity 10 --sku-name "Standard" \
    --output none 2>/dev/null \
  && ok "  text-embedding-ada-002 deployment" \
  || {
    az cognitiveservices account deployment create \
      --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" \
      --deployment-name "text-embedding-ada-002" \
      --model-name "text-embedding-ada-002" --model-version "2" \
      --model-format OpenAI \
      --sku-capacity 10 --sku-name "GlobalStandard" \
      --output none \
    && ok "  text-embedding-ada-002 deployment (GlobalStandard)" \
    || fail "  text-embedding-ada-002 deployment failed";
  }
fi

# ── 6. Azure AI Search ────────────────────────────────────────────────────────
info "6. Azure AI Search..."
SEARCH_NAME="${PREFIX}-search"
if az search service show --name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  skip "$SEARCH_NAME (AI Search)"
else
  az search service create \
    --name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" \
    --sku basic --location "$LOCATION" \
    --output none \
  && ok "$SEARCH_NAME (AI Search)" || fail "Failed to create $SEARCH_NAME"
fi
SEARCH_ENDPOINT="https://${SEARCH_NAME}.search.windows.net"
SEARCH_KEY=$(az search admin-key show \
  --service-name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "primaryKey" -o tsv 2>/dev/null || echo "")

# ── 7. Azure Translator ───────────────────────────────────────────────────────
info "7. Azure Translator..."
TRANSLATOR_NAME="${PREFIX}-translator"
create_cognitive "$TRANSLATOR_NAME" "TextTranslation" "S1" "global"
# Translator uses the global api.cognitive.microsofttranslator.com — no custom domain
TRANSLATOR_KEY=$(az cognitiveservices account keys list \
  --name "$TRANSLATOR_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")

# ── 8. Azure AI Content Safety ────────────────────────────────────────────────
info "8. Azure AI Content Safety..."
SAFETY_NAME="${PREFIX}-safety"
create_cognitive "$SAFETY_NAME" "ContentSafety" "S0"
ensure_custom_domain "$SAFETY_NAME"
SAFETY_ENDPOINT="https://${SAFETY_NAME}.cognitiveservices.azure.com/"
SAFETY_KEY=$(az cognitiveservices account keys list \
  --name "$SAFETY_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "key1" -o tsv 2>/dev/null || echo "")

# ── 9. Storage Account ───────────────────────────────────────────────────────
info "9. Storage Account..."
STORAGE_NAME="${PREFIX}storage"
STORAGE_NAME=$(echo "$STORAGE_NAME" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]' | cut -c1-24)
if az storage account show --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  skip "$STORAGE_NAME (Storage)"
else
  az storage account create \
    --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" --sku Standard_LRS \
    --output none \
  && ok "$STORAGE_NAME (Storage)" || fail "Failed to create storage account"
fi
STORAGE_CONN=$(az storage account show-connection-string \
  --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" \
  --query "connectionString" -o tsv 2>/dev/null || echo "")

if [ -n "$STORAGE_CONN" ]; then
  az storage container create --name documents \
    --connection-string "$STORAGE_CONN" --output none 2>/dev/null \
  && ok "  container 'documents'" || skip "  container 'documents'"
fi

# ── Generate .env ─────────────────────────────────────────────────────────────
info ""
info "=== Generating .env ==="

cat > .env <<EOF
# Auto-generated by setup_azure_resources.sh — $(date)
# Re-run the script at any time to refresh keys.

# --- Azure Subscription -------------------------------------------------
AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}
AZURE_RESOURCE_GROUP=${RESOURCE_GROUP}
AZURE_LOCATION=${LOCATION}

# --- Azure Document Intelligence ----------------------------------------
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=${DOC_INT_ENDPOINT}
AZURE_DOCUMENT_INTELLIGENCE_KEY=${DOC_INT_KEY}

# --- Azure AI Language --------------------------------------------------
AZURE_LANGUAGE_ENDPOINT=${LANGUAGE_ENDPOINT}
AZURE_LANGUAGE_KEY=${LANGUAGE_KEY}

# --- Azure OpenAI -------------------------------------------------------
AZURE_OPENAI_ENDPOINT=${OPENAI_ENDPOINT}
AZURE_OPENAI_API_KEY=${OPENAI_KEY}
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=${CHAT_DEPLOYMENT_NAME}
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# --- Azure AI Vision ----------------------------------------------------
AZURE_VISION_ENDPOINT=${VISION_ENDPOINT}
AZURE_VISION_KEY=${VISION_KEY}

# --- Azure AI Translator ------------------------------------------------
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
AZURE_TRANSLATOR_KEY=${TRANSLATOR_KEY}
AZURE_TRANSLATOR_REGION=${LOCATION}

# --- Azure AI Search ----------------------------------------------------
AZURE_SEARCH_ENDPOINT=${SEARCH_ENDPOINT}
AZURE_SEARCH_ADMIN_KEY=${SEARCH_KEY}
AZURE_SEARCH_INDEX_NAME=documents-index

# --- Azure AI Content Safety --------------------------------------------
AZURE_CONTENT_SAFETY_ENDPOINT=${SAFETY_ENDPOINT}
AZURE_CONTENT_SAFETY_KEY=${SAFETY_KEY}

# --- Azure Blob Storage -------------------------------------------------
AZURE_STORAGE_CONNECTION_STRING=${STORAGE_CONN}
AZURE_STORAGE_CONTAINER_NAME=documents

# --- Application Settings -----------------------------------------------
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf,docx,txt,png,jpg,jpeg,tiff
EOF

ok ".env generated"
echo ""
info "=== Provisioning Summary ==="
echo ""
echo "  Document Intelligence : ${DOC_INT_ENDPOINT}"
echo "  Language              : ${LANGUAGE_ENDPOINT}"
echo "  Vision                : ${VISION_ENDPOINT}"
echo "  OpenAI                : ${OPENAI_ENDPOINT}"
echo "  AI Search             : ${SEARCH_ENDPOINT}"
echo "  Translator            : ${TRANSLATOR_KEY:+configured (global endpoint)}"
echo "  Content Safety        : ${SAFETY_ENDPOINT}"
echo "  Storage               : ${STORAGE_NAME}"
echo ""
info "Next steps:"
echo "  DOCKER_API_VERSION=1.41 docker compose up --build -d"
