# Quick Start: Dialogflow CX Python Automation

This guide helps you quickly set up your PawConnect Dialogflow CX agent using Python automation.

## Prerequisites

1. **Create Agent in Console First**
   - Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx)
   - Create a new agent named "PawConnect AI"
   - Note your project ID and region

2. **Authenticate with GCP**
   ```bash
   gcloud auth application-default login
   ```

3. **Install Python Dependencies**
   ```bash
   pip install google-cloud-dialogflow-cx loguru
   ```

## Get Your Agent ID

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Get agent ID using REST API
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://$REGION-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/$REGION/agents"

# Look for the "name" field in the response
# Format: projects/{PROJECT}/locations/{REGION}/agents/{AGENT_ID}
# Save just the AGENT_ID part (the UUID at the end)
```

## Quick Setup Options

### Option 1: Complete Automation (Recommended)

Creates everything: entity types, intents, pages, flows, and webhooks.

```bash
# Set variables
export PROJECT_ID="your-project-id"
export AGENT_ID="your-agent-id"
export WEBHOOK_URL="https://your-cloud-run-url/webhook"

# Run complete automation
python deployment/dialogflow/setup_complete_automation.py \
  --project-id $PROJECT_ID \
  --agent-id $AGENT_ID \
  --webhook-url $WEBHOOK_URL

# Add transition routes (optional)
python deployment/dialogflow/add_transition_routes.py \
  --project-id $PROJECT_ID \
  --agent-id $AGENT_ID
```

**Creates:**
- 4 entity types
- 7 intents
- 1 webhook
- 6 pages with form parameters
- Updated START_PAGE

### Option 2: Pages & Flows Only

Use this if you already created entity types and intents manually or with the bash script.

```bash
python deployment/dialogflow/setup_dialogflow_automation.py \
  --project-id $PROJECT_ID \
  --agent-id $AGENT_ID \
  --webhook-url $WEBHOOK_URL
```

### Option 3: Transition Routes Only

Use this if you already have pages but need to connect them.

```bash
python deployment/dialogflow/add_transition_routes.py \
  --project-id $PROJECT_ID \
  --agent-id $AGENT_ID
```

## Verification

After running the automation:

1. **Open Dialogflow Console**
   ```bash
   # Windows
   start https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents/$AGENT_ID

   # Mac/Linux
   open https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/$REGION/agents/$AGENT_ID
   ```

2. **Verify Components**
   - Go to **Manage** > **Entity Types** - Should see 4 entity types
   - Go to **Manage** > **Intents** - Should see 7 intents
   - Go to **Manage** > **Webhooks** - Should see PawConnect Webhook
   - Go to **Build** > **Flows** > **Default Start Flow** - Should see 6 pages

3. **Test in Simulator**
   - Click **Test Agent** in top-right
   - Try: "I want to search for a dog"
   - Verify the agent responds appropriately

## Common Issues

### Issue: Agent not found

**Solution:**
```bash
# Verify agent exists
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://$REGION-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/$REGION/agents"
```

### Issue: Permission denied

**Solution:**
```bash
# Ensure you have Dialogflow API Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/dialogflow.admin"
```

### Issue: ModuleNotFoundError

**Solution:**
```bash
# Install required packages
pip install -r requirements.txt
```

### Issue: Already exists warnings

**Solution:** This is normal! The scripts are idempotent and will skip existing resources.

## What Gets Created

### Entity Types
1. **pet_species** - dog, cat, rabbit, bird, small_animal
2. **pet_size** - small, medium, large
3. **pet_age_group** - baby, young, adult, senior
4. **housing_type** - own, rent, live_with_family

### Intents
1. **intent.search_pets** - Search for available pets
2. **intent.get_recommendations** - Get personalized recommendations
3. **intent.schedule_visit** - Schedule a shelter visit
4. **intent.adoption_application** - Start adoption process
5. **intent.foster_application** - Start fostering process
6. **intent.search_more** - Search again
7. **intent.ask_question** - Ask questions about pets

### Pages
1. **START_PAGE** - Welcome message
2. **Pet Search** - Collect search criteria
3. **Pet Details** - Validate pet ID and show details
4. **Get Recommendations** - Collect user preferences
5. **Schedule Visit** - Collect visit information
6. **Adoption Application** - Collect adoption info
7. **Foster Application** - Collect fostering info

### Webhook
- **PawConnect Webhook** - Handles all fulfillment requests
- Tags: search-pets, validate-pet-id, get-recommendations, schedule-visit, submit-application

## Next Steps

1. **Test Your Agent**
   - Use the Dialogflow CX Simulator
   - Try various conversation flows
   - Verify webhook responses

2. **Fine-tune**
   - Adjust training phrases in Console
   - Modify page parameters as needed
   - Test edge cases

3. **Deploy to Production**
   - Update webhook URL to production Cloud Run service
   - Enable logging and monitoring
   - Set up CI/CD pipeline

## Resources

- [Full Setup Guide](README.md) - Detailed documentation
- [Deployment Guide](../../docs/DEPLOYMENT.md) - Production deployment
- [Python Client Reference](https://cloud.google.com/python/docs/reference/dialogflow-cx/latest) - API documentation

## Support

If you encounter issues:
1. Check the [README.md](README.md) troubleshooting section
2. Review the [DEPLOYMENT.md](../../docs/DEPLOYMENT.md) guide
3. Check Dialogflow CX logs in GCP Console
