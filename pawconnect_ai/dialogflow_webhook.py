"""
Dialogflow CX Webhook for PawConnect AI.
Handles webhook fulfillment requests from Dialogflow CX including pet ID validation.
"""

import asyncio
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")

logger.info("Starting PawConnect Dialogflow Webhook...")

try:
    # Import API clients - may initialize with default/missing config
    from .utils.api_clients import rescuegroups_client, google_cloud_client
    logger.info("Successfully imported API clients")
except Exception as e:
    logger.error(f"Failed to import API clients: {e}")
    logger.warning("Continuing startup - API clients may not be fully initialized")
    rescuegroups_client = None
    google_cloud_client = None


# Initialize FastAPI app
app = FastAPI(
    title="PawConnect Dialogflow Webhook",
    description="Webhook fulfillment for PawConnect Dialogflow CX agent",
    version="1.0.0"
)

logger.info("FastAPI app initialized successfully")


class DialogflowRequest(BaseModel):
    """Dialogflow CX webhook request structure."""
    detectIntentResponseId: str
    sessionInfo: Dict[str, Any]
    fulfillmentInfo: Dict[str, Any]
    pageInfo: Dict[str, Any]
    intentInfo: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    languageCode: str = "en"


class DialogflowResponse(BaseModel):
    """Dialogflow CX webhook response structure."""
    fulfillmentResponse: Dict[str, Any]
    sessionInfo: Optional[Dict[str, Any]] = None
    pageInfo: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup_event():
    """Log startup event."""
    logger.info("Webhook service is starting up...")
    logger.info("Health check endpoint available at /health")
    logger.info("Webhook endpoint available at /webhook")

    # Log configuration status (without exposing sensitive values)
    from .config import settings
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Testing mode: {settings.testing_mode}")
    logger.info(f"Mock APIs: {settings.mock_apis}")
    logger.info(f"GCP Project: {settings.gcp_project_id}")
    logger.info(f"RescueGroups API configured: {'Yes' if settings.rescuegroups_api_key else 'No (using defaults)'}")
    logger.info(f"Dialogflow Agent ID configured: {'Yes' if settings.dialogflow_agent_id else 'No (using defaults)'}")

    if rescuegroups_client is None:
        logger.warning("RescueGroups client not initialized - API calls will fail")

    logger.info("Startup complete - ready to accept requests")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "PawConnect Dialogflow Webhook",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check called")
    return {"status": "healthy", "service": "pawconnect-dialogflow-webhook"}


def extract_session_id(session_info: Dict[str, Any]) -> str:
    """
    Extract session ID from Dialogflow session info.

    Args:
        session_info: Dialogflow session information

    Returns:
        Session ID string
    """
    # Example session: "projects/PROJECT/locations/LOCATION/agents/AGENT/sessions/SESSION_ID"
    session = session_info.get("session", "")
    if "/" in session:
        return session.split("/")[-1]
    return session or "unknown"


async def track_user_preferences(session_id: str, parameters: Dict[str, Any]) -> None:
    """
    Track and store user preferences in Firestore.

    Args:
        session_id: Dialogflow session ID
        parameters: Session parameters containing user preferences
    """
    if not google_cloud_client:
        return

    try:
        preferences = {}

        # Extract preference parameters
        if "location" in parameters:
            preferences["location"] = parameters["location"]
        if "species" in parameters:
            preferences["species"] = parameters["species"]
        if "housing" in parameters:
            preferences["housing"] = parameters["housing"]
        if "experience" in parameters:
            preferences["experience"] = parameters["experience"]
        if "distance" in parameters:
            preferences["search_radius"] = parameters["distance"]

        if preferences:
            google_cloud_client.update_user_preferences(session_id, preferences)
            logger.info(f"Updated preferences for session {session_id}: {preferences}")
    except Exception as e:
        logger.error(f"Failed to save user preferences: {e}")


async def track_conversation_event(
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any]
) -> None:
    """
    Track conversation event in Firestore.

    Args:
        session_id: Dialogflow session ID
        event_type: Type of event
        event_data: Event data
    """
    if not google_cloud_client:
        return

    try:
        google_cloud_client.save_conversation_event(session_id, event_type, event_data)
    except Exception as e:
        logger.error(f"Failed to save conversation event: {e}")


async def publish_analytics(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Publish analytics event to Pub/Sub.

    Args:
        event_type: Type of event
        event_data: Event data
    """
    if not google_cloud_client:
        return

    try:
        await google_cloud_client.publish_analytics_event(event_type, event_data)
    except Exception as e:
        logger.error(f"Failed to publish analytics event: {e}")


@app.post("/webhook")
async def dialogflow_webhook(request: Request):
    """
    Main webhook endpoint for Dialogflow CX.

    Handles all webhook tags including:
    - search-pets: Search for pets based on user criteria
    - validate-pet-id: Validate and fetch pet details by ID
    - schedule-visit: Schedule a visit to meet a pet
    - submit-application: Submit adoption/foster application
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Received webhook request: {body}")

        # Extract webhook tag and session info
        tag = body.get("fulfillmentInfo", {}).get("tag")
        session_info = body.get("sessionInfo", {})
        parameters = session_info.get("parameters", {})
        session_id = extract_session_id(session_info)

        # Add user text to session_info for handlers that need it
        session_info["text"] = body.get("text", "")

        # Track user preferences (async, non-blocking)
        await track_user_preferences(session_id, parameters)

        # Route to appropriate handler based on tag
        if tag == "search-pets":
            response = await handle_search_pets(parameters, session_info)
        elif tag == "validate-pet-id":
            response = await handle_validate_pet_id(parameters, session_info)
        elif tag == "ask-pet-question":
            response = await handle_ask_pet_question(parameters, session_info)
        elif tag == "schedule-visit":
            response = await handle_schedule_visit(parameters, session_info)
        elif tag == "submit-application":
            response = await handle_submit_application(parameters, session_info)
        elif tag == "get-recommendations":
            response = await handle_get_recommendations(parameters, session_info)
        else:
            logger.warning(f"Unknown webhook tag: {tag}")
            response = create_text_response("I'm sorry, I don't know how to handle that request yet.")

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error handling webhook request: {e}")
        error_response = create_text_response(
            "I'm sorry, I encountered an error processing your request. Please try again."
        )
        return JSONResponse(content=error_response, status_code=500)


async def handle_validate_pet_id(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a pet ID and return pet details.

    This handler:
    1. Extracts the pet_id parameter from the request
    2. Fetches pet details from RescueGroups API
    3. Returns pet information or validation error
    """
    try:
        pet_id = parameters.get("pet_id")

        if not pet_id:
            return create_text_response(
                "I need a pet ID to look up. Could you provide the pet's ID number?"
            )

        # Check if API client is available
        if rescuegroups_client is None:
            logger.error("RescueGroups client not initialized")
            return create_text_response(
                "I'm sorry, the pet lookup service is currently unavailable. Please try again later."
            )

        # Check if pet_id is a name (non-numeric) instead of an ID
        if not str(pet_id).isdigit():
            logger.info(f"pet_id '{pet_id}' appears to be a name, not an ID. Searching by name...")

            # Search for pets with this name
            # Get location from session for the search
            location = parameters.get("last_search_location") or parameters.get("location")
            pet_type = parameters.get("species") or parameters.get("pet_type")

            if not location:
                return create_text_response(
                    f"I found '{pet_id}' in your recent search, but I need your location to look up the details. "
                    "Could you tell me your ZIP code or city?"
                )

            # Search for pets matching this name
            search_result = await rescuegroups_client.search_pets(
                pet_type=pet_type,
                location=location,
                distance=100,
                limit=50
            )

            # Look for pets with matching names
            matching_pets = []
            if search_result and "data" in search_result:
                for pet_data in search_result["data"]:
                    attributes = pet_data.get("attributes", {})
                    pet_name = attributes.get("name", "")
                    if pet_name.lower() == str(pet_id).lower():
                        matching_pets.append(pet_data)

            if not matching_pets:
                return create_text_response(
                    f"I couldn't find a pet named '{pet_id}' in your area. "
                    "Could you provide the pet's ID number instead? "
                    "You can find it in the recommendations I showed earlier."
                )

            if len(matching_pets) > 1:
                # Multiple pets with the same name - ask for ID
                return create_text_response(
                    f"I found {len(matching_pets)} pets named '{pet_id}'. "
                    "Could you provide the pet's ID number to help me identify the right one? "
                    "You can find it in the recommendations (e.g., ID: 12345)."
                )

            # Found exactly one match - use its ID
            pet_data = matching_pets[0]
            pet_id = pet_data.get("id")
            logger.info(f"Found pet by name '{parameters.get('pet_id')}' with ID: {pet_id}")

            # Update the result to use this pet_data
            result = {
                "data": pet_data,
                "included": search_result.get("included", [])
            }
        else:
            # Fetch pet details from RescueGroups API using GET /public/animals/{id}
            logger.info(f"Validating pet ID: {pet_id}")
            result = await rescuegroups_client.get_pet(pet_id)

        # Check if pet was found
        # GET endpoint returns single object in "data", not an array
        if not result or not result.get("data"):
            logger.info(f"No pet found for ID: {pet_id}")
            return create_text_response(
                f"I couldn't find a pet with ID '{pet_id}'. Please check the ID and try again."
            )

        # Extract pet data (GET endpoint returns single object, not array)
        pet_data = result["data"]
        attributes = pet_data.get("attributes", {})
        returned_pet_id = pet_data.get("id") or attributes.get("id")

        # CRITICAL: Verify the returned pet ID matches the requested ID
        if returned_pet_id and str(returned_pet_id) != str(pet_id):
            logger.error(
                f"API returned wrong pet! Requested: {pet_id}, Got: {returned_pet_id}"
            )
            return create_text_response(
                f"I couldn't find a pet with ID '{pet_id}'. Please check the ID and try again."
            )

        # Parse included data to find species and organization
        included = result.get("included", [])
        org_data = None
        species_name = None

        # Get species ID from relationships
        relationships = pet_data.get("relationships", {})
        species_rel = relationships.get("species", {}).get("data", [])
        species_id = species_rel[0].get("id") if species_rel else None

        # Find matching items in included array
        for item in included:
            if item.get("type") == "orgs":
                org_data = item.get("attributes", {})
            elif item.get("type") == "species" and item.get("id") == species_id:
                species_attrs = item.get("attributes", {})
                species_name = species_attrs.get("singular") or species_attrs.get("plural", "")
                logger.info(f"Found species from included: {species_name} (ID: {species_id})")

        # Extract pet information
        pet_name = attributes.get("name", "this pet")
        species = species_name or ""  # Use species from included relationships
        breed = attributes.get("breedString", attributes.get("breedPrimary", "Mixed breed"))
        age = attributes.get("ageString", attributes.get("ageGroup", "Unknown age"))
        sex = attributes.get("sex", "Unknown gender")
        size = attributes.get("sizeGroup", "")

        # Build species description
        species_text = ""
        if species:
            species_lower = species.lower()
            if species_lower == "dog":
                species_text = "Dog"
            elif species_lower == "cat":
                species_text = "Cat"
            elif species_lower == "rabbit":
                species_text = "Rabbit"
            elif species_lower == "bird":
                species_text = "Bird"
            elif species_lower in ["smallfurry", "small furry", "small_furry"]:
                species_text = "Small Animal"
            else:
                species_text = species.capitalize()

        # Build descriptive text
        description_parts = []
        if age:
            description_parts.append(age)
        if sex:
            description_parts.append(sex)
        if size:
            description_parts.append(size)
        if species_text:
            description_parts.append(species_text)
        if breed and breed != "Mixed breed":
            description_parts.append(breed)
        elif breed == "Mixed breed" and species_text:
            description_parts.append(f"{species_text} Mix")

        description = ", ".join(description_parts) if description_parts else "pet"

        # Store pet details in session for later use
        updated_parameters = {
            **parameters,
            "validated_pet_id": pet_id,
            "pet_name": pet_name,
            "pet_species": species_text,
            "pet_breed": breed,
            "pet_age": age,
            "pet_sex": sex,
            "pet_size": size,
            # Track that we've loaded pet details to prevent duplicate responses
            "pet_details_loaded": True,
            "current_pet_id": pet_id
        }

        if org_data:
            updated_parameters["shelter_name"] = org_data.get("name", "the shelter")
            updated_parameters["shelter_city"] = org_data.get("city", "")
            updated_parameters["shelter_state"] = org_data.get("state", "")

        shelter_info = updated_parameters.get('shelter_name', 'a local shelter')
        if updated_parameters.get("shelter_city") and updated_parameters.get("shelter_state"):
            shelter_info += f" in {updated_parameters['shelter_city']}, {updated_parameters['shelter_state']}"

        response_text = (
            f"Great! I found {pet_name}, a {description}. "
            f"This pet is available at {shelter_info}. "
            f"Would you like to schedule a visit or submit an adoption application?"
        )

        logger.info(f"Successfully validated pet {pet_id}: {pet_name} ({species_text})")

        # Track conversation event and analytics
        session_id = extract_session_id(session_info)
        event_data = {
            "pet_id": pet_id,
            "pet_name": pet_name,
            "pet_species": species_text,
            "shelter_name": updated_parameters.get("shelter_name")
        }
        await track_conversation_event(session_id, "pet_details_viewed", event_data)
        await publish_analytics("pet_details_view", event_data)

        return create_text_response(
            response_text,
            session_parameters=updated_parameters
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error validating pet ID {parameters.get('pet_id')}: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        return create_text_response(
            f"I had trouble looking up pet ID '{parameters.get('pet_id')}'. Please try again or provide a different ID."
        )


async def handle_ask_pet_question(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Answer questions about the current pet in context.
    """
    try:
        # Prioritize session parameters which have validated pet info
        pet_id = parameters.get("validated_pet_id") or parameters.get("pet_id")

        # Use session pet_name if available (it's already validated and clean)
        # Fall back to parameter pet_name only if session doesn't have it
        pet_name = parameters.get("pet_name", "this pet")

        # If pet_name looks suspicious (too long or has question marks), default to "this pet"
        if pet_name and (len(pet_name) > 20 or '?' in pet_name):
            pet_name = "this pet"

        if not pet_id:
            return create_text_response(
                "I need to know which pet you're asking about. Could you tell me the pet's name or ID?"
            )

        # Check if API client is available
        if rescuegroups_client is None:
            logger.error("RescueGroups client not initialized")
            return create_text_response(
                "I'm sorry, the pet information service is currently unavailable. Please try again later."
            )

        # Fetch full pet details from RescueGroups API
        logger.info(f"Fetching details for pet ID: {pet_id}")
        result = await rescuegroups_client.get_pet(pet_id)

        if not result or not result.get("data"):
            logger.info(f"No pet found for ID: {pet_id}")
            return create_text_response(
                f"I couldn't find information about {pet_name}. Please check the pet ID."
            )

        # Extract pet data
        pet_data = result["data"]
        attributes = pet_data.get("attributes", {})

        # Get actual pet name from API response
        actual_pet_name = attributes.get("name", pet_name)

        # Extract key information
        activity_level = attributes.get("activityLevel", "").lower()
        qualities = attributes.get("qualities", [])
        is_housetrained = attributes.get("isHousetrained")
        good_with_kids = attributes.get("isGoodWithKids")
        good_with_cats = attributes.get("isGoodWithCats")
        good_with_dogs = attributes.get("isGoodWithDogs")
        is_special_needs = attributes.get("isSpecialNeeds", False)
        special_needs_desc = attributes.get("specialNeedsDescription", "")

        # Analyze what the user is asking about from the request text
        user_text = session_info.get("text", "").lower()
        response_parts = []

        # Detect question type from user text
        is_medical = any(word in user_text for word in ['medical', 'health', 'medication', 'medicine', 'sick', 'illness', 'condition', 'disease', 'vet', 'doctor'])
        is_kids = any(word in user_text for word in ['kid', 'child', 'children', 'baby', 'toddler'])
        is_cats = any(word in user_text for word in ['cat', 'feline'])
        is_dogs = any(word in user_text for word in ['dog', 'canine', 'other dogs'])
        is_walks = any(word in user_text for word in ['walk', 'exercise', 'active', 'run', 'outdoor', 'leash'])
        is_personality = any(word in user_text for word in ['personality', 'temperament', 'behavior', 'friendly', 'playful', 'calm', 'energetic'])
        is_training = any(word in user_text for word in ['train', 'housetrain', 'potty', 'bathroom'])

        # Answer based on question type
        if is_medical:
            # Medical/health questions
            if is_special_needs and special_needs_desc:
                response_parts.append(f"{actual_pet_name} does have special needs: {special_needs_desc}")
            elif is_special_needs:
                response_parts.append(f"{actual_pet_name} is listed as having special needs. Please contact the shelter for specific details.")
            else:
                response_parts.append(f"{actual_pet_name} does not have any listed special needs or medical issues.")

        elif is_kids:
            # Good with kids questions
            if good_with_kids is True:
                response_parts.append(f"Yes! {actual_pet_name} is good with kids.")
            elif good_with_kids is False:
                response_parts.append(f"{actual_pet_name} may not be the best fit for homes with children.")
            else:
                response_parts.append(f"I don't have specific information about {actual_pet_name}'s compatibility with children. Please ask the shelter!")

        elif is_cats:
            # Good with cats questions
            if good_with_cats is True:
                response_parts.append(f"Yes! {actual_pet_name} is good with cats.")
            elif good_with_cats is False:
                response_parts.append(f"{actual_pet_name} may not be compatible with cats.")
            else:
                response_parts.append(f"I don't have information about {actual_pet_name}'s compatibility with cats.")

        elif is_dogs:
            # Good with other dogs questions
            if good_with_dogs is True:
                response_parts.append(f"Yes! {actual_pet_name} is good with other dogs.")
            elif good_with_dogs is False:
                response_parts.append(f"{actual_pet_name} may prefer to be the only dog.")
            else:
                response_parts.append(f"I don't have information about {actual_pet_name}'s compatibility with other dogs.")

        elif is_training:
            # Housetraining questions
            if is_housetrained:
                response_parts.append(f"Yes! {actual_pet_name} is housetrained.")
            else:
                response_parts.append(f"I don't have information confirming {actual_pet_name} is housetrained. Please ask the shelter for details.")

        elif is_walks or is_personality:
            # Walks/exercise or personality questions
            has_leash_training = any(q for q in qualities if 'leash' in str(q).lower())

            if is_walks and has_leash_training:
                response_parts.append(f"Yes! {actual_pet_name} is leash trained and ready for walks.")
            elif is_walks and activity_level:
                if 'high' in activity_level or 'active' in activity_level:
                    response_parts.append(f"Absolutely! {actual_pet_name} has a {activity_level} activity level and would love regular walks.")
                elif 'moderate' in activity_level:
                    response_parts.append(f"Yes, {actual_pet_name} has a moderate activity level and would enjoy daily walks.")
                elif 'low' in activity_level:
                    response_parts.append(f"{actual_pet_name} has a lower activity level, so shorter, gentler walks would be perfect.")

            # Add personality traits for personality questions or as supplement
            personality_traits = [q for q in qualities if any(trait in str(q).lower() for trait in ['affectionate', 'friendly', 'playful', 'gentle', 'calm', 'energetic'])]
            if personality_traits and (is_personality or is_walks):
                traits_str = ', '.join(personality_traits[:3])
                response_parts.append(f"{actual_pet_name} is described as {traits_str}.")

            if is_housetrained and is_walks:
                response_parts.append(f"{actual_pet_name} is also housetrained, which is great!")

        else:
            # General question - provide overview
            response_parts.append(f"Let me tell you about {actual_pet_name}!")
            personality_traits = [q for q in qualities if any(trait in str(q).lower() for trait in ['affectionate', 'friendly', 'playful', 'gentle', 'calm', 'energetic'])]
            if personality_traits:
                traits_str = ', '.join(personality_traits[:3])
                response_parts.append(f"{actual_pet_name} is {traits_str}.")
            if is_housetrained:
                response_parts.append(f"{actual_pet_name} is housetrained.")

        # Build final conversational response
        response_text = " ".join(response_parts) if response_parts else f"I don't have specific information about that for {actual_pet_name}. Please contact the shelter for more details."
        response_text += f"\n\nWant to schedule a visit to meet {actual_pet_name}?"

        # Track conversation event and analytics
        session_id = extract_session_id(session_info)
        event_data = {
            "pet_id": pet_id,
            "pet_name": actual_pet_name,
            "question_type": "pet_question"
        }
        await track_conversation_event(session_id, "pet_question_asked", event_data)
        await publish_analytics("pet_question", event_data)

        return create_text_response(response_text)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error answering pet question: {e}")
        logger.error(f"Traceback: {error_details}")
        return create_text_response(
            f"I had trouble finding that information about {parameters.get('pet_name', 'this pet')}. "
            "What else would you like to know?"
        )


async def handle_search_pets(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Search for pets based on user criteria.
    """
    try:
        # Extract search parameters
        pet_type = parameters.get("pet_type") or parameters.get("species")
        breed = parameters.get("breed")
        location = parameters.get("location")
        pet_size = parameters.get("pet_size")
        pet_age = parameters.get("pet_age")

        # If breed is specified, infer species if not provided
        if breed and not pet_type:
            # Common dog breeds
            dog_breeds = ["labrador", "golden", "retriever", "shepherd", "bulldog", "beagle", "poodle",
                         "husky", "corgi", "boxer", "dachshund", "terrier"]
            # Common cat breeds
            cat_breeds = ["siamese", "persian", "maine coon", "bengal", "ragdoll", "sphynx"]

            breed_lower = breed.lower()
            if any(db in breed_lower for db in dog_breeds):
                pet_type = "dog"
                logger.info(f"  Inferred pet_type='dog' from breed='{breed}'")
            elif any(cb in breed_lower for cb in cat_breeds):
                pet_type = "cat"
                logger.info(f"  Inferred pet_type='cat' from breed='{breed}'")

        # Validate and clean pet_type
        valid_pet_types = ["dog", "cat", "rabbit", "bird", "small_animal", "puppy", "kitten"]
        if pet_type and pet_type.lower() not in valid_pet_types:
            logger.warning(f"Invalid pet_type extracted: '{pet_type}'")
            # Ask user to clarify
            return create_text_response(
                "I'd be happy to help you find a pet! Are you looking for a dog, cat, rabbit, bird, or other type of pet?"
            )

        # Clean location - extract just the city name or ZIP if it's too long
        if location and len(location) > 50:
            logger.warning(f"Location too long ({len(location)} chars): '{location}'")
            # Try to extract city name from the beginning
            words = location.split()
            if len(words) > 0:
                # Take first word as potential city name
                location = words[0].strip()
                logger.info(f"  Extracted city: '{location}'")

        # Validate location - check if it looks like a common mis-extraction
        invalid_locations = [
            "maintenance", "apartment", "living", "friendly", "sized",
            "good", "suitable", "owner", "first", "time", "children", "cats"
        ]
        if location and location.lower() in invalid_locations:
            logger.warning(f"Invalid location extracted: '{location}' - asking user to clarify")
            return create_text_response(
                "I couldn't quite catch your location. Could you please tell me what city or ZIP code you're in? For example, 'Seattle' or '98101'."
            )

        if not location:
            return create_text_response(
                "I need to know your location to search for pets. What's your ZIP code or city?"
            )

        # Check if API client is available
        if rescuegroups_client is None:
            logger.error("RescueGroups client not initialized")
            return create_text_response(
                "I'm sorry, the pet search service is currently unavailable. Please try again later."
            )

        # Search for pets using RescueGroups API
        logger.info(f"Searching for pets: type={pet_type}, breed={breed}, location={location}")

        result = await rescuegroups_client.search_pets(
            pet_type=pet_type,
            location=location,
            distance=50,
            limit=10
        )

        # Check if any pets were found
        if not result or "data" not in result or not result["data"]:
            breed_text = f" {breed}" if breed else ""
            response_text = (
                f"I couldn't find any{breed_text} {pet_type or 'pet'}s near {location}. "
                "Would you like to expand your search area or try different criteria?"
            )
            return create_text_response(response_text)

        # Count results
        pet_count = len(result["data"])

        # Store search results in session (including breed if provided)
        updated_parameters = {
            **parameters,
            "search_results_count": pet_count,
            "last_search_location": location
        }
        if breed:
            updated_parameters["search_breed"] = breed

        breed_text = f" {breed}" if breed else ""
        response_text = (
            f"Great news! I found {pet_count}{breed_text} {pet_type or 'pet'}{'s' if pet_count != 1 else ''} "
            f"near {location}. Would you like me to show you personalized recommendations "
            f"based on your preferences?"
        )

        # Track conversation event and analytics
        session_id = extract_session_id(session_info)
        event_data = {
            "pet_type": pet_type,
            "location": location,
            "breed": breed,
            "results_count": pet_count
        }
        await track_conversation_event(session_id, "search_pets", event_data)
        await publish_analytics("pet_search", event_data)

        return create_text_response(
            response_text,
            session_parameters=updated_parameters
        )

    except Exception as e:
        logger.error(f"Error searching for pets: {e}")
        return create_text_response(
            "I had trouble searching for pets. Please try again with different criteria."
        )


async def handle_schedule_visit(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Schedule a visit to meet a pet.
    """
    try:
        from datetime import datetime

        pet_id = parameters.get("validated_pet_id") or parameters.get("pet_id")
        pet_name = parameters.get("pet_name", "the pet")
        date_param = parameters.get("date")
        time_param = parameters.get("time")

        if not pet_id:
            return create_text_response(
                "Which pet would you like to visit? Please provide the pet's ID."
            )

        if not date_param or not time_param:
            return create_text_response(
                f"When would you like to visit {pet_name}? Please provide both a date and time."
            )

        # Parse date from Dialogflow's sys.date format
        # The date parameter comes as a dict with year, month, day, and sometimes future/past/partial
        date_str = None
        if isinstance(date_param, dict):
            # Prefer "future" if available (for relative dates like "this Saturday")
            # Otherwise use the top-level year/month/day
            date_dict = date_param.get("future") or date_param

            year = int(date_dict.get("year", 0))
            month = int(date_dict.get("month", 0))
            day = int(date_dict.get("day", 0))

            if year > 0 and month > 0 and day > 0:
                try:
                    date_obj = datetime(year, month, day)
                    # Format as "Saturday, December 7, 2025"
                    date_str = date_obj.strftime("%A, %B %d, %Y")
                except ValueError:
                    date_str = f"{month}/{day}/{year}"
        elif isinstance(date_param, str):
            date_str = date_param
        else:
            date_str = str(date_param)

        # Parse time from Dialogflow's sys.time format
        # The time parameter comes as a dict with hours, minutes, seconds, nanos
        time_str = None
        if isinstance(time_param, dict):
            hours = int(time_param.get("hours", 0))
            minutes = int(time_param.get("minutes", 0))

            # Convert to 12-hour format with AM/PM
            if hours == 0:
                time_str = f"12:{minutes:02d} AM"
            elif hours < 12:
                time_str = f"{hours}:{minutes:02d} AM"
            elif hours == 12:
                time_str = f"12:{minutes:02d} PM"
            else:
                time_str = f"{hours - 12}:{minutes:02d} PM"
        elif isinstance(time_param, str):
            time_str = time_param
        else:
            time_str = str(time_param)

        # Here you would integrate with your calendar/scheduling system
        # For now, we'll create a confirmation message

        response_text = (
            f"Perfect! I've scheduled your visit to meet {pet_name} on {date_str} at {time_str}. "
            f"You'll receive a confirmation email shortly with the shelter's address and "
            f"any specific instructions. Is there anything else I can help you with?"
        )

        # Track conversation event and analytics
        session_id = extract_session_id(session_info)
        event_data = {
            "pet_id": pet_id,
            "pet_name": pet_name,
            "visit_date": date_str,
            "visit_time": time_str
        }
        await track_conversation_event(session_id, "visit_scheduled", event_data)
        await publish_analytics("visit_scheduled", event_data)

        return create_text_response(response_text)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error scheduling visit: {e}")
        logger.error(f"Traceback: {error_details}")
        logger.error(f"Date param: {parameters.get('date')}")
        logger.error(f"Time param: {parameters.get('time')}")
        return create_text_response(
            "I had trouble scheduling your visit. Please try again."
        )


async def handle_submit_application(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Submit an adoption/foster application.
    """
    try:
        pet_id = parameters.get("validated_pet_id") or parameters.get("pet_id")
        pet_name = parameters.get("pet_name", "the pet")

        if not pet_id:
            return create_text_response(
                "Which pet would you like to apply for? Please provide the pet's ID."
            )

        # Here you would integrate with your application submission system
        # For now, we'll create a confirmation message

        response_text = (
            f"Excellent! I'm starting your adoption application for {pet_name}. "
            f"I'll need some information from you to complete the application. "
            f"Let's start with your contact details. What's your full name?"
        )

        # Track conversation event and analytics
        session_id = extract_session_id(session_info)
        event_data = {
            "pet_id": pet_id,
            "pet_name": pet_name
        }
        await track_conversation_event(session_id, "application_started", event_data)
        await publish_analytics("application_started", event_data)

        return create_text_response(response_text)

    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        return create_text_response(
            "I had trouble starting your application. Please try again."
        )


async def handle_get_recommendations(
    parameters: Dict[str, Any],
    session_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get personalized pet recommendations based on user preferences.
    Fetches and displays actual pet listings from RescueGroups API.
    """
    try:
        # Extract user preferences from parameters
        pet_type = parameters.get("pet_type") or parameters.get("species")
        location = parameters.get("location")
        housing = parameters.get("housing")
        experience = parameters.get("experience")

        logger.info(f"Get recommendations - housing: {housing}, experience: {experience}, location: {location}, pet_type: {pet_type}")

        # Validate and clean pet_type
        valid_pet_types = ["dog", "cat", "rabbit", "bird", "small_animal", "puppy", "kitten"]
        if pet_type and pet_type.lower() not in valid_pet_types:
            logger.warning(f"Invalid pet_type extracted: '{pet_type}'")
            pet_type = "dog"  # Default to dog for recommendations
            logger.info(f"  Defaulting to pet_type='dog' for recommendations")

        # Clean location - extract just the city name or ZIP if it's too long
        if location and len(location) > 50:
            logger.warning(f"Location too long ({len(location)} chars): '{location}'")
            words = location.split()
            if len(words) > 0:
                location = words[0].strip()
                logger.info(f"  Extracted city: '{location}'")

        if not location:
            return create_text_response(
                "I need to know your location to find pets near you. What's your ZIP code?"
            )

        # Check if API client is available
        if rescuegroups_client is None:
            logger.error("RescueGroups client not initialized")
            return create_text_response(
                "I'm sorry, the pet recommendation service is currently unavailable. Please try again later."
            )

        # If we have housing and experience, fetch and display actual pets
        if housing and experience:
            # Fetch pets from RescueGroups API
            logger.info(f"Fetching pets for recommendations: type={pet_type}, location={location}")

            result = await rescuegroups_client.search_pets(
                pet_type=pet_type,
                location=location,
                distance=50,
                limit=5  # Show top 5 recommendations
            )

            # Check if any pets were found
            if not result or "data" not in result or not result["data"]:
                response_text = (
                    f"I couldn't find any {pet_type or 'pet'}s near {location}. "
                    "Would you like to expand your search area or try different criteria?"
                )
                return create_text_response(response_text)

            # Build response with actual pet listings
            response_parts = []

            response_parts.append(
                f"Perfect! Based on your preferences (living in {housing}, "
                f"{'experienced' if 'yes' in experience.lower() or 'experience' in experience.lower() else 'new to pets'}), "
                f"here are my top recommendations:\n\n"
            )

            # Display each pet
            for idx, pet in enumerate(result["data"][:5], 1):
                attributes = pet.get("attributes", {})

                name = attributes.get("name", "Unknown")
                breed = attributes.get("breedString") or attributes.get("breedPrimary", "Mixed breed")
                age = attributes.get("ageString") or attributes.get("ageGroup", "Unknown age")
                sex = attributes.get("sex", "Unknown")
                size = attributes.get("sizeGroup", "")

                # Get pet ID from relationships or id
                pet_id = pet.get("id", "")

                response_parts.append(
                    f"{idx}. **{name}** (ID: {pet_id})\n"
                    f"   • {age} {sex} {breed}\n"
                )

                if size:
                    response_parts.append(f"   • Size: {size}\n")

                response_parts.append("\n")

            response_parts.append(
                "Would you like more information about any of these pets? "
                "Just tell me the pet's name or ID number!"
            )

            response_text = "".join(response_parts)

            # Track conversation event and analytics
            session_id = extract_session_id(session_info)
            event_data = {
                "pet_type": pet_type,
                "location": location,
                "housing": housing,
                "experience": experience,
                "recommendations_count": len(result["data"][:5])
            }
            await track_conversation_event(session_id, "get_recommendations", event_data)
            await publish_analytics("pet_recommendations", event_data)

            return create_text_response(response_text)

        # If missing information, ask for it
        if not housing:
            return create_text_response(
                "What type of housing do you have? (apartment, house, condo, etc.)"
            )

        if not experience:
            return create_text_response(
                "Do you have experience with pets?"
            )

        # Fallback
        return create_text_response(
            f"Let me help you find the perfect {pet_type or 'pet'} based on your preferences!"
        )

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return create_text_response(
            "I had trouble getting recommendations. Please try again."
        )


def create_text_response(
    text: str,
    session_parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a Dialogflow CX text response.

    Args:
        text: Response text to send to user
        session_parameters: Optional parameters to update in session

    Returns:
        Dialogflow CX webhook response dictionary
    """
    response = {
        "fulfillmentResponse": {
            "messages": [
                {
                    "text": {
                        "text": [text]
                    }
                }
            ]
        }
    }

    if session_parameters:
        response["sessionInfo"] = {
            "parameters": session_parameters
        }

    return response


# Run with: uvicorn pawconnect_ai.dialogflow_webhook:app --reload --port 8080
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
