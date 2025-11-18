# PawConnect AI - Deployment Guide

This guide covers deploying PawConnect AI to Google Cloud Platform.

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and configured
- Docker installed (for local testing)
- Terraform installed (for infrastructure provisioning)

## Deployment Options

1. **Cloud Run** (Recommended) - Fully managed, auto-scaling
2. **GKE (Kubernetes)** - For advanced orchestration needs
3. **Cloud Functions** - For webhook handlers

## Cloud Run Deployment (Recommended)

### Step 1: Set Up Environment

```bash
# Set project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com
```

### Step 2: Build Container

```bash
# Build with Cloud Build
gcloud builds submit \
  --config deployment/cloudbuild.yaml \
  --substitutions=_REGION=us-central1

# Or build locally
docker build -t gcr.io/$PROJECT_ID/pawconnect-ai:latest \
  -f deployment/Dockerfile .
docker push gcr.io/$PROJECT_ID/pawconnect-ai:latest
```

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy pawconnect-main-agent \
  --image gcr.io/$PROJECT_ID/pawconnect-ai:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60s \
  --max-instances 10 \
  --min-instances 1
```

### Step 4: Configure Secrets

```bash
# Store API keys in Secret Manager
echo -n "your-rescuegroups-key" | \
  gcloud secrets create rescuegroups-api-key --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding rescuegroups-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 5: Test Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe pawconnect-main-agent \
  --region us-central1 --format='value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Test search endpoint
curl -X POST $SERVICE_URL/api/search \
  -H "Content-Type: application/json" \
  -d '{"pet_type":"dog","location":"Seattle, WA"}'
```

---

## Terraform Deployment

For infrastructure as code:

### Step 1: Initialize Terraform

```bash
cd deployment/terraform

# Create state bucket
gsutil mb gs://$PROJECT_ID-terraform-state

# Initialize
terraform init
```

### Step 2: Configure Variables

Create `terraform.tfvars`:

```hcl
project_id           = "your-project-id"
region               = "us-central1"
environment          = "production"
alert_email          = "your-email@example.com"
dialogflow_agent_id  = "your-agent-id"
rescuegroups_api_key = "your-api-key"
```

### Step 3: Plan and Apply

```bash
# Review changes
terraform plan

# Apply infrastructure
terraform apply

# Get outputs
terraform output cloud_run_url
```

---

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}

      - name: Build and Deploy
        run: |
          gcloud builds submit --config deployment/cloudbuild.yaml
```

---

## Monitoring and Logging

### Set Up Alerts

```bash
# CPU usage alert
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High CPU Usage" \
  --condition-display-name="CPU > 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s
```

### View Logs

```bash
# Stream logs
gcloud run services logs tail pawconnect-main-agent \
  --region us-central1

# Query specific logs
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR"
```

---

## Scaling Configuration

### Auto-scaling

```bash
# Update scaling settings
gcloud run services update pawconnect-main-agent \
  --min-instances 2 \
  --max-instances 20 \
  --concurrency 80 \
  --cpu-throttling \
  --region us-central1
```

### Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils

# Run load test
ab -n 1000 -c 10 -T application/json \
  -p request.json \
  $SERVICE_URL/api/search
```

---

## Rollback

```bash
# List revisions
gcloud run revisions list --service pawconnect-main-agent

# Rollback to previous revision
gcloud run services update-traffic pawconnect-main-agent \
  --to-revisions REVISION_NAME=100
```

---

## Cost Optimization

1. **Use minimum instances only for production**
2. **Enable CPU throttling**
3. **Set appropriate memory limits**
4. **Use Cloud CDN for static assets**
5. **Monitor and optimize cold starts**

---

## Troubleshooting

### Common Issues

**Issue**: Container fails to start
**Solution**: Check logs with `gcloud run services logs tail`

**Issue**: High latency
**Solution**: Increase CPU/memory or add more instances

**Issue**: Authentication errors
**Solution**: Verify service account permissions

---

For more details, see [ARCHITECTURE.md](./ARCHITECTURE.md).
