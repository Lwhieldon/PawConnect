# Dialogflow CX Quick Start

## Setup in 3 Steps

### 1. Create Agent
Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx/) and create a new agent named "PawConnect AI Agent"

### 2. Authenticate
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 3. Run Setup Script
```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID
```

**That's it!** Your agent is fully configured.

## Verify Setup

```bash
python deployment/dialogflow/verify_fixes.py \
    --project-id YOUR_PROJECT_ID \
    --agent-id YOUR_AGENT_ID
```

## Test in Simulator

1. Go to Dialogflow CX Console
2. Click "Test Agent"
3. Try: "I want to adopt a dog in Seattle"
4. Should extract "dog" and "Seattle" automatically

## Add Webhook (Optional)

If you have a webhook deployed:

```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID \
    --webhook-url https://your-webhook-url/webhook
```

## Need Help?

- **Detailed Guide**: See [README.md](./README.md)
- **Troubleshooting**: Run `verify_fixes.py`
- **Find Agent ID**: Run `python deployment/dialogflow/list_agents.py --project-id YOUR_PROJECT_ID`

## Files You Need

- ✅ `setup_agent.py` - The only script you need
- ✅ `verify_fixes.py` - Verify configuration
- ✅ `list_agents.py` - List agents

All other files are in the `legacy/` folder for reference only.
