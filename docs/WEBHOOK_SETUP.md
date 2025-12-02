# Dialogflow CX Webhook Setup - Pet ID Validation

This guide explains how to set up webhook fulfillment for dynamic pet ID validation using the RescueGroups API.

## Overview

The webhook allows Dialogflow CX to:
- **Validate pet IDs dynamically** from user input
- **Fetch real-time pet details** from RescueGroups API
- **Store pet information** in session parameters for later use
- **Handle all PawConnect intents** (search, recommendations, scheduling)

## Architecture

```
User → Dialogflow CX → Webhook (Cloud Run) → RescueGroups API
                             ↓
                    PawConnect AI Agent
```

## Quick Setup (20 minutes)

### Step 1: Deploy the Webhook (10 min)

**Note:** No Docker installation required! The deployment uses Google Cloud Build.

#### Option A: Deploy to Google Cloud Run (Recommended)

```bash
# 1. Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export RESCUEGROUPS_API_KEY="your-api-key"

# 2. Authenticate with Google Cloud
gcloud auth login
gcloud config set project ${GCP_PROJECT_ID}

# 3. Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 4. Run deployment script (builds in the cloud - no Docker needed!)
chmod +x deployment/deploy-webhook.sh
./deployment/deploy-webhook.sh
```

The script will output your webhook URL. **Save this URL** - you'll need it for Dialogflow configuration.

#### Option B: Run Locally for Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables in .env file
RESCUEGROUPS_API_KEY=your_api_key_here
RESCUEGROUPS_BASE_URL=https://api.rescuegroups.org/v5

# 3. Run the webhook server
python -m pawconnect_ai.dialogflow_webhook

# Server will run at http://localhost:8080
```

**For local testing with Dialogflow:**
- Use [ngrok](https://ngrok.com/) to expose your local server:
  ```bash
  ngrok http 8080
  ```
- Use the ngrok HTTPS URL as your webhook URL

### Step 2: Configure Dialogflow CX Webhook (5 min)

1. **Go to Dialogflow CX Console**: https://dialogflow.cloud.google.com/cx
2. **Select your PawConnect agent**
3. **Navigate to**: Manage → Webhooks
4. **Click "Create"**

Configure the webhook:
- **Display name**: `PawConnect Webhook`
- **Webhook URL**: `https://your-service-url/webhook` (from deployment output)
- **Timeout**: 30 seconds
- **Authentication**: None (for now - see Security section below)

5. **Click "Save"**

### Step 3: Update Your Intents (10 min)

Now modify your `schedule_visit` intent to use dynamic pet ID validation:

#### A. Update Training Phrases

Instead of manual entity annotation, use **natural training phrases**:

```
I want to schedule a visit for pet 12345
Can I meet pet abc789 tomorrow at 2pm?
Schedule a visit to see pet XYZ123
I'd like to visit pet 456 on Friday
Book an appointment for pet #789
```

#### B. Configure Intent to Use Webhook

1. Go to your `schedule_visit` intent
2. Scroll to **Fulfillment** section
3. Enable **"Call webhook"**
4. Select webhook: `PawConnect Webhook`
5. Add webhook tag: `validate-pet-id`

#### C. Create Pet ID Entity (Simple)

For basic pet ID extraction:

1. **Manage → Entity Types → Create**
2. **Display name**: `pet_id`
3. **Kind**: `Regexp`
4. **Regexp entities**:
   ```
   [A-Za-z0-9]+
   ```
   This matches alphanumeric pet IDs like "abc123", "12345", "PET789"

5. **Annotate in training phrases**:
   - Highlight the ID in "I want to visit pet **12345**"
   - Select `@pet_id` entity
   - Parameter name: `pet_id`

## How It Works

### Pet ID Validation Flow

1. **User says**: "I want to schedule a visit for pet 12345"
2. **Dialogflow extracts**: `pet_id = "12345"`
3. **Webhook is called** with tag `validate-pet-id`
4. **Webhook validates** by calling RescueGroups API:
   ```python
   result = await rescuegroups_client.get_pet("12345")
   ```
5. **If found**:
   - Returns pet details (name, breed, age, shelter)
   - Stores info in session parameters
   - Responds: "Great! I found Max, a 2 year old male Labrador..."
6. **If not found**:
   - Returns error message
   - Asks user to check the ID

### Session Parameters Stored

After validation, these parameters are available in the session:

| Parameter | Example Value | Description |
|-----------|---------------|-------------|
| `validated_pet_id` | `"12345"` | Confirmed valid pet ID |
| `pet_name` | `"Max"` | Pet's name |
| `pet_breed` | `"Labrador Retriever"` | Breed |
| `pet_age` | `"2 years"` | Age string |
| `pet_sex` | `"Male"` | Gender |
| `shelter_name` | `"Seattle Animal Shelter"` | Shelter name |
| `shelter_city` | `"Seattle"` | City |
| `shelter_state` | `"WA"` | State |

You can reference these in your Dialogflow responses:
```
Great! Let's schedule a visit for $session.params.pet_name at $session.params.shelter_name.
```

## Available Webhook Tags

Configure different intents to use these tags:

| Tag | Intent | Description |
|-----|--------|-------------|
| `validate-pet-id` | `schedule_visit` | Validate pet ID and fetch details |
| `search-pets` | `search_pets` | Search for available pets |
| `get-recommendations` | `get_recommendations` | Get personalized recommendations |
| `schedule-visit` | `schedule_visit` | Schedule shelter visit |
| `submit-application` | `submit_application` | Submit adoption application |

## Testing

### Test Webhook Health

```bash
curl https://your-service-url/health
# Should return: {"status":"healthy","service":"pawconnect-dialogflow-webhook"}
```

### Test Pet ID Validation

In Dialogflow CX Test Agent panel:

```
You: I want to visit pet 12345
Agent: [Calls webhook to validate]
       [If valid] Great! I found Max, a 2 year old male Labrador Retriever...
       [If invalid] I couldn't find a pet with ID '12345'. Please check the ID...
```

### Test with Real RescueGroups Pet IDs

1. Go to https://rescuegroups.org
2. Find a pet listing
3. Extract the pet ID from the URL
4. Test in Dialogflow with that ID

## Advanced Configuration

### Custom Entity for Pet ID Format

If your pet IDs follow a specific pattern, create a custom regex:

**Example for numeric IDs (5-7 digits)**:
```
\d{5,7}
```

**Example for alphanumeric with prefix**:
```
PET[A-Z0-9]{4,8}
```

### Error Handling

The webhook handles these error cases:

1. **Pet ID not provided**: Asks user for the ID
2. **Pet not found**: Returns friendly error message
3. **API error**: Generic error message, logs details
4. **Timeout**: Dialogflow will show timeout message

### Logging and Monitoring

**View webhook logs:**
```bash
# Cloud Run logs
gcloud logs read --service=pawconnect-webhook --limit=50

# Or in Cloud Console
# Cloud Run → pawconnect-webhook → Logs
```

**Monitor webhook performance:**
- Cloud Run dashboard shows request count, latency, errors
- Set up alerts for error rates > 5%

## Security

### Production Security (Recommended)

1. **Enable authentication**:
   ```bash
   # Deploy with authentication
   gcloud run deploy pawconnect-webhook \
       --no-allow-unauthenticated \
       --region ${GCP_REGION}
   ```

2. **Create service account for Dialogflow**:
   ```bash
   gcloud iam service-accounts create dialogflow-webhook \
       --display-name="Dialogflow Webhook Caller"

   gcloud run services add-iam-policy-binding pawconnect-webhook \
       --member="serviceAccount:dialogflow-webhook@${PROJECT_ID}.iam.gserviceaccount.com" \
       --role="roles/run.invoker"
   ```

3. **Configure Dialogflow to use service account**:
   - In webhook settings, enable **Authentication**
   - Select the service account: `dialogflow-webhook@PROJECT_ID.iam.gserviceaccount.com`

### API Key Protection

**⚠️ CRITICAL SECURITY WARNING:**
- **NEVER** pass API keys as plain text in command line arguments
- **NEVER** hardcode API keys in source code
- **ALWAYS** use Google Cloud Secret Manager for production deployments

**Option 1: Secret Manager (Recommended for Production)**

Step 1 - Create the secret (one-time setup):
```bash
# Create secret from stdin (will prompt for value)
echo -n "your-api-key" | gcloud secrets create rescuegroups-api-key --data-file=-

# Or create from file
gcloud secrets create rescuegroups-api-key --data-file=path/to/api-key.txt
```

Step 2 - Grant access to Cloud Run (one-time setup):
```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding rescuegroups-api-key \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

Step 3 - Deploy webhook with secret:
```bash
# Deploy with secret mounted as environment variable
gcloud run deploy pawconnect-webhook \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production,TESTING_MODE=False,MOCK_APIS=False,GCP_PROJECT_ID=your-project-id,RESCUEGROUPS_BASE_URL=https://api.rescuegroups.org/v5" \
    --set-secrets="RESCUEGROUPS_API_KEY=rescuegroups-api-key:latest" \
    --timeout=300
```

**Important Notes:**
- The `--set-secrets` flag mounts the secret from Secret Manager as an environment variable
- Format: `ENV_VAR_NAME=secret-name:version` (use `:latest` for most recent version)
- The webhook will now have access to `RESCUEGROUPS_API_KEY` without exposing it in logs
- Secrets are encrypted at rest and in transit

**Option 2: Environment Variables (Local Development Only)**
```bash
# ⚠️ Use this ONLY for local testing, NEVER for production!
# Set in .env file (which is in .gitignore)
RESCUEGROUPS_API_KEY=your-api-key-here

# Run locally
python -m pawconnect_ai.dialogflow_webhook
```

## Troubleshooting

### Common Issues

#### 0. "Pet search service is currently unavailable"
**Symptom**: Webhook returns "I'm sorry, the pet search service is currently unavailable" or similar message

**Cause**: RescueGroups API client is not initialized because the API key is missing from the Cloud Run environment

**Solution**:
1. **Check if secret exists**:
   ```bash
   gcloud secrets list --filter="name:rescuegroups-api-key"
   ```

2. **Verify Cloud Run has access**:
   ```bash
   gcloud run services describe pawconnect-webhook --region us-central1 --format="value(spec.template.spec.containers[0].env)"
   ```
   You should see `RESCUEGROUPS_API_KEY` in the environment variables (not secrets section)

3. **Check startup logs**:
   ```bash
   gcloud run services logs read pawconnect-webhook --region us-central1 --limit 20
   ```
   Look for: `RescueGroups API configured: Yes` (if No, the key is not loaded)

4. **Redeploy with secret**:
   ```bash
   gcloud run deploy pawconnect-webhook \
       --source . \
       --region us-central1 \
       --allow-unauthenticated \
       --set-env-vars="ENVIRONMENT=production,TESTING_MODE=False,MOCK_APIS=False,GCP_PROJECT_ID=your-project-id" \
       --set-secrets="RESCUEGROUPS_API_KEY=rescuegroups-api-key:latest"
   ```

**Important**: Always use `--set-secrets` (not `--set-env-vars`) for sensitive credentials!

#### 1. Webhook timeout
**Symptom**: "Webhook call failed. Error: DEADLINE_EXCEEDED"

**Solution**:
- Increase timeout in Dialogflow webhook settings (max 60s)
- Optimize RescueGroups API calls
- Add caching for frequent queries

#### 2. Pet ID not extracted
**Symptom**: Webhook receives empty `pet_id` parameter

**Solution**:
- Check entity is properly annotated in training phrases
- Add more training phrases with varied formats
- Verify entity type is correctly configured

#### 3. Authentication errors
**Symptom**: 403 Forbidden or 401 Unauthorized

**Solution**:
- Check webhook URL is correct
- Verify service allows unauthenticated calls (for testing)
- Check service account permissions (for production)

#### 4. Pet not found (but should exist)
**Symptom**: Webhook returns "pet not found" for valid ID

**Solution**:
- Check RescueGroups API key is valid
- Verify pet ID format matches RescueGroups format
- Test API directly: `curl -H "Authorization: YOUR_KEY" https://api.rescuegroups.org/v5/public/animals/search`

### Debug Mode

Enable debug logging:

```python
# In dialogflow_webhook.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Then check Cloud Run logs for detailed request/response information.

## Cost Optimization

### Cloud Run Pricing

**Free tier**: 2 million requests/month, 360,000 GB-seconds compute time

**Typical costs** (after free tier):
- Request: $0.40 per million requests
- Compute: $0.00002400 per GB-second
- Memory: $0.00000250 per GB-second

**Example**: 100,000 webhook calls/month
- Requests: ~$0.04
- Compute (1GB, 2s avg): ~$4.80
- **Total: ~$5/month**

### Optimization Tips

1. **Set minimum instances to 0** (cold starts acceptable for most use cases)
2. **Use caching** for frequently accessed pet data
3. **Set max instances** to limit costs: `--max-instances=10`
4. **Monitor usage** with Cloud Monitoring alerts

## Next Steps

Once webhook is working:

1. **Add more webhook tags** for other intents
2. **Implement session entity population** for dynamic pet lists
3. **Add user authentication** for personalized experiences
4. **Set up scheduled data sync** from RescueGroups
5. **Implement caching** to reduce API calls
6. **Add analytics** to track user interactions

## Resources

- [Dialogflow CX Webhook Documentation](https://cloud.google.com/dialogflow/cx/docs/concept/webhook)
- [RescueGroups API v5 Docs](https://userguide.rescuegroups.org/display/APIDG/API+Developer+Guide)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Support

For issues with:
- **Webhook code**: Check `pawconnect_ai/dialogflow_webhook.py`
- **Deployment**: Check `deployment/deploy-webhook.sh` (uses Cloud Build, no Docker required)
- **Container configuration**: Check `Dockerfile` in project root
- **RescueGroups API**: Check `pawconnect_ai/utils/api_clients.py`

---

**Ready to go!** Your webhook is now set up to dynamically validate pet IDs from RescueGroups API.
