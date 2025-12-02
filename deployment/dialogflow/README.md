# PawConnect Dialogflow CX Agent Setup Guide

This directory contains configuration files and scripts to help you set up the PawConnect Dialogflow CX agent.

## 📋 Files in this Directory

- **`agent-config.yaml`** - Reference configuration showing all intents, entity types, and flows
- **`setup-agent.sh`** - Automated script to create intents and entity types via gcloud CLI
- **`setup_complete_automation.py`** - Complete Python automation for full agent setup
- **`setup_dialogflow_automation.py`** - Core automation for pages, flows, and webhooks
- **`update_intent_parameters.py`** - Add parameter annotations to intent training phrases
- **`fix_parameter_extraction.py`** - ⚠️ **CRITICAL FIX** - Fixes parameter extraction from user utterances
- **`add_transition_routes.py`** - Add transition routes with intent matchers
- **`CONVERSATION_FLOW.md`** - Visual guide to conversation flows and testing scenarios
- **`README.md`** - This file

## 🚀 Setup Options

### Option 1: Full Python Automation with Parameter Fix (Recommended) ⭐

**⚠️ CRITICAL:** Use this option for production deployments to ensure proper parameter extraction from user utterances.

```bash
# 1. Create your agent in Dialogflow Console first

# 2. Authenticate with Google Cloud
gcloud auth application-default login

# 3. Get your agent ID using REST API
export PROJECT_ID=$(gcloud config get-value project)
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://us-central1-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/us-central1/agents"

# Alternative: View in browser to get agent ID
# Windows: start https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/us-central1/agents
# Mac/Linux: open https://dialogflow.cloud.google.com/cx/projects/$PROJECT_ID/locations/us-central1/agents

# 4. Run the COMPLETE fix script (includes all setup + parameter extraction fix)
python deployment/dialogflow/fix_parameter_extraction.py \
  --project-id $PROJECT_ID \
  --agent-id YOUR_AGENT_ID \
  --location us-central1 \
  --webhook-url https://your-cloud-run-url/webhook
```

**What this creates:**
- ✅ 4 entity types (pet_species, pet_size, pet_age_group, housing_type)
- ✅ 7 intents with **parameter-annotated** training phrases
- ✅ 1 webhook configuration
- ✅ 6 pages with form parameters
- ✅ Updated START_PAGE with welcome message
- ✅ Transition routes with **parameter presets**
- ✅ Flow restart logic to prevent conversation loops
- ✅ **CRITICAL:** Parameter extraction from initial user utterance

**Why this is critical:**
- Without parameter extraction, users get frustrated by repetitive questions
- Example: User says "I want to adopt a dog in Seattle" but agent asks "Where do you live?"
- This fix ensures location and species are extracted automatically from the first message

**Manual steps still needed:**
- Test in Dialogflow Simulator
- Fine-tune any edge cases

### Option 2: Basic Python Automation (Without Parameter Fix)

Use this if you already have intents configured with parameter annotations:

```bash
# Run the complete automation script (without parameter fix)
python deployment/dialogflow/setup_complete_automation.py \
  --project-id $PROJECT_ID \
  --agent-id YOUR_AGENT_ID \
  --webhook-url https://your-cloud-run-url/webhook
```

**What this creates:**
- ✅ 4 entity types
- ✅ 7 intents with basic training phrases (no parameter annotations)
- ✅ 1 webhook configuration
- ✅ 6 pages with form parameters
- ✅ Transition routes

**Manual steps still needed:**
- Add parameter annotations to training phrases manually
- Configure parameter presets in transition routes
- Test and adjust parameters

### Option 3: Bash Script Only (Intents & Entities)

Use the bash script if you only want to automate entity types and intents:

```bash
# 1. Create your agent in Dialogflow Console first

# 2. Set quota project for API calls (one-time setup)
gcloud auth application-default set-quota-project $PROJECT_ID

# 3. Get your agent ID (see Option 1 for how to get this)

# 4. Run the setup script with your agent ID
chmod +x deployment/dialogflow/setup-agent.sh
./deployment/dialogflow/setup-agent.sh YOUR_AGENT_ID us-central1 $PROJECT_ID
```

**What this script creates:**
- ✅ 4 entity types (pet_species, pet_size, pet_age_group, housing_type)
- ✅ 7 intents with training phrases

**What you still need to create:**
- Pages and flows (use Option 1 or create manually)
- Webhook configuration
- Page parameters and transitions

### Option 4: Manual Setup (Full Control)

Follow these step-by-step instructions to manually create the agent in the Dialogflow CX Console.

---

## 📖 Step-by-Step Manual Setup

### Step 1: Create the Agent

1. Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx)
2. Click **"Create agent"**
3. Configure:
   - **Display Name**: `PawConnect AI`
   - **Location**: `us-central1` (or your preferred region)
   - **Time Zone**: Select your timezone
4. Click **"Create"**

### Step 2: Create Entity Types

Go to **Manage** > **Entity Types** > **Create** and add each of these:

#### 1. pet_species
- **Kind**: Map
- **Enable fuzzy matching**: ✓
- **Entities**:
  - `dog` → synonyms: dog, dogs, puppy, puppies, canine
  - `cat` → synonyms: cat, cats, kitten, kittens, feline
  - `rabbit` → synonyms: rabbit, rabbits, bunny, bunnies
  - `bird` → synonyms: bird, birds, parrot, parakeet
  - `small_animal` → synonyms: hamster, guinea pig, ferret

#### 2. pet_size
- **Kind**: Map
- **Entities**:
  - `small` → synonyms: small, tiny, little, miniature
  - `medium` → synonyms: medium, average, mid-sized
  - `large` → synonyms: large, big, giant, huge

#### 3. pet_age_group
- **Kind**: Map
- **Entities**:
  - `baby` → synonyms: baby, newborn, infant, very young
  - `young` → synonyms: young, puppy, kitten, juvenile
  - `adult` → synonyms: adult, mature, grown
  - `senior` → synonyms: senior, elderly, old, older

#### 4. housing_type
- **Kind**: Map
- **Entities**:
  - `apartment` → synonyms: apartment, apt, flat, apartments, apartment building
  - `house` → synonyms: house, home, single family, single-family home
  - `condo` → synonyms: condo, condominium, townhouse, townhome
  - `own` → synonyms: own, owner, homeowner, I own, own my home
  - `rent` → synonyms: rent, renter, renting, I rent, lease, renting a place
  - `live_with_family` → synonyms: live with family, parents, family home, with parents, parents house

### Step 3: Create Intents

Go to **Manage** > **Intents** > **Create** and add each intent with training phrases:

#### intent.search_pets
Training phrases:
- "I want to search for a pet"
- "Show me available dogs"
- "I'm looking for a cat to adopt"
- "Can you help me find a pet"
- "Search for pets near me"
- "Find me a puppy"
- "I'm looking for a rescue animal"

#### intent.get_recommendations
Training phrases:
- "What pet would be good for me"
- "Can you recommend a pet"
- "Which pet should I adopt"
- "Help me find the right pet"
- "I don't know what pet to get"
- "Recommend a pet for my lifestyle"

#### intent.schedule_visit
Training phrases:
- "I want to schedule a visit"
- "Can I meet the pet"
- "Schedule a time to see the pet"
- "I'd like to visit the shelter"
- "Book a visit"
- "Set up an appointment"

#### intent.adoption_application
Training phrases:
- "I want to adopt"
- "Start adoption application"
- "Apply to adopt this pet"
- "I'd like to adopt"
- "Begin adoption process"
- "Submit adoption application"

#### intent.foster_application
Training phrases:
- "I want to foster"
- "Start foster application"
- "Apply to foster this pet"
- "I'd like to foster"
- "Can I foster temporarily"

#### intent.search_more
Training phrases:
- "Show me more pets"
- "Search again"
- "Find other pets"
- "Start a new search"

#### intent.ask_question
Training phrases:
- "Tell me about Golden Retrievers"
- "What do I need to know about cats"
- "How much exercise does a dog need"
- "What should I prepare before adopting"
- "What's the adoption process"

### Step 4: Create Webhook

1. Go to **Manage** > **Webhooks**
2. Click **"Create"**
3. Configure:
   - **Display Name**: `PawConnect Webhook`
   - **Webhook URL**: `https://YOUR-CLOUD-RUN-URL/webhook`
   - **Timeout**: `30s`
4. Click **"Save"**

**Note:** You'll get the actual URL after deploying your Cloud Run service.

### Step 5: Create Pages and Flows

#### Start Page (Already exists)
1. Go to **Build** > **Flows** > **Default Start Flow**
2. Click on **START_PAGE**
3. Edit **Entry fulfillment**:
   - Add message: "Hello! I'm PawConnect AI, your personal pet adoption assistant. I can help you search for pets, get personalized recommendations, schedule shelter visits, and submit adoption or foster applications. How can I help you today?"

#### Pet Search Page
1. In Default Start Flow, click **"+"** to add a new page
2. Name it **"Pet Search"**
3. Add **Form parameters**:
   - `species` (type: `@pet_species`, optional)
   - `breed` (type: `@sys.any`, optional)
   - `location` (type: `@sys.any`, optional)
4. Add **Entry fulfillment** with webhook:
   - Select webhook: `PawConnect Webhook`
   - Webhook tag: `search-pets`
5. Click **"Save"**

#### Pet Details Page
1. Add new page: **"Pet Details"**
2. Add **Form parameters**:
   - `pet_id` (type: `@sys.any`, **required**)
   - Prompt: "Please provide the pet ID you're interested in"
3. Add **Fulfillment** with webhook:
   - Webhook: `PawConnect Webhook`
   - Tag: `validate-pet-id`
4. Click **"Save"**

#### Schedule Visit Page
1. Add new page: **"Schedule Visit"**
2. Add **Form parameters**:
   - `visit_date` (type: `@sys.date`, required)
   - `visit_time` (type: `@sys.time`, required)
   - `visitor_name` (type: `@sys.any`, required)
   - `visitor_email` (type: `@sys.any`, required, **redact**)
   - `visitor_phone` (type: `@sys.phone-number`, required, **redact**)
3. Add **Fulfillment** with webhook:
   - Webhook: `PawConnect Webhook`
   - Tag: `schedule-visit`
4. Click **"Save"**

### Step 6: Add Page Transitions

Create transitions between pages:

1. **START_PAGE → Pet Search**:
   - Add route with intent `intent.search_pets`
   - Target: Pet Search page

2. **Pet Search → Pet Details**:
   - Add route with condition: `$page.params.status = "FINAL"`
   - Target: Pet Details page

3. **Pet Details → Schedule Visit**:
   - Add route with intent `intent.schedule_visit`
   - Target: Schedule Visit page

(Continue adding other pages and transitions as needed)

---

## 🔧 Post-Setup Configuration

### Update Webhook URL

After deploying your Cloud Run service:

```bash
# Get webhook URL
export WEBHOOK_URL=$(gcloud run services describe pawconnect-dialogflow-webhook \
  --region $REGION \
  --format='value(status.url)')

echo "Webhook URL: $WEBHOOK_URL/webhook"
```

Then update in Dialogflow Console:
- **Manage** > **Webhooks** > **PawConnect Webhook**
- Update **Webhook URL** to: `$WEBHOOK_URL/webhook`

### Store Agent ID in Secret Manager

```bash
# Get agent ID using REST API (just the ID portion, not the full path)
# Example: If full path is projects/.../agents/47cb5224-5f15-474a-9b07-49cd6633fdf5
# You want: 47cb5224-5f15-474a-9b07-49cd6633fdf5
AGENT_ID="your-agent-id-here"

# Store in Secret Manager
echo -n "$AGENT_ID" | gcloud secrets versions add dialogflow-agent-id --data-file=-
```

---

## 🧪 Testing Your Agent

### Test in Simulator

1. Click **"Test Agent"** in the top-right corner
2. Try these test phrases:
   - "I want to search for a dog"
   - "Can you recommend a pet for me?"
   - "I'd like to adopt"
   - "Schedule a visit"

### Test Webhook Directly

```bash
# Test webhook endpoint
curl -X POST $WEBHOOK_URL/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "fulfillmentInfo": {"tag": "search-pets"},
    "sessionInfo": {
      "parameters": {
        "species": "dog",
        "location": "Seattle"
      }
    }
  }'
```

---

## 📚 Reference Files

- **`agent-config.yaml`**: Complete reference configuration
- **`CONVERSATION_FLOW.md`**: Detailed conversation flow diagrams
- **[DEPLOYMENT.md](../../docs/DEPLOYMENT.md)**: Full deployment guide

---

## 🛠️ Troubleshooting

### Issue: Intents not matching

**Solution:**
1. Add more training phrases
2. Enable spell correction (Agent settings)
3. Check intent priority values

### Issue: Webhook not responding

**Solution:**
1. Verify webhook URL is correct
2. Check Cloud Run service is deployed and running
3. Check webhook logs:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pawconnect-dialogflow-webhook" --limit=50
   ```

### Issue: Parameters not being extracted

**Symptoms:**
- User says "I want to adopt a dog in Seattle" but agent asks "Where do you live?"
- Location, species, or other parameters not extracted from initial utterance
- User gets frustrated by repetitive questions

**Solution:**

Run the parameter extraction fix script (RECOMMENDED):

```bash
python deployment/dialogflow/fix_parameter_extraction.py \
  --project-id $PROJECT_ID \
  --agent-id $AGENT_ID \
  --location us-central1 \
  --webhook-url $WEBHOOK_URL
```

Or manually fix:
1. Add parameter annotations to training phrases in Dialogflow Console
2. Configure parameter presets in transition routes
3. Enable fuzzy matching on entity types
4. Use system entities where appropriate (@sys.date, @sys.time, etc.)

**What the fix script does:**
- Updates `intent.search_pets` with parameter-annotated training phrases
- Adds parameter presets to transition routes (maps intent params → page params)
- Ensures location/species extracted from user's first message

---

## 🔗 Additional Resources

- [Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- [Webhook Integration Guide](https://cloud.google.com/dialogflow/cx/docs/concept/webhook)
- [Best Practices](https://cloud.google.com/dialogflow/cx/docs/concept/best-practices)

---

## 💡 Tips

1. **Start simple**: Create the basic flow first, then add complexity
2. **Test frequently**: Test after adding each page or intent
3. **Use webhook tags**: Makes it easy to route to different backend handlers
4. **Enable PII redaction**: Mark email, phone, address fields as redact=true
5. **Monitor logs**: Check both Dialogflow and Cloud Run logs for debugging

---

## 🐍 Python Automation Scripts

### Available Scripts

1. **`fix_parameter_extraction.py`** ⭐ - **RECOMMENDED** - Complete fix including parameter extraction
2. **`setup_complete_automation.py`** - Complete setup combining bash and Python automation
3. **`setup_dialogflow_automation.py`** - Core automation for pages, flows, and webhooks
4. **`update_intent_parameters.py`** - Add parameter annotations to intent training phrases
5. **`add_transition_routes.py`** - Add transition routes with intent matchers

### Script Usage Examples

#### Complete Setup with Parameter Fix (Recommended) ⭐

```bash
# ⚠️ CRITICAL for production: Fixes parameter extraction from user utterances
# This is the ONLY script you need to run for a complete, production-ready setup
python deployment/dialogflow/fix_parameter_extraction.py \
  --project-id my-project \
  --agent-id $AGENT_ID \
  --location us-central1 \
  --webhook-url https://my-app.run.app/webhook
```

**What it does:**
- Step 1: Updates intents with parameter-annotated training phrases
- Step 2: Creates pages, flows, and webhooks with parameter presets
- Step 3: Configures flow restart logic to prevent conversation loops
- **Result:** Users can say "I want to adopt a dog in Seattle" and the location is extracted automatically

#### Complete Setup (Without Parameter Fix)

```bash
# Full automation including intents, entities, pages, flows, and webhooks
python deployment/dialogflow/setup_complete_automation.py \
  --project-id my-project \
  --agent-id $AGENT_ID \
  --webhook-url https://my-app.run.app/webhook

# Skip bash script if intents/entities already exist
python deployment/dialogflow/setup_complete_automation.py \
  --project-id my-project \
  --agent-id $AGENT_ID \
  --skip-bash-setup
```

#### Update Intent Parameters Only

```bash
# Add parameter annotations to existing intent training phrases
python deployment/dialogflow/update_intent_parameters.py \
  --project-id my-project \
  --agent-id $AGENT_ID \
  --location us-central1
```

#### Pages & Flows Only

```bash
# Create only pages, flows, and webhooks (assumes intents/entities exist)
python deployment/dialogflow/setup_dialogflow_automation.py \
  --project-id my-project \
  --agent-id $AGENT_ID \
  --webhook-url https://my-app.run.app/webhook
```

#### Transition Routes Only

```bash
# Add transition routes between existing pages
python deployment/dialogflow/add_transition_routes.py \
  --project-id my-project \
  --agent-id $AGENT_ID
```

### Script Features

The Python automation scripts provide:

- **Idempotent operations**: Safe to run multiple times, won't duplicate resources
- **Error handling**: Clear error messages and graceful failures
- **Caching**: Efficient lookups for intents and pages
- **Validation**: Verifies agent exists before making changes
- **Logging**: Detailed logs of all operations

### How to Get Your Agent ID

```bash
# Method 1: Using REST API
export PROJECT_ID=$(gcloud config get-value project)
curl -s \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://us-central1-dialogflow.googleapis.com/v3/projects/$PROJECT_ID/locations/us-central1/agents" \
  | grep -o '"name": "[^"]*"' | head -1

# Method 2: View in Console
# Navigate to Dialogflow CX Console and copy the agent ID from the URL
# URL format: https://dialogflow.cloud.google.com/cx/projects/{PROJECT}/locations/{LOCATION}/agents/{AGENT_ID}

# Method 3: From Python
python -c "
from google.cloud.dialogflowcx_v3 import AgentsClient
client = AgentsClient()
agents = client.list_agents(parent='projects/YOUR_PROJECT/locations/us-central1')
for agent in agents:
    print(f'{agent.display_name}: {agent.name.split(\"/\")[-1]}')
"
```

### Environment Setup

Ensure you have the required dependencies:

```bash
# Install dependencies (if not already installed)
pip install google-cloud-dialogflow-cx loguru

# Authenticate with Google Cloud
gcloud auth application-default login

# Set project (optional)
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Troubleshooting Python Scripts

#### Issue: ModuleNotFoundError

```bash
# Install required packages
pip install -r requirements.txt
```

#### Issue: Authentication errors

```bash
# Re-authenticate
gcloud auth application-default login

# Or set credentials explicitly
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

#### Issue: Permission denied

```bash
# Ensure you have Dialogflow API Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/dialogflow.admin"
```

#### Issue: Agent not found

```bash
# Verify agent exists
gcloud alpha dialogflow agents list --location=us-central1

# Or check in Console
# https://dialogflow.cloud.google.com/cx
```

### Architecture

The Python automation uses the official Google Cloud Dialogflow CX Python client library:

- **AgentsClient**: Verify agent exists
- **FlowsClient**: Manage flows
- **PagesClient**: Create and update pages
- **WebhooksClient**: Configure webhooks
- **IntentsClient**: Look up intent resource names
- **TransitionRoute**: Connect pages and flows

For more information, see the [Dialogflow CX Python Client Documentation](https://cloud.google.com/python/docs/reference/dialogflow-cx/latest).

---

**Need more help?** See the complete deployment guide in [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md)
