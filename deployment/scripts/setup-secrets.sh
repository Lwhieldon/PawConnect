#!/bin/bash
# Setup secrets in Google Cloud Secret Manager
# This script helps you create all required secrets for PawConnect AI
#
# Usage:
#   ./deployment/scripts/setup-secrets.sh

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PawConnect - Setup Secrets${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project is set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "GCP Project: ${BLUE}${PROJECT_ID}${NC}"
echo ""

# Confirm with user
echo -e "${YELLOW}This script will create secrets in Secret Manager.${NC}"
echo -e "${YELLOW}Existing secrets will NOT be overwritten.${NC}"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi
echo ""

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com
echo -e "${GREEN}✓ API enabled${NC}"
echo ""

# Function to create a secret
create_secret() {
    local SECRET_NAME=$1
    local PROMPT=$2
    local DESCRIPTION=$3

    echo "----------------------------------------"
    echo -e "${BLUE}Setting up: ${SECRET_NAME}${NC}"
    echo -e "Description: ${DESCRIPTION}"
    echo ""

    # Check if secret already exists
    if gcloud secrets describe "$SECRET_NAME" &>/dev/null; then
        echo -e "${YELLOW}⚠ Secret already exists${NC}"
        read -p "Update with new value? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipped."
            return
        fi
        # Add new version
        echo "$PROMPT"
        read -sp "Enter value (input hidden): " SECRET_VALUE
        echo
        if [ -n "$SECRET_VALUE" ]; then
            echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
            echo -e "${GREEN}✓ Secret updated${NC}"
        else
            echo -e "${YELLOW}⚠ Empty value, skipped${NC}"
        fi
    else
        # Create new secret
        echo "$PROMPT"
        read -sp "Enter value (input hidden): " SECRET_VALUE
        echo
        if [ -n "$SECRET_VALUE" ]; then
            echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
                --data-file=- \
                --replication-policy="automatic"
            echo -e "${GREEN}✓ Secret created${NC}"
        else
            echo -e "${YELLOW}⚠ Empty value, skipped${NC}"
        fi
    fi
    echo ""
}

# Create all required secrets
echo "Setting up required secrets..."
echo ""

# 1. RescueGroups API Key
create_secret \
    "rescuegroups-api-key" \
    "Enter your RescueGroups API key:" \
    "API key for RescueGroups.org API v5"

# 2. Redis Password
echo "----------------------------------------"
echo -e "${BLUE}Setting up: redis-password${NC}"
echo -e "Description: Password for Memorystore Redis"
echo ""

if gcloud secrets describe redis-password &>/dev/null; then
    echo -e "${YELLOW}⚠ Secret already exists${NC}"
    echo "This will be auto-updated when you create Memorystore instance."
else
    # Generate temporary password
    TEMP_PASSWORD=$(openssl rand -base64 32)
    echo -n "$TEMP_PASSWORD" | gcloud secrets create redis-password \
        --data-file=- \
        --replication-policy="automatic"
    echo -e "${GREEN}✓ Secret created with temporary password${NC}"
    echo "This will be updated with actual Memorystore auth string."
fi
echo ""

# 3. Dialogflow Agent ID
create_secret \
    "dialogflow-agent-id" \
    "Enter your Dialogflow CX Agent ID:" \
    "Dialogflow CX Agent ID for PawConnect"

# Grant access to default service account
echo "----------------------------------------"
echo "Granting access to Cloud Run service account..."

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo -e "Service Account: ${BLUE}${SERVICE_ACCOUNT}${NC}"
echo ""

for SECRET in rescuegroups-api-key redis-password dialogflow-agent-id; do
    echo -n "Granting access to $SECRET... "
    gcloud secrets add-iam-policy-binding "$SECRET" \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet
    echo -e "${GREEN}✓${NC}"
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Secrets setup complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# List all secrets
echo "Created secrets:"
gcloud secrets list --filter="name:rescuegroups-api-key OR name:redis-password OR name:dialogflow-agent-id"
echo ""

echo "Next steps:"
echo "  1. If you created Memorystore, update redis-password:"
echo "     gcloud redis instances get-auth-string pawconnect-redis --region=us-central1 | gcloud secrets versions add redis-password --data-file=-"
echo ""
echo "  2. Deploy to Cloud Run (secrets will be automatically injected)"
echo "     See: docs/DEPLOYMENT.md"
echo ""
echo "  3. Load secrets locally for development:"
echo "     source deployment/scripts/load-secrets.sh"
echo ""
