#!/bin/bash
# Deploy PawConnect Dialogflow Webhook to Google Cloud Run using Cloud Build
# No local Docker installation required!

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="pawconnect-webhook"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "========================================"
echo "PawConnect Webhook Deployment"
echo "(Using Cloud Build - no Docker needed)"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "========================================"

# Check if required environment variables are set
if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set"
    exit 1
fi

if [ -z "$RESCUEGROUPS_API_KEY" ]; then
    echo "Error: RESCUEGROUPS_API_KEY environment variable is not set"
    exit 1
fi

# Build and deploy using Cloud Build
echo "Building and deploying with Cloud Build..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 10 \
    --min-instances 0 \
    --startup-cpu-boost \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --set-env-vars "RESCUEGROUPS_API_KEY=${RESCUEGROUPS_API_KEY}" \
    --set-env-vars "RESCUEGROUPS_BASE_URL=${RESCUEGROUPS_BASE_URL:-https://api.rescuegroups.org/v5}" \
    --project ${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)' \
    --project ${PROJECT_ID})

echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo "Service URL: ${SERVICE_URL}"
echo "Webhook URL: ${SERVICE_URL}/webhook"
echo "Health Check: ${SERVICE_URL}/health"
echo ""
echo "Next steps:"
echo "1. Copy the Webhook URL above"
echo "2. Go to Dialogflow CX Console"
echo "3. Navigate to Manage → Webhooks"
echo "4. Create a new webhook with the URL: ${SERVICE_URL}/webhook"
echo "5. Use webhook tags like 'validate-pet-id', 'search-pets', etc."
echo "========================================"
