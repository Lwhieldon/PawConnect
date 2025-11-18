# Dialogflow CX Quick Start - PawConnect

**⏱️ Estimated time: 20-30 minutes**

This is a streamlined version of the setup. For detailed instructions, see [DIALOGFLOW_SETUP.md](./DIALOGFLOW_SETUP.md).

## Quick Setup Checklist

### ✅ Step 1: Enable API (2 min)
```bash
gcloud services enable dialogflow.googleapis.com
```

### ✅ Step 2: Create Agent (3 min)
1. Go to https://dialogflow.cloud.google.com/cx
2. Click **"Create agent"**
3. Settings:
   - Name: `PawConnect AI Agent`
   - Location: `us-central1` ⚠️ Must match your .env GCP_REGION
   - Language: English

### ✅ Step 3: Create Entity Types (5 min)

Create these 7 entity types under **Manage → Entity Types**:

| Entity Type | Values |
|-------------|--------|
| `pet_type` | dog, cat, rabbit, bird, small_furry |
| `pet_size` | small, medium, large, extra_large |
| `pet_age` | baby, young, adult, senior |
| `home_type` | house, apartment, townhouse |
| `experience_level` | first_time, some_experience, experienced |
| `activity_level` | low, moderate, high |
| `yes_no` | yes, no |

**Quick tip:** Use synonyms! Example for `dog`: dogs, puppy, puppies, canine, pup

### ✅ Step 4: Create Core Intents (10 min)

Create these intents under **Manage → Intents** with sample training phrases:

#### Required Intents:

**1. greeting**
```
Hi, Hello, Hey, Good morning
```

**2. search_pets** (with parameters)
```
I want to find a dog
Looking for a cat in Seattle
Search for small puppies
Find me a pet
```
Parameters: `pet_type`, `location`, `size`, `age`

**3. get_recommendations**
```
Recommend a pet for me
What pets match me?
Find the best match
```

**4. schedule_visit**
```
Schedule a visit
I want to meet this pet
Book an appointment
```
Parameters: `pet_id`, `date`, `time`

**5. help**
```
Help, What can you do?, How does this work?
```

### ✅ Step 5: Build Basic Flow (5 min)

1. Go to **Build → Default Start Flow**
2. Edit **Start** page entry fulfillment:
```
Hello! Welcome to PawConnect. I'm here to help you find your perfect furry friend.

I can help you:
• Search for available pets
• Get personalized recommendations
• Schedule shelter visits

What would you like to do today?
```

3. Create routes:
   - `search_pets` → Create page "Pet Search"
   - `get_recommendations` → Create page "Recommendations"
   - `help` → Stay on page (show help text)

### ✅ Step 6: Configure Pet Search Page (3 min)

Create **Pet Search** page with required form parameters:

1. `pet_type` (@pet_type) - Required ✅
   - Prompt: "What type of pet would you like?"

2. `location` (@sys.location) - Required ✅
   - Prompt: "What's your location?"

3. When complete → Enable webhook with tag: `search-pets`

### ✅ Step 7: Get Agent ID (1 min)

1. Click **gear icon** (Agent Settings)
2. Copy **Agent ID** (looks like: `12345678-1234-1234-1234-123456789abc`)

### ✅ Step 8: Update .env (1 min)

```env
DIALOGFLOW_AGENT_ID=your-agent-id-here
DIALOGFLOW_LOCATION=us-central1
```

### ✅ Step 9: Test (2 min)

Click **"Test Agent"** in top-right corner and try:
```
You: Hi
Agent: Welcome message
You: I want to find a dog
Agent: What's your location?
You: Seattle
Agent: [Would trigger webhook if configured]
```

---

## Minimal Working Configuration

If you want the absolute minimum to get started:

**Required:**
- ✅ Agent created
- ✅ Entity types: `pet_type`, `pet_size`
- ✅ Intents: `greeting`, `search_pets`
- ✅ One flow with Pet Search page
- ✅ Agent ID in .env

**Optional (can add later):**
- Other entity types
- Recommendation flow
- Visit scheduling
- Webhooks

---

## Quick Test Commands

Test these phrases in the Test Agent panel:

```
✅ "Hello" → Should trigger greeting
✅ "I want to find a dog" → Should trigger search_pets and ask for location
✅ "Seattle" → Should fill location parameter
✅ "Recommend a pet" → Should trigger get_recommendations
✅ "Help" → Should show help message
```

---

## Common Issues & Quick Fixes

❌ **"Agent not found"**
- Check agent ID is correct
- Verify DIALOGFLOW_LOCATION matches agent region

❌ **Intent not detected**
- Add more training phrases (aim for 10+ per intent)
- Check spelling and synonyms

❌ **Entity not extracted**
- Verify entity type exists
- Add synonyms to entity values
- Annotate entities in training phrases

❌ **Webhook not working**
- For now, disable webhooks if not deployed yet
- Agent will work for conversation flow without backend

---

## Next Steps After Quick Setup

Once basic agent is working:

1. **Add more intents** (breed_info, care_info, submit_application)
2. **Build recommendation flow** with preference questions
3. **Set up webhook** to connect to PawConnect backend
4. **Add more training phrases** (aim for 20+ per intent)
5. **Test edge cases** (typos, unexpected inputs)
6. **Enable sentiment analysis** in agent settings
7. **Review logs** in Cloud Logging

---

## Full Documentation

For complete setup including:
- All 11 intents
- Complete conversation flows
- Webhook integration
- Testing strategies
- Troubleshooting guide

See: **[DIALOGFLOW_SETUP.md](./DIALOGFLOW_SETUP.md)**

---

## Support

- 📚 [Full Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- 🎓 [Dialogflow CX Tutorials](https://codelabs.developers.google.com/?cat=Dialogflow)
- 💬 [Stack Overflow: dialogflow-cx](https://stackoverflow.com/questions/tagged/dialogflow-cx)

---

**Ready to go!** 🚀 Your basic PawConnect Dialogflow CX agent is now configured.
