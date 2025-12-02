#!/bin/bash
# Validate that all required secrets are properly configured
# This script checks if secrets exist and are accessible
#
# Usage:
#   ./deployment/scripts/validate-secrets.sh

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PawConnect - Validate Secrets${NC}"
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
    exit 1
fi

echo -e "GCP Project: ${BLUE}${PROJECT_ID}${NC}"
echo ""

# Required secrets
REQUIRED_SECRETS=(
    "rescuegroups-api-key"
    "redis-password"
    "dialogflow-agent-id"
)

PASSED=0
FAILED=0
WARNINGS=0

# Function to check a secret
check_secret() {
    local SECRET_NAME=$1

    echo -n "Checking ${SECRET_NAME}... "

    # Check if secret exists
    if ! gcloud secrets describe "$SECRET_NAME" &>/dev/null; then
        echo -e "${RED}✗ Not found${NC}"
        echo "  → Create with: gcloud secrets create $SECRET_NAME --data-file=-"
        ((FAILED++))
        return 1
    fi

    # Check if we can access it
    if ! gcloud secrets versions access latest --secret="$SECRET_NAME" &>/dev/null; then
        echo -e "${RED}✗ Access denied${NC}"
        echo "  → Grant access with IAM policy binding"
        ((FAILED++))
        return 1
    fi

    # Get secret value length
    SECRET_VALUE=$(gcloud secrets versions access latest --secret="$SECRET_NAME" 2>/dev/null)
    VALUE_LENGTH=${#SECRET_VALUE}

    # Check if value looks valid
    if [ $VALUE_LENGTH -lt 10 ]; then
        echo -e "${YELLOW}⚠ Found but value seems short (${VALUE_LENGTH} chars)${NC}"
        echo "  → Verify this is the correct value"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓ OK (${VALUE_LENGTH} chars)${NC}"
        ((PASSED++))
    fi

    # Check IAM permissions
    local PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    local SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

    if ! gcloud secrets get-iam-policy "$SECRET_NAME" --flatten="bindings[].members" | grep -q "$SERVICE_ACCOUNT"; then
        echo -e "  ${YELLOW}⚠ Service account may not have access${NC}"
        echo "  → Grant access: gcloud secrets add-iam-policy-binding $SECRET_NAME --member=serviceAccount:$SERVICE_ACCOUNT --role=roles/secretmanager.secretAccessor"
        ((WARNINGS++))
    fi

    return 0
}

# Check all required secrets
echo "Checking required secrets..."
echo ""

for SECRET in "${REQUIRED_SECRETS[@]}"; do
    check_secret "$SECRET"
    echo ""
done

# Summary
echo "========================================" -e "${BLUE}"
echo "Validation Summary:"
echo "  Passed:   ${GREEN}${PASSED}${NC}"
echo "  Warnings: ${YELLOW}${WARNINGS}${NC}"
echo "  Failed:   ${RED}${FAILED}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Secret Manager API
echo "Additional checks:"
echo -n "Secret Manager API enabled... "
if gcloud services list --enabled | grep -q secretmanager.googleapis.com; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "  → Enable: gcloud services enable secretmanager.googleapis.com"
    ((FAILED++))
fi

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Validation failed with ${FAILED} error(s)${NC}"
    echo "Please fix the errors above before deploying."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Validation passed with ${WARNINGS} warning(s)${NC}"
    echo "Consider addressing the warnings above."
    exit 0
else
    echo ""
    echo -e "${GREEN}✓ All secrets are properly configured!${NC}"
    echo "You're ready to deploy to production."
    exit 0
fi
