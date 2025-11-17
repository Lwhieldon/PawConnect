"""
Integration tests for API clients and external service integrations.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from pawconnect_ai.utils.api_clients import PetfinderClient, GoogleCloudClient
from pawconnect_ai.sub_agents.pet_search_agent import PetSearchAgent
from pawconnect_ai.sub_agents.vision_agent import VisionAgent
from pawconnect_ai.config import settings


class TestPetfinderIntegration:
    """Integration tests for Petfinder API client."""

    @pytest.fixture
    def petfinder_client(self):
        """Create a Petfinder client for testing."""
        # Use mock APIs in testing
        settings.mock_apis = True
        return PetfinderClient()

    @pytest.mark.asyncio
    async def test_search_pets_integration(self, petfinder_client):
        """Test searching for pets through Petfinder API."""
        # This test uses mock data since we can't hit real API in CI
        search_agent = PetSearchAgent()

        pets = await search_agent.search_pets(
            pet_type="dog",
            location="Seattle, WA",
            distance=50,
            limit=10
        )

        assert isinstance(pets, list)
        assert len(pets) > 0

        # Verify pet structure
        pet = pets[0]
        assert hasattr(pet, "pet_id")
        assert hasattr(pet, "name")
        assert hasattr(pet, "species")
        assert hasattr(pet, "shelter")

    @pytest.mark.asyncio
    async def test_search_with_filters(self, petfinder_client):
        """Test pet search with various filters."""
        search_agent = PetSearchAgent()

        # Search for cats
        cats = await search_agent.search_pets(
            pet_type="cat",
            location="98101",
            distance=25,
            limit=5
        )

        assert isinstance(cats, list)
        if cats:  # May be empty in test mode
            assert all(pet.species.value == "cat" for pet in cats)

    @pytest.mark.asyncio
    async def test_get_pet_by_id(self, petfinder_client):
        """Test retrieving a specific pet by ID."""
        search_agent = PetSearchAgent()

        # First get some pets
        pets = await search_agent.search_pets(
            pet_type="dog",
            location="Seattle, WA",
            limit=1
        )

        if pets:
            pet_id = pets[0].pet_id
            pet = await search_agent.get_pet_by_id(pet_id)

            assert pet is not None
            assert pet.pet_id == pet_id


class TestVisionIntegration:
    """Integration tests for Vision API."""

    @pytest.fixture
    def vision_agent(self):
        """Create a Vision agent for testing."""
        settings.mock_apis = True
        return VisionAgent()

    @pytest.mark.asyncio
    async def test_analyze_pet_image(self, vision_agent):
        """Test analyzing a pet image."""
        # Use a mock image URL
        image_url = "https://example.com/pet.jpg"

        analysis = await vision_agent.analyze_pet_image(
            image_url=image_url,
            pet_type="dog"
        )

        assert analysis is not None
        assert hasattr(analysis, "primary_breed")
        assert hasattr(analysis, "breed_confidence")
        assert hasattr(analysis, "estimated_age")

    @pytest.mark.asyncio
    async def test_batch_image_analysis(self, vision_agent):
        """Test analyzing multiple images in batch."""
        image_urls = [
            "https://example.com/pet1.jpg",
            "https://example.com/pet2.jpg",
            "https://example.com/pet3.jpg"
        ]

        analyses = await vision_agent.analyze_multiple_images(
            image_urls=image_urls,
            pet_type="dog"
        )

        assert len(analyses) == len(image_urls)
        for analysis in analyses:
            assert hasattr(analysis, "model_version")


class TestWorkflowIntegration:
    """Integration tests for workflow processes."""

    @pytest.mark.asyncio
    async def test_complete_application_workflow(self):
        """Test complete application submission workflow."""
        from pawconnect_ai.sub_agents.workflow_agent import WorkflowAgent

        agent = WorkflowAgent()

        # Create application
        app = agent.create_application(
            user_id="test_user_001",
            pet_id="test_pet_001",
            application_type="adoption"
        )

        assert app["status"] == "draft"
        assert app["user_id"] == "test_user_001"

        # Submit application
        form_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "206-555-0123",
            "address": "123 Main St",
            "city": "Seattle",
            "state": "WA",
            "zip_code": "98101",
            "home_type": "house",
            "home_owned_rented": "owned",
            "adoption_reason": "Looking for a companion"
        }

        app = agent.submit_application(app["application_id"], form_data)

        assert app["status"] in ["submitted", "under_review", "background_check"]
        assert app["form_data"] == form_data

    @pytest.mark.asyncio
    async def test_visit_scheduling(self):
        """Test visit scheduling workflow."""
        from pawconnect_ai.tools import PawConnectTools
        from datetime import datetime, timedelta

        tools = PawConnectTools()

        visit_time = datetime.utcnow() + timedelta(days=1)

        visit = tools.schedule_visit(
            user_id="test_user_001",
            pet_id="test_pet_001",
            preferred_time=visit_time
        )

        assert visit is not None
        assert visit["status"] == "scheduled"
        assert "visit_id" in visit


@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests across multiple components."""

    @pytest.mark.asyncio
    async def test_search_and_recommend_flow(self):
        """Test complete flow from search to recommendations."""
        from pawconnect_ai.agent import PawConnectMainAgent
        from pawconnect_ai.schemas.user_profile import UserProfile, UserPreferences, PetType, HomeType, ExperienceLevel

        # Enable mock mode
        settings.mock_apis = True
        settings.testing_mode = True

        agent = PawConnectMainAgent()

        # Create user profile
        user_data = {
            "user_id": "test_user_001",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "city": "Seattle",
            "state": "WA",
            "zip_code": "98101",
            "preferences": {
                "pet_type": "dog",
                "home_type": "house",
                "has_yard": True,
                "experience_level": "some_experience",
                "activity_level": "moderate"
            },
            "is_adopter": True
        }

        user_profile = await agent.create_user_profile(user_data)
        assert user_profile.user_id == "test_user_001"

        # Find matches
        matches = await agent.find_matches(user_profile, top_k=5)

        assert isinstance(matches, list)
        if matches:
            assert len(matches) <= 5
            # Verify match structure
            match = matches[0]
            assert hasattr(match, "pet")
            assert hasattr(match, "overall_score")
            assert hasattr(match, "match_explanation")
            assert 0 <= match.overall_score <= 1

    @pytest.mark.asyncio
    async def test_conversational_flow(self):
        """Test conversational interaction flow."""
        from pawconnect_ai.agent import PawConnectMainAgent

        settings.mock_apis = True
        settings.testing_mode = True

        agent = PawConnectMainAgent()

        # Simulate conversation
        response1 = await agent.process_user_request(
            user_id="test_user_002",
            message="I'm looking for a dog to adopt"
        )

        assert "response" in response1
        assert response1["intent"] == "search_pets"

        response2 = await agent.process_user_request(
            user_id="test_user_002",
            message="Seattle, WA"
        )

        assert "response" in response2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
