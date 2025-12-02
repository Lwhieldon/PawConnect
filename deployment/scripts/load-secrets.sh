#!/bin/bash
# Load secrets from Google Cloud Secret Manager into environment variables
# This script is useful for local development and testing
#
# Usage:
#   source deployment/scripts/load-secrets.sh
#   (or)
#   . deployment/scripts/load-secrets.sh
#
# Note: Use 'source' or '.' to run this script so environment variables persist

# Determine if script is being sourced or executed
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0

# Function to exit or return based on how script was called
safe_exit() {
    local exit_code=$1
    if [ $SOURCED -eq 1 ]; then
        return $exit_code
    else
        exit $exit_code
    fi
}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PawConnect - Load Secrets from GCP${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if script is being sourced
if [ $SOURCED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Script is being executed, not sourced${NC}"
    echo -e "${YELLOW}   Environment variables will NOT persist after script exits${NC}"
    echo ""
    echo -e "To properly load secrets, run:"
    echo -e "  ${GREEN}source deployment/scripts/load-secrets.sh${NC}"
    echo -e "  ${GREEN}. deployment/scripts/load-secrets.sh${NC}"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    echo ""
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    safe_exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with gcloud${NC}"
    echo "Run: gcloud auth login"
    safe_exit 1
fi

# Get current project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project is set${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    safe_exit 1
fi

echo -e "${GREEN}✓ Authenticated with GCP${NC}"
echo -e "  Project: ${BLUE}${PROJECT_ID}${NC}"
echo ""

# List of secrets to load
SECRETS=(
    "rescuegroups-api-key:RESCUEGROUPS_API_KEY"
    "redis-password:REDIS_PASSWORD"
    "dialogflow-agent-id:DIALOGFLOW_AGENT_ID"
)

# Function to load a single secret
load_secret() {
    local SECRET_NAME=$1
    local ENV_VAR_NAME=$2

    echo -n "Loading ${SECRET_NAME}... "

    # Try to access the secret
    SECRET_VALUE=$(gcloud secrets versions access latest --secret="${SECRET_NAME}" 2>/dev/null)
    local EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ] && [ -n "$SECRET_VALUE" ]; then
        export ${ENV_VAR_NAME}="${SECRET_VALUE}"
        echo -e "${GREEN}✓ Loaded${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Not found or access denied${NC}"
        return 1
    fi
}

# Load all secrets
echo "Loading secrets from Secret Manager..."
echo ""

LOADED_COUNT=0
FAILED_COUNT=0

for SECRET_MAPPING in "${SECRETS[@]}"; do
    IFS=':' read -r SECRET_NAME ENV_VAR_NAME <<< "$SECRET_MAPPING"
    if load_secret "$SECRET_NAME" "$ENV_VAR_NAME"; then
        ((LOADED_COUNT++))
    else
        ((FAILED_COUNT++))
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "Secrets loaded: ${GREEN}${LOADED_COUNT}${NC}"
echo -e "Secrets failed: ${YELLOW}${FAILED_COUNT}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${YELLOW}Note: Some secrets could not be loaded${NC}"
    echo "This might be because:"
    echo "  1. The secrets don't exist in Secret Manager"
    echo "  2. You don't have permission to access them"
    echo "  3. You're in the wrong GCP project"
    echo ""
    echo "To create missing secrets, run:"
    echo -e "  ${GREEN}./deployment/scripts/setup-secrets.sh${NC}"
    echo ""
    echo "See docs/DEPLOYMENT.md for more information."
    echo ""
fi

# Verify environment variables are set
echo "Verifying loaded secrets..."
if [ -n "$RESCUEGROUPS_API_KEY" ]; then
    echo -e "  RESCUEGROUPS_API_KEY: ${GREEN}Set (${#RESCUEGROUPS_API_KEY} chars)${NC}"
else
    echo -e "  RESCUEGROUPS_API_KEY: ${YELLOW}Not set${NC}"
fi

if [ -n "$REDIS_PASSWORD" ]; then
    echo -e "  REDIS_PASSWORD: ${GREEN}Set (${#REDIS_PASSWORD} chars)${NC}"
else
    echo -e "  REDIS_PASSWORD: ${YELLOW}Not set${NC}"
fi

if [ -n "$DIALOGFLOW_AGENT_ID" ]; then
    echo -e "  DIALOGFLOW_AGENT_ID: ${GREEN}Set (${#DIALOGFLOW_AGENT_ID} chars)${NC}"
else
    echo -e "  DIALOGFLOW_AGENT_ID: ${YELLOW}Not set${NC}"
fi

echo ""

if [ $SOURCED -eq 1 ]; then
    echo -e "${GREEN}✓ Secrets loaded into environment${NC}"
    echo "You can now run your application with production credentials"
else
    echo -e "${YELLOW}⚠️  Note: Variables were loaded but won't persist${NC}"
    echo "To persist variables, run:"
    echo -e "  ${GREEN}source deployment/scripts/load-secrets.sh${NC}"
fi

echo ""
echo -e "${YELLOW}⚠️  WARNING: These are PRODUCTION secrets!${NC}"
echo -e "${YELLOW}   Do not log them or share your terminal session${NC}"
echo ""

# Return success if at least some secrets loaded
if [ $LOADED_COUNT -gt 0 ]; then
    safe_exit 0
else
    safe_exit 1
fi
