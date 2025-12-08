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
    from google.adk.apps import App
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
                    "requires_input": "location",
                    "intent": "search_pets"
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
                "error": str(e),
                "intent": "search_pets"
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
                    "requires_input": "preferences",
                    "intent": "get_recommendations"
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
                    "recommendations": [],
                    "intent": "get_recommendations"
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
                "error": str(e),
                "intent": "get_recommendations"
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
                    "requires_input": "pet_selection",
                    "intent": "schedule_visit"
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
                "error": str(e),
                "intent": "schedule_visit"
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
                    "requires_input": "user_info",
                    "intent": "submit_application"
                }

            # Get pet from context
            recommendations = session["context"].get("recommendations", [])

            if not recommendations:
                return {
                    "response": "Which pet would you like to apply for? Please select from your recommendations.",
                    "requires_input": "pet_selection",
                    "intent": "submit_application"
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
                "error": str(e),
                "intent": "submit_application"
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
    from typing import Dict, List
    from datetime import datetime, timedelta

    # ============================================================================
    # Conversation State Management - Store recent search results for follow-ups
    # ============================================================================
    class ConversationState:
        """Manages conversation state to enable follow-up questions about pets."""

        def __init__(self, ttl_minutes: int = 30):
            self._searches: Dict[str, dict] = {}  # session_id -> {timestamp, pets}
            self._ttl = timedelta(minutes=ttl_minutes)

        def store_search_results(self, session_id: str, pets: List[dict]):
            """Store search results for a session."""
            self._searches[session_id] = {
                'timestamp': datetime.utcnow(),
                'pets': pets
            }
            logger.info(f"Stored {len(pets)} pets for session {session_id}")

        def get_search_results(self, session_id: str) -> List[dict]:
            """Get recent search results for a session."""
            if session_id not in self._searches:
                return []

            search = self._searches[session_id]
            # Check if results are still fresh
            if datetime.utcnow() - search['timestamp'] > self._ttl:
                del self._searches[session_id]
                return []

            return search['pets']

        def find_pet_by_name(self, session_id: str, pet_name: str) -> dict:
            """Find a specific pet from recent searches by name."""
            pets = self.get_search_results(session_id)
            pet_name_lower = pet_name.lower()

            for pet in pets:
                if pet['name'].lower() == pet_name_lower:
                    logger.info(f"Found pet {pet_name} in cached results")
                    return pet

            return None

        def cleanup_old_sessions(self):
            """Remove expired sessions."""
            now = datetime.utcnow()
            expired = [
                sid for sid, data in self._searches.items()
                if now - data['timestamp'] > self._ttl
            ]
            for sid in expired:
                del self._searches[sid]

    # Global conversation state instance
    conversation_state = ConversationState(ttl_minutes=30)

    # Define system instruction for the ADK agent
    SYSTEM_INSTRUCTION = """You are PawConnect AI, a helpful assistant specializing in pet adoption and fostering.

Your capabilities include:
- Searching for available pets from RescueGroups.org database
- Answering questions about pet adoption and fostering
- Providing information about breeds and pet care
- Guiding users through the adoption process
- Discussing pet characteristics and matching
- Providing rescue organization contact information

Key features:
- Powered by Google Gemini for natural language understanding
- Direct access to RescueGroups API for real-time pet availability
- Conversational AI with context awareness and memory of recent searches
- Expert knowledge about pets and adoption

IMPORTANT - Context Awareness & Memory:
After performing a search with search_pets, the results are automatically cached for 30 minutes.
This means follow-up questions about pets from the search can be answered WITHOUT calling search_pets again.

When a user asks follow-up questions about a specific pet (e.g., "Tell me more about LOGAN", "What's Apollo's temperament?", "Show me Kona's photo"):
1. First, check if you have the pet's information from your most recent search_pets call
2. If you have the information, answer DIRECTLY using that data - DON'T call any functions
3. For example, if the search returned LOGAN's breed, age, description, and shelter info, just answer the question using that data
4. Only call get_rescue_contact if:
   - You DON'T have information about that pet from recent searches, OR
   - The user explicitly asks for contact information or scheduling
5. Only call search_pets again if the user is asking for a **NEW search with DIFFERENT criteria**:
   - Different pet type (dogs → cats)
   - Different size (any dogs → small dogs)
   - Different age (any dogs → puppies)
   - Different breed (any dogs → Golden Retrievers)
   - Different location (98101 → 98102)
   - User explicitly asks to "search again" or "find different pets"

Benefits of using context:
- Faster responses (no API calls needed)
- More conversational experience
- Reduces unnecessary API usage
- The pet data includes: name, breed, age, size, sex, description, location, shelter info, and photo link

Example conversation flows:

**Example 1: Follow-up questions about a specific pet**
User: "Find dogs in 98101"
You: [Call search_pets(pet_type="dog", location="98101")] "I found 10 dogs including Apollo, Lexi, Kona, LOGAN, and BLACKJACK..."
User: "Tell me more about LOGAN"
You: [NO function call needed] "LOGAN is a [age] [breed] who [description from search results]. He's located at [shelter] in [city, state]."
User: "What's his temperament?"
You: [NO function call needed] [Answer from description field in search results]
User: "I want to schedule a visit with LOGAN"
You: [Call schedule_visit with LOGAN's name] - the function will use cached data automatically

**Example 2: New search with different size criteria**
User: "Find dogs in 98101"
You: [Call search_pets(pet_type="dog", location="98101")] "I found 10 dogs..."
User: "Tell me about LOGAN"
You: [NO function call] "LOGAN is a large German Shepherd..."
User: "I want to schedule a visit"
You: [Call schedule_visit("LOGAN")] "Great! Visit scheduled..."
User: "Actually, show me small dogs instead"
You: [Call search_pets(pet_type="dog", size="small", location="98101")] "I found 5 small dogs..."
NOTE: This is a NEW search with DIFFERENT criteria (size filter added), so you MUST call search_pets again!

When a user asks to find pets:
1. If the user hasn't specified what type of pet (dog, cat, rabbit, etc.), ask them what kind of pet they're interested in
2. Use the search_pets function to query RescueGroups with the specified pet_type and location
3. **IMPORTANT - Use ALL available search filters when specified by the user:**
   - **Size filter**: If user mentions "small", "medium", "large", or "extra-large", pass the `size` parameter
     - Examples: "small dogs" → size="small", "large cats" → size="large"
   - **Age filter**: If user mentions age, pass the `age` parameter
     - "puppies" → age="baby", "young dogs" → age="young", "senior dogs" → age="senior", "adult dogs" → age="adult"
   - **Breed filter**: If user mentions a specific breed, pass the `breed` parameter
     - "Golden Retrievers" → breed="Golden Retriever"
   - **Always include location** if the user provided it in this or a previous message

   **Examples of proper filter usage:**
   - User: "Show me small dogs in 98101" → search_pets(pet_type="dog", size="small", location="98101")
   - User: "Find puppies near me" → search_pets(pet_type="dog", age="baby", location="[their location]")
   - User: "I want a large Golden Retriever" → search_pets(pet_type="dog", breed="Golden Retriever", size="large", location="[their location]")
   - User: "Show me senior cats" → search_pets(pet_type="cat", age="senior", location="[their location]")

   **IMPORTANT - Remember location across searches:**
   - Once a user provides a location (like "98101"), remember it for subsequent searches in the same conversation
   - Example: User says "Find dogs in 98101", then later says "Now show me small dogs" → use location="98101" for the second search too
   - Only omit location if the user explicitly asks to search without location restrictions

4. IMPORTANT - Location filtering LIMITATION:
   - The RescueGroups public API may not filter results by location reliably
   - Even when a ZIP code is provided (e.g., "98101"), results may include pets from ALL locations nationwide
   - ALWAYS check the "location" field for each pet and INFORM the user that results may include pets from outside their search area
   - Suggest users contact shelters in their local area directly or visit local animal shelters
   - When presenting results, GROUP pets by location and clearly indicate which ones are in the user's area vs. other locations
   - If user wants only local results, apologize and explain the API limitation, then suggest they visit local shelter websites directly
4. Present the results with the following information for EACH pet:
   - Pet name (bold)
   - Breed
   - Age and gender
   - **LOCATION** (city, state) - MUST be included for every pet
   - Brief description
   - Photo (if available)
   - Shelter name
   - Adoption link or contact information
5. Include links to adoption pages ONLY when a valid shelter website URL is available
6. If no adoption URL is provided, direct users to contact the shelter directly using the shelter_contact information
7. Remind users they can right-click links to open them in a new tab
8. Encourage users to contact the shelter directly for the most up-to-date information

Example format for presenting a pet:
**Max** - Golden Retriever, Adult Male
📍 Location: Seattle, WA
A friendly and energetic dog who loves playing fetch...
🏠 Shelter: Seattle Humane Society
🔗 [Adoption Link] or Contact: (206) 555-1234

IMPORTANT - Displaying Pet Photos:
When users ask to see a pet's picture or photo:
1. If you have the pet's information from a recent search, extract the photo_link from the results
2. If you don't have the pet's information, use the get_rescue_contact function to find the pet and get their photo_link
3. Provide the photo as a clickable link: "Here's [Pet Name]'s photo: [View Photo](photo_link)"
4. On a separate line, include a brief description and the shelter contact info
5. If the photo_link is None, explain no photo is available in the database and provide contact info
6. NEVER say you cannot show images - always provide the photo_link as a clickable link

Example response format:
"Here's Bella's photo: [View Bella's Photo](https://cdn.rescuegroups.org/photo.jpg)

Bella is a 3-year-old Golden Retriever. For more photos and information, contact Seattle Humane Society at (206) 555-1234."

DO NOT use complex markdown formatting. Keep responses simple with plain text and basic links only.
IMPORTANT: The field is called photo_link (NOT photo_url) to prevent automatic image embedding.

IMPORTANT - Scheduling Appointments & Visits:
When users ask about scheduling appointments, meeting pets, or visiting shelters:

1. **FIRST, ask for their preferred time** if they haven't provided it:
   - Ask: "When would you like to visit [Pet Name]? Please let me know your preferred date and time."
   - Example times to suggest: weekday mornings, weekday afternoons, weekend mornings, weekend afternoons
   - Wait for user response with their preferred time

2. **THEN, use the schedule_visit function** with their preferred time:
   - Pass the pet_name and the user's preferred_date and preferred_time
   - The function will create a visit request
   - Provide the rescue's contact information
   - Give next steps for confirming the appointment

3. **After scheduling, explain that:**
   - The visit request has been created for their requested time
   - The rescue will contact them to confirm or suggest alternative times
   - They should bring valid ID and any questions about adoption
   - They can contact the rescue directly if they need to make changes

Example interaction:
User: "I want to schedule an appointment to meet Lucky"
You: "I'd be happy to help you schedule a visit to meet Lucky! When would you like to visit? Please let me know your preferred date and time (for example, 'this Saturday at 10 AM' or 'next Tuesday afternoon')."

User: "This Saturday at 10 AM"
You: [Call schedule_visit with preferred_date="2025-12-07" and preferred_time="10:00 AM"]

Then respond:
"I've scheduled a visit request for you to meet Lucky!

📅 Requested Time: Saturday, December 7 at 10:00 AM
🏠 Rescue: Rescue Ranch
📍 Address: 2216 Oberlin Rd., Yreka, Ca 96097
📞 Phone: (530) 842-0829
✉️ Email: Inquiries@rrdog.org

Next steps:
1. The rescue will contact you to confirm the appointment or suggest alternative times
2. Bring a valid ID when you visit
3. Feel free to call or email them if you need to make changes

I recommend preparing any questions you have about the adoption process!"

IMPORTANT: Always ask for preferred time BEFORE calling schedule_visit, unless the user already specified it in their request.

Be friendly, empathetic, and guide users through the pet adoption journey with real pet listings."""

    # Set environment variables for Vertex AI (required by ADK)
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.gcp_project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.gcp_region

    # Also set VERTEXAI environment variable to force Vertex AI usage
    os.environ["VERTEXAI"] = "1"

    # Create function tools for RescueGroups API access
    async def search_pets(
        pet_type: str = "",
        location: str = "",
        distance: int = 50,
        breed: str = "",
        size: str = "",
        age: str = "",
        limit: int = 10,
        session_id: str = "default"
    ) -> str:
        """
        Search for available pets from RescueGroups.org database.

        IMPORTANT: Use the filter parameters (size, age, breed) when the user specifies them!
        - If user says "small dogs", pass size="small"
        - If user says "puppies", pass age="baby"
        - If user says "Golden Retrievers", pass breed="Golden Retriever"

        IMPORTANT LIMITATION: The RescueGroups public API may not filter by location reliably.
        Results may include pets from all locations regardless of ZIP code provided.
        Always check each pet's "location" field and inform users about pets from outside their area.

        Args:
            pet_type: Type of pet to search for (dog, cat, rabbit, etc.). If not specified, searches all types.
                     REQUIRED when user specifies a pet type.
            location: Location to search. Provide ZIP code (e.g., "98101") but be aware results may include
                     pets from anywhere in the country due to API limitations.
            distance: Search radius in miles from the location (default 50, max 500). May not be honored by API.
            breed: Specific breed to search for. USE THIS when user mentions a breed!
                  Examples: "Golden Retriever", "Labrador Retriever", "Siamese"
            size: Size of pet. USE THIS when user mentions size!
                 Valid values: "small", "medium", "large", "extra-large"
                 Examples: "small dogs" → size="small", "large cats" → size="large"
            age: Age group. USE THIS when user mentions age!
                Valid values: "baby", "young", "adult", "senior"
                Examples: "puppies" → age="baby", "senior dogs" → age="senior"
            limit: Maximum number of results to return (default 10, max 100)
            session_id: Session identifier for caching results (automatically provided by ADK)

        Returns:
            JSON string containing list of available pets with details. Each pet includes a "location" field
            showing where the pet is actually located.

        Examples:
            - User: "Find small dogs in 98101" → search_pets(pet_type="dog", size="small", location="98101")
            - User: "Show me puppies" → search_pets(pet_type="dog", age="baby", location="[user's location]")
            - User: "Large Golden Retrievers" → search_pets(pet_type="dog", breed="Golden Retriever", size="large", location="[user's location]")
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
                distance=distance,
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
                    # Construct adoption URL with priority order:
                    # 1. Direct animal URL from API (if available)
                    # 2. Shelter's website URL (if available)
                    # 3. None (direct user to contact information)
                    adoption_url = None

                    # Priority 1: Check if API provided direct animal URL
                    if hasattr(pet, 'animal_url') and pet.animal_url:
                        adoption_url = str(pet.animal_url)
                        logger.debug(f"Using animal_url for {pet.name}: {adoption_url}")
                    # Priority 2: Use shelter's website
                    elif pet.shelter and hasattr(pet.shelter, 'website') and pet.shelter.website:
                        adoption_url = str(pet.shelter.website)
                        logger.debug(f"Using shelter website for {pet.name}: {adoption_url}")
                    else:
                        logger.debug(f"No adoption URL available for {pet.name}, animal_url: {getattr(pet, 'animal_url', 'N/A')}")

                    # Build shelter contact information
                    shelter_contact = {}
                    if pet.shelter:
                        shelter_contact = {
                            "name": pet.shelter.name,
                            "address": getattr(pet.shelter, 'address', None),
                            "city": pet.shelter.city,
                            "state": pet.shelter.state,
                            "zip_code": pet.shelter.zip_code,
                            "phone": getattr(pet.shelter, 'phone', None),
                            "email": getattr(pet.shelter, 'email', None),
                            "website": str(pet.shelter.website) if hasattr(pet.shelter, 'website') and pet.shelter.website else None
                        }

                    # Build full description including special needs if available
                    full_description = pet.description[:200] + "..." if len(pet.description) > 200 else pet.description
                    if hasattr(pet, 'special_needs_info') and pet.special_needs_info:
                        full_description += f"\n\n⚠️ SPECIAL NEEDS: {pet.special_needs_info}"
                    if hasattr(pet, 'has_allergies') and pet.has_allergies:
                        full_description += "\n\n⚠️ Has allergies - please inquire with shelter for details."

                    pet_dict = {
                        "id": pet.pet_id,
                        "name": pet.name,
                        "breed": pet.breed or "Mixed Breed",
                        "age": pet.age.value if hasattr(pet.age, 'value') else str(pet.age),
                        "size": pet.size.value if hasattr(pet.size, 'value') else str(pet.size),
                        "sex": pet.gender.value if hasattr(pet.gender, 'value') else str(pet.gender),
                        "description": full_description,
                        "location": f"{pet.shelter.city}, {pet.shelter.state}" if pet.shelter else "Location not specified",
                        "shelter_name": pet.shelter.name if pet.shelter else "Unknown",
                        "shelter_contact": shelter_contact,
                        "photo_link": str(pet.primary_photo_url) if pet.primary_photo_url else None,
                        "adoption_url": adoption_url
                    }
                    results.append(pet_dict)
                except Exception as e:
                    logger.error(f"Error processing pet {pet.name}: {e}")
                    continue

            # Store search results in conversation state for follow-up questions
            conversation_state.store_search_results(session_id, results)

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

    async def get_rescue_contact(pet_name: str, location: str = "", session_id: str = "default") -> str:
        """
        Get contact information for the rescue organization caring for a specific pet.
        Use this when users ask about scheduling appointments, visiting, or contacting the rescue.

        Args:
            pet_name: Name of the pet the user is interested in
            location: Optional location to help narrow down the search
            session_id: Session ID for retrieving cached pet data

        Returns:
            JSON string with rescue contact information
        """
        import json
        from .sub_agents.pet_search_agent import PetSearchAgent

        try:
            logger.info(f"Getting rescue contact for pet: {pet_name}")

            # First, check if pet is in recent search results (avoid unnecessary API call)
            cached_pet = conversation_state.find_pet_by_name(session_id, pet_name)

            if cached_pet:
                logger.info(f"Using cached data for {pet_name}")
                # Pet found in cache - return contact info directly
                contact_info = {
                    "pet_name": cached_pet['name'],
                    "pet_breed": cached_pet.get('breed', 'Mixed Breed'),
                    "pet_age": cached_pet.get('age', 'Unknown'),
                    "pet_description": cached_pet.get('description', 'No description available'),
                    "photo_link": cached_pet.get('photo_link'),
                    "rescue_name": cached_pet.get('shelter_contact', {}).get('name', 'Unknown'),
                    "phone": cached_pet.get('shelter_contact', {}).get('phone'),
                    "email": cached_pet.get('shelter_contact', {}).get('email'),
                    "website": cached_pet.get('shelter_contact', {}).get('website'),
                    "address": cached_pet.get('shelter_contact', {}).get('address'),
                    "city": cached_pet.get('shelter_contact', {}).get('city'),
                    "state": cached_pet.get('shelter_contact', {}).get('state'),
                    "zip_code": cached_pet.get('shelter_contact', {}).get('zip_code'),
                    "full_address": f"{cached_pet.get('shelter_contact', {}).get('address', '')}, {cached_pet.get('shelter_contact', {}).get('city', '')}, {cached_pet.get('shelter_contact', {}).get('state', '')} {cached_pet.get('shelter_contact', {}).get('zip_code', '')}".strip(", ")
                }

                return json.dumps({
                    "success": True,
                    "message": f"Contact information for {cached_pet['name']} at {cached_pet.get('shelter_contact', {}).get('name', 'the rescue')}",
                    "contact": contact_info,
                    "from_cache": True
                }, indent=2)

            # Pet not in cache - need to search
            logger.info(f"Pet {pet_name} not in cache, performing search")
            search_agent = PetSearchAgent()
            pets = await search_agent.search_pets(
                location=location,
                limit=20
            )

            # Find the pet by name (case insensitive)
            pet = None
            for p in pets:
                if p.name.lower() == pet_name.lower():
                    pet = p
                    break

            if not pet or not pet.shelter:
                return json.dumps({
                    "success": False,
                    "message": f"Could not find contact information for a pet named {pet_name}. Please search for pets first.",
                })

            # Extract complete contact information including photo
            contact_info = {
                "pet_name": pet.name,
                "pet_breed": pet.breed or "Mixed Breed",
                "pet_age": pet.age.value if hasattr(pet.age, 'value') else str(pet.age),
                "pet_description": pet.description[:200] + "..." if len(pet.description) > 200 else pet.description,
                "photo_link": str(pet.primary_photo_url) if pet.primary_photo_url else None,
                "rescue_name": pet.shelter.name,
                "phone": getattr(pet.shelter, 'phone', None),
                "email": getattr(pet.shelter, 'email', None),
                "website": str(pet.shelter.website) if hasattr(pet.shelter, 'website') and pet.shelter.website else None,
                "address": getattr(pet.shelter, 'address', None),
                "city": pet.shelter.city,
                "state": pet.shelter.state,
                "zip_code": pet.shelter.zip_code,
                "full_address": f"{getattr(pet.shelter, 'address', '')}, {pet.shelter.city}, {pet.shelter.state} {pet.shelter.zip_code}".strip(", ")
            }

            return json.dumps({
                "success": True,
                "message": f"Contact information for {pet.name} at {pet.shelter.name}",
                "contact": contact_info,
                "from_cache": False
            }, indent=2)

        except Exception as e:
            logger.error(f"Error getting rescue contact: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error retrieving contact information: {str(e)}"
            })

    async def schedule_visit(
        pet_name: str,
        location: str = "",
        preferred_date: str = "",
        preferred_time: str = "",
        session_id: str = "default"
    ) -> str:
        """
        Schedule a visit to meet a pet at their rescue organization.
        This creates a visit request that will be sent to the rescue for confirmation.

        Args:
            pet_name: Name of the pet the user wants to meet
            location: Optional location to help find the pet
            preferred_date: Preferred date for visit (e.g., "2025-12-15" or "next week")
            preferred_time: Preferred time for visit (e.g., "2:00 PM", "morning", "afternoon")
            session_id: Session ID for retrieving cached pet data

        Returns:
            JSON string with visit scheduling confirmation
        """
        import json
        from .sub_agents.pet_search_agent import PetSearchAgent
        from datetime import datetime, timedelta

        try:
            logger.info(f"Scheduling visit for pet: {pet_name}")

            # First, check if pet is in recent search results (avoid unnecessary API call)
            cached_pet = conversation_state.find_pet_by_name(session_id, pet_name)

            if cached_pet:
                logger.info(f"Using cached data for {pet_name}")
                # Pet found in cache - use cached data
                pet_id = cached_pet['id']
                pet_breed = cached_pet.get('breed', 'Mixed Breed')
                shelter_name = cached_pet.get('shelter_contact', {}).get('name', 'Unknown')
                shelter_phone = cached_pet.get('shelter_contact', {}).get('phone')
                shelter_email = cached_pet.get('shelter_contact', {}).get('email')
                shelter_website = cached_pet.get('shelter_contact', {}).get('website')
                shelter_address = cached_pet.get('shelter_contact', {}).get('address', '')
                shelter_city = cached_pet.get('shelter_contact', {}).get('city', '')
                shelter_state = cached_pet.get('shelter_contact', {}).get('state', '')
                shelter_zip = cached_pet.get('shelter_contact', {}).get('zip_code', '')
                full_address = f"{shelter_address}, {shelter_city}, {shelter_state} {shelter_zip}".strip(", ")

                # Parse preferred time
                if preferred_date:
                    try:
                        visit_datetime = datetime.fromisoformat(preferred_date)
                    except:
                        visit_datetime = datetime.utcnow() + timedelta(days=1)
                        visit_datetime = visit_datetime.replace(hour=14, minute=0, second=0, microsecond=0)
                else:
                    visit_datetime = datetime.utcnow() + timedelta(days=1)
                    visit_datetime = visit_datetime.replace(hour=14, minute=0, second=0, microsecond=0)

                # Create tools instance and schedule visit
                tools = PawConnectTools()
                user_id = "web_user"

                visit_info = tools.schedule_visit(
                    user_id=user_id,
                    pet_id=pet_id,
                    preferred_time=visit_datetime
                )

                return json.dumps({
                    "success": True,
                    "message": f"Visit request submitted for {pet_name}!",
                    "visit": {
                        "visit_id": visit_info["visit_id"],
                        "pet_name": pet_name,
                        "pet_breed": pet_breed,
                        "scheduled_time": visit_info["scheduled_time"],
                        "status": visit_info["status"],
                        "rescue_name": shelter_name,
                        "rescue_phone": shelter_phone,
                        "rescue_email": shelter_email,
                        "rescue_website": shelter_website,
                        "rescue_address": full_address,
                        "next_steps": [
                            f"The rescue will receive your visit request for {visit_datetime.strftime('%A, %B %d at %I:%M %p')}",
                            "They will contact you to confirm the appointment or suggest alternative times",
                            "Please call or email them directly if you need to make changes",
                            "Bring a valid ID and any questions you have about the adoption process"
                        ]
                    },
                    "from_cache": True
                }, indent=2)

            # Pet not in cache - need to search
            logger.info(f"Pet {pet_name} not in cache, performing search")
            search_agent = PetSearchAgent()
            pets = await search_agent.search_pets(
                location=location,
                limit=20
            )

            # Find the pet by name (case insensitive)
            pet = None
            for p in pets:
                if p.name.lower() == pet_name.lower():
                    pet = p
                    break

            if not pet or not pet.shelter:
                return json.dumps({
                    "success": False,
                    "message": f"Could not find a pet named {pet_name}. Please search for pets first.",
                })

            # Parse preferred time (simplified - just schedule for tomorrow if not specified)
            if preferred_date:
                # Simple date parsing - in production would use more sophisticated parsing
                try:
                    visit_datetime = datetime.fromisoformat(preferred_date)
                except:
                    # Default to tomorrow at 2 PM
                    visit_datetime = datetime.utcnow() + timedelta(days=1)
                    visit_datetime = visit_datetime.replace(hour=14, minute=0, second=0, microsecond=0)
            else:
                # Default to tomorrow at 2 PM
                visit_datetime = datetime.utcnow() + timedelta(days=1)
                visit_datetime = visit_datetime.replace(hour=14, minute=0, second=0, microsecond=0)

            # Create tools instance and schedule visit
            tools = PawConnectTools()
            user_id = "web_user"  # Default user ID for web interface

            visit_info = tools.schedule_visit(
                user_id=user_id,
                pet_id=pet.pet_id,
                preferred_time=visit_datetime
            )

            # Build response with visit details and rescue contact info
            return json.dumps({
                "success": True,
                "message": f"Visit request submitted for {pet.name}!",
                "visit": {
                    "visit_id": visit_info["visit_id"],
                    "pet_name": pet.name,
                    "pet_breed": pet.breed or "Mixed Breed",
                    "scheduled_time": visit_info["scheduled_time"],
                    "status": visit_info["status"],
                    "rescue_name": pet.shelter.name,
                    "rescue_phone": getattr(pet.shelter, 'phone', None),
                    "rescue_email": getattr(pet.shelter, 'email', None),
                    "rescue_website": str(pet.shelter.website) if hasattr(pet.shelter, 'website') and pet.shelter.website else None,
                    "rescue_address": f"{getattr(pet.shelter, 'address', '')}, {pet.shelter.city}, {pet.shelter.state} {pet.shelter.zip_code}".strip(", "),
                    "next_steps": [
                        f"The rescue will receive your visit request for {visit_datetime.strftime('%A, %B %d at %I:%M %p')}",
                        "They will contact you to confirm the appointment or suggest alternative times",
                        "Please call or email them directly if you need to make changes",
                        "Bring a valid ID and any questions you have about the adoption process"
                    ]
                },
                "from_cache": False
            }, indent=2)

        except Exception as e:
            logger.error(f"Error scheduling visit: {e}")
            return json.dumps({
                "success": False,
                "message": f"Error scheduling visit: {str(e)}"
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
            tools=[search_pets, get_rescue_contact, schedule_visit]
        )

        logger.info(f"ADK root_agent created successfully with Vertex AI Gemini")
        logger.info(f"Project: {settings.gcp_project_id}, Region: {settings.gcp_region}")
        logger.info(f"Custom VertexAI Gemini class configured")
        logger.info(f"Function tools registered: search_pets, get_rescue_contact, schedule_visit")

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

# Create the App object for ADK integration
if ADK_AVAILABLE:
    app = App(name="pawconnect_ai", root_agent=root_agent)
    logger.info("ADK App created successfully")
else:
    app = None
    logger.warning("ADK not available - app is None")
