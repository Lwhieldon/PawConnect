# Load secrets from Google Cloud Secret Manager into environment variables
# This script is useful for local development and testing (Windows PowerShell)
#
# Usage:
#   . .\deployment\scripts\load-secrets.ps1
#   (or)
#   & .\deployment\scripts\load-secrets.ps1
#
# Note: Use dot-sourcing (. .\script.ps1) to persist environment variables

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "PawConnect - Load Secrets from GCP" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Check if gcloud is installed
try {
    $null = Get-Command gcloud -ErrorAction Stop
} catch {
    Write-Host "Error: gcloud CLI is not installed" -ForegroundColor Red
    Write-Host "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Check if user is authenticated
try {
    $account = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>&1
    if ([string]::IsNullOrWhiteSpace($account)) {
        throw "Not authenticated"
    }
} catch {
    Write-Host "Error: Not authenticated with gcloud" -ForegroundColor Red
    Write-Host "Run: gcloud auth login"
    exit 1
}

# Get current project ID
try {
    $PROJECT_ID = gcloud config get-value project 2>$null
    if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
        throw "No project set"
    }
} catch {
    Write-Host "Error: No GCP project is set" -ForegroundColor Red
    Write-Host "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
}

Write-Host "✓ Authenticated with GCP" -ForegroundColor Green
Write-Host "  Project: $PROJECT_ID" -ForegroundColor Blue
Write-Host ""

# List of secrets to load (SecretName:EnvVarName)
$secrets = @(
    "rescuegroups-api-key:RESCUEGROUPS_API_KEY",
    "redis-password:REDIS_PASSWORD",
    "dialogflow-agent-id:DIALOGFLOW_AGENT_ID"
)

# Function to load a single secret
function Load-Secret {
    param(
        [string]$SecretName,
        [string]$EnvVarName
    )

    Write-Host "Loading $SecretName... " -NoNewline

    try {
        $secretValue = gcloud secrets versions access latest --secret="$SecretName" 2>&1
        if ($LASTEXITCODE -eq 0) {
            [Environment]::SetEnvironmentVariable($EnvVarName, $secretValue, "Process")
            Write-Host "✓ Loaded" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠ Not found or access denied" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "⚠ Error loading secret" -ForegroundColor Yellow
        return $false
    }
}

# Load all secrets
Write-Host "Loading secrets from Secret Manager..."
Write-Host ""

$loadedCount = 0
$failedCount = 0

foreach ($secretMapping in $secrets) {
    $parts = $secretMapping -split ":"
    $secretName = $parts[0]
    $envVarName = $parts[1]

    if (Load-Secret -SecretName $secretName -EnvVarName $envVarName) {
        $loadedCount++
    } else {
        $failedCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "Secrets loaded: $loadedCount" -ForegroundColor Green
Write-Host "Secrets failed: $failedCount" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

if ($failedCount -gt 0) {
    Write-Host "Note: Some secrets could not be loaded" -ForegroundColor Yellow
    Write-Host "This might be because:"
    Write-Host "  1. The secrets don't exist in Secret Manager"
    Write-Host "  2. You don't have permission to access them"
    Write-Host "  3. You're in the wrong GCP project"
    Write-Host ""
    Write-Host "To create missing secrets, see: docs/DEPLOYMENT.md"
    Write-Host ""
}

# Verify environment variables are set
Write-Host "Verifying loaded secrets..."

$rescueGroupsKey = [Environment]::GetEnvironmentVariable("RESCUEGROUPS_API_KEY", "Process")
if ($rescueGroupsKey) {
    Write-Host "  RESCUEGROUPS_API_KEY: Set ($($rescueGroupsKey.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "  RESCUEGROUPS_API_KEY: Not set" -ForegroundColor Yellow
}

$redisPassword = [Environment]::GetEnvironmentVariable("REDIS_PASSWORD", "Process")
if ($redisPassword) {
    Write-Host "  REDIS_PASSWORD: Set ($($redisPassword.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "  REDIS_PASSWORD: Not set" -ForegroundColor Yellow
}

$dialogflowAgentId = [Environment]::GetEnvironmentVariable("DIALOGFLOW_AGENT_ID", "Process")
if ($dialogflowAgentId) {
    Write-Host "  DIALOGFLOW_AGENT_ID: Set ($($dialogflowAgentId.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "  DIALOGFLOW_AGENT_ID: Not set" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✓ Secrets loaded into environment" -ForegroundColor Green
Write-Host "You can now run your application with production credentials"
Write-Host ""
Write-Host "⚠️  WARNING: These are PRODUCTION secrets!" -ForegroundColor Yellow
Write-Host "   Do not log them or share your terminal session" -ForegroundColor Yellow
Write-Host ""
