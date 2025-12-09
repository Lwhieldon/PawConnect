# MCP Email & Calendar Setup Guide

This guide will help you set up MCP (Model Context Protocol) servers for Email and Calendar functionality in PawConnect, enabling foster/adopter connections through automated emails and calendar scheduling.

## Overview

PawConnect supports multiple email and calendar providers:

**Email Providers:**
- **Gmail** - Best for development and small-scale deployments
- **Outlook/Microsoft 365** - Enterprise option for organizations using Microsoft ecosystem
- **SendGrid** - Production-grade transactional email service (recommended for production)

**Calendar Providers:**
- **Google Calendar** - Integrated with Gmail, excellent for personal/small org use
- **Outlook Calendar** - Part of Microsoft 365, good for enterprise environments

## Prerequisites

- Node.js 18+ (for running MCP servers via npx)
- Access to Google Cloud Console, Azure Portal, or SendGrid account
- Basic understanding of OAuth 2.0 authentication

## Quick Start

### 1. Choose Your Providers

Edit your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Set your preferred providers
MCP_EMAIL_PROVIDER=gmail
MCP_CALENDAR_PROVIDER=google-calendar

# Enable MCP features
MCP_EMAIL_ENABLED=True
MCP_CALENDAR_ENABLED=True
```

### 2. Set Up Credentials

Follow the provider-specific setup instructions below.

---

## Gmail Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your Project ID

### Step 2: Enable Gmail API

1. Navigate to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click **Enable**

### Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: **External** (for testing) or **Internal** (for organization)
   - App name: `PawConnect AI`
   - User support email: Your email
   - Authorized domains: Your domain
   - Scopes: Add `gmail.send`, `gmail.modify`
4. Application type: **Web application**
5. Name: `PawConnect Gmail Client`
6. Authorized redirect URIs: `http://localhost:8080/oauth/callback`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### Step 4: Get Refresh Token

Run this Python script to obtain a refresh token:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost:8080/oauth/callback"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    SCOPES
)

creds = flow.run_local_server(port=8080)
print(f"Refresh Token: {creds.refresh_token}")
```

### Step 5: Update .env File

```bash
GMAIL_CLIENT_ID=your_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REDIRECT_URI=http://localhost:8080/oauth/callback
GMAIL_REFRESH_TOKEN=your_refresh_token
GMAIL_FROM_EMAIL=noreply@pawconnect.org
GMAIL_FROM_NAME=PawConnect Team
```

---

## Google Calendar Setup

### Step 1: Enable Calendar API

1. In the same Google Cloud project, go to **APIs & Services** > **Library**
2. Search for "Google Calendar API"
3. Click **Enable**

### Step 2: Use Same OAuth Credentials (or create new ones)

You can reuse the Gmail OAuth credentials or create separate ones following the same process.

### Step 3: Get Refresh Token with Calendar Scopes

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost:8080/oauth/callback"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    SCOPES
)

creds = flow.run_local_server(port=8080)
print(f"Refresh Token: {creds.refresh_token}")
```

### Step 4: Update .env File

```bash
GOOGLE_CALENDAR_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=your_client_secret
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth/callback
GOOGLE_CALENDAR_REFRESH_TOKEN=your_refresh_token
GOOGLE_CALENDAR_ID=primary
```

**Calendar ID Options:**
- `primary` - Your primary Google Calendar
- `shelter@pawconnect.org` - A specific calendar email address
- Calendar ID from Calendar Settings > Integrate calendar

---

## Microsoft Outlook/365 Setup

### Step 1: Register Application in Azure

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory)
3. Go to **App registrations** > **+ New registration**
4. Name: `PawConnect AI`
5. Supported account types: Choose based on your needs
6. Redirect URI: `http://localhost:8080/oauth/callback`
7. Click **Register**
8. Note the **Application (client) ID** and **Directory (tenant) ID**

### Step 2: Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **+ New client secret**
3. Description: `PawConnect MCP Secret`
4. Expires: Choose duration (recommend 24 months)
5. Click **Add**
6. **Copy the secret value immediately** (you won't be able to see it again)

### Step 3: Configure API Permissions

1. Go to **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Choose **Delegated permissions**
5. Add these permissions:
   - `Mail.Send` - Send emails
   - `Calendars.ReadWrite` - Create and manage calendar events
6. Click **Add permissions**
7. Click **Grant admin consent** (if you have admin rights)

### Step 4: Get Refresh Token

```python
from msal import PublicClientApplication

app = PublicClientApplication(
    client_id="YOUR_CLIENT_ID",
    authority="https://login.microsoftonline.com/common"
)

scopes = ["Mail.Send", "Calendars.ReadWrite", "offline_access"]

# This will open a browser for authentication
result = app.acquire_token_interactive(scopes=scopes)

if "refresh_token" in result:
    print(f"Refresh Token: {result['refresh_token']}")
else:
    print("Error:", result.get("error_description"))
```

### Step 5: Update .env File

```bash
OUTLOOK_CLIENT_ID=your_application_id
OUTLOOK_CLIENT_SECRET=your_client_secret
OUTLOOK_REDIRECT_URI=http://localhost:8080/oauth/callback
OUTLOOK_REFRESH_TOKEN=your_refresh_token
OUTLOOK_TENANT_ID=common
```

---

## SendGrid Setup (Recommended for Production)

SendGrid is the easiest to set up and most reliable for production email sending.

### Step 1: Create SendGrid Account

1. Go to [SendGrid](https://signup.sendgrid.com/)
2. Sign up for a free account (100 emails/day free tier)
3. Complete the verification process

### Step 2: Verify Sender Identity

1. Go to **Settings** > **Sender Authentication**
2. Choose **Single Sender Verification** (easiest) or **Domain Authentication** (recommended for production)
3. For single sender:
   - Enter your email address
   - Complete the verification email
4. For domain authentication:
   - Follow the DNS record setup instructions
   - This allows sending from any email at your domain

### Step 3: Create API Key

1. Go to **Settings** > **API Keys**
2. Click **Create API Key**
3. Name: `PawConnect MCP`
4. Permissions: **Full Access** or **Restricted Access** with Mail Send permission
5. Click **Create & View**
6. **Copy the API key immediately** (you won't be able to see it again)

### Step 4: Update .env File

```bash
SENDGRID_API_KEY=SG.your_api_key_here
SENDGRID_FROM_EMAIL=noreply@pawconnect.org
SENDGRID_FROM_NAME=PawConnect Team
```

---

## Testing Your Setup

### Test Email Sending

Create a test script `test_mcp_email.py`:

```python
import asyncio
from datetime import datetime
from pawconnect_ai.utils.mcp_email_client import get_email_client

async def test_email():
    email_client = get_email_client()

    result = await email_client.send_visit_confirmation(
        to_email="your_test_email@example.com",
        user_name="Test User",
        pet_name="Max",
        pet_id="test_123",
        visit_datetime=datetime(2025, 12, 15, 14, 0),
        shelter_name="Test Shelter",
        shelter_address="123 Main St, Seattle, WA 98101",
        visit_id="test_visit_001",
    )

    print(f"Email result: {result}")

if __name__ == "__main__":
    asyncio.run(test_email())
```

Run: `python test_mcp_email.py`

### Test Calendar Integration

Create a test script `test_mcp_calendar.py`:

```python
import asyncio
from datetime import datetime, timedelta
from pawconnect_ai.utils.mcp_calendar_client import get_calendar_client

async def test_calendar():
    calendar_client = get_calendar_client()

    visit_time = datetime.now() + timedelta(days=7)

    result = await calendar_client.create_visit_event(
        user_name="Test User",
        user_email="your_test_email@example.com",
        pet_name="Max",
        pet_id="test_123",
        visit_datetime=visit_time,
        duration_minutes=45,
        shelter_name="Test Shelter",
        shelter_address="123 Main St, Seattle, WA 98101",
        visit_id="test_visit_001",
    )

    print(f"Calendar result: {result}")

if __name__ == "__main__":
    asyncio.run(test_calendar())
```

Run: `python test_mcp_calendar.py`

### Test Full Visit Scheduling

```python
import asyncio
from datetime import datetime, timedelta
from pawconnect_ai.tools import PawConnectTools

async def test_visit_scheduling():
    tools = PawConnectTools()

    visit_time = datetime.now() + timedelta(days=7)

    result = await tools.schedule_visit(
        user_id="test_user_001",
        pet_id="mock_001",  # Use mock pet in testing mode
        preferred_time=visit_time,
        user_name="Test User",
        user_email="your_test_email@example.com",
    )

    print(f"Visit scheduled: {result}")
    print(f"Email sent: {result.get('email_sent')}")
    print(f"Calendar event: {result.get('calendar_event_id')}")

if __name__ == "__main__":
    asyncio.run(test_visit_scheduling())
```

---

## Production Deployment

### Secrets Management

**DO NOT** commit credentials to Git. Use Google Cloud Secret Manager:

```bash
# Store secrets
gcloud secrets create gmail-client-secret --data-file=-
gcloud secrets create gmail-refresh-token --data-file=-
gcloud secrets create sendgrid-api-key --data-file=-
gcloud secrets create google-calendar-refresh-token --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding gmail-client-secret \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Cloud Run Configuration

Update `deployment/cloudbuild.yaml` to inject secrets:

```yaml
- name: 'gcr.io/cloud-builders/gcloud'
  args:
    - 'run'
    - 'deploy'
    - 'pawconnect-ai'
    - '--image=gcr.io/$PROJECT_ID/pawconnect-ai:$SHORT_SHA'
    - '--set-secrets=GMAIL_CLIENT_SECRET=gmail-client-secret:latest'
    - '--set-secrets=GMAIL_REFRESH_TOKEN=gmail-refresh-token:latest'
    - '--set-secrets=SENDGRID_API_KEY=sendgrid-api-key:latest'
    - '--set-secrets=GOOGLE_CALENDAR_REFRESH_TOKEN=google-calendar-refresh-token:latest'
```

### Provider Recommendations

- **Development**: Gmail + Google Calendar (easiest setup, good for testing)
- **Small Production**: SendGrid + Google Calendar (reliable, affordable)
- **Enterprise**: Outlook + Outlook Calendar (integrated with existing Microsoft infrastructure)

---

## Troubleshooting

### Email Not Sending

1. **Check provider credentials**: Verify Client ID, Secret, and Refresh Token
2. **Check API quotas**: Gmail has sending limits (500/day for free accounts)
3. **Verify sender domain**: Ensure sender email is authorized
4. **Check logs**: `tail -f logs/pawconnect.log`

### Calendar Events Not Creating

1. **Verify Calendar API is enabled**: Check Google Cloud Console
2. **Check calendar permissions**: Ensure OAuth scopes include `calendar.events`
3. **Verify calendar ID**: Use `primary` or a valid calendar email

### OAuth Token Expired

Refresh tokens should be long-lived, but if they expire:

1. Re-run the OAuth flow to get a new refresh token
2. Update the `.env` file or Secret Manager
3. Restart the application

### Rate Limiting

If you hit rate limits:

1. **Gmail**: Upgrade to Google Workspace for higher limits
2. **SendGrid**: Upgrade plan or spread sends over time
3. **Outlook**: Contact Microsoft support for higher quotas

---

## Advanced Configuration

### Multiple Calendar Support

To support multiple shelter calendars:

```python
# In mcp_calendar_client.py, pass calendar_id dynamically
calendar_result = await calendar_client.create_event(
    calendar_id="shelter_seattle@pawconnect.org",
    # ... other params
)
```

### Email Templates

Customize templates in `pawconnect_ai/utils/mcp_email_client.py`:

- `send_visit_confirmation()` - Visit confirmation emails
- `send_application_status_update()` - Application updates

### Foster-Adopter Matching Emails

Add new method to `MCPEmailClient`:

```python
async def send_foster_adopter_match_notification(
    self,
    foster_email: str,
    adopter_name: str,
    pet_name: str,
    # ... other params
):
    # Custom email template for foster-adopter introductions
    pass
```

---

## Support & Resources

- **Gmail API Docs**: https://developers.google.com/gmail/api
- **Google Calendar API**: https://developers.google.com/calendar
- **Microsoft Graph API**: https://docs.microsoft.com/en-us/graph/
- **SendGrid Docs**: https://docs.sendgrid.com/
- **MCP Specification**: https://spec.modelcontextprotocol.io/

For issues, check `docs/TROUBLESHOOTING.md` or open an issue on GitHub.
