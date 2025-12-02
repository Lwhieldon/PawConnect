#!/bin/bash
# Deploy PawConnect Dialogflow Webhook to Google Cloud Run
# Production configuration with Secret Manager integration

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="pawconnect-dialogflow-webhook"
VPC_CONNECTOR="${VPC_CONNECTOR:-pawconnect-connector}"

echo "========================================"
echo "PawConnect Webhook Deployment"
echo "Production Configuration"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "VPC Connector: ${VPC_CONNECTOR}"
echo "========================================"

# Check if required environment variables are set
if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set"
    echo "Usage: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

# Get Redis host from environment or use default
REDIS_HOST="${REDIS_HOST:-10.0.0.3}"

echo ""
echo "Deploying with production settings:"
echo "  - TESTING_MODE=False"
echo "  - MOCK_APIS=False"
echo "  - Using Secret Manager for credentials"
echo "  - VPC connector for Redis access"
echo ""

# Deploy to Cloud Run using source deployment with Cloud Build
echo "Building and deploying with Cloud Build..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --vpc-connector ${VPC_CONNECTOR} \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60s \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 80 \
    --cpu-throttling \
    --set-env-vars "\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
ENVIRONMENT=production,\
TESTING_MODE=False,\
MOCK_APIS=False,\
LOG_LEVEL=INFO,\
REDIS_HOST=${REDIS_HOST},\
REDIS_PORT=6379,\
RESCUEGROUPS_BASE_URL=https://api.rescuegroups.org/v5,\
VISION_API_ENABLED=True" \
    --set-secrets "\
RESCUEGROUPS_API_KEY=rescuegroups-api-key:latest,\
REDIS_PASSWORD=redis-password:latest" \
    --project ${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)' \
    --project ${PROJECT_ID})

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo "Service URL: ${SERVICE_URL}"
echo "Webhook URL: ${SERVICE_URL}/webhook"
echo "Health Check: ${SERVICE_URL}/health"
echo ""
echo "Testing health endpoint..."
curl -s ${SERVICE_URL}/health | grep -q "healthy" && echo "✓ Health check passed" || echo "✗ Health check failed"
echo ""
echo "Next steps:"
echo "1. Copy the Webhook URL above: ${SERVICE_URL}/webhook"
echo "2. Go to Dialogflow CX Console: https://dialogflow.cloud.google.com/cx"
echo "3. Navigate to Manage → Webhooks"
echo "4. Create or update webhook with URL: ${SERVICE_URL}/webhook"
echo "5. Configure webhook tags:"
echo "   - validate-pet-id: Validate pet IDs from RescueGroups"
echo "   - search-pets: Search for pets by criteria"
echo "   - get-recommendations: Get personalized recommendations"
echo "   - schedule-visit: Schedule shelter visits"
echo "   - submit-application: Submit adoption applications"
echo "========================================"
