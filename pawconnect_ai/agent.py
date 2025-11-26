"""
PawConnect Main Agent - Orchestrator
Coordinates all sub-agents and manages the overall pet matching workflow.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from .config import settings
from .tools import PawConnectTools
from .sub_agents.conversation_agent import ConversationAgent
from .schemas.user_profile import UserProfile
from .schemas.pet_data import PetMatch
from .utils.validators import validate_user_input

# Import ADK for web interface support
try:
    from google.adk.agents import Agent, LlmAgent
    from google.genai.types import Content, Part
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    logger.warning("ADK not available. Web interface will not work.")


class PawConnectMainAgent:
    """
    Main orchestrator agent that coordinates all sub-agents and manages
    the complete pet adoption and fostering workflow.
    """

    def __init__(self):
        """Initialize the main agent and all sub-systems."""
        logger.info("Initializing PawConnect Main Agent")
        self.tools = PawConnectTools()
        self.conversation_agent = ConversationAgent()
        self.user_sessions = {}  # Store user session data

    async def process_user_request(
        self,
        user_id: str,
        message: str,
        user_profile: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the agent system.

        Args:
            user_id: User identifier
            message: User message or request
            user_profile: Optional existing user profile

        Returns:
            Dictionary with response and any relevant data
        """
        try:
            logger.info(f"Processing request from user {user_id}: {message}")

            # Get or create session
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {
                    "created_at": datetime.utcnow(),
                    "profile": user_profile,
                    "context": {}
                }

            session = self.user_sessions[user_id]

            # Process message through conversation agent
            conv_result = self.conversation_agent.process_user_input(
                user_id=user_id,
                message=message,
                context=session["context"]
            )

            intent = conv_result["intent"]
            entities = conv_result["entities"]

            # Route to appropriate handler based on intent
            if intent == "search_pets":
                result = await self._handle_search_pets(user_id, entities, session)
            elif intent == "get_recommendations":
                result = await self._handle_get_recommendations(user_id, session)
            elif intent == "schedule_visit":
                result = await self._handle_schedule_visit(user_id, entities, session)
            elif intent == "submit_application":
                result = await self._handle_submit_application(user_id, entities, session)
            else:
                result = {
                    "response": conv_result["response"],
                    "intent": intent
                }

            # Update session context
            session["context"]["last_intent"] = intent
            session["context"]["last_entities"] = entities

            return result

        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {
                "response": "I'm sorry, I encountered an error processing your request. Please try again.",
                "error": str(e)
            }

    async def _handle_search_pets(
        self,
        user_id: str,
        entities: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle pet search intent."""
        try:
            # Extract search parameters
            pet_type = entities.get("pet_type")
            location = session.get("profile", {}).get("city") if session.get("profile") else None

            if not location:
                return {
                    "response": "I need to know your location to search for pets. What city and state are you in?",
                    "requires_input": "location"
                }

            # Search for pets
            pets = await self.tools.fetch_shelter_data(
                pet_type=pet_type,
                location=location,
                distance=50,
                limit=50
            )

            # Store in session context
            session["context"]["search_results"] = [pet.dict() for pet in pets]

            response = f"I found {len(pets)} {pet_type or 'pet'}s near {location}. "
            if pets:
                response += "Would you like me to recommend the best matches for you?"

            return {
                "response": response,
                "pets_found": len(pets),
                "intent": "search_pets"
            }

        except Exception as e:
            logger.error(f"Error handling search pets: {e}")
            return {
                "response": "I had trouble searching for pets. Please try again.",
                "error": str(e)
            }

    async def _handle_get_recommendations(
        self,
        user_id: str,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle recommendation request."""
        try:
            user_profile = session.get("profile")

            if not user_profile:
                return {
                    "response": "I need to learn more about your preferences first. What type of pet are you looking for?",
                    "requires_input": "preferences"
                }

            # Get search results from session or search
            search_results = session["context"].get("search_results")

            if not search_results:
                # Search for pets
                pets = await self.tools.fetch_shelter_data(
                    pet_type=user_profile.preferences.pet_type.value if user_profile.preferences.pet_type else None,
                    location=f"{user_profile.city}, {user_profile.state}",
                    distance=50,
                    limit=100
                )
            else:
                # Convert dict back to Pet objects
                from .schemas.pet_data import Pet
                pets = [Pet(**pet_data) for pet_data in search_results]

            if not pets:
                return {
                    "response": "I couldn't find any pets matching your criteria. Would you like to adjust your search?",
                    "recommendations": []
                }

            # Generate recommendations
            recommendations = self.tools.generate_recommendations(
                user=user_profile,
                pets=pets,
                top_k=5
            )

            # Store in session
            session["context"]["recommendations"] = [rec.dict() for rec in recommendations]

            # Build response
            if recommendations:
                response = f"I found {len(recommendations)} great matches for you! Here are my top recommendations:\n\n"
                for i, rec in enumerate(recommendations[:3], 1):
                    pet = rec.pet
                    response += f"{i}. {pet.name} - {pet.breed or pet.species.value.title()}"
                    response += f" ({rec.overall_score:.0%} match)\n"
                    response += f"   {rec.match_explanation}\n\n"
            else:
                response = "I couldn't find any pets that match your criteria well. Would you like to adjust your preferences?"

            return {
                "response": response,
                "recommendations": [rec.dict() for rec in recommendations[:5]],
                "intent": "get_recommendations"
            }

        except Exception as e:
            logger.error(f"Error handling recommendations: {e}")
            return {
                "response": "I had trouble generating recommendations. Please try again.",
                "error": str(e)
            }

    async def _handle_schedule_visit(
        self,
        user_id: str,
        entities: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle visit scheduling intent."""
        try:
            # Get pet from context or entities
            recommendations = session["context"].get("recommendations", [])

            if not recommendations:
                return {
                    "response": "Which pet would you like to visit? Please tell me the pet's name or select from your recommendations.",
                    "requires_input": "pet_selection"
                }

            # For simplicity, schedule visit for first recommended pet
            pet_data = recommendations[0]["pet"]
            pet_id = pet_data["pet_id"]

            # Schedule for tomorrow at 2 PM (simplified)
            from datetime import timedelta
            visit_time = datetime.utcnow() + timedelta(days=1, hours=14)

            visit_info = self.tools.schedule_visit(
                user_id=user_id,
                pet_id=pet_id,
                preferred_time=visit_time
            )

            pet_name = pet_data["name"]
            shelter_name = pet_data["shelter"]["name"]

            response = f"Great! I've scheduled a visit for you to meet {pet_name} at {shelter_name} "
            response += f"on {visit_time.strftime('%A, %B %d at %I:%M %p')}. "
            response += "You'll receive a confirmation email shortly."

            return {
                "response": response,
                "visit_info": visit_info,
                "intent": "schedule_visit"
            }

        except Exception as e:
            logger.error(f"Error handling schedule visit: {e}")
            return {
                "response": "I had trouble scheduling your visit. Please try again.",
                "error": str(e)
            }

    async def _handle_submit_application(
        self,
        user_id: str,
        entities: Dict[str, Any],
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle application submission intent."""
        try:
            user_profile = session.get("profile")

            if not user_profile:
                return {
                    "response": "I need your information to start an application. Please provide your contact details.",
                    "requires_input": "user_info"
                }

            # Get pet from context
            recommendations = session["context"].get("recommendations", [])

            if not recommendations:
                return {
                    "response": "Which pet would you like to apply for? Please select from your recommendations.",
                    "requires_input": "pet_selection"
                }

            pet_data = recommendations[0]["pet"]
            pet_id = pet_data["pet_id"]

            # Build application data from user profile
            application_data = {
                "first_name": user_profile.first_name,
                "last_name": user_profile.last_name,
                "email": user_profile.email,
                "phone": user_profile.phone or "",
                "address": user_profile.address or "",
                "city": user_profile.city,
                "state": user_profile.state,
                "zip_code": user_profile.zip_code,
                "home_type": user_profile.preferences.home_type.value,
                "home_owned_rented": "owned",  # Simplified
                "adoption_reason": "Looking for a companion"  # Simplified
            }

            # Process application
            application = self.tools.process_application(
                user_id=user_id,
                pet_id=pet_id,
                application_data=application_data,
                application_type="adoption"
            )

            pet_name = pet_data["name"]

            response = f"Your adoption application for {pet_name} has been submitted successfully! "
            response += f"Application ID: {application['application_id']}. "
            response += "The shelter will review your application and contact you within 2-3 business days."

            return {
                "response": response,
                "application": application,
                "intent": "submit_application"
            }

        except Exception as e:
            logger.error(f"Error handling application submission: {e}")
            return {
                "response": "I had trouble submitting your application. Please try again.",
                "error": str(e)
            }

    async def create_user_profile(self, user_data: Dict[str, Any]) -> UserProfile:
        """
        Create a user profile from provided data.

        Args:
            user_data: Dictionary containing user information

        Returns:
            UserProfile object

        Raises:
            ValueError: If validation fails
        """
        is_valid, error_msg, user_profile = validate_user_input(user_data)

        if not is_valid:
            logger.warning(f"Invalid user data: {error_msg}")
            raise ValueError(f"Invalid user data: {error_msg}")

        logger.info(f"Created user profile for {user_profile.user_id}")
        return user_profile

    async def find_matches(
        self,
        user_profile: UserProfile,
        top_k: int = 10
    ) -> List[PetMatch]:
        """
        Complete matching flow: search and recommend pets for a user.

        Args:
            user_profile: User profile with preferences
            top_k: Number of recommendations to return

        Returns:
            List of PetMatch objects
        """
        try:
            logger.info(f"Finding matches for user {user_profile.user_id}")

            matches = await self.tools.search_and_recommend(
                user=user_profile,
                top_k=top_k
            )

            logger.info(f"Found {len(matches)} matches")
            return matches

        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return []

    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        return self.user_sessions.get(user_id)

    def clear_session(self, user_id: str) -> None:
        """Clear user session data."""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")


# Main entry point for command-line usage
async def main():
    """Main entry point for running the agent."""
    import argparse

    parser = argparse.ArgumentParser(description="PawConnect AI Agent")
    parser.add_argument("--user-location", required=True, help="User location (zip code like '98101' or 'City, State' like 'Seattle, WA')")
    parser.add_argument("--pet-type", default="dog", help="Type of pet (dog, cat, etc.)")
    parser.add_argument("--size", default="medium", help="Pet size preference")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum results")

    args = parser.parse_args()

    # Initialize agent
    agent = PawConnectMainAgent()

    # Create a test user profile
    from .schemas.user_profile import UserProfile, UserPreferences, HomeType, ExperienceLevel, PetType, PetSize

    # Handle both "City, State" and "ZipCode" formats
    if "," in args.user_location:
        # City, State format
        city, state = args.user_location.split(",")
        city = city.strip()
        state = state.strip()
        zip_code = "00000"
    else:
        # Zip code format - use placeholder values that pass validation
        city = "Location"
        state = "WA"  # Use valid state code as placeholder
        zip_code = args.user_location.strip()

    user_data = {
        "user_id": "test_user_001",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "preferences": {
            "pet_type": args.pet_type,
            "pet_size": [args.size],
            "home_type": "house",
            "experience_level": "some_experience"
        },
        "is_adopter": True
    }

    try:
        user_profile = await agent.create_user_profile(user_data)

        # Find matches
        matches = await agent.find_matches(user_profile, top_k=args.max_results)

        # Print results
        print(f"\n=== PawConnect AI - Pet Recommendations ===\n")
        print(f"Found {len(matches)} matches for {user_profile.first_name}\n")

        for i, match in enumerate(matches, 1):
            pet = match.pet
            print(f"{i}. {pet.name} - {pet.breed or pet.species.value.title()}")
            print(f"   Match Score: {match.overall_score:.0%}")
            print(f"   {match.match_explanation}")
            print(f"   Shelter: {pet.shelter.name}, {pet.shelter.city}, {pet.shelter.state}")
            print()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())


# ============================================================================
# ADK Web Interface Integration
# ============================================================================

if ADK_AVAILABLE:
    from google.adk.models import Gemini
    import os

    # Define system instruction for the ADK agent
    SYSTEM_INSTRUCTION = """You are PawConnect AI, a helpful assistant specializing in pet adoption and fostering.

Your capabilities include:
- Searching for available pets from RescueGroups.org database
- Answering questions about pet adoption and fostering
- Providing information about breeds and pet care
- Guiding users through the adoption process
- Discussing pet characteristics and matching

Key features:
- Powered by Google Gemini for natural language understanding
- Direct access to RescueGroups API for real-time pet availability
- Conversational AI with context awareness
- Expert knowledge about pets and adoption

When a user asks to find pets:
1. Use the search_pets function to query RescueGroups
2. Present the results with pet names, breeds, and descriptions
3. Include links to adoption pages when available

Be friendly, empathetic, and guide users through the pet adoption journey with real pet listings."""

    # Set environment variables for Vertex AI (required by ADK)
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.gcp_project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.gcp_region

    # Also set VERTEXAI environment variable to force Vertex AI usage
    os.environ["VERTEXAI"] = "1"

    # Create function tools for RescueGroups API access
    async def search_pets(
        pet_type: str = "dog",
        location: str = "",
        breed: str = "",
        size: str = "",
        age: str = "",
        limit: int = 10
    ) -> str:
        """
        Search for available pets from RescueGroups.org database.

        Args:
            pet_type: Type of pet to search for (dog, cat, rabbit, etc.)
            location: Location to search (city, state or ZIP code)
            breed: Specific breed to search for (optional)
            size: Size of pet (small, medium, large, extra-large) (optional)
            age: Age group (baby, young, adult, senior) (optional)
            limit: Maximum number of results to return (default 10, max 100)

        Returns:
            JSON string containing list of available pets with details
        """
        import json
        from .sub_agents.pet_search_agent import PetSearchAgent

        try:
            # Create search agent
            search_agent = PetSearchAgent()

            # Build kwargs for additional filters
            kwargs = {}
            if breed:
                kwargs['breed'] = breed
            if size:
                kwargs['size'] = size
            if age:
                kwargs['age'] = age

            # Run async search (we're already in async context from ADK)
            pets = await search_agent.search_pets(
                pet_type=pet_type,
                location=location,
                limit=min(limit, 100),
                **kwargs
            )

            # Format results for Gemini
            if not pets:
                return json.dumps({
                    "success": False,
                    "message": f"No {pet_type}s found in {location or 'the database'}",
                    "pets": []
                })

            # Convert Pet objects to dicts (limit to requested number)
            results = []
            for pet in pets[:limit]:
                try:
                    pet_dict = {
                        "id": pet.pet_id,
                        "name": pet.name,
                        "breed": pet.breed or "Mixed Breed",
                        "age": pet.age.value if hasattr(pet.age, 'value') else str(pet.age),
                        "size": pet.size.value if hasattr(pet.size, 'value') else str(pet.size),
                        "sex": pet.gender.value if hasattr(pet.gender, 'value') else str(pet.gender),
                        "description": pet.description[:200] + "..." if len(pet.description) > 200 else pet.description,
                        "location": f"{pet.shelter.city}, {pet.shelter.state}" if pet.shelter else "Location not specified",
                        "shelter_name": pet.shelter.name if pet.shelter else "Unknown",
                        "photo_url": str(pet.primary_photo_url) if pet.primary_photo_url else None,
                        "adoption_url": f"https://rescuegroups.org/animal/{pet.external_id}" if pet.external_id else None
                    }
                    results.append(pet_dict)
                except Exception as e:
                    logger.error(f"Error processing pet {pet.name}: {e}")
                    continue

            return json.dumps({
                "success": True,
                "message": f"Found {len(results)} {pet_type}(s) in {location or 'the database'}",
                "count": len(results),
                "pets": results
            }, indent=2)

        except Exception as e:
            logger.error(f"Error in search_pets function: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error searching for pets: {str(e)}",
                "pets": []
            })

    # Create the ADK LlmAgent with Vertex AI configuration
    try:
        from google.genai import Client
        from functools import cached_property

        # Create a custom Gemini subclass that properly maintains Vertex AI config
        class VertexAIGemini(Gemini):
            """Custom Gemini class that ensures Vertex AI configuration persists."""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Store the Vertex AI configuration
                self._vertexai = kwargs.get('vertexai', True)
                self._project = kwargs.get('project')
                self._location = kwargs.get('location')
                # Pre-create the client
                self._cached_client = Client(
                    vertexai=self._vertexai,
                    project=self._project,
                    location=self._location
                )

            @property
            def api_client(self):
                """Override api_client property to return our pre-configured client."""
                return self._cached_client

        # Create a VertexAIGemini LLM instance with proper configuration
        # Using Gemini 2.0 Flash (Gemini 1.5 models retired April 2025)
        gemini_llm = VertexAIGemini(
            model="gemini-2.0-flash-001",
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region
        )

        # Create the ADK LlmAgent with the configured Gemini LLM and tools
        root_agent = LlmAgent(
            name="pawconnect_ai",
            model=gemini_llm,
            instruction=SYSTEM_INSTRUCTION,
            tools=[search_pets]
        )

        logger.info(f"ADK root_agent created successfully with Vertex AI Gemini")
        logger.info(f"Project: {settings.gcp_project_id}, Region: {settings.gcp_region}")
        logger.info(f"Custom VertexAI Gemini class configured")
        logger.info(f"Function tools registered: search_pets")

    except Exception as e:
        logger.error(f"Failed to create ADK agent with Gemini LLM: {e}")
        logger.warning(f"Error details: {type(e).__name__}: {str(e)}")

        # If this fails, PawConnect won't work with ADK web interface
        # User will need to check their GCP credentials and configuration
        raise RuntimeError(
            f"Failed to initialize PawConnect AI with Vertex AI. "
            f"Please ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly. "
            f"Error: {e}"
        )

else:
    # Create a dummy agent if ADK is not available
    class DummyAgent:
        """Dummy agent for when ADK is not available."""
        async def send(self, message: str, user_id: str = "default") -> str:
            return "ADK is not available. Please install google-adk package."

    root_agent = DummyAgent()
    logger.warning("ADK not available - created dummy root_agent")
