# PawConnect Dialogflow CX Setup

Complete guide to setting up your PawConnect Dialogflow CX agent using a single consolidated script.

## Quick Start (3 Steps)

### 1. Create Agent in Console

1. Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx/)
2. Click **"Create Agent"**
3. Configure:
   - **Display Name**: `PawConnect AI Agent`
   - **Location**: `us-central1` (or your preferred region)
   - **Time Zone**: Your timezone
4. Click **"Create"**

### 2. Authenticate & Install Dependencies

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Install Python dependencies
pip install google-cloud-dialogflow-cx loguru python-dotenv
```

### 3. Configure & Run Setup

#### Option A: Using .env File (Recommended)

```bash
# Navigate to project root
cd PawConnect

# Copy .env.example to .env
cp .env.example .env

# Edit .env file with your settings:
#   GCP_PROJECT_ID=your-project-id
#   DIALOGFLOW_AGENT_ID=your-agent-id  # Optional - will auto-detect
#   DIALOGFLOW_LOCATION=us-central1
#   DIALOGFLOW_WEBHOOK_URL=https://your-webhook-url/webhook  # Optional

# Run setup (reads from .env automatically)
python deployment/dialogflow/setup_agent.py
```

#### Option B: Using Command-Line Arguments

```bash
# Simple setup (auto-detects agent ID)
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID

# With all parameters
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID \
    --agent-id YOUR_AGENT_ID \
    --location us-central1 \
    --webhook-url https://your-webhook-url/webhook
```

> **Note:** Command-line arguments override .env values if both are specified.

---

## What Gets Created

The setup script automatically creates:

### Entity Types
- **housing_type**: apartment, house, condo, own, rent, live_with_family
- **pet_species**: dog, cat, rabbit, bird, small_animal
- **pet_size**: small, medium, large, extra_large
- **pet_age_group**: baby, young, adult, senior

### Intents
- **intent.search_pets**: Search for pets with location/species extraction
- **intent.get_recommendations**: Get pet recommendations (includes "Yes", "Sure", etc.)
- **intent.schedule_visit**: Schedule shelter visits
- **intent.adoption_application**: Start adoption process
- **intent.foster_application**: Start foster process
- **intent.search_more**: Search for more pets
- **intent.ask_question**: Ask questions about pets

### Pages & Flows
- **START_PAGE**: Welcome message with transition routes
- **Pet Search**: Collects location and species, calls webhook
- **Get Recommendations**: Collects housing and experience, calls webhook

### Webhook
- **PawConnect Webhook**: Configured with your webhook URL
- Handles tags: `search-pets`, `get-recommendations`

---

## Verify Setup

Check that everything is configured correctly:

```bash
python deployment/dialogflow/verify_fixes.py \
    --project-id YOUR_PROJECT_ID \
    --agent-id YOUR_AGENT_ID
```

You should see:
```
✓ intent.search_pets: PASS
✓ intent.get_recommendations: PASS
✓ housing_type entity: PASS

✓ ALL CHECKS PASSED!
```

---

## Test in Simulator

1. Open [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx/)
2. Click **"Test Agent"** in the top-right corner
3. Try these test phrases:

**Test 1: Parameter Extraction**
```
User: "I want to adopt a dog in Seattle"
Expected: Agent extracts "dog" and "Seattle" automatically
         Should NOT ask "Where do you live?" again
```

**Test 2: Affirmative Response**
```
User: "Yes please show me recommendations"
Expected: Agent recognizes this as intent.get_recommendations
         Transitions to Get Recommendations page
```

**Test 3: Entity Recognition**
```
User: "apartment" (when asked about housing)
Expected: Agent recognizes "apartment" as valid housing_type
         Should NOT trigger sys.no-match-default
```

---

## Troubleshooting

### Agent ID Not Found

Find your agent ID:
```bash
python deployment/dialogflow/list_agents.py \
    --project-id YOUR_PROJECT_ID
```

### Changes Not Showing in Simulator

1. Wait 2-3 minutes for Google's backend to propagate changes
2. Clear browser cache or use incognito window
3. Click "Reset" in the simulator to start fresh conversation

### "sys.no-match-default" Errors

1. Run the setup script again (it's safe to rerun):
   ```bash
   python deployment/dialogflow/setup_agent.py
   ```
2. Wait for propagation (2-3 minutes)
3. Run verify_fixes.py to confirm configuration

### Permission Errors

Ensure you have the correct permissions:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:your-email@example.com" \
    --role="roles/dialogflow.admin"
```

### Still having issues?

1. Check authentication: `gcloud auth application-default login`
2. Verify project: `gcloud config get-value project`
3. Check logs in the script output for specific errors

---

## Updating Configuration

The setup script can be run multiple times safely. It will:
- Update existing resources instead of creating duplicates
- Preserve any custom changes you've made in the console
- Only update training phrases, entities, and routes

To update your agent after making changes to the script:

```bash
python deployment/dialogflow/setup_agent.py
```

---

## Files in This Directory

### Active Scripts
- **`setup_agent.py`** - ⭐ The ONLY script you need for setup
- **`verify_fixes.py`** - Verify configuration is correct
- **`list_agents.py`** - List all agents in your project

### Documentation
- **`README.md`** - This file (complete setup guide)
- **`CONVERSATION_FLOW.md`** - Visual conversation flow diagrams
- **`agent-config.yaml`** - Reference configuration

### Legacy Files (For Reference Only)
The `legacy/` folder contains old scripts that have been consolidated into `setup_agent.py`:

- `setup_dialogflow_automation.py`
- `setup_complete_automation.py`
- `fix_parameter_extraction.py`
- `update_entity_types.py`
- `update_intent_parameters.py`
- `add_transition_routes.py`
- `setup-agent.sh`

These files are kept for reference but are no longer needed. Everything has been consolidated into `setup_agent.py`.

---

## Integration with Webhook

The webhook should handle these tags:
- `search-pets`: Returns pet search results
- `get-recommendations`: Returns personalized pet recommendations

Webhook request format:
```json
{
  "sessionInfo": {
    "parameters": {
      "location": "Seattle",
      "species": "dog",
      "housing": "apartment",
      "experience": "yes"
    }
  },
  "fulfillmentInfo": {
    "tag": "search-pets"
  }
}
```

See `pawconnect_ai/dialogflow_webhook.py` for webhook implementation.

---

## Next Steps

1. **Configure Webhook** (if not done yet):
   - Deploy your webhook to Cloud Run
   - Run setup script with `--webhook-url` parameter
   - See [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md) for details

2. **Fine-tune Agent**:
   - Adjust training phrases in Dialogflow Console
   - Test various conversation flows
   - Monitor webhook responses

3. **Deploy to Production**:
   - Follow [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)
   - Enable logging and monitoring
   - Set up CI/CD pipeline

---

## Additional Resources

- **[CONVERSATION_FLOW.md](./CONVERSATION_FLOW.md)** - Visual conversation flows
- **[docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)** - Production deployment guide
- **[Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)** - Official docs
- **[Webhook Integration Guide](https://cloud.google.com/dialogflow/cx/docs/concept/webhook)** - Webhook docs

---

**Setup Time:** ~5 minutes | **Skill Level:** Beginner-friendly
