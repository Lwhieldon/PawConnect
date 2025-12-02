# PawConnect Dialogflow CX - Conversation Flow Guide

This document provides a visual overview of the PawConnect AI conversation flows and how users interact with the agent.

## 🗺️ High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          START PAGE                                     │
│  "Hello! I'm PawConnect AI, your personal pet adoption assistant..."    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
        │  Pet Search   │  │ Recommendations│  │  Ask Question    │
        │               │  │                │  │                  │
        │ Collect:      │  │ Collect:       │  │  General Q&A     │
        │ - Species     │  │ - Lifestyle    │  │  about pets,     │
        │ - Breed       │  │ - Home type    │  │  breeds, care    │
        │ - Location    │  │                │  │                  │
        └───────┬───────┘  └───────┬────────┘  └──────────────────┘
                │                  │
                │    Webhook:      │    Webhook:
                │  search-pets     │  get-recommendations
                │                  │
                └──────────────────┴─────────────┐
                                                 │
                                   ┌─────────────▼───────────────┐
                                   │      Pet Details            │
                                   │                             │
                                   │  Collect: Pet ID            │
                                   │  Webhook: validate-pet-id   │
                                   │                             │
                                   │  Validates pet and shows:   │
                                   │  - Name, breed, age, sex    │
                                   │  - Shelter information      │
                                   └──────────────┬──────────────┘
                                                  │
                                   ┌──────────────▼──────────────┐
                                   │       Next Steps            │
                                   │                             │
                                   │  "What would you like to    │
                                   │   do next?"                 │
                                   └──────────────┬──────────────┘
                                                  │
                ┌─────────────────────────────────┼────────────────────────┐
                │                                 │                        │
                ▼                                 ▼                        ▼
    ┌────────────────────┐          ┌─────────────────────┐    ┌──────────────────┐
    │ Schedule Visit    │          │ Adoption Application│    │ Foster Application│
    │                   │          │                     │    │                   │
    │ Collect:          │          │ Collect:            │    │ Collect:          │
    │ - Date            │          │ - Full Name         │    │ - Full Name       │
    │ - Time            │          │ - Email             │    │ - Email           │
    │ - Name            │          │ - Phone             │    │ - Phone           │
    │ - Email           │          │ - Address           │    │ - Duration        │
    │ - Phone           │          │ - Housing Type      │    │ - Experience      │
    │                   │          │ - Yard Info         │    │                   │
    │ Webhook:          │          │ - Other Pets        │    │ Webhook:          │
    │ schedule-visit    │          │ - Experience        │    │ submit-application│
    │                   │          │ - Reason            │    │                   │
    │                   │          │                     │    │                   │
    │                   │          │ Webhook:            │    │                   │
    │                   │          │ submit-application  │    │                   │
    └─────────┬──────────┘          └──────────┬──────────┘    └─────────┬────────┘
              │                               │                          │
              │                               │                          │
              └───────────────────────────────┼──────────────────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │   Confirmation      │
                                   │                     │
                                   │ "All done! You'll   │
                                   │  receive a          │
                                   │  confirmation       │
                                   │  email shortly."    │
                                   └─────────────────────┘
```

## 📝 Page-by-Page Breakdown

### 1. START_PAGE
**Purpose:** Welcome users and introduce capabilities

**User Entry Points:**
- "I want to search for a dog"
- "Can you recommend a pet for me?"
- "I have questions about adoption"

**Transitions To:**
- Pet Search (on search intent)
- Get Recommendations (on recommendations intent)
- Ask Question (on question intent)

---

### 2. Pet Search
**Purpose:** Collect search criteria for finding pets

**Parameters Collected:**
- `species` (optional) - Dog, cat, rabbit, bird, etc.
- `breed` (optional) - Specific breed preference
- `location` (optional) - City, state, or zip code

**Webhook Integration:**
- **Tag:** `search-pets`
- **Action:** Searches RescueGroups API for matching pets
- **Returns:** List of available pets matching criteria

**Transitions To:**
- Pet Details (after search completes)

**Example Conversation:**
```
User: I want to search for a pet
Bot:  I'd be happy to help! What type of pet are you looking for?
User: A golden retriever in Seattle
Bot:  Let me search for pets matching your criteria...
      [Transitions to Pet Details]
```

---

### 3. Get Recommendations
**Purpose:** Provide personalized pet recommendations

**Parameters Collected:**
- `lifestyle` (optional) - Active, quiet, etc.
- `home_environment` (optional) - Apartment, house with yard, etc.

**Webhook Integration:**
- **Tag:** `get-recommendations`
- **Action:** Uses AI to recommend pets based on user profile
- **Returns:** Personalized pet recommendations

**Transitions To:**
- Pet Details (to view recommended pets)

---

### 4. Pet Details
**Purpose:** Validate pet ID and display detailed information

**Parameters Collected:**
- `pet_id` (required) - Unique pet identifier from RescueGroups

**Webhook Integration:**
- **Tag:** `validate-pet-id`
- **Action:** Fetches complete pet details from RescueGroups API
- **Returns:** Pet info including:
  - Name, breed, age, sex
  - Shelter name and location
  - Photos and description
  - Special needs or requirements

**Session Parameters Stored:**
- `validated_pet_id`
- `pet_name`
- `pet_breed`
- `pet_age`
- `pet_sex`
- `shelter_name`
- `shelter_city`
- `shelter_state`

**Transitions To:**
- Next Steps (after successful validation)

**Example Conversation:**
```
User: I'm interested in pet ID 12345
Bot:  Great! I found Max, a 2 year old male Golden Retriever.
      This pet is available at Seattle Animal Shelter.
      [Transitions to Next Steps]
```

---

### 5. Next Steps
**Purpose:** Present options for what to do next

**Options Presented:**
1. Schedule a visit to meet the pet
2. Submit an adoption application
3. Submit a foster application
4. Search for more pets

**Transitions To:**
- Schedule Visit (intent: schedule_visit)
- Adoption Application (intent: adoption_application)
- Foster Application (intent: foster_application)
- Pet Search (intent: search_more)

---

### 6. Schedule Visit
**Purpose:** Collect information to schedule shelter visit

**Parameters Collected:**
- `visit_date` (required) - Preferred date (sys.date)
- `visit_time` (required) - Preferred time (sys.time)
- `visitor_name` (required) - Full name
- `visitor_email` (required) - Email address (redacted in logs)
- `visitor_phone` (required) - Phone number (redacted in logs)

**Webhook Integration:**
- **Tag:** `schedule-visit`
- **Action:** Submits visit request to shelter via RescueGroups API
- **Returns:** Confirmation message with visit details

**Transitions To:**
- Confirmation (after successful scheduling)

**Example Conversation:**
```
User: I want to schedule a visit
Bot:  What date would you like to schedule your visit?
User: Next Saturday
Bot:  What time works best for you?
User: 2 PM
Bot:  May I have your full name for the visit?
User: John Doe
Bot:  What's the best email address to send the confirmation?
User: john@example.com
Bot:  And what's your phone number in case the shelter needs to reach you?
User: 555-123-4567
Bot:  Perfect! Let me schedule your visit...
      [Transitions to Confirmation]
```

---

### 7. Adoption Application
**Purpose:** Collect complete adoption application information

**Parameters Collected:**
- `applicant_name` (required) - Full name
- `applicant_email` (required) - Email (redacted)
- `applicant_phone` (required) - Phone (redacted)
- `applicant_address` (required) - Home address (redacted)
- `housing_type` (required) - Own, rent, or live with family
- `has_yard` (optional) - Yard information
- `other_pets` (optional) - Information about current pets
- `experience` (optional) - Previous pet experience
- `reason_for_adoption` (required) - Why adopting

**Webhook Integration:**
- **Tag:** `submit-application`
- **Action:** Submits adoption application to shelter
- **Returns:** Application confirmation and next steps

**Transitions To:**
- Confirmation (after successful submission)

**Privacy Features:**
- Email, phone, and address are marked as `redact: true`
- PII is not logged in Dialogflow logs

---

### 8. Foster Application
**Purpose:** Collect foster application information

**Parameters Collected:**
- `applicant_name` (required) - Full name
- `applicant_email` (required) - Email (redacted)
- `applicant_phone` (required) - Phone (redacted)
- `foster_duration` (required) - How long can foster
- `foster_experience` (optional) - Previous fostering experience

**Webhook Integration:**
- **Tag:** `submit-application`
- **Action:** Submits foster application to shelter
- **Returns:** Application confirmation and next steps

**Transitions To:**
- Confirmation (after successful submission)

---

### 9. Confirmation
**Purpose:** Confirm successful action completion

**Response:**
```
"All done! You'll receive a confirmation email shortly.
Is there anything else I can help you with?"
```

**Transitions To:**
- Pet Search (if user wants to search more)
- START_PAGE (if user wants to start over)
- End conversation (if user is done)

---

## 🎯 Intent Reference

### intent.search_pets
**Training Phrases:**
- "I want to search for a pet"
- "Show me available dogs"
- "I'm looking for a cat to adopt"
- "Can you help me find a pet"
- "Search for pets near me"

**Triggers:** Pet Search page

---

### intent.get_recommendations
**Training Phrases:**
- "What pet would be good for me"
- "Can you recommend a pet"
- "Help me find the right pet"
- "I don't know what pet to get"

**Triggers:** Get Recommendations page

---

### intent.schedule_visit
**Training Phrases:**
- "I want to schedule a visit"
- "Can I meet the pet"
- "Book a visit"
- "Set up an appointment"

**Triggers:** Schedule Visit page (from Next Steps)

---

### intent.adoption_application
**Training Phrases:**
- "I want to adopt"
- "Start adoption application"
- "Apply to adopt this pet"
- "Submit adoption application"

**Triggers:** Adoption Application page (from Next Steps)

---

### intent.foster_application
**Training Phrases:**
- "I want to foster"
- "Start foster application"
- "Apply to foster this pet"
- "I want to be a foster parent"

**Triggers:** Foster Application page (from Next Steps)

---

### intent.search_more
**Training Phrases:**
- "Show me more pets"
- "Search again"
- "Find other pets"
- "Start a new search"

**Triggers:** Pet Search page (from anywhere)

---

### intent.ask_question
**Training Phrases:**
- "What do I need to know about Golden Retrievers"
- "Tell me about cat care"
- "What's the adoption process"
- "I have a question about pets"

**Triggers:** General Q&A handling

---

## 🔧 Webhook Tags Reference

| Webhook Tag | Purpose | Parameters In | Returns |
|------------|---------|---------------|---------|
| `search-pets` | Search for available pets | species, breed, location | List of matching pets |
| `validate-pet-id` | Validate and fetch pet details | pet_id | Complete pet information |
| `get-recommendations` | Get personalized pet recommendations | lifestyle, home_environment | Recommended pets |
| `schedule-visit` | Schedule shelter visit | visit_date, visit_time, visitor info | Confirmation message |
| `submit-application` | Submit adoption/foster application | All application fields | Confirmation and next steps |

---

## 🔐 Privacy & Security Features

**Redacted Parameters:**
- All email addresses (`applicant_email`, `visitor_email`)
- All phone numbers (`applicant_phone`, `visitor_phone`)
- Home addresses (`applicant_address`)

**Sensitive Data Handling:**
- PII is not stored in Dialogflow logs
- Webhook receives all data for processing
- Data is transmitted over HTTPS
- Backend validates and sanitizes all inputs

---

## 🧪 Testing Your Agent

### Quick Test Scenarios

**Scenario 1: Pet Search Flow**
```
You: I want to search for a dog
Bot: I'd be happy to help! What type of pet are you looking for?
You: A golden retriever in Seattle
Bot: Let me search for pets matching your criteria...
     I found some pets! If you have a specific pet ID...
You: I'm interested in pet 12345
Bot: Great! I found Max, a 2 year old male Golden Retriever...
     What would you like to do next?
You: Schedule a visit
[Continues through scheduling...]
```

**Scenario 2: Recommendations Flow**
```
You: Can you recommend a pet for me?
Bot: I'd love to give you personalized recommendations!
     Tell me about your lifestyle...
You: I'm very active and have a large yard
Bot: What's your home like?
You: House with a big fenced yard
Bot: [Provides recommendations based on profile]
```

**Scenario 3: Direct Application**
```
You: I want to adopt
Bot: Let's start your adoption application...
[Proceeds directly to application form]
```

---

## 📊 Analytics & Monitoring

Track these metrics in Dialogflow CX:
- **Intent Match Rate** - How often intents are correctly matched
- **Session Abandonment** - Where users drop off
- **Parameter Fill Success** - How often parameters are successfully collected
- **Webhook Success Rate** - Webhook call success/failure rate
- **Average Session Length** - How long conversations last

---

## 🔄 Continuous Improvement

**Add Training Phrases:**
- Monitor unmatched queries in logs
- Add variations to existing intents
- Create new intents for common patterns

**Optimize Flows:**
- Reduce steps where possible
- Make optional parameters truly optional
- Add confirmation steps for important actions

**Improve Responses:**
- Use rich responses (cards, images)
- Add suggestion chips for common next actions
- Personalize responses with session parameters

---

## 📚 Related Documentation

- **[agent.json](./agent.json)** - Complete agent configuration
- **[README.md](./README.md)** - Import and setup instructions
- **[DEPLOYMENT.md](../../docs/DEPLOYMENT.md)** - Full deployment guide
- **[Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)** - Official documentation
