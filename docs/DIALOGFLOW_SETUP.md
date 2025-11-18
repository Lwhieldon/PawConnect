# Dialogflow CX Setup Guide for PawConnect

This guide provides step-by-step instructions for creating and configuring a Dialogflow CX agent for the PawConnect AI application.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Create Your Agent](#create-your-agent)
3. [Configure Entity Types](#configure-entity-types)
4. [Create Intents](#create-intents)
5. [Build Conversation Flows](#build-conversation-flows)
6. [Set Up Webhook Fulfillment](#set-up-webhook-fulfillment)
7. [Test Your Agent](#test-your-agent)
8. [Get Agent ID and Configure .env](#get-agent-id-and-configure-env)
9. [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

Before you begin:

✅ **Google Cloud Project** with billing enabled
✅ **Dialogflow CX API** enabled in your project
✅ **IAM Permissions**: You need the `Dialogflow API Admin` role

### Enable Dialogflow CX API

```bash
gcloud services enable dialogflow.googleapis.com
```

Or via the [Google Cloud Console](https://console.cloud.google.com/apis/library/dialogflow.googleapis.com)

---

## Create Your Agent

### Step 1: Access Dialogflow CX Console

1. Navigate to https://dialogflow.cloud.google.com/cx
2. Select your Google Cloud project from the dropdown at the top
3. Click **"Create agent"** button

### Step 2: Configure Basic Agent Settings

**Agent Configuration:**
- **Display Name**: `PawConnect AI Agent`
- **Location**: `us-central1` (or your preferred region - must match your GCP_REGION in .env)
- **Default Time Zone**: Select your time zone (e.g., `America/Los_Angeles`)
- **Default Language**: `English - en`

**Optional Settings:**
- **Description**: "Conversational agent for PawConnect pet adoption platform"
- **Enable Speech and IVR features**: ✅ (if you want voice support)
- **Enable Sentiment Analysis**: ✅ (recommended for better user experience)

Click **"Create"** to create your agent.

---

## Configure Entity Types

Entity types define the data you want to extract from user input. Create these custom entities:

### Step 3: Create Custom Entity Types

Navigate to **"Manage" → "Entity Types"** and create the following:

#### 1. Entity Type: `pet_type`

- **Display Name**: `pet_type`
- **Kind**: List
- **Entities**:
  ```
  dog        | Synonyms: dogs, puppy, puppies, canine, pup
  cat        | Synonyms: cats, kitten, kittens, feline, kitty
  rabbit     | Synonyms: rabbits, bunny, bunnies
  bird       | Synonyms: birds, parrot, parakeet
  small_furry | Synonyms: hamster, guinea pig, ferret, gerbil, mouse, rat
  ```

#### 2. Entity Type: `pet_size`

- **Display Name**: `pet_size`
- **Kind**: List
- **Entities**:
  ```
  small       | Synonyms: tiny, little, compact
  medium      | Synonyms: mid-sized, average, moderate
  large       | Synonyms: big, huge
  extra_large | Synonyms: extra large, xl, giant, very large
  ```

#### 3. Entity Type: `pet_age`

- **Display Name**: `pet_age`
- **Kind**: List
- **Entities**:
  ```
  baby   | Synonyms: puppy, kitten, newborn, infant
  young  | Synonyms: juvenile, adolescent
  adult  | Synonyms: grown, mature
  senior | Synonyms: old, elderly, older
  ```

#### 4. Entity Type: `home_type`

- **Display Name**: `home_type`
- **Kind**: List
- **Entities**:
  ```
  house     | Synonyms: single family, home
  apartment | Synonyms: flat, condo, unit
  townhouse | Synonyms: townhome, row house
  ```

#### 5. Entity Type: `experience_level`

- **Display Name**: `experience_level`
- **Kind**: List
- **Entities**:
  ```
  first_time      | Synonyms: beginner, never had, first pet, novice
  some_experience | Synonyms: had before, some, moderate, intermediate
  experienced     | Synonyms: expert, lots of experience, many pets
  ```

#### 6. Entity Type: `activity_level`

- **Display Name**: `activity_level`
- **Kind**: List
- **Entities**:
  ```
  low      | Synonyms: sedentary, not active, couch potato, lazy
  moderate | Synonyms: average, normal, somewhat active
  high     | Synonyms: very active, energetic, athletic, sporty
  ```

#### 7. Entity Type: `yes_no`

- **Display Name**: `yes_no`
- **Kind**: List
- **Entities**:
  ```
  yes | Synonyms: yeah, yep, sure, absolutely, definitely, of course
  no  | Synonyms: nope, nah, not really, negative
  ```

**Note**: For location data, use the built-in `@sys.location` entity type.

---

## Create Intents

Intents represent what users want to do. Create these intents:

### Step 4: Create Training Phrases for Each Intent

Navigate to **"Manage" → "Intents"** and create the following:

#### Intent 1: `greeting`

**Training Phrases:**
```
Hello
Hi there
Hey
Good morning
Good afternoon
Greetings
Hi
Hello there
Howdy
What's up
```

**No parameters needed for this intent.**

---

#### Intent 2: `search_pets`

**Training Phrases:**
```
I want to find a dog
Looking for a cat
Search for pets
Find me a puppy
I'm looking for a pet
Can you help me find a dog?
I need a small dog
Show me available cats
I want to adopt a dog
Search for large dogs near Seattle
```

**Parameters to Extract:**
- `pet_type` (Entity: `@pet_type`)
- `size` (Entity: `@pet_size`)
- `age` (Entity: `@pet_age`)
- `location` (Entity: `@sys.location`)

**Parameter Configuration Example:**
```
Parameter ID: pet_type
Entity Type: @pet_type
Required: No
```

---

#### Intent 3: `adopt_pet`

**Training Phrases:**
```
I want to adopt
I'd like to adopt a pet
How do I adopt?
Adoption process
I want to get a pet
Start adoption
Begin adoption process
Ready to adopt
I want to adopt this dog
```

**Parameters:**
- `pet_type` (Entity: `@pet_type`)

---

#### Intent 4: `foster_pet`

**Training Phrases:**
```
I want to foster
Foster a dog
Become a foster parent
Temporary home for a pet
Foster program
How does fostering work?
I'd like to foster a cat
Can I foster?
```

**Parameters:**
- `pet_type` (Entity: `@pet_type`)

---

#### Intent 5: `get_recommendations`

**Training Phrases:**
```
What pets match me?
Recommend a pet for me
Find the best match
What's a good pet for me?
Show me recommendations
Suggest some pets
What pet should I get?
Help me choose a pet
Match me with a pet
```

**No specific parameters needed (will use profile data).**

---

#### Intent 6: `schedule_visit`

**Training Phrases:**
```
Schedule a visit
I want to meet this pet
Book an appointment
Schedule a meet and greet
Visit the shelter
When can I visit?
Make an appointment
I'd like to meet this dog
```

**Parameters:**
- `pet_id` (Entity: `@sys.any`) - Can be extracted from context
- `date` (Entity: `@sys.date`)
- `time` (Entity: `@sys.time`)

---

#### Intent 7: `submit_application`

**Training Phrases:**
```
Apply for adoption
Submit application
I want to apply
Fill out adoption form
Start application
Application process
I'd like to apply for this pet
```

**Parameters:**
- `pet_id` (Entity: `@sys.any`)

---

#### Intent 8: `provide_preferences`

**Training Phrases:**
```
I have children
I have a yard
I live in an apartment
I have other pets
I have a dog already
I have cats at home
I'm a first-time pet owner
I'm very active
I don't have much experience
```

**Parameters:**
- `has_children` (Entity: `@yes_no`)
- `has_yard` (Entity: `@yes_no`)
- `home_type` (Entity: `@home_type`)
- `has_other_pets` (Entity: `@yes_no`)
- `experience_level` (Entity: `@experience_level`)
- `activity_level` (Entity: `@activity_level`)

---

#### Intent 9: `breed_info`

**Training Phrases:**
```
Tell me about Golden Retrievers
What is a Labrador like?
Information about German Shepherds
Describe this breed
What are Siamese cats like?
Breed characteristics
Tell me more about this breed
```

**Parameters:**
- `breed_name` (Entity: `@sys.any`)

---

#### Intent 10: `care_info`

**Training Phrases:**
```
What does a dog need?
How do I care for a cat?
Pet care requirements
What does this pet require?
Care instructions
What should I know about care?
How much exercise does it need?
```

**Parameters:**
- `pet_type` (Entity: `@pet_type`)
- `care_topic` (Entity: `@sys.any`)

---

#### Intent 11: `help`

**Training Phrases:**
```
Help
I need help
What can you do?
How does this work?
Can you assist me?
What are my options?
```

---

## Build Conversation Flows

Flows organize your conversation logic.

### Step 5: Create Main Conversation Flow

#### Default Start Flow (Modify Existing)

**Start Page:**

1. Navigate to **"Build" → "Default Start Flow"**
2. Click on the **"Start"** page

**Configure Start Page:**
- **Entry fulfillment** → Add text response:
  ```
  Hello! Welcome to PawConnect. I'm here to help you find your perfect furry friend.

  I can help you:
  • Search for available pets
  • Get personalized recommendations
  • Schedule shelter visits
  • Answer questions about breeds and pet care

  What would you like to do today?
  ```

**Add Routes from Start:**

1. Click **"+"** next to Routes
2. Create route for each intent:

**Route 1: Search Pets**
- **Intent**: `search_pets`
- **Transition**: Create new page → "Pet Search"
- **Fulfillment**:
  ```
  Great! I'll help you find the perfect pet. What type of pet are you looking for?
  ```

**Route 2: Get Recommendations**
- **Intent**: `get_recommendations`
- **Transition**: Create new page → "Collect Preferences"
- **Fulfillment**:
  ```
  I'd love to recommend some pets for you! First, let me ask you a few questions to understand your lifestyle and preferences.
  ```

**Route 3: Help**
- **Intent**: `help`
- **Transition**: Stay on current page
- **Fulfillment**:
  ```
  I can help you with:

  🐕 Search for adoptable pets by type, size, age, and location
  💝 Get personalized pet recommendations based on your lifestyle
  📅 Schedule visits to meet pets at shelters
  📋 Submit adoption applications
  ℹ️ Answer questions about breeds and pet care

  What would you like to do?
  ```

---

### Step 6: Create "Pet Search" Page

**Create New Page:**
1. Click **"+"** next to Pages
2. Name: `Pet Search`

**Configure Pet Search Page:**

**Entry Fulfillment:**
```
I'll help you search for pets. Let me gather some information:

What type of pet are you interested in? (dog, cat, rabbit, etc.)
```

**Add Form Parameters:**
1. Click **"+"** next to Parameters
2. Add required parameters:

**Parameter 1:**
- **Display Name**: `pet_type`
- **Entity Type**: `@pet_type`
- **Required**: ✅
- **Prompts**: "What type of pet would you like?"

**Parameter 2:**
- **Display Name**: `location`
- **Entity Type**: `@sys.location`
- **Required**: ✅
- **Prompts**: "What's your location (city, state, or zip code)?"

**Parameter 3:**
- **Display Name**: `size`
- **Entity Type**: `@pet_size`
- **Required**: ❌
- **Prompts**: "Any preferred size? (small, medium, large)"

**Parameter 4:**
- **Display Name**: `age`
- **Entity Type**: `@pet_age`
- **Required**: ❌
- **Prompts**: "Any age preference? (baby, young, adult, senior)"

**Condition Route (When all required parameters filled):**
- **Condition**: `$page.params.status = "FINAL"`
- **Fulfillment**:
  ```
  Perfect! Searching for $session.params.pet_type in $session.params.location...

  This will connect to your backend webhook for actual search results.
  ```
- **Transition**: Create page → "Search Results"
- **Webhook**: Enable webhook (we'll configure this later)

---

### Step 7: Create "Collect Preferences" Page

**Create New Page:**
- Name: `Collect Preferences`

**Entry Fulfillment:**
```
To give you the best recommendations, I'd like to learn about your living situation and lifestyle. This will only take a minute!
```

**Add Form Parameters:**

1. `home_type` (@home_type) - Required
   - Prompt: "What type of home do you have? (house, apartment, townhouse)"

2. `has_yard` (@yes_no) - Required
   - Prompt: "Do you have a yard?"

3. `has_children` (@yes_no) - Required
   - Prompt: "Do you have children at home?"

4. `has_other_pets` (@yes_no) - Required
   - Prompt: "Do you have any other pets?"

5. `experience_level` (@experience_level) - Required
   - Prompt: "What's your experience level with pets? (first time, some experience, experienced)"

6. `activity_level` (@activity_level) - Required
   - Prompt: "How would you describe your activity level? (low, moderate, high)"

**Condition Route (When complete):**
- **Condition**: `$page.params.status = "FINAL"`
- **Fulfillment**:
  ```
  Thank you! Based on your preferences, I'm finding the perfect matches for you...
  ```
- **Webhook**: Enable webhook (for recommendation engine)
- **Transition**: Page → "Show Recommendations"

---

### Step 8: Create "Show Recommendations" Page

**Create New Page:**
- Name: `Show Recommendations`

**Entry Fulfillment (with webhook):**
```
Here are your top pet recommendations:

[Results will be populated by webhook]

Would you like to:
• Learn more about any of these pets
• Schedule a visit
• Search for more pets
```

**Add Routes:**
- Route to "Schedule Visit" if user wants to meet
- Route to "Pet Details" if user asks for more info
- Route back to Start for new search

---

### Step 9: Create "Schedule Visit" Page

**Create New Page:**
- Name: `Schedule Visit`

**Form Parameters:**

1. `pet_id` (@sys.any) - Required
   - Prompt: "Which pet would you like to meet? (provide name or ID)"

2. `preferred_date` (@sys.date) - Required
   - Prompt: "What date works best for you?"

3. `preferred_time` (@sys.time) - Required
   - Prompt: "What time would you prefer?"

**Condition Route (Complete):**
- **Fulfillment**:
  ```
  Great! I'm scheduling your visit to meet $session.params.pet_id on $session.params.preferred_date at $session.params.preferred_time.

  I'll send you a confirmation email with all the details and the shelter location.
  ```
- **Webhook**: Enable for actual scheduling
- **Transition**: End Flow

---

## Set Up Webhook Fulfillment

Webhooks connect Dialogflow to your PawConnect backend.

### Step 10: Configure Webhook

1. Navigate to **"Manage" → "Webhooks"**
2. Click **"Create"**

**Webhook Configuration:**
- **Display Name**: `PawConnect Backend`
- **Webhook URL**: Your Cloud Function or Cloud Run URL
  - Example: `https://YOUR_REGION-YOUR_PROJECT.cloudfunctions.net/pawconnect-webhook`
  - Or: `https://pawconnect-api-XXXXX.run.app/webhook`
- **Timeout**: 30 seconds (default)
- **Authentication** (if using Cloud Functions/Run):
  - For Cloud Run: Use service account authentication
  - Add headers if needed for your API key

**Webhook Request Format:**
Your webhook will receive requests like:
```json
{
  "sessionInfo": {
    "session": "projects/PROJECT/locations/LOCATION/agents/AGENT/sessions/SESSION",
    "parameters": {
      "pet_type": "dog",
      "location": "Seattle, WA",
      "size": "medium"
    }
  },
  "fulfillmentInfo": {
    "tag": "search-pets"
  }
}
```

**Webhook Response Format:**
Your webhook should return:
```json
{
  "fulfillmentResponse": {
    "messages": [
      {
        "text": {
          "text": ["I found 15 dogs in Seattle! Here are the top matches..."]
        }
      }
    ]
  },
  "sessionInfo": {
    "parameters": {
      "search_results": [...],
      "result_count": 15
    }
  }
}
```

### Step 11: Create Webhook Tags

For each page that needs webhook fulfillment, add a webhook tag:

- **Pet Search** → Tag: `search-pets`
- **Collect Preferences** → Tag: `get-recommendations`
- **Schedule Visit** → Tag: `schedule-visit`
- **Submit Application** → Tag: `submit-application`

**To add webhook tags:**
1. Go to the page
2. Click on the route condition
3. Enable "Webhook" toggle
4. Add tag in "Webhook tag" field

---

## Test Your Agent

### Step 12: Test in Dialogflow Console

1. Click **"Test Agent"** button in the top-right corner
2. Try these test conversations:

**Test 1: Basic Search**
```
You: Hi
Agent: [Welcome message]
You: I'm looking for a dog
Agent: [Asks for location]
You: Seattle, WA
Agent: [Shows search results via webhook]
```

**Test 2: Recommendations**
```
You: Recommend a pet for me
Agent: [Asks preference questions]
You: [Answer questions about home, lifestyle, etc.]
Agent: [Shows recommendations via webhook]
```

**Test 3: Schedule Visit**
```
You: Schedule a visit
Agent: [Asks which pet]
You: Max (the Labrador)
Agent: [Asks for date]
You: Tomorrow
Agent: [Asks for time]
You: 2pm
Agent: [Confirms appointment]
```

### Step 13: Review Conversation History

- Check the **"Test Agent"** panel logs
- Review intent detection accuracy
- Verify entity extraction
- Test webhook responses

---

## Get Agent ID and Configure .env

### Step 14: Retrieve Your Agent ID

**Method 1: From Dialogflow Console**
1. Go to **"Agent Settings"** (gear icon)
2. Find the **"Agent ID"** field
3. Copy the ID (format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)

**Method 2: From URL**
When viewing your agent, the URL looks like:
```
https://dialogflow.cloud.google.com/cx/projects/PROJECT_ID/locations/REGION/agents/AGENT_ID
```
Copy the `AGENT_ID` part.

### Step 15: Update Your .env File

```env
# Dialogflow CX Configuration
DIALOGFLOW_AGENT_ID=your-agent-id-here
DIALOGFLOW_LOCATION=us-central1

# Google Cloud Project
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
```

**Important**: Make sure `DIALOGFLOW_LOCATION` matches the region where you created the agent!

---

## Advanced Configuration

### Step 16: Enable Sentiment Analysis

1. Go to **"Agent Settings"**
2. Under **"Speech and IVR"** tab
3. Enable **"Enable sentiment analysis"**
4. This helps detect user frustration and adjust responses

### Step 17: Configure Session TTL

1. In **"Agent Settings"**
2. **"General"** tab
3. **"Session TTL"**: Set to 30 minutes
   - This determines how long user context is maintained

### Step 18: Set Up Environment Versions

For production deployments:

1. Navigate to **"Manage" → "Environments"**
2. Create environments:
   - **Development**: For testing
   - **Staging**: For pre-production
   - **Production**: For live traffic

3. Create versions:
   - Click **"Create Version"**
   - Name: `v1.0-initial`
   - Description: "Initial PawConnect agent"

### Step 19: Configure Data Retention

1. **"Agent Settings"** → **"General"**
2. **"Log settings"**:
   - Enable Cloud Logging: ✅
   - Enable Stackdriver: ✅
   - Log level: Info (change to Debug for troubleshooting)

### Step 20: Set Up Multilingual Support (Optional)

If you want to support multiple languages:

1. **"Agent Settings"** → **"General"**
2. Click **"Add language"**
3. Add Spanish (es), French (fr), etc.
4. Translate training phrases and responses

---

## Integration with PawConnect Code

### Step 21: Update Your Application

Your PawConnect application should use the Dialogflow client library:

**Python Integration Example:**
```python
from google.cloud import dialogflow_cx_v3 as dialogflow_cx

def detect_intent(project_id, location, agent_id, session_id, text, language_code="en"):
    """Send text to Dialogflow CX and get response."""

    session_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}/sessions/{session_id}"

    client = dialogflow_cx.SessionsClient()

    text_input = dialogflow_cx.TextInput(text=text)
    query_input = dialogflow_cx.QueryInput(text=text_input, language_code=language_code)

    request = dialogflow_cx.DetectIntentRequest(
        session=session_path,
        query_input=query_input
    )

    response = client.detect_intent(request=request)

    return response
```

### Step 22: Implement Webhook Handler

Create a webhook endpoint in your application:

```python
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

@app.post("/webhook")
async def dialogflow_webhook(request: Request):
    """Handle Dialogflow webhook requests."""

    req = await request.json()

    tag = req.get("fulfillmentInfo", {}).get("tag")
    parameters = req.get("sessionInfo", {}).get("parameters", {})

    if tag == "search-pets":
        # Call your pet search logic
        results = await search_pets(
            pet_type=parameters.get("pet_type"),
            location=parameters.get("location")
        )
        response_text = format_search_results(results)

    elif tag == "get-recommendations":
        # Call recommendation engine
        recommendations = await get_recommendations(parameters)
        response_text = format_recommendations(recommendations)

    # ... handle other tags

    return {
        "fulfillmentResponse": {
            "messages": [
                {"text": {"text": [response_text]}}
            ]
        }
    }
```

---

## Troubleshooting

### Common Issues

**Issue 1: "Agent not found" error**
- Solution: Verify agent ID is correct in .env
- Check that DIALOGFLOW_LOCATION matches agent region

**Issue 2: Webhook timeout**
- Solution: Increase timeout in webhook settings
- Optimize your backend response time
- Add caching for common queries

**Issue 3: Intents not detected**
- Solution: Add more training phrases
- Check entity annotations are correct
- Review conversation logs in Dialogflow

**Issue 4: Parameters not extracted**
- Solution: Verify entity types are configured
- Add synonyms to entity values
- Check parameter annotations in training phrases

### Debugging Tips

1. **Use Test Agent**: Test in Dialogflow console before code integration
2. **Check Logs**: View logs in Cloud Logging
3. **Enable Debug**: Set log level to DEBUG in agent settings
4. **Test Webhooks**: Use tools like Postman to test webhook separately
5. **Monitor Quotas**: Check API usage in GCP console

---

## Next Steps

✅ **Agent Created and Configured**
✅ **Intents and Entities Defined**
✅ **Flows Built**
✅ **Webhook Integrated**

Now you can:

1. **Deploy your webhook** to Cloud Functions or Cloud Run
2. **Test end-to-end** conversation flows
3. **Monitor** agent performance and user interactions
4. **Iterate** on training phrases based on real usage
5. **Scale** by adding more intents and flows

---

## Additional Resources

- [Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- [Webhook Guide](https://cloud.google.com/dialogflow/cx/docs/concept/webhook)
- [Best Practices](https://cloud.google.com/dialogflow/cx/docs/concept/best-practices)
- [Python Client Library](https://googleapis.dev/python/dialogflow-cx/latest/)

---

**Questions or Issues?**
Check the PawConnect GitHub repository or Google Cloud Support.
