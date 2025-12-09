"""
Custom tools for PawConnect AI agents.
Provides specialized functions for pet search, matching, and workflow operations.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from .sub_agents.pet_search_agent import PetSearchAgent
from .sub_agents.recommendation_agent import RecommendationAgent
from .sub_agents.vision_agent import VisionAgent
from .sub_agents.workflow_agent import WorkflowAgent
from .schemas.pet_data import Pet, PetMatch
from .schemas.user_profile import UserProfile
from .utils.mcp_email_client import get_email_client
from .utils.mcp_calendar_client import get_calendar_client
from .config import settings


class PawConnectTools:
    """Collection of tools for PawConnect AI agent system."""

    def __init__(self):
        """Initialize all tools and sub-agents."""
        self.search_agent = PetSearchAgent()
        self.recommendation_agent = RecommendationAgent()
        self.vision_agent = VisionAgent()
        self.workflow_agent = WorkflowAgent()

    async def fetch_shelter_data(
        self,
        pet_type: Optional[str] = None,
        location: Optional[str] = None,
        distance: int = 50,
        limit: int = 100,
        **kwargs
    ) -> List[Pet]:
        """
        Fetch available pets from shelter APIs.

        Args:
            pet_type: Type of pet to search for
            location: Location (ZIP code or city, state)
            distance: Search radius in miles
            limit: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of Pet objects
        """
        try:
            logger.info(f"Fetching shelter data: type={pet_type}, location={location}")

            pets = await self.search_agent.search_pets(
                pet_type=pet_type,
                location=location,
                distance=distance,
                limit=limit,
                **kwargs
            )

            return pets

        except Exception as e:
            logger.error(f"Error fetching shelter data: {e}")
            return []

    def calculate_compatibility_score(
        self,
        user: UserProfile,
        pet: Pet
    ) -> Dict[str, float]:
        """
        Calculate compatibility score between user and pet.

        Args:
            user: User profile
            pet: Pet profile

        Returns:
            Dictionary of compatibility scores
        """
        try:
            match = self.recommendation_agent.score_single_pet(user, pet)

            return {
                "overall_score": match.overall_score,
                "lifestyle_score": match.lifestyle_score,
                "personality_score": match.personality_score,
                "practical_score": match.practical_score,
                "urgency_boost": match.urgency_boost
            }

        except Exception as e:
            logger.error(f"Error calculating compatibility score: {e}")
            return {
                "overall_score": 0.5,
                "lifestyle_score": 0.5,
                "personality_score": 0.5,
                "practical_score": 0.5,
                "urgency_boost": 0.0
            }

    def generate_recommendations(
        self,
        user: UserProfile,
        pets: List[Pet],
        top_k: int = 10
    ) -> List[PetMatch]:
        """
        Generate personalized pet recommendations.

        Args:
            user: User profile
            pets: List of candidate pets
            top_k: Number of recommendations to return

        Returns:
            List of PetMatch objects with scores and explanations
        """
        try:
            return self.recommendation_agent.generate_recommendations(
                user=user,
                pets=pets,
                top_k=top_k
            )

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    async def analyze_pet_image(
        self,
        image_url: str,
        pet_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a pet image using computer vision.

        Args:
            image_url: URL of the pet image
            pet_type: Optional pet type hint

        Returns:
            Dictionary with vision analysis results
        """
        try:
            analysis = await self.vision_agent.analyze_pet_image(
                image_url=image_url,
                pet_type=pet_type
            )

            return analysis.dict()

        except Exception as e:
            logger.error(f"Error analyzing pet image: {e}")
            return {}

    async def schedule_visit(
        self,
        user_id: str,
        pet_id: str,
        preferred_time: datetime,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        duration_minutes: int = 45,
    ) -> Dict[str, Any]:
        """
        Schedule a shelter visit to meet a pet with MCP-powered email and calendar integration.

        Args:
            user_id: User identifier
            pet_id: Pet identifier
            preferred_time: Preferred visit time
            user_name: User's name (optional, will fetch from DB if not provided)
            user_email: User's email (optional, will fetch from DB if not provided)
            duration_minutes: Visit duration in minutes (default: 45)

        Returns:
            Dictionary with visit confirmation details including calendar event and email status
        """
        try:
            visit_id = f"visit_{user_id}_{pet_id}_{int(datetime.utcnow().timestamp())}"

            # Fetch pet details
            pet = await self.search_agent.get_pet_by_id(pet_id)
            if not pet:
                raise ValueError(f"Pet not found: {pet_id}")

            # If user info not provided, fetch from database (placeholder for now)
            # TODO: Integrate with Firestore to fetch user profile
            if not user_name:
                user_name = "Valued User"  # Placeholder
            if not user_email:
                user_email = "user@example.com"  # Placeholder

            # Extract shelter information
            shelter_name = pet.shelter.name if pet.shelter else "Local Shelter"
            shelter_address = (
                f"{pet.shelter.city}, {pet.shelter.state} {pet.shelter.zip_code}"
                if pet.shelter
                else "Contact shelter for address"
            )

            visit_info = {
                "visit_id": visit_id,
                "user_id": user_id,
                "user_name": user_name,
                "user_email": user_email,
                "pet_id": pet_id,
                "pet_name": pet.name,
                "scheduled_time": preferred_time.isoformat(),
                "duration_minutes": duration_minutes,
                "shelter_name": shelter_name,
                "shelter_address": shelter_address,
                "status": "scheduled",
                "created_at": datetime.utcnow().isoformat(),
                "calendar_event_id": None,
                "email_sent": False,
            }

            # Create calendar event if enabled
            if settings.mcp_calendar_enabled:
                try:
                    calendar_client = get_calendar_client()
                    calendar_result = await calendar_client.create_visit_event(
                        user_name=user_name,
                        user_email=user_email,
                        pet_name=pet.name,
                        pet_id=pet_id,
                        visit_datetime=preferred_time,
                        duration_minutes=duration_minutes,
                        shelter_name=shelter_name,
                        shelter_address=shelter_address,
                        visit_id=visit_id,
                    )
                    visit_info["calendar_event_id"] = calendar_result.get("event_id")
                    visit_info["calendar_link"] = calendar_result.get("html_link") or calendar_result.get("web_link")
                    logger.info(f"Calendar event created: {calendar_result.get('event_id')}")
                except Exception as e:
                    logger.warning(f"Failed to create calendar event: {e}")
                    visit_info["calendar_error"] = str(e)

            # Send confirmation email if enabled
            if settings.mcp_email_enabled and settings.email_notify_visit_scheduled:
                try:
                    email_client = get_email_client()
                    email_result = await email_client.send_visit_confirmation(
                        to_email=user_email,
                        user_name=user_name,
                        pet_name=pet.name,
                        pet_id=pet_id,
                        visit_datetime=preferred_time,
                        shelter_name=shelter_name,
                        shelter_address=shelter_address,
                        visit_id=visit_id,
                    )
                    visit_info["email_sent"] = email_result.get("status") == "success"
                    visit_info["email_message_id"] = email_result.get("message_id")
                    logger.info(f"Confirmation email sent: {email_result.get('message_id')}")
                except Exception as e:
                    logger.warning(f"Failed to send confirmation email: {e}")
                    visit_info["email_error"] = str(e)

            logger.info(f"Visit scheduled successfully: {visit_id}")
            return visit_info

        except Exception as e:
            logger.error(f"Error scheduling visit: {e}")
            raise

    def process_application(
        self,
        user_id: str,
        pet_id: str,
        application_data: Dict[str, Any],
        application_type: str = "adoption"
    ) -> Dict[str, Any]:
        """
        Process an adoption or foster application.

        Args:
            user_id: User identifier
            pet_id: Pet identifier
            application_data: Application form data
            application_type: Type of application (adoption or foster)

        Returns:
            Dictionary with application status and details
        """
        try:
            # Create application
            application = self.workflow_agent.create_application(
                user_id=user_id,
                pet_id=pet_id,
                application_type=application_type
            )

            # Submit with form data
            application = self.workflow_agent.submit_application(
                application_id=application["application_id"],
                form_data=application_data
            )

            logger.info(f"Application processed: {application['application_id']}")
            return application

        except Exception as e:
            logger.error(f"Error processing application: {e}")
            raise

    async def search_and_recommend(
        self,
        user: UserProfile,
        top_k: int = 10
    ) -> List[PetMatch]:
        """
        Complete flow: search for pets and generate recommendations.

        Args:
            user: User profile with preferences
            top_k: Number of recommendations

        Returns:
            List of recommended pets with match information
        """
        try:
            # Extract search parameters from user preferences
            pet_type = user.preferences.pet_type.value if user.preferences.pet_type else None

            # Prefer zip code for location filtering, fall back to city/state
            if user.zip_code and user.zip_code != "00000":
                location = user.zip_code
            else:
                location = f"{user.city}, {user.state}"

            # Search for pets
            pets = await self.fetch_shelter_data(
                pet_type=pet_type,
                location=location,
                distance=50,
                limit=100
            )

            if not pets:
                logger.warning("No pets found in search")
                return []

            # Generate recommendations
            recommendations = self.generate_recommendations(
                user=user,
                pets=pets,
                top_k=top_k
            )

            return recommendations

        except Exception as e:
            logger.error(f"Error in search and recommend flow: {e}")
            return []

    def get_application_status(self, application_id: str) -> Optional[str]:
        """
        Get the current status of an application.

        Args:
            application_id: Application identifier

        Returns:
            Application status string or None if not found
        """
        return self.workflow_agent.get_application_status(application_id)

    def get_user_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all applications for a user.

        Args:
            user_id: User identifier

        Returns:
            List of application dictionaries
        """
        return self.workflow_agent.get_user_applications(user_id)
