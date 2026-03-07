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
# =============================================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-ai-foundry-lab}"
LOCATION="${AZURE_LOCATION:-eastus}"
PREFIX="ai102lab"

echo "=== Azure AI Foundry Lab — Resource Provisioning ==="
echo "Resource Group : $RESOURCE_GROUP"
echo "Location       : $LOCATION"
echo ""

# ── Resource Group ────────────────────────────────────────────────────────────
echo "1. Creating Resource Group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none
echo "   ✅ Resource Group: $RESOURCE_GROUP"

# ── Azure AI Services (multi-service) ─────────────────────────────────────────
echo "2. Creating Azure AI Services (multi-service endpoint)..."
AI_SERVICES_NAME="${PREFIX}-ai-services"
az cognitiveservices account create \
  --name "$AI_SERVICES_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind CognitiveServices \
  --sku S0 \
  --location "$LOCATION" \
  --yes \
  --output none
AI_ENDPOINT=$(az cognitiveservices account show --name "$AI_SERVICES_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
AI_KEY=$(az cognitiveservices account keys list --name "$AI_SERVICES_NAME" --resource-group "$RESOURCE_GROUP" --query "key1" -o tsv)
echo "   ✅ AI Services: $AI_SERVICES_NAME"

# ── Document Intelligence ──────────────────────────────────────────────────────
echo "3. Creating Document Intelligence..."
DOC_INT_NAME="${PREFIX}-doc-intel"
az cognitiveservices account create \
  --name "$DOC_INT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind FormRecognizer \
  --sku S0 \
  --location "$LOCATION" \
  --yes \
  --output none
DOC_INT_ENDPOINT=$(az cognitiveservices account show --name "$DOC_INT_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
DOC_INT_KEY=$(az cognitiveservices account keys list --name "$DOC_INT_NAME" --resource-group "$RESOURCE_GROUP" --query "key1" -o tsv)
echo "   ✅ Document Intelligence: $DOC_INT_NAME"

# ── Azure OpenAI ───────────────────────────────────────────────────────────────
echo "4. Creating Azure OpenAI..."
OPENAI_NAME="${PREFIX}-openai"
az cognitiveservices account create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind OpenAI \
  --sku S0 \
  --location "$LOCATION" \
  --yes \
  --output none

# Deploy GPT-4o
az cognitiveservices account deployment create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "gpt-4o" \
  --model-name "gpt-4o" \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard" \
  --output none

# Deploy text-embedding-ada-002
az cognitiveservices account deployment create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name "text-embedding-ada-002" \
  --model-name "text-embedding-ada-002" \
  --model-version "2" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard" \
  --output none

OPENAI_ENDPOINT=$(az cognitiveservices account show --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
OPENAI_KEY=$(az cognitiveservices account keys list --name "$OPENAI_NAME" --resource-group "$RESOURCE_GROUP" --query "key1" -o tsv)
echo "   ✅ Azure OpenAI: $OPENAI_NAME (gpt-4o + text-embedding-ada-002)"

# ── Azure AI Search ────────────────────────────────────────────────────────────
echo "5. Creating Azure AI Search..."
SEARCH_NAME="${PREFIX}-search"
az search service create \
  --name "$SEARCH_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --sku basic \
  --location "$LOCATION" \
  --output none
SEARCH_ENDPOINT="https://${SEARCH_NAME}.search.windows.net"
SEARCH_KEY=$(az search admin-key show --service-name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" --query "primaryKey" -o tsv)
echo "   ✅ Azure AI Search: $SEARCH_NAME"

# ── Azure Translator ───────────────────────────────────────────────────────────
echo "6. Creating Azure Translator..."
TRANSLATOR_NAME="${PREFIX}-translator"
az cognitiveservices account create \
  --name "$TRANSLATOR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind TextTranslation \
  --sku S1 \
  --location global \
  --yes \
  --output none
TRANSLATOR_KEY=$(az cognitiveservices account keys list --name "$TRANSLATOR_NAME" --resource-group "$RESOURCE_GROUP" --query "key1" -o tsv)
echo "   ✅ Translator: $TRANSLATOR_NAME"

# ── Azure AI Content Safety ────────────────────────────────────────────────────
echo "7. Creating Azure AI Content Safety..."
SAFETY_NAME="${PREFIX}-safety"
az cognitiveservices account create \
  --name "$SAFETY_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind ContentSafety \
  --sku S0 \
  --location "$LOCATION" \
  --yes \
  --output none
SAFETY_ENDPOINT=$(az cognitiveservices account show --name "$SAFETY_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.endpoint" -o tsv)
SAFETY_KEY=$(az cognitiveservices account keys list --name "$SAFETY_NAME" --resource-group "$RESOURCE_GROUP" --query "key1" -o tsv)
echo "   ✅ Content Safety: $SAFETY_NAME"

# ── Storage Account ────────────────────────────────────────────────────────────
echo "8. Creating Storage Account..."
STORAGE_NAME="${PREFIX}storage"
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --output none
STORAGE_CONN=$(az storage account show-connection-string --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" --query "connectionString" -o tsv)
az storage container create --name documents --connection-string "$STORAGE_CONN" --output none
echo "   ✅ Storage: $STORAGE_NAME"

# ── Generate .env file ─────────────────────────────────────────────────────────
echo ""
echo "=== Generating .env file ==="
cat > .env <<EOF
# Auto-generated by setup_azure_resources.sh — $(date)

AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$DOC_INT_ENDPOINT
AZURE_DOCUMENT_INTELLIGENCE_KEY=$DOC_INT_KEY

AZURE_LANGUAGE_ENDPOINT=$AI_ENDPOINT
AZURE_LANGUAGE_KEY=$AI_KEY

AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=$OPENAI_KEY
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

AZURE_VISION_ENDPOINT=$AI_ENDPOINT
AZURE_VISION_KEY=$AI_KEY

AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
AZURE_TRANSLATOR_KEY=$TRANSLATOR_KEY
AZURE_TRANSLATOR_REGION=$LOCATION

AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT
AZURE_SEARCH_ADMIN_KEY=$SEARCH_KEY
AZURE_SEARCH_INDEX_NAME=documents-index

AZURE_CONTENT_SAFETY_ENDPOINT=$SAFETY_ENDPOINT
AZURE_CONTENT_SAFETY_KEY=$SAFETY_KEY

AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN
AZURE_STORAGE_CONTAINER_NAME=documents

APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
EOF

echo "✅ .env file generated"
echo ""
echo "=== Setup Complete! ==="
echo "Run: pip install -r requirements.txt && uvicorn app.main:app --reload"
