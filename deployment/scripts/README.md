# PawConnect Deployment Scripts

This directory contains helper scripts for managing secrets and deployment tasks.

## Scripts

### 1. `setup-secrets.sh`

Interactive script to create all required secrets in Google Cloud Secret Manager.

**Usage:**
```bash
./deployment/scripts/setup-secrets.sh
```

**What it does:**
- Creates `rescuegroups-api-key` secret
- Creates `redis-password` secret (temporary, updated after Memorystore creation)
- Creates `dialogflow-agent-id` secret
- Grants access to Cloud Run service account
- Prompts you for each secret value securely

**When to use:** First-time setup or when adding new secrets

---

### 2. `load-secrets.sh` (Linux/Mac)

Load secrets from Secret Manager into environment variables for local development.

**Usage:**
```bash
# CORRECT: Use 'source' to persist environment variables in current shell
source deployment/scripts/load-secrets.sh

# Or using dot notation
. deployment/scripts/load-secrets.sh

# INCORRECT: Don't run directly (variables won't persist)
# ./deployment/scripts/load-secrets.sh  # ❌ This won't work properly
```

**What it does:**
- Loads `RESCUEGROUPS_API_KEY` from Secret Manager
- Loads `REDIS_PASSWORD` from Secret Manager
- Loads `DIALOGFLOW_AGENT_ID` from Secret Manager
- Sets them as environment variables in your current shell
- Detects if being sourced vs executed and warns accordingly

**When to use:** Before running PawConnect locally with production credentials

**Important Notes:**
- Always use `source` or `.` - this loads variables into your current shell
- If run directly with `./`, the script will warn you and offer to continue
- Variables only persist for the duration of your shell session

---

### 3. `load-secrets.ps1` (Windows PowerShell)

Windows PowerShell version of `load-secrets.sh`.

**Usage:**
```powershell
# Must use dot-sourcing to persist environment variables
. .\deployment\scripts\load-secrets.ps1

# Or
& .\deployment\scripts\load-secrets.ps1
```

**What it does:** Same as `load-secrets.sh` but for Windows

**When to use:** Before running PawConnect locally on Windows with production credentials

---

### 4. `validate-secrets.sh`

Validate that all required secrets are properly configured and accessible.

**Usage:**
```bash
./deployment/scripts/validate-secrets.sh
```

**What it does:**
- Checks if all required secrets exist
- Verifies you have access to read them
- Validates secret values (checks length, not content)
- Checks IAM permissions for Cloud Run service account
- Returns exit code 0 if all valid, 1 if errors found

**When to use:**
- Before deploying to production
- When troubleshooting secret access issues
- As part of CI/CD pipeline

**Example output:**
```
Checking rescuegroups-api-key... ✓ OK (64 chars)
Checking redis-password... ✓ OK (44 chars)
Checking dialogflow-agent-id... ✓ OK (36 chars)

Validation Summary:
  Passed:   3
  Warnings: 0
  Failed:   0

✓ All secrets are properly configured!
```

---

## Common Workflows

### First-Time Setup

1. **Create all secrets:**
   ```bash
   ./deployment/scripts/setup-secrets.sh
   ```

2. **Validate secrets:**
   ```bash
   ./deployment/scripts/validate-secrets.sh
   ```

3. **Deploy to production:**
   ```bash
   gcloud builds submit --config deployment/cloudbuild.yaml
   ```

### Local Development with Production Secrets

1. **Load secrets into environment:**
   ```bash
   # Linux/Mac
   source deployment/scripts/load-secrets.sh

   # Windows
   . .\deployment\scripts\load-secrets.ps1
   ```

2. **Run your application:**
   ```bash
   python -m pawconnect_ai.agent
   ```

### Updating a Secret

**Option 1: Using gcloud directly**
```bash
echo -n "new_secret_value" | gcloud secrets versions add rescuegroups-api-key --data-file=-
```

**Option 2: Using setup script**
```bash
./deployment/scripts/setup-secrets.sh
# Select the secret to update
```

### Troubleshooting

If secrets aren't working:

1. **Validate configuration:**
   ```bash
   ./deployment/scripts/validate-secrets.sh
   ```

2. **Check your GCP project:**
   ```bash
   gcloud config get-value project
   ```

3. **Verify authentication:**
   ```bash
   gcloud auth list
   ```

4. **Check secret existence:**
   ```bash
   gcloud secrets list
   ```

5. **Test direct access:**
   ```bash
   gcloud secrets versions access latest --secret="rescuegroups-api-key"
   ```

---

## Security Best Practices

1. **Never log secret values** - These scripts hide input and don't print secret values
2. **Use `source` for load scripts** - Ensures variables are in current shell only
3. **Rotate secrets regularly** - Update secret versions periodically
4. **Limit access** - Only grant Secret Accessor role to necessary service accounts
5. **Audit regularly** - Check Secret Manager audit logs for unexpected access

---

## Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
steps:
  - name: Validate Secrets
    run: |
      ./deployment/scripts/validate-secrets.sh
      if [ $? -ne 0 ]; then
        echo "Secret validation failed"
        exit 1
      fi
```

---

## Additional Resources

- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [PawConnect Deployment Guide](../docs/DEPLOYMENT.md)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)

---

## Troubleshooting Common Issues

### "Permission denied" errors

**Solution:** Grant Secret Accessor role:
```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### Secrets not updating in Cloud Run

**Solution:** Restart Cloud Run service:
```bash
gcloud run services update pawconnect-main-agent --region=us-central1
```

### Scripts fail on Windows

**Solution:** Use PowerShell version:
- Use `load-secrets.ps1` instead of `load-secrets.sh`
- Or use Git Bash / WSL for bash scripts

### VSCode Terminal Crashes when running load-secrets.sh

**Symptom:** Terminal closes or becomes unresponsive

**Cause:** Running the script directly (`./load-secrets.sh`) instead of sourcing it

**Solution:**
```bash
# ✅ CORRECT - Use source
source deployment/scripts/load-secrets.sh

# ✅ CORRECT - Use dot notation
. deployment/scripts/load-secrets.sh

# ❌ WRONG - Don't run directly
./deployment/scripts/load-secrets.sh  # This can cause terminal issues
```

**Why this happens:**
- The script uses `return` statements which are only valid when sourced
- Running directly with `./` executes in a subshell, causing `return` to behave incorrectly
- The fixed version detects execution mode and handles both cases safely

---

For more information, see the main [DEPLOYMENT.md](../docs/DEPLOYMENT.md) documentation.
