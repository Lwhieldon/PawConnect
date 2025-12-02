# Legacy Dialogflow Setup Scripts

This directory contains legacy scripts that have been replaced by the consolidated `setup_agent.py` script.

## Why These Scripts Are Here

These scripts were used during development but have been consolidated into a single, simpler script (`setup_agent.py`) for easier maintenance and use.

## Legacy Scripts

- **`setup_dialogflow_automation.py`** - Core automation for pages, flows, and webhooks
- **`setup_complete_automation.py`** - Complete setup combining bash and Python automation
- **`fix_parameter_extraction.py`** - Wrapper script for parameter extraction fixes
- **`update_entity_types.py`** - Update housing_type entity
- **`update_intent_parameters.py`** - Add parameter annotations to intent training phrases
- **`add_transition_routes.py`** - Add transition routes with intent matchers
- **`setup-agent.sh`** - Bash script for creating intents and entity types

## Current Recommended Approach

**Use `setup_agent.py` instead:**

```bash
python deployment/dialogflow/setup_agent.py \
    --project-id YOUR_PROJECT_ID
```

This single script replaces all the scripts in this directory and provides:
- Auto-detection of agent ID
- Complete entity type setup
- Complete intent setup with parameter annotations
- Page and flow configuration
- Webhook configuration
- Welcome message setup

## Why Consolidate?

**Problems with the old approach:**
1. Too many scattered scripts
2. Unclear which script to run and in what order
3. Difficult to maintain multiple scripts
4. Confusing for new users

**Benefits of the new approach:**
1. Single entry point
2. Clear, simple usage
3. Easier to maintain
4. Can be run multiple times safely
5. Auto-detects agent ID

## If You Need These Scripts

These scripts are kept for reference purposes. If you need to understand how specific functionality was implemented, you can review these files. However, for production use, please use `setup_agent.py` instead.

## See Also

- [../README.md](../README.md) - Current Dialogflow setup documentation
- [../setup_agent.py](../setup_agent.py) - Current setup script
- [../verify_fixes.py](../verify_fixes.py) - Verification tool
