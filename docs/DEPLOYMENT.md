# PawConnect AI - Production Deployment Guide

This comprehensive guide covers deploying PawConnect AI to Google Cloud Platform in a **production capacity** with `TESTING_MODE=false` and `MOCK_APIS=false`.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Project Setup](#gcp-project-setup)
3. [Environment Configuration](#environment-configuration)
4. [Enable Required APIs](#enable-required-apis)
5. [Configure Secrets Manager](#configure-secrets-manager)
6. [Deploy Firestore Database](#deploy-firestore-database)
7. [Deploy Memorystore (Redis)](#deploy-memorystore-redis)
8. [Configure Pub/Sub](#configure-pubsub)
9. [Deploy to Cloud Run](#deploy-to-cloud-run)
10. [Configure Dialogflow CX](#configure-dialogflow-cx)
11. [Deploy Dialogflow Webhook](#deploy-dialogflow-webhook)
12. [Configure Cloud Vision API](#configure-cloud-vision-api)
13. [Setup Monitoring & Logging](#setup-monitoring--logging)
14. [Testing Production Deployment](#testing-production-deployment)
15. [CI/CD Pipeline](#cicd-pipeline)
16. [Scaling & Performance](#scaling--performance)
17. [Security Best Practices](#security-best-practices)
18. [Troubleshooting](#troubleshooting)
19. [Cost Optimization](#cost-optimization)

---

## Prerequisites

Before deploying PawConnect AI to production, ensure you have:

- **Google Cloud Project** with billing enabled
- **`gcloud` CLI** installed and configured ([Install Guide](https://cloud.google.com/sdk/docs/install))
- **Python 3.11.3 or higher** installed locally for testing
- **Git** installed for version control
- **RescueGroups API Key** ([Sign up here](https://userguide.rescuegroups.org/display/APIDG/API+Developers+Guide+Home))
- **Organizational permissions** to enable APIs and create resources in GCP
- **Domain name** (optional, for custom Dialogflow webhook URLs)
- **`curl`** installed for Dialogflow API calls (pre-installed on Mac/Linux, available on Windows 10+)

> **Note:** The `gcloud dialogflow` commands do not exist in the gcloud CLI. This guide uses the Dialogflow REST API via `curl` commands or directs you to the Dialogflow CX Console for agent management.

---

## GCP Project Setup

### Step 1: Create or Select Project

You can either create a new project or use an existing one.

#### Option A: Use an Existing Project

```bash
# Set your existing project ID
export PROJECT_ID="[Insert Your Existing Project ID Here]"
export REGION="[Insert Region Here]"

# Set active project & region
gcloud config set project $PROJECT_ID

# Verify project is set
gcloud config get-value project

# Check if billing is enabled
gcloud billing projects describe $PROJECT_ID
```

#### Option B: Create a New Project

```bash
# Set variables for new project
export PROJECT_ID="[Insert Your New Project ID Here]"
export PROJECT_NAME="[Insert Your Project Name Here]"
export REGION="[Insert Region Here]"

# Check if project ID is available
gcloud projects describe $PROJECT_ID 2>/dev/null && echo "Project ID already exists! Please choose a different ID or use Option A." || echo "Project ID is available"

# Create new project (only if ID is available)
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"

# Set active project
gcloud config set project $PROJECT_ID

# Link billing account (replace BILLING_ACCOUNT_ID with your billing account ID)
# Find your billing account ID: gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# Verify project is set
gcloud config get-value project
```

**Note**: If you get an error that the project ID already exists, use **Option A** to select your existing project instead.

### Step 2: Get Project Number

```bash
# Get project number (needed for IAM bindings)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
echo "Project Number: $PROJECT_NUMBER"
```

---

## Environment Configuration

### Production Environment Variables

Create a `.env` file in the project root with the following production configuration:

```env
# ============================================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# ============================================================

# Environment & Debug Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=False

# CRITICAL: Production Mode Settings
TESTING_MODE=False
MOCK_APIS=False

# ============================================================
# GOOGLE CLOUD PLATFORM
# ============================================================

GCP_PROJECT_ID=[Insert Your Project ID Here]
GCP_REGION=[Insert Region Here]
# Leave empty - uses Application Default Credentials (ADC) in production
GCP_CREDENTIALS_PATH=

# ============================================================
# RESCUEGROUPS API (Production)
# ============================================================

RESCUEGROUPS_API_KEY=your_production_rescuegroups_api_key
RESCUEGROUPS_BASE_URL=https://api.rescuegroups.org/v5

# ============================================================
# DIALOGFLOW CX
# ============================================================

DIALOGFLOW_AGENT_ID=your_production_dialogflow_agent_id
DIALOGFLOW_LOCATION=[Insert Region Here]

# ============================================================
# VERTEX AI & GEMINI
# ============================================================

# Vertex AI (for custom models - optional)
VERTEX_AI_ENDPOINT=
VERTEX_AI_MODEL_NAME=[Insert Your Model Name Here]

# Gemini AI (for ConversationAgent)
# Uses Vertex AI SDK - ensure GCP_PROJECT_ID and GCP_REGION are set above
GEMINI_MODEL_NAME=gemini-2.0-flash-001
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_OUTPUT_TOKENS=1024
USE_GEMINI_FOR_CONVERSATION=True

# ============================================================
# CLOUD VISION API
# ============================================================

VISION_API_ENABLED=True

# ============================================================
# CLOUD PUB/SUB
# ============================================================

PUBSUB_TOPIC_PREFIX=pawconnect-prod
PUBSUB_SEARCH_TOPIC=pawconnect-prod-search-results
PUBSUB_RECOMMENDATION_TOPIC=pawconnect-prod-recommendations

# ============================================================
# FIRESTORE DATABASE
# ============================================================

FIRESTORE_COLLECTION_USERS=users
FIRESTORE_COLLECTION_APPLICATIONS=applications
FIRESTORE_COLLECTION_SESSIONS=sessions

# ============================================================
# MEMORYSTORE (REDIS) - Production
# ============================================================

# Production Redis - will be set to Memorystore internal IP
REDIS_HOST=10.0.0.3
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password
CACHE_TTL=3600

# ============================================================
# API SETTINGS (Production)
# ============================================================

API_TIMEOUT=30
API_MAX_RETRIES=3
API_RATE_LIMIT=100

# ============================================================
# SEARCH SETTINGS
# ============================================================

DEFAULT_SEARCH_RADIUS=50
MAX_SEARCH_RESULTS=100

# ============================================================
# RECOMMENDATION SETTINGS
# ============================================================

RECOMMENDATION_TOP_K=10
RECOMMENDATION_MIN_SCORE=0.5

# ============================================================
# MODEL SETTINGS
# ============================================================

MODEL_CONFIDENCE_THRESHOLD=0.7
```

**Important Notes:**
- Store this file securely - **NEVER commit it to version control** (`.env` is already in `.gitignore`)
- Use Secret Manager for sensitive values (see next section)
- The `REDIS_HOST` will be updated after deploying Memorystore
- You can copy `.env.example` as a starting point: `cp .env.example .env`

---

## Enable Required APIs

Enable all necessary Google Cloud APIs for PawConnect AI:

```bash
# Enable all required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  artifactregistry.googleapis.com \
  dialogflow.googleapis.com \
  vision.googleapis.com \
  aiplatform.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudfunctions.googleapis.com \
  compute.googleapis.com \
  vpcaccess.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

---

## Configure Secrets Manager

**CRITICAL**: Never store sensitive credentials in code, environment files, or version control. Google Cloud Secret Manager provides secure storage for API keys, passwords, and other sensitive data.

### Quick Start with Helper Scripts

We provide helper scripts to simplify secrets management:

```bash
# 1. Create all required secrets (interactive)
./deployment/scripts/setup-secrets.sh

# 2. Validate secrets are configured correctly
./deployment/scripts/validate-secrets.sh

# 3. Load secrets for local development
source deployment/scripts/load-secrets.sh
```

**📖 Complete Guide:** For comprehensive secrets management documentation, see [SECRETS_MANAGEMENT.md](./SECRETS_MANAGEMENT.md)

**🔧 Script Documentation:** For helper script details, see [deployment/scripts/README.md](../deployment/scripts/README.md)

### Why Use Secret Manager?

- **Encrypted at rest and in transit** - Secrets are encrypted using Google-managed keys
- **Access control** - Fine-grained IAM permissions control who can access secrets
- **Audit logging** - All access to secrets is logged for compliance
- **Version management** - Keep multiple versions of secrets and rotate them easily
- **Integration** - Seamlessly integrates with Cloud Run, Cloud Functions, and GKE

### Step 1: Enable Secret Manager API

```bash
# Enable the API if not already enabled
gcloud services enable secretmanager.googleapis.com

# Verify it's enabled
gcloud services list --enabled | grep secretmanager
```

### Step 2: Create Secrets

Create secrets for all sensitive credentials:

```bash
# IMPORTANT: Replace placeholder values with your actual credentials

# 1. RescueGroups API Key (REQUIRED for production)
# Get your key from: https://userguide.rescuegroups.org/display/APIDG/API+Developers+Guide+Home
echo -n "your_actual_rescuegroups_api_key" | \
  gcloud secrets create rescuegroups-api-key \
  --data-file=- \
  --replication-policy="automatic"

# 2. Redis Password (will be auto-generated by Memorystore)
# We'll update this after creating the Redis instance
echo -n "temporary_password" | \
  gcloud secrets create redis-password \
  --data-file=- \
  --replication-policy="automatic"

# 3. Dialogflow Agent ID
# Get this from Dialogflow CX Console after creating your agent
echo -n "your_dialogflow_agent_id" | \
  gcloud secrets create dialogflow-agent-id \
  --data-file=- \
  --replication-policy="automatic"

# List all secrets to verify creation
gcloud secrets list

# View secret metadata (does NOT show the actual secret value)
gcloud secrets describe rescuegroups-api-key
```

### Step 3: Grant Service Account Access

```bash
# Get your project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Cloud Run service account (default compute service account)
export SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Secret Manager access to: ${SERVICE_ACCOUNT}"

# Grant Secret Manager Secret Accessor role to all secrets
for SECRET in rescuegroups-api-key redis-password dialogflow-agent-id; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

  echo "✓ Granted access to: $SECRET"
done

# Verify permissions for a secret
echo ""
echo "Verifying permissions..."
gcloud secrets get-iam-policy rescuegroups-api-key
```

### Step 4: Update Secret Values (When Needed)

```bash
# To update a secret value, add a new version
# Example: Update RescueGroups API key
echo -n "new_api_key_value" | \
  gcloud secrets versions add rescuegroups-api-key --data-file=-

# List versions of a secret
gcloud secrets versions list rescuegroups-api-key

# Cloud Run automatically uses the "latest" version
# No need to redeploy unless you want to force a restart
```

### Step 5: Access Secrets Locally (For Development/Testing)

**⚡ Quick Start:** See [QUICK_START_SECRETS.md](./QUICK_START_SECRETS.md) for step-by-step instructions.

**OPTION 1: Use our helper script (Recommended)**
```bash
# IMPORTANT: Use 'source' not './'
source deployment/scripts/load-secrets.sh

# Or using dot notation
. deployment/scripts/load-secrets.sh

# ⚠️ DON'T run directly - will crash terminal!
# ./deployment/scripts/load-secrets.sh  # ❌ WRONG
```

**OPTION 2: Access secrets directly via gcloud**
```bash
# Get secret value and set as environment variable
export RESCUEGROUPS_API_KEY=$(gcloud secrets versions access latest --secret="rescuegroups-api-key")
export REDIS_PASSWORD=$(gcloud secrets versions access latest --secret="redis-password")
export DIALOGFLOW_AGENT_ID=$(gcloud secrets versions access latest --secret="dialogflow-agent-id")

# Verify (will print the actual secret value - be careful!)
echo $RESCUEGROUPS_API_KEY
```

**OPTION 3: For Python applications, use the Secret Manager client library**
```python
# Already integrated in PawConnect - see pawconnect_ai/config.py
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
# Automatically loads secrets in production
```

### Step 6: Verify Secret Access

```bash
# Test that service account can access secrets
gcloud secrets versions access latest \
  --secret="rescuegroups-api-key" \
  --impersonate-service-account="${SERVICE_ACCOUNT}" 2>&1 | \
  grep -q "permission denied" && echo "❌ Access denied" || echo "✓ Access granted"

# Test all secrets
for SECRET in rescuegroups-api-key redis-password dialogflow-agent-id; do
  echo -n "Testing $SECRET: "
  gcloud secrets versions access latest --secret="$SECRET" > /dev/null 2>&1 && \
    echo "✓ Accessible" || echo "❌ Not accessible"
done
```

### Best Practices for Secret Management

1. **Never log secret values** - Ensure your application doesn't log credentials
2. **Use latest version** - Always reference `:latest` to automatically get updates
3. **Rotate regularly** - Update secrets periodically (see secret rotation section)
4. **Principle of least privilege** - Only grant access to services that need it
5. **Audit access** - Regularly review audit logs for secret access
6. **Use Secret Manager for ALL credentials** - API keys, passwords, tokens, certificates
7. **Delete unused secrets** - Clean up old secrets to reduce attack surface

### Secret Rotation Strategy

```bash
# Create a rotation script (example for RescueGroups API key)
cat > rotate-rescuegroups-key.sh <<'EOF'
#!/bin/bash
set -e

echo "Rotating RescueGroups API key..."

# 1. Generate new API key from RescueGroups website
read -sp "Enter new RescueGroups API key: " NEW_KEY
echo

# 2. Add new version to Secret Manager
echo -n "$NEW_KEY" | gcloud secrets versions add rescuegroups-api-key --data-file=-

# 3. Test new key
echo "Testing new API key..."
# Add test command here

# 4. Restart Cloud Run services to pick up new secret
gcloud run services update pawconnect-main-agent --region=us-central1
gcloud run services update pawconnect-dialogflow-webhook --region=us-central1

echo "✓ API key rotated successfully"
EOF

chmod +x rotate-rescuegroups-key.sh
```

### Troubleshooting Secrets

#### Secret Not Found
```bash
# Check if secret exists
gcloud secrets list | grep rescuegroups-api-key

# If not found, create it
echo -n "your_key" | gcloud secrets create rescuegroups-api-key --data-file=-
```

#### Permission Denied
```bash
# Verify service account has access
gcloud secrets get-iam-policy rescuegroups-api-key

# Grant access if missing
gcloud secrets add-iam-policy-binding rescuegroups-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

#### Cloud Run Can't Access Secret
```bash
# Check Cloud Run service configuration
gcloud run services describe pawconnect-main-agent \
  --region=us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"

# Verify service account in Cloud Run matches IAM binding
gcloud run services describe pawconnect-main-agent \
  --region=us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"
```

### Cost Considerations

Secret Manager pricing:
- **Secret versions**: $0.06 per 10,000 versions per month
- **Access operations**: $0.03 per 10,000 access operations
- **First 6 secret versions per secret**: FREE
- **First 10,000 access operations**: FREE

For most applications, Secret Manager costs are negligible (< $1/month).

### Security Checklist

- [ ] All secrets created in Secret Manager
- [ ] No credentials in `.env` file committed to git
- [ ] Service account has `secretAccessor` role for all secrets
- [ ] Secrets are referenced as `:latest` in Cloud Run
- [ ] Local development uses `gcloud secrets` or helper script
- [ ] Audit logging enabled for secret access
- [ ] Secret rotation schedule documented
- [ ] Team members know how to access secrets safely

---

## Deploy Firestore Database

PawConnect uses Firestore for storing user profiles, applications, and session data.

### Step 1: Create Firestore Database

```bash
# Create Firestore database in Native mode
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native

# Verify database creation
gcloud firestore databases list
```

### Step 2: Set Up Firestore Collections

The application will automatically create collections, but you can pre-configure indexes:

```bash
# Create composite indexes for common queries
gcloud firestore indexes composite create \
  --collection-group=users \
  --query-scope=COLLECTION \
  --field-config field-path=createdAt,order=DESCENDING \
  --field-config field-path=location,order=ASCENDING

gcloud firestore indexes composite create \
  --collection-group=applications \
  --query-scope=COLLECTION \
  --field-config field-path=status,order=ASCENDING \
  --field-config field-path=submittedAt,order=DESCENDING

# List indexes
gcloud firestore indexes composite list
```

### Step 3: Grant Firestore Permissions

```bash
# Grant Firestore access to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/datastore.user"
```

---

## Deploy Memorystore (Redis)

Memorystore provides managed Redis for caching API responses and session data.

### Step 1: Create VPC Network (if not exists)

```bash
# Check if default network exists
gcloud compute networks list

# Create custom VPC for production (recommended)
gcloud compute networks create pawconnect-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional

# Create subnet
gcloud compute networks subnets create pawconnect-subnet \
  --network=pawconnect-vpc \
  --region=$REGION \
  --range=10.0.0.0/24
```

### Step 2: Create Memorystore Instance

```bash
# Create Redis instance (Basic tier for production, Standard tier for high availability)
gcloud redis instances create pawconnect-redis \
  --size=1 \
  --region=$REGION \
  --tier=BASIC \
  --redis-version=redis_7_0 \
  --network=pawconnect-vpc \
  --enable-auth

# This takes 5-10 minutes. Monitor progress:
gcloud redis instances describe pawconnect-redis --region=$REGION

# Get Redis host IP and auth string
export REDIS_HOST=$(gcloud redis instances describe pawconnect-redis \
  --region=$REGION --format="value(host)")
export REDIS_AUTH=$(gcloud redis instances get-auth-string pawconnect-redis \
  --region=$REGION)

echo "Redis Host: $REDIS_HOST"
echo "Redis Auth String: $REDIS_AUTH"

# Update redis-password secret with auth string
echo -n "$REDIS_AUTH" | gcloud secrets versions add redis-password --data-file=-
```

### Step 3: Configure VPC Access for Cloud Run

```bash
# Create VPC Access Connector (required for Cloud Run to access Memorystore)
gcloud compute networks vpc-access connectors create pawconnect-connector \
  --region=$REGION \
  --network=pawconnect-vpc \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3

# Verify connector
gcloud compute networks vpc-access connectors describe pawconnect-connector \
  --region=$REGION
```

---

## Configure Pub/Sub

Set up Pub/Sub topics for event-driven communication between agents.

### Step 1: Create Topics

```bash
# Create topics for agent communication
gcloud pubsub topics create pawconnect-prod-search-results
gcloud pubsub topics create pawconnect-prod-recommendations
gcloud pubsub topics create pawconnect-prod-vision-analysis
gcloud pubsub topics create pawconnect-prod-workflow-events

# List topics
gcloud pubsub topics list
```

### Step 2: Create Subscriptions

```bash
# Create subscriptions for each topic
gcloud pubsub subscriptions create pawconnect-prod-search-sub \
  --topic=pawconnect-prod-search-results \
  --ack-deadline=60 \
  --message-retention-duration=7d

gcloud pubsub subscriptions create pawconnect-prod-recommendation-sub \
  --topic=pawconnect-prod-recommendations \
  --ack-deadline=60 \
  --message-retention-duration=7d

gcloud pubsub subscriptions create pawconnect-prod-vision-sub \
  --topic=pawconnect-prod-vision-analysis \
  --ack-deadline=60 \
  --message-retention-duration=7d

gcloud pubsub subscriptions create pawconnect-prod-workflow-sub \
  --topic=pawconnect-prod-workflow-events \
  --ack-deadline=60 \
  --message-retention-duration=7d

# List subscriptions
gcloud pubsub subscriptions list
```

### Step 3: Grant Pub/Sub Permissions

```bash
# Grant Pub/Sub permissions to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.subscriber"
```

---

## Deploy to Cloud Run

Deploy the main PawConnect AI application to Cloud Run.

### Step 1: Build Container with Cloud Build

**Prerequisites Check:**
```bash
# Verify required APIs are enabled
gcloud services list --enabled | grep -E 'cloudbuild|run\.googleapis'

# Verify you're in the correct project
gcloud config get-value project

# Verify region is set
echo $REGION
```

**Build and Deploy:**
```bash
# Set your region if not already set
export REGION="us-central1"

# Build using Cloud Build (no Docker required locally)
gcloud builds submit \
  --config deployment/cloudbuild.yaml \
  --substitutions=_REGION=$REGION

# Monitor build progress in Cloud Console or:
gcloud builds list --limit=5

# Check build logs if there are errors
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

**Common Build Errors:**

❌ **Error: "invalid value for 'build.substitutions': key ... is not a valid built-in substitution"**

**Cause:** Shell variables in bash scripts need to be escaped with `$$` in Cloud Build YAML.

**Solution:** Ensure bash variables use `$$` not `$`:
```yaml
# ❌ WRONG
SERVICE_URL=$variable

# ✅ CORRECT
SERVICE_URL=$$variable
```

❌ **Error: "Build artifacts bucket does not exist"**

**Cause:** The GCS bucket for artifacts doesn't exist.

**Solution:**
```bash
# Create artifacts bucket
gsutil mb -p $PROJECT_ID gs://${PROJECT_ID}-artifacts

# Or skip artifacts by commenting out the artifacts section in cloudbuild.yaml
```

❌ **Error: "VPC connector not found"**

**Cause:** VPC connector hasn't been created yet.

**Solution:** Either create the connector first (see Memorystore section) or deploy without it initially:
```bash
# Deploy without VPC connector (won't be able to access Redis)
gcloud builds submit \
  --config deployment/cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_VPC_CONNECTOR=""
```

### Step 2: Deploy to Cloud Run with Production Configuration

```bash
# Deploy with all production settings
gcloud run deploy pawconnect-main-agent \
  --image gcr.io/$PROJECT_ID/pawconnect-ai:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --vpc-connector pawconnect-connector \
  --set-env-vars "\
GCP_PROJECT_ID=$PROJECT_ID,\
GCP_REGION=$REGION,\
ENVIRONMENT=production,\
TESTING_MODE=False,\
MOCK_APIS=False,\
LOG_LEVEL=INFO,\
REDIS_HOST=$REDIS_HOST,\
REDIS_PORT=6379,\
USE_GEMINI_FOR_CONVERSATION=True,\
GEMINI_MODEL_NAME=gemini-2.0-flash-001,\
VISION_API_ENABLED=True,\
PUBSUB_TOPIC_PREFIX=pawconnect-prod,\
FIRESTORE_COLLECTION_USERS=users,\
FIRESTORE_COLLECTION_APPLICATIONS=applications" \
  --set-secrets "\
RESCUEGROUPS_API_KEY=rescuegroups-api-key:latest,\
REDIS_PASSWORD=redis-password:latest,\
DIALOGFLOW_AGENT_ID=dialogflow-agent-id:latest" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300s \
  --max-instances 20 \
  --min-instances 1 \
  --concurrency 80 \
  --cpu-throttling \
  --service-account $SERVICE_ACCOUNT

# Get service URL
export SERVICE_URL=$(gcloud run services describe pawconnect-main-agent \
  --region $REGION --format='value(status.url)')

echo "PawConnect Main Agent deployed at: $SERVICE_URL"
```

### Step 3: Verify Deployment

```bash
# Test health endpoint
curl $SERVICE_URL/health

# Expected response:
# {"status":"healthy","service":"pawconnect-main-agent"}
```

---

## Configure Dialogflow CX

Dialogflow CX provides the conversational interface for PawConnect AI.

### Step 1: Create Dialogflow CX Agent

1. Navigate to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx)
2. Click **Create Agent**
3. Configure:
   - **Display Name**: `PawConnect AI`
   - **Location**: `us-central1` (same as your GCP region)
   - **Time Zone**: Select your timezone
4. Click **Create**

### Step 2: Configure Dialogflow CX Agent

PawConnect provides a single, simple script to configure your entire Dialogflow CX agent.

**What You'll Create:**
- 7 intents (search pets, recommendations, scheduling, applications, etc.)
- 4 custom entity types (housing type, pet species, pet size, pet age group)
- Pages and flows with proper transition routes
- Webhook integration
- Training phrases with parameter annotations
- Welcome message

**Simple Setup (ONE Command):**

```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login

# 2. Install Python dependencies (if not already installed)
pip install google-cloud-dialogflow-cx loguru

# 3. Run the setup script (auto-detects agent ID)
python deployment/dialogflow/setup_agent.py \
  --project-id $PROJECT_ID

# Optional: Include webhook URL if already deployed
python deployment/dialogflow/setup_agent.py \
  --project-id $PROJECT_ID \
  --webhook-url https://your-webhook-url/webhook
```

**What this creates:**
- ✅ 4 entity types (housing_type, pet_species, pet_size, pet_age_group)
- ✅ 7 intents with **parameter-annotated** training phrases
- ✅ Webhook configuration (if URL provided)
- ✅ Pages with form parameters
- ✅ START_PAGE with welcome message
- ✅ Transition routes with **parameter presets**
- ✅ Flow restart logic to prevent conversation loops
- ✅ **CRITICAL:** Parameter extraction from initial user utterance

**Why this is critical:**
- Without parameter extraction, users get frustrated by repetitive questions
- Example: User says "I want to adopt a dog in Seattle" but agent asks "Where do you live?"
- The script ensures location and species are extracted automatically from the first message

**Verify Configuration:**

```bash
# Run verification script to confirm everything is configured correctly
python deployment/dialogflow/verify_fixes.py \
  --project-id $PROJECT_ID \
  --agent-id YOUR_AGENT_ID
```

**Manual Option:**

If you prefer full control, follow the step-by-step guide in **[deployment/dialogflow/README.md](../deployment/dialogflow/README.md)**

**📖 Additional Resources:**
- **[deployment/dialogflow/README.md](../deployment/dialogflow/README.md)** - Detailed setup guide
- **[deployment/dialogflow/agent-config.yaml](../deployment/dialogflow/agent-config.yaml)** - Reference configuration
- **[deployment/dialogflow/CONVERSATION_FLOW.md](../deployment/dialogflow/CONVERSATION_FLOW.md)** - Visual conversation flows

### Step 3: Configure Webhook (After Deployment)

You'll create the webhook configuration after deploying your Cloud Run service (see "Deploy Dialogflow Webhook" section below).

**Create Webhook (do this after deploying webhook service):**

1. In Dialogflow CX Console, go to **Manage** > **Webhooks**
2. Click **"Create"**
3. Configure:
   - **Display Name**: `PawConnect Webhook`
   - **Webhook URL**: `https://YOUR-CLOUD-RUN-WEBHOOK-URL/webhook`
   - **Timeout**: `30s`
4. Click **Save**

**Note:** You'll get your actual webhook URL in the "Deploy Dialogflow Webhook" section below. Come back to complete this step after deployment.

### Step 4: Get Dialogflow Agent ID

```bash
# List Dialogflow agents using REST API (gcloud dialogflow commands don't exist)
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://$REGION-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/$REGION/agents" | grep -o '"name":"[^"]*' | head -1

# Or view in browser to get the agent ID:
# Windows: start https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents
# Mac/Linux: open https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents

# Save agent ID to Secret Manager (extract just the agent ID from the full path)
# Format: projects/PROJECT_ID/locations/REGION/agents/AGENT_ID
echo -n "your_agent_id_from_above" | \
  gcloud secrets versions add dialogflow-agent-id --data-file=-
```

See [WEBHOOK_SETUP.md](./WEBHOOK_SETUP.md) for complete Dialogflow configuration instructions.

---

## Deploy Dialogflow Webhook

Deploy the webhook service that handles Dialogflow fulfillment requests.

### Step 1: Deploy Webhook to Cloud Run

```bash
# Use the deployment script
chmod +x deployment/deploy-webhook.sh

# Set required environment variables
export RESCUEGROUPS_API_KEY="your_rescuegroups_api_key"

# Run deployment
./deployment/deploy-webhook.sh

# Or deploy manually:
gcloud run deploy pawconnect-dialogflow-webhook \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --vpc-connector pawconnect-connector \
  --set-env-vars "\
GCP_PROJECT_ID=$PROJECT_ID,\
GCP_REGION=$REGION,\
ENVIRONMENT=production,\
TESTING_MODE=False,\
MOCK_APIS=False,\
REDIS_HOST=$REDIS_HOST" \
  --set-secrets "\
RESCUEGROUPS_API_KEY=rescuegroups-api-key:latest,\
REDIS_PASSWORD=redis-password:latest" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60s \
  --max-instances 10 \
  --min-instances 0

# Get webhook URL
export WEBHOOK_URL=$(gcloud run services describe pawconnect-dialogflow-webhook \
  --region $REGION --format='value(status.url)')

echo "Dialogflow Webhook URL: $WEBHOOK_URL/webhook"
```

### Step 2: Update Dialogflow Webhook Configuration

1. Return to Dialogflow CX Console
2. Go to **Manage** > **Webhooks**
3. Edit **PawConnect Webhook**
4. Set **Webhook URL** to: `$WEBHOOK_URL/webhook`
5. Click **Save**

### Step 3: Test Webhook Integration

```bash
# Test webhook endpoint directly
curl -X POST $WEBHOOK_URL/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "detectIntentResponseId": "test-123",
    "sessionInfo": {
      "parameters": {}
    },
    "fulfillmentInfo": {
      "tag": "validate-pet-id"
    },
    "pageInfo": {
      "displayName": "Pet Details"
    },
    "text": "test",
    "languageCode": "en"
  }'
```

---

## Configure Cloud Vision API

Cloud Vision API is used by the Vision Agent for pet image analysis.

### Step 1: Verify API is Enabled

```bash
# Already enabled in earlier step, but verify:
gcloud services list --enabled | grep vision.googleapis.com
```

### Step 2: Grant Vision API Permissions

```bash
# Grant Cloud Vision permissions to service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudvision.user"
```

### Step 3: (Optional) Create Cloud Storage Bucket for Images

```bash
# Create bucket for storing pet images
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-pet-images

# Set bucket lifecycle (delete images after 90 days)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://${PROJECT_ID}-pet-images

# Grant storage permissions
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectCreator \
  gs://${PROJECT_ID}-pet-images
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectViewer \
  gs://${PROJECT_ID}-pet-images
```

---

## Setup Monitoring & Logging

Configure comprehensive monitoring and alerting for production.

### Step 1: Create Uptime Check

```bash
# Create uptime check for main agent
gcloud monitoring uptime-checks create http pawconnect-uptime \
  --display-name="PawConnect Main Agent Uptime" \
  --url="${SERVICE_URL}/health" \
  --request-method=GET \
  --check-interval=60s

# List uptime checks
gcloud monitoring uptime-checks list
```

### Step 2: Create Alert Policies

```bash
# Create notification channel (email)
gcloud alpha monitoring channels create \
  --display-name="PawConnect Alerts" \
  --type=email \
  --channel-labels=email_address=your-email@example.com

# Get channel ID
export CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --filter="displayName='PawConnect Alerts'" \
  --format="value(name)")

# Create alert policies
# 1. High Error Rate Alert
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="PawConnect High Error Rate" \
  --condition-display-name="Error Rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s

# 2. High Latency Alert
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="PawConnect High Latency" \
  --condition-display-name="P95 Latency > 2s" \
  --condition-threshold-value=2000 \
  --condition-threshold-duration=300s

# 3. High Memory Usage Alert
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="PawConnect High Memory Usage" \
  --condition-display-name="Memory > 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s

# List alert policies
gcloud alpha monitoring policies list
```

### Step 3: Configure Log-Based Metrics

```bash
# Create log-based metric for application errors
gcloud logging metrics create application_errors \
  --description="Count of application errors" \
  --log-filter='resource.type="cloud_run_revision"
    resource.labels.service_name="pawconnect-main-agent"
    severity>=ERROR'

# Create log-based metric for API failures
gcloud logging metrics create api_failures \
  --description="Count of external API failures" \
  --log-filter='resource.type="cloud_run_revision"
    resource.labels.service_name="pawconnect-main-agent"
    jsonPayload.message=~"API.*failed"'

# List metrics
gcloud logging metrics list
```

### Step 4: Create Dashboard

```bash
# Create custom monitoring dashboard (use Cloud Console for visual configuration)
# Navigate to: https://console.cloud.google.com/monitoring/dashboards
# Click "Create Dashboard" and add the following widgets:
# - Request Count (Cloud Run)
# - Request Latency (Cloud Run)
# - Memory Utilization (Cloud Run)
# - Error Rate (Log-based metric)
# - Firestore Operations
# - Redis Cache Hit Rate
# - Pub/Sub Message Count
```

### Step 5: View Logs

```bash
# Stream logs from Cloud Run
gcloud run services logs tail pawconnect-main-agent --region $REGION

# Query specific logs
gcloud logging read \
  "resource.type=cloud_run_revision AND \
   resource.labels.service_name=pawconnect-main-agent AND \
   severity>=ERROR" \
  --limit 50 \
  --format json

# Query by time range
gcloud logging read \
  "resource.type=cloud_run_revision AND \
   resource.labels.service_name=pawconnect-main-agent" \
  --freshness=1h

# Export logs to BigQuery for analysis
gcloud logging sinks create pawconnect-logs-sink \
  bigquery.googleapis.com/projects/$PROJECT_ID/datasets/pawconnect_logs \
  --log-filter='resource.type="cloud_run_revision" AND
                resource.labels.service_name="pawconnect-main-agent"'
```

---

## Testing Production Deployment

Comprehensive testing procedures for production deployment.

### Step 1: Health Checks

```bash
# Test main agent health
curl $SERVICE_URL/health

# Test webhook health
curl $WEBHOOK_URL/health

# Expected responses:
# {"status":"healthy","service":"..."}
```

### Step 2: API Integration Tests

```bash
# Test RescueGroups API integration (production)
curl -X POST $SERVICE_URL/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "pet_type": "dog",
    "location": "Seattle, WA",
    "distance": 50,
    "limit": 10
  }'

# Test recommendations endpoint
curl -X POST $SERVICE_URL/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "preferences": {
      "pet_type": "cat",
      "size": "medium",
      "age": "adult"
    }
  }'
```

### Step 3: Dialogflow Integration Test

1. Open Dialogflow CX Console
2. Click **Test Agent**
3. Test conversations:
   - "I want to adopt a dog"
   - "Show me cats near Seattle"
   - "Tell me about pet ID 12345"
4. Verify webhook calls are successful in logs

### Step 4: Vision API Test

```bash
# Test vision analysis endpoint (if exposed)
curl -X POST $SERVICE_URL/api/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/pet-image.jpg"
  }'
```

### Step 5: End-to-End Test

```bash
# Run comprehensive integration tests
cd PawConnect
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Set production test environment variables
export GCP_PROJECT_ID=$PROJECT_ID
export SERVICE_URL=$SERVICE_URL
export TESTING_MODE=False
export MOCK_APIS=False

# Run tests
python -m pytest tests/integration/ -v --service-url=$SERVICE_URL

# Run smoke tests
python -m pytest tests/integration/test_smoke.py -v
```

### Step 6: Load Testing

```bash
# Install Apache Bench (if not installed)
# Ubuntu/Debian: apt-get install apache2-utils
# macOS: brew install apache2-utils

# Create test payload
cat > search_payload.json <<EOF
{
  "pet_type": "dog",
  "location": "Seattle, WA",
  "distance": 50
}
EOF

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -T application/json -p search_payload.json \
  $SERVICE_URL/api/search

# Monitor Cloud Run metrics during load test
gcloud run services describe pawconnect-main-agent \
  --region $REGION \
  --format="table(status.url,status.latestCreatedRevisionName)"
```

---

## CI/CD Pipeline

Automate deployments using Cloud Build triggers.

### Option 1: GitHub Integration

```bash
# Connect GitHub repository to Cloud Build
gcloud builds connections create github \
  --region=$REGION \
  pawconnect-github-connection

# Create trigger for main branch
gcloud builds triggers create github \
  --name=pawconnect-production-deploy \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --repo-name=PawConnect \
  --branch-pattern="^main$" \
  --build-config=deployment/cloudbuild.yaml \
  --substitutions=_REGION=$REGION

# List triggers
gcloud builds triggers list
```

### Option 2: GitHub Actions

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        env:
          TESTING_MODE: "true"
          MOCK_APIS: "true"
        run: |
          pytest tests/ --cov=pawconnect_ai --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and Deploy
        run: |
          gcloud builds submit \
            --config deployment/cloudbuild.yaml \
            --substitutions=_REGION=${{ secrets.GCP_REGION }}

      - name: Run Integration Tests
        run: |
          SERVICE_URL=$(gcloud run services describe pawconnect-main-agent \
            --region ${{ secrets.GCP_REGION }} \
            --format='value(status.url)')
          pip install pytest pytest-asyncio
          pytest tests/integration/ --service-url=$SERVICE_URL
```

### Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `GCP_SA_KEY`: Service account JSON key with permissions
- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_REGION`: Your deployment region

---

## Scaling & Performance

Optimize PawConnect AI for production load.

### Step 1: Configure Auto-Scaling

```bash
# Update Cloud Run scaling parameters
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --min-instances 2 \
  --max-instances 50 \
  --concurrency 100 \
  --cpu-boost \
  --no-cpu-throttling

# Update webhook scaling
gcloud run services update pawconnect-dialogflow-webhook \
  --region $REGION \
  --min-instances 1 \
  --max-instances 20 \
  --concurrency 80
```

### Step 2: Optimize Redis for Performance

```bash
# Upgrade to Standard tier for high availability (if needed)
gcloud redis instances update pawconnect-redis \
  --region=$REGION \
  --tier=STANDARD_HA \
  --replica-count=1

# Increase memory (if needed)
gcloud redis instances update pawconnect-redis \
  --region=$REGION \
  --size=5
```

### Step 3: Configure CDN (for static assets)

```bash
# Create Cloud Storage bucket for static assets
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-static

# Enable Cloud CDN
gcloud compute backend-buckets create pawconnect-static-backend \
  --gcs-bucket-name=${PROJECT_ID}-static \
  --enable-cdn

# Configure CDN cache settings
gcloud compute backend-buckets update pawconnect-static-backend \
  --cache-mode=CACHE_ALL_STATIC
```

### Step 4: Performance Monitoring

```bash
# View Cloud Run metrics
gcloud run services describe pawconnect-main-agent \
  --region $REGION \
  --format="yaml(status.traffic,spec.template.spec.containers[0].resources)"

# Monitor request latency
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --format=table

# Monitor instance count
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/container/instance_count"' \
  --format=table
```

---

## Security Best Practices

Secure your production deployment.

### Step 1: Enable Cloud Armor (DDoS Protection)

```bash
# Create security policy
gcloud compute security-policies create pawconnect-security-policy \
  --description="Security policy for PawConnect"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=pawconnect-security-policy \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=600

# Apply to load balancer (if using)
```

### Step 2: Configure IAM Roles

```bash
# Create custom service account with minimal permissions
gcloud iam service-accounts create pawconnect-prod \
  --display-name="PawConnect Production Service Account"

export PAWCONNECT_SA="pawconnect-prod@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant only necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PAWCONNECT_SA}" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PAWCONNECT_SA}" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PAWCONNECT_SA}" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PAWCONNECT_SA}" \
  --role="roles/cloudvision.user"

# Update Cloud Run to use custom service account
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --service-account $PAWCONNECT_SA
```

### Step 3: Enable VPC Service Controls

```bash
# Create access policy (organization-level)
gcloud access-context-manager policies create \
  --title="PawConnect Access Policy" \
  --organization=YOUR_ORG_ID

# Create service perimeter
gcloud access-context-manager perimeters create pawconnect_perimeter \
  --title="PawConnect Perimeter" \
  --resources=projects/$PROJECT_NUMBER \
  --restricted-services=storage.googleapis.com,firestore.googleapis.com
```

### Step 4: Rotate Secrets Regularly

```bash
# Create script for secret rotation
cat > rotate_secrets.sh <<'EOF'
#!/bin/bash
# Rotate RescueGroups API key
echo -n "new_api_key" | gcloud secrets versions add rescuegroups-api-key --data-file=-

# Rotate Redis password
NEW_PASSWORD=$(openssl rand -base64 32)
echo -n "$NEW_PASSWORD" | gcloud secrets versions add redis-password --data-file=-

# Update Redis instance with new password
gcloud redis instances update pawconnect-redis --update-auth-string=$NEW_PASSWORD --region=$REGION

# Restart Cloud Run services to pick up new secrets
gcloud run services update pawconnect-main-agent --region=$REGION
gcloud run services update pawconnect-dialogflow-webhook --region=$REGION

echo "Secrets rotated successfully"
EOF

chmod +x rotate_secrets.sh

# Schedule monthly rotation with Cloud Scheduler
gcloud scheduler jobs create http pawconnect-rotate-secrets \
  --location=$REGION \
  --schedule="0 0 1 * *" \
  --uri="https://your-secret-rotation-endpoint.com/rotate" \
  --http-method=POST
```

### Step 5: Enable Audit Logging

```bash
# Enable audit logs for sensitive operations
gcloud projects get-iam-policy $PROJECT_ID \
  --format=yaml > policy.yaml

# Edit policy.yaml to add audit logs, then apply:
gcloud projects set-iam-policy $PROJECT_ID policy.yaml

# View audit logs
gcloud logging read \
  "protoPayload.serviceName='run.googleapis.com' AND \
   protoPayload.methodName:'update'" \
  --limit 50
```

---

## Troubleshooting

Common issues and solutions for production deployment.

### Issue: gcloud dialogflow Command Not Found

**Symptoms**: `ERROR: (gcloud) Invalid choice: 'dialogflow'`

**Solution**:
The `gcloud dialogflow` commands don't exist in the gcloud CLI. Use the REST API instead:

```bash
# First, set quota project (one-time setup)
gcloud auth application-default set-quota-project $PROJECT_ID

# List Dialogflow agents using REST API with regional endpoint
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://$REGION-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/$REGION/agents"

# Alternative: Use the Dialogflow CX Console
# Windows: start https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents
# Mac/Linux: open https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents
```

**Note:** Always use the regional endpoint format: `https://$REGION-dialogflow.googleapis.com` (not the global endpoint).

### Issue: Container Fails to Start

**Symptoms**: Cloud Run service shows "Revision failed"

**Solution**:
```bash
# Check logs
gcloud run services logs tail pawconnect-main-agent --region $REGION

# Common causes:
# 1. Missing environment variables
# 2. Invalid secrets
# 3. VPC connector issues
# 4. Application code errors

# Test locally with production settings
docker build -t pawconnect-test -f deployment/Dockerfile .
docker run -p 8080:8080 --env-file .env pawconnect-test
```

### Issue: High Latency

**Symptoms**: Requests taking >2 seconds

**Solution**:
```bash
# Check Cloud Run metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"'

# Common causes:
# 1. Redis cache misses - check REDIS_HOST
# 2. Cold starts - increase min-instances
# 3. External API slowness - check RescueGroups API status
# 4. Insufficient resources - increase CPU/memory

# Increase resources
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --memory 4Gi \
  --cpu 4 \
  --min-instances 3
```

### Issue: Dialogflow Webhook Timeouts

**Symptoms**: Dialogflow shows "Webhook timeout"

**Solution**:
```bash
# Increase webhook timeout
gcloud run services update pawconnect-dialogflow-webhook \
  --region $REGION \
  --timeout 60s

# Check webhook logs
gcloud run services logs tail pawconnect-dialogflow-webhook --region $REGION

# Verify webhook URL in Dialogflow
# Ensure URL ends with /webhook
```

### Issue: Firestore Permission Errors

**Symptoms**: "403 Forbidden" when accessing Firestore

**Solution**:
```bash
# Verify service account has Firestore permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}"

# Grant missing permission
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/datastore.user"
```

### Issue: Redis Connection Failures

**Symptoms**: "Connection refused" or "Connection timeout" to Redis

**Solution**:
```bash
# Verify VPC connector is attached
gcloud run services describe pawconnect-main-agent \
  --region $REGION \
  --format="value(spec.template.metadata.annotations['run.googleapis.com/vpc-access-connector'])"

# Check Redis instance status
gcloud redis instances describe pawconnect-redis --region=$REGION

# Test connectivity from Cloud Shell (in same VPC)
sudo apt-get install redis-tools
redis-cli -h $REDIS_HOST -a $REDIS_AUTH ping
```

### Issue: API Rate Limiting

**Symptoms**: "429 Too Many Requests" from RescueGroups

**Solution**:
```bash
# Check current rate limit settings
grep API_RATE_LIMIT .env

# Adjust rate limiter in application
# Update environment variable
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --update-env-vars API_RATE_LIMIT=50

# Implement exponential backoff in code (already implemented)
```

---

## Cost Optimization

Strategies to optimize GCP costs in production.

### Step 1: Analyze Current Costs

```bash
# View current billing
gcloud billing accounts list
gcloud billing projects describe $PROJECT_ID

# Export billing data to BigQuery
gcloud billing accounts get-iam-policy BILLING_ACCOUNT_ID

# View cost breakdown in Cloud Console:
# https://console.cloud.google.com/billing
```

### Step 2: Optimize Cloud Run

```bash
# Use CPU throttling to reduce costs when idle
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --cpu-throttling

# Reduce min-instances during low-traffic hours
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --min-instances 1

# Set appropriate memory (don't over-provision)
gcloud run services update pawconnect-main-agent \
  --region $REGION \
  --memory 1Gi  # Adjust based on actual usage
```

### Step 3: Optimize Storage

```bash
# Set lifecycle policies for Cloud Storage
gsutil lifecycle set lifecycle.json gs://${PROJECT_ID}-pet-images

# Delete old logs
gcloud logging sinks delete old-logs-sink --quiet

# Configure log retention
gcloud logging buckets update _Default \
  --location=global \
  --retention-days=30
```

### Step 4: Optimize Memorystore

```bash
# Use BASIC tier instead of STANDARD for non-critical caches
gcloud redis instances update pawconnect-redis \
  --region=$REGION \
  --tier=BASIC

# Right-size memory allocation
gcloud redis instances update pawconnect-redis \
  --region=$REGION \
  --size=1  # GB, adjust based on usage
```

### Step 5: Set Budget Alerts

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="PawConnect Monthly Budget" \
  --budget-amount=100USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100

# List budgets
gcloud billing budgets list --billing-account=BILLING_ACCOUNT_ID
```

### Cost Optimization Checklist

- [ ] Use Cloud Run CPU throttling
- [ ] Set appropriate min/max instances
- [ ] Configure log retention policies
- [ ] Use BASIC tier for Memorystore
- [ ] Set Cloud Storage lifecycle policies
- [ ] Configure budget alerts
- [ ] Review and delete unused resources
- [ ] Use committed use discounts for predictable workloads
- [ ] Enable auto-scaling to scale to zero when idle (for non-critical services)

---

## Production Deployment Checklist

Before going live with PawConnect AI, verify:

### Infrastructure
- [ ] GCP project created with billing enabled
- [ ] All required APIs enabled
- [ ] VPC network and subnet configured
- [ ] VPC Access Connector created
- [ ] Firestore database provisioned
- [ ] Memorystore (Redis) instance created
- [ ] Pub/Sub topics and subscriptions created
- [ ] Cloud Storage buckets created (if using images)

### Security
- [ ] Secrets stored in Secret Manager
- [ ] Service account with minimal permissions created
- [ ] IAM roles properly configured
- [ ] VPC Service Controls enabled (optional)
- [ ] Cloud Armor configured (optional)
- [ ] Audit logging enabled

### Application
- [ ] Environment variables set to production values
- [ ] `TESTING_MODE=False` and `MOCK_APIS=False`
- [ ] RescueGroups API key configured (production)
- [ ] Dialogflow CX agent created and configured
- [ ] Webhook deployed and connected to Dialogflow
- [ ] Cloud Run services deployed successfully
- [ ] Health checks passing

### Monitoring
- [ ] Uptime checks configured
- [ ] Alert policies created
- [ ] Notification channels configured
- [ ] Log-based metrics created
- [ ] Monitoring dashboard created
- [ ] Log export to BigQuery configured (optional)

### Testing
- [ ] Health endpoints responding correctly
- [ ] API integration tests passing
- [ ] Dialogflow conversation tests successful
- [ ] End-to-end tests passing
- [ ] Load testing completed

### Documentation
- [ ] Production environment variables documented
- [ ] Runbook created for common issues
- [ ] Team trained on monitoring and alerts
- [ ] Incident response plan documented

---

## Additional Resources

### Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Cloud Vision API Documentation](https://cloud.google.com/vision/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

### PawConnect Specific Docs
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [WEBHOOK_SETUP.md](./WEBHOOK_SETUP.md) - Dialogflow webhook configuration
- [API.md](./API.md) - API reference and endpoints
- [README.md](../README.md) - Project overview and local development

### Support
- For PawConnect issues: [GitHub Issues](https://github.com/Lwhieldon/PawConnect/issues)
- For GCP issues: [Google Cloud Support](https://cloud.google.com/support)
- For RescueGroups API: [RescueGroups Support](https://rescuegroups.org/services/)

---

## Summary

You have now deployed PawConnect AI to Google Cloud Platform in a production capacity with:

✅ **Full Production Mode**: `TESTING_MODE=False`, `MOCK_APIS=False`
✅ **All GCP Services**: Cloud Run, Dialogflow CX, Vertex AI, Cloud Vision, Firestore, Pub/Sub, Memorystore
✅ **Security**: Secrets Manager, IAM, audit logging
✅ **Monitoring**: Uptime checks, alerts, logging, dashboards
✅ **Scalability**: Auto-scaling, load balancing, caching
✅ **CI/CD**: Automated deployments with Cloud Build or GitHub Actions

Your PawConnect AI system is now ready to help connect pets with loving homes! 🐾

For questions or issues, refer to the troubleshooting section or create an issue in the GitHub repository.
