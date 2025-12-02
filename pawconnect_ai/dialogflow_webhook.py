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
    from .utils.api_clients import rescuegroups_client
    logger.info("Successfully imported API clients")
except Exception as e:
    logger.error(f"Failed to import API clients: {e}")
    logger.warning("Continuing startup - API clients may not be fully initialized")
    rescuegroups_client = None


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

        # Extract webhook tag
        tag = body.get("fulfillmentInfo", {}).get("tag")
        session_info = body.get("sessionInfo", {})
        parameters = session_info.get("parameters", {})

        # Route to appropriate handler based on tag
        if tag == "search-pets":
            response = await handle_search_pets(parameters, session_info)
        elif tag == "validate-pet-id":
            response = await handle_validate_pet_id(parameters, session_info)
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

        # Fetch pet details from RescueGroups API
        logger.info(f"Validating pet ID: {pet_id}")
        result = await rescuegroups_client.get_pet(pet_id)

        # Check if pet was found
        if not result or "data" not in result or not result["data"]:
            return create_text_response(
                f"I couldn't find a pet with ID '{pet_id}'. Please check the ID and try again."
            )

        # Extract pet data
        pet_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
        attributes = pet_data.get("attributes", {})

        # Parse included organizations
        included = result.get("included", [])
        org_data = None
        for item in included:
            if item.get("type") == "orgs":
                org_data = item.get("attributes", {})
                break

        # Build response with pet information
        pet_name = attributes.get("name", "this pet")
        breed = attributes.get("breedString", attributes.get("breedPrimary", "Mixed breed"))
        age = attributes.get("ageString", attributes.get("ageGroup", "Unknown age"))
        sex = attributes.get("sex", "Unknown gender")

        # Store pet details in session for later use
        updated_parameters = {
            **parameters,
            "validated_pet_id": pet_id,
            "pet_name": pet_name,
            "pet_breed": breed,
            "pet_age": age,
            "pet_sex": sex
        }

        if org_data:
            updated_parameters["shelter_name"] = org_data.get("name", "the shelter")
            updated_parameters["shelter_city"] = org_data.get("city", "")
            updated_parameters["shelter_state"] = org_data.get("state", "")

        response_text = (
            f"Great! I found {pet_name}, a {age} {sex} {breed}. "
            f"This pet is available at {updated_parameters.get('shelter_name', 'a local shelter')}. "
            f"Would you like to schedule a visit or submit an adoption application?"
        )

        return create_text_response(
            response_text,
            session_parameters=updated_parameters
        )

    except Exception as e:
        logger.error(f"Error validating pet ID: {e}")
        return create_text_response(
            f"I had trouble looking up pet ID '{parameters.get('pet_id')}'. Please try again or provide a different ID."
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
        pet_type = parameters.get("pet_type")
        location = parameters.get("location")
        pet_size = parameters.get("pet_size")
        pet_age = parameters.get("pet_age")

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
        logger.info(f"Searching for pets: type={pet_type}, location={location}")

        result = await rescuegroups_client.search_pets(
            pet_type=pet_type,
            location=location,
            distance=50,
            limit=10
        )

        # Check if any pets were found
        if not result or "data" not in result or not result["data"]:
            response_text = (
                f"I couldn't find any {pet_type or 'pet'}s near {location}. "
                "Would you like to expand your search area or try different criteria?"
            )
            return create_text_response(response_text)

        # Count results
        pet_count = len(result["data"])

        # Store search results in session
        updated_parameters = {
            **parameters,
            "search_results_count": pet_count,
            "last_search_location": location
        }

        response_text = (
            f"Great news! I found {pet_count} {pet_type or 'pet'}{'s' if pet_count != 1 else ''} "
            f"near {location}. Would you like me to show you personalized recommendations "
            f"based on your preferences?"
        )

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
        pet_id = parameters.get("validated_pet_id") or parameters.get("pet_id")
        pet_name = parameters.get("pet_name", "the pet")
        date = parameters.get("date")
        time = parameters.get("time")

        if not pet_id:
            return create_text_response(
                "Which pet would you like to visit? Please provide the pet's ID."
            )

        if not date or not time:
            return create_text_response(
                f"When would you like to visit {pet_name}? Please provide both a date and time."
            )

        # Here you would integrate with your calendar/scheduling system
        # For now, we'll create a confirmation message

        response_text = (
            f"Perfect! I've scheduled your visit to meet {pet_name} on {date} at {time}. "
            f"You'll receive a confirmation email shortly with the shelter's address and "
            f"any specific instructions. Is there anything else I can help you with?"
        )

        return create_text_response(response_text)

    except Exception as e:
        logger.error(f"Error scheduling visit: {e}")
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
