# PawConnect Dialogflow CX Setup

Simple, clean setup for your PawConnect Dialogflow CX agent using a single script.

## Quick Start

### Prerequisites

1. **Create a Dialogflow CX agent** in the Google Cloud Console:
   - Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx/)
   - Create a new agent named "PawConnect AI Agent"
   - Note your project ID

2. **Set up authentication**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

### Setup Your Agent

**Run this ONE command to configure everything:**

```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID
```

That's it! The script will:
- ✅ Auto-detect your agent ID
- ✅ Create/update all entity types (housing_type, pet_species, pet_size, pet_age_group)
- ✅ Create/update all intents with proper parameter annotations
- ✅ Set up pages and flows with transition routes
- ✅ Configure welcome message
- ✅ Set up webhook (if URL provided)

### With Webhook

If you have a webhook deployed, include the URL:

```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID \
    --webhook-url https://your-webhook-url/webhook
```

### Manual Agent ID

If auto-detection doesn't work, specify the agent ID manually:

```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID \
    --agent-id YOUR_AGENT_ID
```

## What Gets Configured

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

## Testing

After setup, test in the Dialogflow CX Simulator:

1. **"I want to adopt a dog in Seattle"**
   - Agent should extract "dog" and "Seattle" automatically
   - Should not ask "Where do you live?" again

2. **"Yes please show me recommendations"**
   - Agent should recognize this as intent.get_recommendations
   - Should transition to Get Recommendations page

3. **"apartment"** (when asked about housing)
   - Agent should recognize "apartment" as valid housing_type
   - Should not trigger sys.no-match-default

## Verification

To verify your configuration is correct:

```bash
python deployment/dialogflow/verify_fixes.py \
    --project-id YOUR_PROJECT_ID \
    --agent-id YOUR_AGENT_ID
```

This checks:
- ✓ intent.search_pets has parameter annotations
- ✓ intent.get_recommendations has affirmative responses
- ✓ housing_type entity includes apartment/house/condo

## Troubleshooting

### "Agent not found" error
Run this to find your agent ID:
```bash
python deployment/dialogflow/list_agents.py --project-id YOUR_PROJECT_ID
```

### Changes not showing in simulator
1. Wait 2-3 minutes for Google's backend to propagate changes
2. Clear browser cache or use incognito window
3. Click "Reset" in the simulator to start fresh conversation

### "sys.no-match-default" errors
1. Run the setup script again - it's safe to rerun
2. Wait for propagation (2-3 minutes)
3. Run verify_fixes.py to confirm configuration

### Still having issues?
1. Check authentication: `gcloud auth application-default login`
2. Verify project: `gcloud config get-value project`
3. Check logs in the script output for specific errors

## Updating Configuration

The setup script can be run multiple times safely. It will:
- Update existing resources instead of creating duplicates
- Preserve any custom changes you've made in the console
- Only update training phrases, entities, and routes

To update your agent after making changes to the script:

```bash
python deployment/dialogflow/setup_agent.py --project-id YOUR_PROJECT_ID
```

## Files in This Directory

### Active Scripts
- **`setup_agent.py`** - ⭐ The ONLY script you need for setup
- **`verify_fixes.py`** - Verify configuration is correct
- **`list_agents.py`** - List all agents in your project

### Legacy Files (For Reference Only)
These files are kept for reference but are no longer needed. Everything has been consolidated into `setup_agent.py`:

- `setup_dialogflow_automation.py`
- `setup_complete_automation.py`
- `fix_parameter_extraction.py`
- `update_entity_types.py`
- `update_intent_parameters.py`
- `add_transition_routes.py`
- `setup-agent.sh`

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

## Additional Resources

- [Main Deployment Guide](../../docs/DEPLOYMENT.md)
- [Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- [Webhook Integration Guide](https://cloud.google.com/dialogflow/cx/docs/concept/webhook)
