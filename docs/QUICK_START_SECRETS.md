# Quick Start: Loading Secrets for Local Development

This guide shows you how to safely load production secrets for local testing.

## ⚠️ Important: How to Run the Script

The `load-secrets.sh` script **MUST** be sourced, not executed directly.

### ✅ CORRECT Usage

```bash
# Option 1: Using 'source' command
source deployment/scripts/load-secrets.sh

# Option 2: Using dot notation
. deployment/scripts/load-secrets.sh
```

### ❌ INCORRECT Usage (Will Crash Terminal)

```bash
# DON'T DO THIS - Will cause terminal to crash or close
./deployment/scripts/load-secrets.sh

# DON'T DO THIS EITHER
bash deployment/scripts/load-secrets.sh
```

## Why Sourcing is Required

When you **source** a script:
- It runs in your **current shell session**
- Environment variables persist after the script finishes
- `return` statements work correctly

When you **execute** a script directly:
- It runs in a **new subshell**
- Environment variables disappear when the script exits
- `return` statements outside functions cause errors

## Step-by-Step Guide

### 1. Open Terminal in VSCode

- Press `` Ctrl + ` `` (or `View` > `Terminal`)
- Make sure you're in the project root: `C:\Users\lwhieldon\KaggleAgentsCapstone\PawConnect`

### 2. Verify gcloud is Configured

```bash
# Check authentication
gcloud auth list

# Check current project
gcloud config get-value project

# If not set, configure it
gcloud config set project YOUR_PROJECT_ID
```

### 3. Load Secrets (IMPORTANT: Use 'source')

```bash
source deployment/scripts/load-secrets.sh
```

**Expected Output:**
```
========================================
PawConnect - Load Secrets from GCP
========================================

✓ Authenticated with GCP
  Project: your-project-id

Loading secrets from Secret Manager...

Loading rescuegroups-api-key... ✓ Loaded
Loading redis-password... ✓ Loaded
Loading dialogflow-agent-id... ✓ Loaded

========================================
Secrets loaded: 3
Secrets failed: 0
========================================

Verifying loaded secrets...
  RESCUEGROUPS_API_KEY: Set (64 chars)
  REDIS_PASSWORD: Set (44 chars)
  DIALOGFLOW_AGENT_ID: Set (36 chars)

✓ Secrets loaded into environment
You can now run your application with production credentials

⚠️  WARNING: These are PRODUCTION secrets!
   Do not log them or share your terminal session
```

### 4. Verify Secrets are Loaded

```bash
# Check that variables are set (shows length, not value)
echo ${#RESCUEGROUPS_API_KEY}
echo ${#REDIS_PASSWORD}
echo ${#DIALOGFLOW_AGENT_ID}
```

### 5. Run Your Application

```bash
# Now you can run PawConnect with production credentials
python -m pawconnect_ai.agent
```

## Troubleshooting

### Terminal Crashed or Closed

**Problem:** You ran `./deployment/scripts/load-secrets.sh` directly

**Solution:**
1. Open a new terminal
2. Use `source deployment/scripts/load-secrets.sh` instead

### "Not authenticated with gcloud"

**Solution:**
```bash
gcloud auth login
gcloud auth application-default login
```

### "No GCP project is set"

**Solution:**
```bash
gcloud config set project YOUR_PROJECT_ID
```

### "Secret not found or access denied"

**Solution:**
1. Create secrets first:
   ```bash
   ./deployment/scripts/setup-secrets.sh
   ```

2. Verify you have access:
   ```bash
   ./deployment/scripts/validate-secrets.sh
   ```

### Secrets Don't Persist After Script Runs

**Problem:** You executed the script instead of sourcing it

**Solution:** Always use `source` or `.` to run the script

## Windows Users

### PowerShell

```powershell
# Use the PowerShell version
. .\deployment\scripts\load-secrets.ps1
```

### Git Bash

```bash
# Use source with forward slashes
source deployment/scripts/load-secrets.sh
```

### Command Prompt

Command Prompt doesn't support sourcing. Use PowerShell or Git Bash instead.

## Security Best Practices

1. **Never log secret values** - The script only shows lengths
2. **Close terminal when done** - Secrets remain in environment
3. **Don't commit `.env` with secrets** - Always use Secret Manager
4. **Rotate secrets regularly** - See `docs/SECRETS_MANAGEMENT.md`

## Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│         Loading Secrets Cheat Sheet             │
├─────────────────────────────────────────────────┤
│                                                  │
│  ✅ CORRECT:                                     │
│     source deployment/scripts/load-secrets.sh   │
│     . deployment/scripts/load-secrets.sh        │
│                                                  │
│  ❌ WRONG:                                       │
│     ./deployment/scripts/load-secrets.sh        │
│     bash deployment/scripts/load-secrets.sh     │
│                                                  │
│  💡 Remember:                                    │
│     - Use 'source' to persist variables         │
│     - Variables only last current session       │
│     - Run from project root directory           │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Additional Resources

- **Complete Secrets Guide:** [docs/SECRETS_MANAGEMENT.md](./SECRETS_MANAGEMENT.md)
- **Script Documentation:** [deployment/scripts/README.md](../deployment/scripts/README.md)
- **Deployment Guide:** [docs/DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Need Help?** If you're still having issues, check the troubleshooting sections in the documents above or create an issue on GitHub.
