#!/bin/bash
# Setup script for PawConnect Dialogflow CX Agent
# This script creates all intents, entity types, and flows for the PawConnect agent

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PawConnect Dialogflow CX Agent Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if agent ID is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Agent ID is required${NC}"
    echo "Usage: $0 <AGENT_ID> [REGION] [PROJECT_ID]"
    echo ""
    echo "Example:"
    echo "  $0 your-agent-id us-central1 your-project-id"
    echo ""
    exit 1
fi

AGENT_ID=$1
REGION=${2:-us-central1}
PROJECT_ID=${3:-$(gcloud config get-value project)}

echo -e "${GREEN}Configuration:${NC}"
echo "  Agent ID: $AGENT_ID"
echo "  Region: $REGION"
echo "  Project ID: $PROJECT_ID"
echo ""

# Set up authentication
echo -e "${BLUE}Setting up authentication...${NC}"
ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}Error: Failed to get access token${NC}"
    echo "Please run: gcloud auth application-default login"
    exit 1
fi

# Set API endpoint
API_ENDPOINT="https://${REGION}-dialogflow.googleapis.com/v3"
AGENT_PATH="projects/${PROJECT_ID}/locations/${REGION}/agents/${AGENT_ID}"
echo -e "${GREEN}✓ Authentication configured${NC}"
echo ""

# Verify agent exists
echo -e "${BLUE}Verifying agent exists...${NC}"
AGENT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "x-goog-user-project: ${PROJECT_ID}" \
    "${API_ENDPOINT}/${AGENT_PATH}")

HTTP_CODE=$(echo "$AGENT_RESPONSE" | tail -n1)
AGENT_BODY=$(echo "$AGENT_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}Error: Agent $AGENT_ID not found (HTTP $HTTP_CODE)${NC}"
    echo "Response: $AGENT_BODY"
    echo "Please create the agent first in the Dialogflow CX Console"
    exit 1
fi
echo -e "${GREEN}✓ Agent verified${NC}"
echo ""

# Function to create an intent
create_intent() {
    local intent_name=$1
    local display_name=$2
    shift 2
    local training_phrases=("$@")

    echo -e "${BLUE}Creating intent: $display_name${NC}"

    # Create training phrases JSON
    local phrases_json="["
    for phrase in "${training_phrases[@]}"; do
        phrases_json+="{\"parts\":[{\"text\":\"$phrase\"}],\"repeatCount\":1},"
    done
    phrases_json="${phrases_json%,}]"  # Remove trailing comma

    # Create intent JSON for Dialogflow CX
    local intent_json=$(cat <<EOF
{
  "displayName": "$display_name",
  "trainingPhrases": $phrases_json,
  "priority": 500000
}
EOF
)

    # Refresh access token for each request
    ACCESS_TOKEN=$(gcloud auth application-default print-access-token)

    # Create the intent using REST API
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        -H "Content-Type: application/json" \
        -d "$intent_json" \
        "${API_ENDPOINT}/${AGENT_PATH}/intents")

    HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo -e "${GREEN}✓ Intent created${NC}"
    elif echo "$HTTP_RESPONSE" | grep -q "already exists"; then
        echo -e "${YELLOW}⚠ Intent already exists${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: Unexpected response (HTTP $HTTP_CODE)${NC}"
    fi
}

# Function to create an entity type
create_entity_type() {
    local display_name=$1
    shift
    local entities=("$@")

    echo -e "${BLUE}Creating entity type: $display_name${NC}"

    # Create entities JSON - parse synonyms into array
    local entities_json="["
    for entity in "${entities[@]}"; do
        IFS='|' read -r value synonyms <<< "$entity"
        # Split synonyms by comma and create JSON array
        local syn_array="["
        IFS=',' read -ra SYN_LIST <<< "$synonyms"
        for syn in "${SYN_LIST[@]}"; do
            syn_array+="\"$(echo "$syn" | xargs)\","
        done
        syn_array="${syn_array%,}]"  # Remove trailing comma
        entities_json+="{\"value\":\"$value\",\"synonyms\":$syn_array},"
    done
    entities_json="${entities_json%,}]"  # Remove trailing comma

    # Create entity type JSON for Dialogflow CX
    local entity_type_json=$(cat <<EOF
{
  "displayName": "$display_name",
  "kind": "KIND_MAP",
  "entities": $entities_json,
  "enableFuzzyExtraction": true
}
EOF
)

    # Refresh access token for each request
    ACCESS_TOKEN=$(gcloud auth application-default print-access-token)

    # Create the entity type using REST API
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "x-goog-user-project: ${PROJECT_ID}" \
        -H "Content-Type: application/json" \
        -d "$entity_type_json" \
        "${API_ENDPOINT}/${AGENT_PATH}/entityTypes")

    HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo -e "${GREEN}✓ Entity type created${NC}"
    elif echo "$HTTP_RESPONSE" | grep -q "already exists"; then
        echo -e "${YELLOW}⚠ Entity type already exists${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: Unexpected response (HTTP $HTTP_CODE)${NC}"
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Creating Entity Types${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create entity types
create_entity_type "pet_species" \
    "dog|dog,dogs,puppy,puppies,canine" \
    "cat|cat,cats,kitten,kittens,feline" \
    "rabbit|rabbit,rabbits,bunny,bunnies" \
    "bird|bird,birds,parrot,parakeet" \
    "small_animal|hamster,guinea pig,ferret"

create_entity_type "pet_size" \
    "small|small,tiny,little,miniature" \
    "medium|medium,average,mid-sized" \
    "large|large,big,giant,huge" \
    "extra_large|extra-large, xl, giant, huge, very large"

create_entity_type "pet_age_group" \
    "baby|baby,newborn,infant" \
    "young|young,puppy,kitten,juvenile" \
    "adult|adult,mature,grown" \
    "senior|senior,elderly,old,older"

create_entity_type "housing_type" \
    "apartment|apartment,apt,flat,apartments,apartment building" \
    "house|house,home,single family,single-family home" \
    "condo|condo,condominium,townhouse,townhome" \
    "own|own,owner,homeowner,I own,own my home" \
    "rent|rent,renter,renting,lease,I rent,renting a place" \
    "live_with_family|live with family,parents,family home,with parents,parents house"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Creating Intents${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create intents
create_intent "search_pets" "intent.search_pets" \
    "I want to search for a pet" \
    "Show me available dogs" \
    "I'm looking for a cat to adopt" \
    "Can you help me find a pet" \
    "Search for pets near me" \
    "Find me a puppy" \
    "I'm looking for a rescue animal"

create_intent "get_recommendations" "intent.get_recommendations" \
    "What pet would be good for me" \
    "Can you recommend a pet" \
    "Which pet should I adopt" \
    "Help me find the right pet" \
    "I don't know what pet to get" \
    "Recommend a pet for my lifestyle"

create_intent "schedule_visit" "intent.schedule_visit" \
    "I want to schedule a visit" \
    "Can I meet the pet" \
    "Schedule a time to see the pet" \
    "I'd like to visit the shelter" \
    "Book a visit" \
    "Set up an appointment"

create_intent "adoption_application" "intent.adoption_application" \
    "I want to adopt" \
    "Start adoption application" \
    "Apply to adopt this pet" \
    "I'd like to adopt" \
    "Begin adoption process" \
    "Submit adoption application"

create_intent "foster_application" "intent.foster_application" \
    "I want to foster" \
    "Start foster application" \
    "Apply to foster this pet" \
    "I'd like to foster" \
    "Can I foster temporarily"

create_intent "search_more" "intent.search_more" \
    "Show me more pets" \
    "Search again" \
    "Find other pets" \
    "Look for different pets" \
    "Start a new search"

create_intent "ask_question" "intent.ask_question" \
    "Tell me about Golden Retrievers" \
    "What do I need to know about cats" \
    "How much exercise does a dog need" \
    "What should I prepare before adopting" \
    "What's the adoption process"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure webhook in Dialogflow Console"
echo "2. Create pages and flows manually or using the Console"
echo "3. Test your agent in the Dialogflow CX Simulator"
echo ""
echo -e "${BLUE}For detailed instructions, see:${NC}"
echo "  deployment/dialogflow/README.md"
echo ""
