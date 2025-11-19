# Comprehensive Dialogflow CX Setup for PawConnect

Complete step-by-step guide to deploying the PawConnect Dialogflow CX agent with all flows, pages, intents, and webhook integrations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Create the Dialogflow CX Agent](#create-the-dialogflow-cx-agent)
3. [Manage Section Setup](#manage-section-setup)
   - [Webhooks](#webhooks)
   - [Entity Types](#entity-types)
   - [Intents](#intents)
4. [Build Section Setup](#build-section-setup)
   - [Flows](#flows)
   - [Pages](#pages)
5. [Testing](#testing)
6. [Integration & Deployment](#integration--deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Google Cloud Project Setup

**Requirements:**
- Google Cloud project with billing enabled
- Dialogflow CX API enabled
- Cloud Run service deployed (webhook)

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project: `[Your Project Name Here]`
3. Enable Dialogflow CX API:
   - Navigate to **APIs & Services** → **Library**
   - Search for "Dialogflow CX"
   - Click **Enable**

### 2. Webhook Deployment

Ensure your PawConnect webhook is deployed and running:

```bash
# Verify webhook is running
curl https://[insert-url-here]/health

# Expected response:
# {"status":"healthy","service":"pawconnect-dialogflow-webhook"}
```

**Webhook URL:** `https:/[insert-url-here]/webhook`

### 3. RescueGroups API Key

Ensure you have:
- ✅ RescueGroups API key configured in Cloud Run environment variables
- ✅ API key has proper permissions

---

## Create the Dialogflow CX Agent

### Step 1: Navigate to Dialogflow CX

1. Go to [Dialogflow CX Console](https://dialogflow.cloud.google.com/cx)
2. Sign in with your Google account
3. Select your project: `[Your Project Name Here]`
4. Select region: `[Your Region]` (same as Cloud Run)

### Step 2: Create New Agent

1. Click **Create agent**
2. Configure agent settings:

```yaml
Display name: PawConnect Agent
Location: [Your Region]
Time zone: (UTC-08:00) America/Los_Angeles (or your timezone)
Default language: English - en
```

3. Click **Create**

### Step 3: Agent Settings (Optional)

1. Click the agent name → **Agent Settings**
2. Configure:
   - **Speech and IVR**: Enable if using voice
   - **General**:
     - Enable logging: ✅
     - Enable stackdriver logging: ✅
   - **ML Settings**:
     - Confidence threshold: `0.3` (default)
     - Classification threshold: `0.3` (default)

3. Click **Save**

---

## Manage Section Setup

Navigate to **Manage** in the left sidebar for all configurations below.

---

### Webhooks

#### Create PawConnect Webhook

**Navigation:** Manage → Webhooks

1. Click **Create**
2. Configure webhook:

```yaml
Display name: PawConnect Webhook
Webhook URL: https://[Insert URL Here]/webhook
Webhook service: Standard webhook
Timeout: 60 seconds
```

3. Leave authentication empty (public Cloud Run service)
4. Click **Save**

**Webhook Tags Supported:**
- `search-pets` - Search for available pets
- `validate-pet-id` - Validate and fetch pet details
- `get-recommendations` - Get personalized recommendations
- `schedule-visit` - Schedule a shelter visit
- `submit-application` - Start adoption application

> **Note:** Tags are configured when using the webhook in pages, not here.

---

### Entity Types

Create custom entity types for better NLP understanding.

**Navigation:** Manage → Entity Types

---

#### 1. Pet Type Entity

1. Click **Create**
2. Configure:

```yaml
Display name: pet-type
Entity entries:
  - dog
    Synonyms: dog, dogs, puppy, puppies, canine, pup
  - cat
    Synonyms: cat, cats, kitten, kittens, feline, kitty
  - rabbit
    Synonyms: rabbit, rabbits, bunny, bunnies
  - bird
    Synonyms: bird, birds, parrot, parakeet, cockatiel
  - small_furry
    Synonyms: hamster, guinea pig, gerbil, ferret, small pet
```

3. Advanced options:
   - ✅ Enable fuzzy matching
   - ✅ Enable redact in log
4. Click **Save**

---

#### 2. Pet Size Entity

1. Click **Create**
2. Configure:

```yaml
Display name: pet-size
Entity entries:
  - small
    Synonyms: small, tiny, little, petite, compact
  - medium
    Synonyms: medium, mid-size, average, moderate
  - large
    Synonyms: large, big, sizeable
  - extra_large
    Synonyms: extra large, xl, giant, huge, very large
```

3. ✅ Enable fuzzy matching
4. Click **Save**

---

#### 3. Pet Age Entity

1. Click **Create**
2. Configure:

```yaml
Display name: pet-age
Entity entries:
  - baby
    Synonyms: baby, puppy, kitten, newborn, infant
  - young
    Synonyms: young, juvenile, adolescent, teenager
  - adult
    Synonyms: adult, mature, grown
  - senior
    Synonyms: senior, elderly, old, aged
```

3. ✅ Enable fuzzy matching
4. Click **Save**

---

#### 4. Pet ID Entity

1. Click **Create**
2. Configure:

```yaml
Display name: pet-id
Entity entries:
  - 12345
    Synonyms: 12345, #12345, pet 12345, pet-12345
  - abc789
    Synonyms: abc789, #abc789, pet abc789
  - (Add more example IDs from RescueGroups)
```

3. Advanced options:
   - ✅ Enable fuzzy matching
   - ✅ Enable redact in log (for privacy)
4. Click **Save**

---

#### 5. Location Entity (Optional)

You can use `@sys.geo-city` or create custom:

```yaml
Display name: location
Entity entries:
  - seattle
    Synonyms: Seattle, Seattle WA, Seattle Washington
  - 98101
    Synonyms: 98101, zip 98101
  - (Add your target locations)
```

---

### Intents

Create intents that recognize user utterances.

**Navigation:** Manage → Intents

---

#### 1. search.pets Intent

**Purpose:** User wants to search for pets

1. Click **Create**
2. Configure:

```yaml
Display name: search.pets
Description: User wants to search for available pets
```

3. Add **Training Phrases** (20+ recommended):

```
I'm looking for a dog
Find me a cat near Seattle
Search for pets in 98101
I want to adopt a dog
Show me available cats
Are there any puppies available?
I'm interested in adopting a pet
Find dogs in my area
Search for small dogs
I want a kitten
Looking for a pet to adopt
Show me pets near me
I need a furry friend
Find me a companion animal
Search for adoptable dogs
Are there cats available for adoption?
I want to find a pet
Help me find a dog to adopt
Show me available animals
Looking for a rescue dog
```

4. **Annotate parameters** in training phrases:
   - Highlight `dog`, `cat`, `kitten` → Entity: `@pet-type`, Parameter: `pet_type`
   - Highlight `Seattle`, `98101` → Entity: `@sys.geo-city`, Parameter: `location`
   - Highlight `small` → Entity: `@pet-size`, Parameter: `pet_size`

5. Click **Save**

---

#### 2. validate.pet.id Intent

**Purpose:** User provides a pet ID to learn more

1. Click **Create**
2. Configure:

```yaml
Display name: validate.pet.id
Description: User wants to validate and learn about a specific pet ID
```

3. Add **Training Phrases**:

```
Tell me about pet 12345
I'm interested in pet abc789
What can you tell me about pet #456
Show me details for pet XYZ123
I want to know about pet 789
Pet 12345 looks interesting
Can you give me info on pet ABC123?
Tell me more about pet number 456
I saw pet 999 on the website
Pet ID 12345 please
Show me pet #789
I'm curious about pet DOG123
What's the story with pet 456?
Pet abc789 info please
More details on pet 12345
I want to learn about pet #999
Can you look up pet XYZ789?
Pet 123 information
Tell me about pet CAT456
Show details for pet number 789
```

4. **Annotate parameters**:
   - Highlight pet IDs (12345, abc789, etc.) → Entity: `@pet-id`, Parameter: `pet_id`

5. Click **Save**

---

#### 3. schedule.visit Intent

**Purpose:** User wants to schedule a visit

1. Click **Create**
2. Configure:

```yaml
Display name: schedule.visit
Description: User wants to schedule a visit to meet a pet
```

3. Add **Training Phrases**:

```
I want to schedule a visit
Can I meet the pet?
Schedule a visit for tomorrow
Book an appointment to see the pet
I'd like to visit the pet
Can I come see the pet on Friday?
Schedule a time to meet the pet
I want to meet the pet tomorrow at 2pm
Book a visit for next week
Can I visit on Monday?
I'd like to come by and meet the pet
Schedule an appointment
When can I meet the pet?
I want to visit the shelter
Can I see the pet in person?
Schedule a meeting with the pet
I'd like to arrange a visit
Book a time to see the pet
Can I come visit tomorrow?
I want to meet the pet this weekend
```

4. **Annotate parameters**:
   - Highlight `tomorrow`, `Friday`, `next week` → Entity: `@sys.date`, Parameter: `date`
   - Highlight `2pm` → Entity: `@sys.time`, Parameter: `time`

5. Click **Save**

---

#### 4. schedule.visit.with.pet.id Intent

**Purpose:** User wants to schedule a visit for a specific pet ID

1. Click **Create**
2. Configure:

```yaml
Display name: schedule.visit.with.pet.id
Description: User wants to schedule a visit for a specific pet by ID
```

3. Add **Training Phrases**:

```
I want to schedule a visit for pet 12345
Can I meet pet abc789 tomorrow at 2pm?
Book an appointment for pet #456
Schedule a visit to see pet XYZ123
I'd like to visit pet 789 next Friday at 3pm
Can I come see pet ABC123 on Monday at 10am?
Schedule a visit for pet 12345 tomorrow
I want to meet pet #999 this weekend
Book a time to see pet DOG123 on the 15th at 2pm
Visit pet 456 next Tuesday
Schedule pet 789 for Wednesday at noon
I want to see pet CAT123 on Friday afternoon
Meet pet 456 tomorrow morning
Visit for pet #789 on Saturday
Schedule appointment for pet ABC456 next week
Can I visit pet 12345 on Monday at 11am?
Book pet 789 for tomorrow at 3pm
Schedule to see pet XYZ456 on the 20th
Meet with pet 999 next Friday
Visit pet DOG789 this Saturday at 2pm
```

4. **Annotate parameters**:
   - Pet IDs → Entity: `@pet-id`, Parameter: `pet_id`
   - Dates → Entity: `@sys.date`, Parameter: `date`
   - Times → Entity: `@sys.time`, Parameter: `time`

5. Click **Save**

---

#### 5. submit.application Intent

**Purpose:** User wants to submit adoption application

1. Click **Create**
2. Configure:

```yaml
Display name: submit.application
Description: User wants to submit an adoption or foster application
```

3. Add **Training Phrases**:

```
I want to adopt this pet
I'd like to submit an application
Start the adoption process
I want to apply for adoption
Begin the application
I'd like to adopt
Can I apply to adopt this pet?
Start adoption application
I want to fill out an application
Submit an application for this pet
I'd like to foster this pet
Apply for fostering
I want to adopt the pet
Can I start the adoption paperwork?
I'm ready to apply
I want to move forward with adoption
Submit my application
I'd like to apply for this pet
Start the foster application
I want to complete an adoption application
```

4. Click **Save**

---

#### 6. get.recommendations Intent

**Purpose:** User wants personalized pet recommendations

1. Click **Create**
2. Configure:

```yaml
Display name: get.recommendations
Description: User wants personalized pet recommendations based on preferences
```

3. Add **Training Phrases**:

```
Show me recommendations
What pets would be good for me?
Recommend some pets
Which pets match my lifestyle?
Can you suggest some pets?
What would be a good match?
Show me the best matches
Recommend pets for me
What pets do you think I'd like?
Give me some suggestions
Which pets are best for me?
Show me personalized recommendations
What pets match my preferences?
Suggest pets based on my lifestyle
Show me my best matches
Which pets would suit me?
Recommend the best pets
Show me compatible pets
What are my top matches?
Give me pet recommendations
```

4. Click **Save**

---

#### 7. provide.location Intent

**Purpose:** User provides their location

1. Click **Create**
2. Configure:

```yaml
Display name: provide.location
Description: User provides their location for pet search
```

3. Add **Training Phrases**:

```
I'm in Seattle
My zip code is 98101
I live in New York
Seattle, WA
98101
I'm located in Los Angeles
My location is San Francisco
I'm in the 98101 area
Chicago, IL
60601
I live in Portland
My zip is 90210
I'm in Boston
Seattle Washington
Zip code 10001
```

4. **Annotate parameters**:
   - Highlight locations → Entity: `@sys.geo-city`, Parameter: `location`
   - Highlight zip codes → Entity: `@sys.any`, Parameter: `location`

5. Click **Save**

---

#### 8. greeting Intent (Optional but recommended)

1. Click **Create**
2. Configure:

```yaml
Display name: greeting
Description: User greets the agent
```

3. Add **Training Phrases**:

```
Hello
Hi
Hey there
Good morning
Good afternoon
Hi there
Greetings
Hey
Hello there
Good day
```

4. Click **Save**

---

#### 9. goodbye Intent (Optional)

1. Click **Create**
2. Configure:

```yaml
Display name: goodbye
Description: User wants to end conversation
```

3. Add **Training Phrases**:

```
Goodbye
Bye
See you later
Talk to you later
That's all
I'm done
Thanks, goodbye
Bye bye
See you
Take care
```

4. Click **Save**

---

## Build Section Setup

Navigate to **Build** in the left sidebar.

---

### Flows

Flows organize conversation logic into manageable sections.

**Recommended Flow Structure:**

```
PawConnect Agent
├── Default Start Flow (pre-existing)
│   ├── Start Page
│   ├── Welcome & Greeting
│   └── Route to other flows
├── Pet Search Flow
│   ├── Search Pets
│   ├── View Results
│   └── Get Recommendations
├── Pet Details Flow
│   ├── Validate Pet ID
│   ├── View Pet Details
│   └── Next Actions
├── Visit Scheduling Flow
│   ├── Schedule Visit
│   ├── Confirm Details
│   └── Confirmation
└── Adoption Application Flow
    ├── Start Application
    ├── Collect Information
    └── Submit Application
```

---

### Create Flows

#### 1. Default Start Flow (Already exists)

This is the entry point. We'll configure it later.

---

#### 2. Pet Search Flow

1. Click **Create Flow**
2. Configure:

```yaml
Display name: Pet Search Flow
Description: Handle pet search and recommendations
```

3. Click **Save**

---

#### 3. Pet Details Flow

1. Click **Create Flow**
2. Configure:

```yaml
Display name: Pet Details Flow
Description: Validate pet IDs and show pet details
```

3. Click **Save**

---

#### 4. Visit Scheduling Flow

1. Click **Create Flow**
2. Configure:

```yaml
Display name: Visit Scheduling Flow
Description: Schedule shelter visits to meet pets
```

3. Click **Save**

---

#### 5. Adoption Application Flow

1. Click **Create Flow**
2. Configure:

```yaml
Display name: Adoption Application Flow
Description: Handle adoption and foster applications
```

3. Click **Save**

---

### Pages

Now we'll create pages within each flow.

---

## Default Start Flow Pages

Click on **Default Start Flow** to open it.

### Start Page (Already exists)

Configure the Start page to route to other flows.

#### Entry Fulfillment

1. Click on **Start** page
2. Scroll to **Entry fulfillment**
3. Click **Edit fulfillment**
4. Add text response:

```
Welcome to PawConnect! I'm here to help you find your perfect pet companion.
I can help you search for pets, learn about specific animals, schedule visits,
or start an adoption application. What would you like to do?
```

5. Click **Save**

---

#### Add Routes to Start Page

We'll add routes to handle intents and navigate to flows.

##### Route 1: Greeting Intent

1. Scroll to **Routes** section
2. Click **Add route**
3. Configure:

```yaml
Intent: greeting
Condition: (leave empty)
Fulfillment text:
  Hello! I'm PawConnect, your pet adoption assistant.
  I can help you search for pets, learn about specific animals,
  schedule visits, or start an adoption application.
  What would you like to do today?
Transition: (None - stay on Start page)
```

4. Click **Save**

---

##### Route 2: Search Pets Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: search.pets
Condition: (leave empty)
Fulfillment text: Let me help you search for pets!
Transition: Pet Search Flow → Search Pets page
```

3. Click **Save**

---

##### Route 3: Validate Pet ID Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: validate.pet.id
Condition: (leave empty)
Fulfillment text: Let me look up that pet for you.
Transition: Pet Details Flow → Validate Pet ID page
```

3. Click **Save**

---

##### Route 4: Schedule Visit Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: schedule.visit
Condition: (leave empty)
Fulfillment text: I'll help you schedule a visit!
Transition: Visit Scheduling Flow → Schedule Visit page
```

3. Click **Save**

---

##### Route 5: Schedule Visit with Pet ID Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: schedule.visit.with.pet.id
Condition: (leave empty)
Fulfillment text: Let me schedule that visit for you.
Transition: Visit Scheduling Flow → Schedule Visit with Pet ID page
```

3. Click **Save**

---

##### Route 6: Submit Application Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: submit.application
Condition: (leave empty)
Fulfillment text: Wonderful! Let me start your adoption application.
Transition: Adoption Application Flow → Submit Application page
```

3. Click **Save**

---

##### Route 7: Goodbye Intent

1. Click **Add route**
2. Configure:

```yaml
Intent: goodbye
Condition: (leave empty)
Fulfillment text:
  Thank you for using PawConnect! Good luck finding your perfect pet.
  Feel free to come back anytime!
Transition: End Session
```

3. Click **Save**

---

## Pet Search Flow Pages

Click on **Pet Search Flow** to open it.

---

### Page 1: Search Pets

Create the main search page with webhook integration.

#### Create Page

1. In Pet Search Flow, click **"+"** or **Add page**
2. **Display name**: `Search Pets`
3. Click **Save**

#### Configure Entry Fulfillment

1. Click on **Search Pets** page
2. Scroll to **Entry fulfillment**
3. Click **Edit fulfillment**
4. Add text:

```
I'll help you search for adoptable pets. Let me get some information first.
```

5. Click **Save**

---

#### Add Parameters

1. Scroll to **Parameters** section

**Parameter 1: location**

2. Click **Add parameter**
3. Configure:

```yaml
Display name: location
Entity type: @sys.geo-city
Required: ✅ Yes
```

4. Click on the parameter to expand
5. Under **Initial prompt fulfillment**, add:

```
What's your location? Please provide your ZIP code or city name.
```

6. Click **Save**

---

**Parameter 2: pet_type**

1. Click **Add parameter**
2. Configure:

```yaml
Display name: pet_type
Entity type: @pet-type
Required: ❌ No (optional)
```

3. Click **Save**

---

**Parameter 3: pet_size**

1. Click **Add parameter**
2. Configure:

```yaml
Display name: pet_size
Entity type: @pet-size
Required: ❌ No (optional)
```

---

**Parameter 4: pet_age**

1. Click **Add parameter**
2. Configure:

```yaml
Display name: pet_age
Entity type: @pet-age
Required: ❌ No (optional)
```

---

#### Configure Fulfillment (Webhook)

1. Scroll to **Fulfillment** section
2. Click **Edit fulfillment**
3. Configure:

```yaml
Enable webhook: ✅ ON
Tag: search-pets
Webhook: PawConnect Webhook
Timeout: 60 seconds
```

4. Optionally add fallback text response:

```
Let me search for pets matching your criteria...
```

5. ✅ Check **"Use webhook response"**
6. Click **Save**

---

#### Add Completion Route

1. Scroll to **Routes** section
2. Click **Add route**
3. Configure:

```yaml
Condition: $page.params.status = "FINAL"
Fulfillment: (use webhook response)
Transition: Get Recommendations page
```

4. Click **Save**

---

### Page 2: Get Recommendations

#### Create Page

1. Click **"+"** to add new page
2. **Display name**: `Get Recommendations`
3. Click **Save**

#### Configure Entry Fulfillment

```
Based on your preferences, let me find the best pet matches for you!
```

#### Add Parameters

**Use session parameters from previous page:**
- `$session.params.location`
- `$session.params.pet_type`

No new parameters needed unless collecting additional preferences.

#### Configure Fulfillment (Webhook)

```yaml
Enable webhook: ✅ ON
Tag: get-recommendations
Webhook: PawConnect Webhook
Timeout: 60 seconds
Use webhook response: ✅
```

#### Add Routes

**Route 1: View specific pet**

```yaml
Intent: validate.pet.id
Transition: Pet Details Flow → Validate Pet ID page
```

**Route 2: Schedule visit**

```yaml
Intent: schedule.visit.with.pet.id
Transition: Visit Scheduling Flow → Schedule Visit with Pet ID page
```

**Route 3: New search**

```yaml
Intent: search.pets
Transition: Pet Search Flow → Search Pets page
```

---

### Page 3: No Results

Create a fallback page if no pets found.

#### Create Page

```yaml
Display name: No Results
```

#### Entry Fulfillment

```
I couldn't find any pets matching your criteria.
Would you like to:
- Expand your search area
- Try different criteria
- Get notified when matching pets become available
```

#### Routes

```yaml
Route 1: New search → Search Pets page
Route 2: End session
```

---

## Pet Details Flow Pages

Click on **Pet Details Flow** to open it.

---

### Page 1: Validate Pet ID

Validate and fetch pet details from RescueGroups API.

#### Create Page

```yaml
Display name: Validate Pet ID
Description: Validate pet ID and fetch details from API
```

#### Entry Fulfillment

```
Let me look up that pet for you...
```

#### Add Parameters

**Parameter: pet_id**

```yaml
Display name: pet_id
Entity type: @pet-id (or @sys.any)
Required: ✅ Yes
Initial prompt: What's the pet ID you'd like to learn more about?
Redact in log: ✅ (optional, for privacy)
```

#### Configure Fulfillment (Webhook)

```yaml
Enable webhook: ✅ ON
Tag: validate-pet-id
Webhook: PawConnect Webhook
Timeout: 60 seconds
Use webhook response: ✅
```

**The webhook will return and store in session:**
- `validated_pet_id`
- `pet_name`
- `pet_breed`
- `pet_age`
- `pet_sex`
- `shelter_name`
- `shelter_city`
- `shelter_state`

---

#### Add Routes

**Route 1: Pet Found - Schedule Visit**

```yaml
Condition: $session.params.validated_pet_id != null
Intent: schedule.visit
Fulfillment: Great! Let me schedule your visit to meet $session.params.pet_name.
Transition: Visit Scheduling Flow → Schedule Visit page
```

**Route 2: Pet Found - Apply**

```yaml
Condition: $session.params.validated_pet_id != null
Intent: submit.application
Fulfillment: Wonderful! Let's start your application for $session.params.pet_name.
Transition: Adoption Application Flow → Submit Application page
```

**Route 3: Pet Not Found**

```yaml
Condition: $session.params.validated_pet_id = null
Fulfillment: I couldn't find that pet ID. Would you like to search for other pets?
Transition: Pet Search Flow → Search Pets page (or End Session)
```

**Route 4: Auto-transition on success**

```yaml
Condition: $page.params.status = "FINAL"
Transition: View Pet Details page
```

---

### Page 2: View Pet Details

Display detailed information about the validated pet.

#### Create Page

```yaml
Display name: View Pet Details
```

#### Entry Fulfillment

```
Here's what I know about $session.params.pet_name:

Name: $session.params.pet_name
Breed: $session.params.pet_breed
Age: $session.params.pet_age
Gender: $session.params.pet_sex
Location: $session.params.shelter_name in $session.params.shelter_city, $session.params.shelter_state

Would you like to:
- Schedule a visit to meet $session.params.pet_name
- Submit an adoption application
- Search for other pets
```

#### Add Routes

```yaml
Route 1: Schedule Visit
  Intent: schedule.visit
  Transition: Visit Scheduling Flow → Schedule Visit page

Route 2: Submit Application
  Intent: submit.application
  Transition: Adoption Application Flow → Submit Application page

Route 3: Search Again
  Intent: search.pets
  Transition: Pet Search Flow → Search Pets page

Route 4: End conversation
  Intent: goodbye
  Transition: End Session
```

---

## Visit Scheduling Flow Pages

Click on **Visit Scheduling Flow** to open it.

---

### Page 1: Schedule Visit

Schedule a visit without specific pet ID (will use session data).

#### Create Page

```yaml
Display name: Schedule Visit
```

#### Entry Fulfillment

```
I'll help you schedule a visit to meet the pet at the shelter.
```

#### Add Parameters

**Parameter 1: date**

```yaml
Display name: date
Entity type: @sys.date
Required: ✅ Yes
Initial prompt: What date would you like to visit?
```

**Parameter 2: time**

```yaml
Display name: time
Entity type: @sys.time
Required: ✅ Yes
Initial prompt: What time works best for you?
```

**Parameter 3: pet_id (from session)**

This comes from `$session.params.validated_pet_id` - no need to collect.

#### Configure Fulfillment (Webhook)

```yaml
Enable webhook: ✅ ON
Tag: schedule-visit
Webhook: PawConnect Webhook
Timeout: 60 seconds
Use webhook response: ✅
```

#### Add Routes

```yaml
Route 1: Success
  Condition: $page.params.status = "FINAL"
  Fulfillment: (use webhook response)
  Transition: Visit Confirmation page

Route 2: Schedule another
  Intent: schedule.visit
  Transition: Schedule Visit page (loop back)
```

---

### Page 2: Schedule Visit with Pet ID

For when user provides pet ID directly in scheduling request.

#### Create Page

```yaml
Display name: Schedule Visit with Pet ID
```

#### Entry Fulfillment

```
Let me schedule your visit to meet the pet.
```

#### Add Parameters

**Parameter 1: pet_id**

```yaml
Display name: pet_id
Entity type: @pet-id
Required: ✅ Yes
Initial prompt: What's the pet ID you'd like to visit?
```

**Parameter 2: date**

```yaml
Display name: date
Entity type: @sys.date
Required: ✅ Yes
Initial prompt: What date would you like to visit?
```

**Parameter 3: time**

```yaml
Display name: time
Entity type: @sys.time
Required: ✅ Yes
Initial prompt: What time works best for you?
```

#### Configure Fulfillment (Webhook)

**Option A: Two-stage (Recommended)**

First validate pet ID, then schedule:

1. Call webhook with tag `validate-pet-id` to verify pet exists
2. If successful, call webhook with tag `schedule-visit` to book appointment

**Option B: Single-stage (Simpler)**

```yaml
Enable webhook: ✅ ON
Tag: schedule-visit
Webhook: PawConnect Webhook
Timeout: 60 seconds
Use webhook response: ✅
```

#### Add Routes

```yaml
Route 1: Success
  Condition: $page.params.status = "FINAL"
  Transition: Visit Confirmation page

Route 2: Invalid Pet ID
  Condition: (check for error in webhook response)
  Fulfillment: I couldn't find that pet. Please check the ID and try again.
  Transition: Pet Details Flow → Validate Pet ID page
```

---

### Page 3: Visit Confirmation

Confirm the scheduled visit.

#### Create Page

```yaml
Display name: Visit Confirmation
```

#### Entry Fulfillment

```
Perfect! Your visit has been scheduled:

Pet: $session.params.pet_name
Date: $session.params.date
Time: $session.params.time
Location: $session.params.shelter_name

You'll receive a confirmation email shortly with the shelter's address
and any special instructions.

Is there anything else I can help you with?
```

#### Add Routes

```yaml
Route 1: Submit application
  Intent: submit.application
  Fulfillment: Great! Let's start your adoption application.
  Transition: Adoption Application Flow → Submit Application page

Route 2: Search for more pets
  Intent: search.pets
  Transition: Pet Search Flow → Search Pets page

Route 3: End
  Intent: goodbye
  Transition: End Session
```

---

## Adoption Application Flow Pages

Click on **Adoption Application Flow** to open it.

---

### Page 1: Submit Application

Start the adoption application process.

#### Create Page

```yaml
Display name: Submit Application
```

#### Entry Fulfillment

```
Excellent! I'm starting your adoption application for $session.params.pet_name.
I'll need some information from you to complete the application.
```

#### Add Parameters

**Parameter: pet_id (from session)**

Use `$session.params.validated_pet_id` - no need to collect again.

If not in session:

```yaml
Display name: pet_id
Entity type: @pet-id
Required: ✅ Yes
Initial prompt: Which pet would you like to apply for? Please provide the pet ID.
```

#### Configure Fulfillment (Webhook)

```yaml
Enable webhook: ✅ ON
Tag: submit-application
Webhook: PawConnect Webhook
Timeout: 60 seconds
Use webhook response: ✅
```

The webhook will ask for user information and start the application process.

#### Add Routes

```yaml
Route 1: Application started
  Condition: $page.params.status = "FINAL"
  Transition: Collect User Info page

Route 2: Invalid pet
  Condition: (check for error)
  Transition: Pet Details Flow → Validate Pet ID page
```

---

### Page 2: Collect User Info

Collect applicant information.

#### Create Page

```yaml
Display name: Collect User Info
```

#### Entry Fulfillment

```
Let's start with your contact information. What's your full name?
```

#### Add Parameters

**Parameter 1: full_name**

```yaml
Display name: full_name
Entity type: @sys.person
Required: ✅ Yes
Initial prompt: What's your full name?
```

**Parameter 2: email**

```yaml
Display name: email
Entity type: @sys.email
Required: ✅ Yes
Initial prompt: What's your email address?
```

**Parameter 3: phone**

```yaml
Display name: phone
Entity type: @sys.phone-number
Required: ✅ Yes
Initial prompt: What's your phone number?
```

**Parameter 4: address**

```yaml
Display name: address
Entity type: @sys.location (or @sys.any)
Required: ✅ Yes
Initial prompt: What's your home address?
```

#### Add Routes

```yaml
Route 1: Information collected
  Condition: $page.params.status = "FINAL"
  Transition: Application Confirmation page
```

---

### Page 3: Application Confirmation

Confirm application submission.

#### Create Page

```yaml
Display name: Application Confirmation
```

#### Entry Fulfillment

```
Thank you, $session.params.full_name!

Your adoption application for $session.params.pet_name has been submitted successfully!

Application Details:
- Pet: $session.params.pet_name
- Applicant: $session.params.full_name
- Email: $session.params.email
- Phone: $session.params.phone

The shelter will review your application and contact you within 2-3 business days.

You'll receive a confirmation email at $session.params.email shortly.

Is there anything else I can help you with today?
```

#### Add Routes

```yaml
Route 1: Search more pets
  Intent: search.pets
  Transition: Pet Search Flow → Search Pets page

Route 2: Schedule visit
  Intent: schedule.visit
  Fulfillment: Would you also like to schedule a visit while we process your application?
  Transition: Visit Scheduling Flow → Schedule Visit page

Route 3: End
  Intent: goodbye
  Transition: End Session
```

---

## Testing

### Test in Simulator

1. Click **Test Agent** button (top right corner)
2. Try these test conversations:

---

#### Test Scenario 1: Full Pet Search Flow

```
User: Hi
Agent: Hello! I'm PawConnect... What would you like to do today?

User: I'm looking for a dog
Agent: I'll help you search for pets! Let me get some information first.
       What's your location?

User: Seattle
Agent: Let me search for pets matching your criteria...
       [Webhook response with search results]

User: Show me recommendations
Agent: Based on your preferences, let me find the best pet matches for you!
       [Webhook response with recommendations]
```

---

#### Test Scenario 2: Pet ID Validation & Visit Scheduling

```
User: Tell me about pet 12345
Agent: Let me look up that pet for you...
       [Webhook validates and returns pet details]
       Great! I found [PetName], a [breed]...

User: I want to schedule a visit tomorrow at 2pm
Agent: Let me schedule your visit to meet [PetName].
       [Webhook schedules visit]
       Perfect! Your visit has been scheduled...
```

---

#### Test Scenario 3: Direct Visit Scheduling with Pet ID

```
User: Schedule a visit for pet 789 on Friday at 3pm
Agent: Let me schedule your visit to meet the pet.
       [Parameters collected: pet_id=789, date=Friday, time=3pm]
       [Webhook schedules visit]
       Perfect! Visit scheduled for Friday at 3pm...
```

---

#### Test Scenario 4: Application Submission

```
User: I want to adopt pet abc123
Agent: Let me look up that pet...
       [Validates pet]
       Wonderful! Let's start your adoption application.

Agent: Let's start with your contact information. What's your full name?
User: John Smith

Agent: What's your email address?
User: john@example.com

Agent: What's your phone number?
User: 555-1234

Agent: What's your home address?
User: 123 Main St, Seattle WA

Agent: Thank you, John Smith! Your adoption application has been submitted...
```

---

### Verify Webhook Calls

1. In the simulator, click on a response
2. Click **"⋮"** → **View fulfillment details**
3. Check:
   - ✅ Webhook name: PawConnect Webhook
   - ✅ Tag: correct tag for the action
   - ✅ Parameters sent
   - ✅ Response received

---

### Check Cloud Run Logs

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Cloud Run** → **pawconnect-webhook**
3. Click **Logs** tab
4. Filter by severity: **INFO** and **ERROR**
5. Look for:
   ```
   INFO: Received webhook request: {...}
   INFO: Validating pet ID: 12345
   INFO: Searching for pets: type=dog, location=Seattle
   ```

---

### Test Edge Cases

Test these scenarios to ensure error handling:

```
❌ Invalid pet ID
User: Tell me about pet 99999
Expected: "I couldn't find a pet with ID '99999'..."

❌ Missing location
User: Search for dogs
Expected: "What's your location? Please provide your ZIP code or city name."

❌ Past date
User: Schedule a visit for yesterday
Expected: (Should handle gracefully or ask for valid future date)

❌ Invalid time
User: Schedule at 25:00
Expected: "What time works best for you?" (re-prompt)
```

---

## Integration & Deployment

### 1. Integrate with Website/App

#### Get Agent ID

1. Go to **Agent Settings**
2. Copy your **Agent ID**
3. Note your **Location**: `[Your Region]`
4. Format: `projects/{project}/locations/{location}/agents/{agent}`

Example:
```
projects/[Your Project Name]/locations/us-central1/agents/{agent-id}
```

---

#### Dialogflow CX Integration Options

**Option A: Web Chat Widget**

1. Go to **Integrations** in Dialogflow CX
2. Click **Dialogflow Messenger**
3. Enable integration
4. Copy the HTML snippet
5. Add to your website:

```html
<script src="https://www.gstatic.com/dialogflow-console/fast/messenger/bootstrap.js?v=1"></script>
<df-messenger
  chat-title="PawConnect"
  agent-id="your-agent-id"
  language-code="en"
  chat-icon="https://your-logo.png">
</df-messenger>
```

---

**Option B: Custom Integration via API**

Use Dialogflow CX API to send/receive messages:

```python
from google.cloud import dialogflowcx_v3 as dialogflow

def detect_intent(project_id, location, agent_id, session_id, text):
    client = dialogflow.SessionsClient()
    session_path = client.session_path(
        project_id, location, agent_id, session_id
    )

    text_input = dialogflow.TextInput(text=text)
    query_input = dialogflow.QueryInput(
        text=text_input, language_code="en"
    )

    request = dialogflow.DetectIntentRequest(
        session=session_path, query_input=query_input
    )

    response = client.detect_intent(request=request)
    return response.query_result
```

---

**Option C: Phone Integration (Voice)**

1. Go to **Integrations** → **Dialogflow Phone Gateway**
2. Follow setup to get phone number
3. Configure voice settings

---

### 2. Environment Setup

#### Development Environment

1. Create a **Draft** version:
   - Go to **Manage** → **Versions**
   - Keep working in draft for testing

#### Production Environment

1. Create a production version:
   - Click **Create version**
   - Add description: "Production v1.0"
   - Click **Create**

2. Create environment:
   - Go to **Manage** → **Environments**
   - Click **Create**
   - Name: `Production`
   - Select version
   - Click **Save**

---

### 3. Monitoring & Analytics

#### Enable Analytics

1. Go to **Agent Settings** → **General**
2. Enable:
   - ✅ Enable logging
   - ✅ Enable Stackdriver logging
   - ✅ Enable interaction logging

#### View Analytics

1. Go to **Analytics** in left sidebar
2. Monitor:
   - Conversation count
   - Intent detection confidence
   - Webhook success rate
   - Average conversation duration

---

### 4. Continuous Improvement

#### Review Conversations

1. Go to **Conversations** in left sidebar
2. Review real user conversations
3. Identify:
   - Unhandled intents
   - Low confidence matches
   - Common user phrases not in training data

#### Update Training Data

1. Add new training phrases based on real conversations
2. Create new intents for common unhandled requests
3. Re-train and test

---

## Troubleshooting

### Common Issues

---

#### Issue 1: Intent Not Matching

**Symptoms:**
- User input not triggering correct intent
- "Default fallback" triggered instead

**Solutions:**
1. Add more training phrases (aim for 20+ per intent)
2. Add variations and synonyms
3. Check intent confidence threshold in Agent Settings
4. Review similar intents for conflicts

---

#### Issue 2: Webhook Not Called

**Symptoms:**
- Page doesn't trigger webhook
- No response from webhook

**Solutions:**
1. Verify webhook is enabled in page fulfillment
2. Check webhook URL is correct
3. Test webhook manually:
   ```bash
   curl -X POST https://your-webhook-url/webhook \
     -H "Content-Type: application/json" \
     -d '{"fulfillmentInfo":{"tag":"validate-pet-id"},"sessionInfo":{"parameters":{"pet_id":"12345"}}}'
   ```
4. Check Cloud Run logs for errors
5. Verify tag name matches exactly (case-sensitive)

---

#### Issue 3: Webhook Timeout

**Symptoms:**
- "Webhook timeout" error
- No response after long wait

**Solutions:**
1. Increase timeout in webhook settings (60+ seconds)
2. Check Cloud Run logs for slow API calls
3. Optimize webhook code
4. Increase Cloud Run resources (memory/CPU)

---

#### Issue 4: Parameters Not Extracted

**Symptoms:**
- Parameters not filled from user input
- Agent keeps asking for already-provided info

**Solutions:**
1. Verify parameter annotations in training phrases
2. Check entity type is correct
3. Ensure parameter name matches across pages
4. Use session parameters: `$session.params.parameter_name`

---

#### Issue 5: Pet ID Not Found

**Symptoms:**
- "Couldn't find pet ID" error
- Valid IDs not being recognized

**Solutions:**
1. Check RescueGroups API key is configured
2. Test API directly:
   ```bash
   curl -X POST https://api.rescuegroups.org/v5/public/animals/search \
     -H "Authorization: YOUR_API_KEY" \
     -H "Content-Type: application/vnd.api+json"
   ```
3. Verify pet ID format matches RescueGroups format
4. Check webhook logs for API errors

---

#### Issue 6: Session Parameters Not Persisting

**Symptoms:**
- Data lost between pages
- Need to re-enter information

**Solutions:**
1. Use `$session.params.` not `$page.params.`
2. Webhook must return parameters in response:
   ```python
   response = {
       "sessionInfo": {
           "parameters": {
               "validated_pet_id": pet_id,
               "pet_name": pet_name
           }
       }
   }
   ```
3. Check parameter scope (session vs. page)

---

### Debug Mode

Enable debug logging:

1. Go to **Agent Settings** → **General**
2. Enable all logging options
3. In simulator, click response → View fulfillment details
4. Check:
   - Intent matched
   - Confidence score
   - Parameters extracted
   - Webhook request/response
   - Transition target

---

### Testing Webhook Locally

For faster development, test webhook locally:

```bash
# Run webhook locally
uvicorn pawconnect_ai.dialogflow_webhook:app --reload --port 8080

# Use ngrok for public URL
ngrok http 8080

# Update webhook URL in Dialogflow to ngrok URL
# Example: https://abc123.ngrok.io/webhook
```

---

## Next Steps

### Phase 1: Basic Deployment ✅
- [x] Create agent
- [x] Configure webhooks
- [x] Add basic intents
- [x] Create core pages
- [x] Test basic flows

### Phase 2: Enhancement 🔄
- [ ] Add more training phrases (100+ per intent)
- [ ] Implement conversation repair
- [ ] Add context handling
- [ ] Create FAQ intents
- [ ] Add small talk responses

### Phase 3: Advanced Features 📈
- [ ] Multi-language support
- [ ] Voice optimization
- [ ] Sentiment analysis
- [ ] Analytics dashboard
- [ ] A/B testing different flows

### Phase 4: Integration 🔌
- [ ] Website integration
- [ ] Mobile app integration
- [ ] SMS/phone integration
- [ ] Social media integration
- [ ] CRM integration

---

## Additional Resources

### Documentation
- [Dialogflow CX Documentation](https://cloud.google.com/dialogflow/cx/docs)
- [Webhook Setup Guide](./WEBHOOK_SETUP.md)
- [RescueGroups API Docs](https://userguide.rescuegroups.org/display/APIDG/API+Developers+Guide+Home)

### Best Practices
- Add 20+ training phrases per intent
- Use session parameters for data persistence
- Implement proper error handling
- Log all webhook calls
- Monitor conversation analytics
- Regular intent review and updates

### Support
- Dialogflow Community: https://groups.google.com/g/dialogflow
- Stack Overflow: Tag `dialogflow-cx`
- GitHub Issues: Report webhook bugs

---

## Summary Checklist

Use this checklist to verify complete setup:

### Manage Section
- [ ] Webhook created with correct URL
- [ ] 5 custom entity types created
- [ ] 9 intents created with training phrases
- [ ] All parameters annotated in training phrases

### Build Section
- [ ] 5 flows created
- [ ] Default Start Flow configured
- [ ] Pet Search Flow (3 pages)
- [ ] Pet Details Flow (2 pages)
- [ ] Visit Scheduling Flow (3 pages)
- [ ] Adoption Application Flow (3 pages)
- [ ] All pages have webhook tags configured
- [ ] Routes connect pages properly

### Testing
- [ ] All intents match correctly
- [ ] Webhooks called successfully
- [ ] Parameters extracted properly
- [ ] Session data persists
- [ ] Error handling works
- [ ] Edge cases handled

### Deployment
- [ ] Cloud Run webhook deployed
- [ ] Environment variables configured
- [ ] Production version created
- [ ] Integration completed
- [ ] Analytics enabled

---

**You're all set!** Your PawConnect Dialogflow CX agent is ready to help users find their perfect pet companion. 🐾
