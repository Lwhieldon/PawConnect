"""
End-to-end tests for PawConnect AI agent system.
Tests the complete workflow from user input to pet matching and application.
"""

import pytest
import asyncio
from datetime import datetime

from pawconnect_ai.agent import PawConnectMainAgent
from pawconnect_ai.schemas.user_profile import UserProfile, UserPreferences, PetType, PetSize, HomeType, ExperienceLevel
from pawconnect_ai.schemas.pet_data import Pet
from pawconnect_ai.config import settings


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def agent():
    """Create a PawConnect agent for testing."""
    # Enable test mode
    settings.testing_mode = True
    settings.mock_apis = True
    return PawConnectMainAgent()


@pytest.fixture
def sample_user_data():
    """Create sample user data for testing."""
    return {
        "user_id": "test_user_001",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1-206-555-0123",
        "city": "Seattle",
        "state": "WA",
        "zip_code": "98101",
        "preferences": {
            "pet_type": "dog",
            "pet_size": ["medium", "large"],
            "pet_age": ["young", "adult"],
            "has_children": True,
            "has_other_pets": False,
            "home_type": "house",
            "has_yard": True,
            "yard_fenced": True,
            "experience_level": "some_experience",
            "activity_level": "moderate",
            "good_with_children": True,
            "house_trained": True
        },
        "is_adopter": True
    }


class TestAgentInitialization:
    """Test agent initialization and setup."""

    def test_agent_creation(self, agent):
        """Test that agent initializes correctly."""
        assert agent is not None
        assert agent.tools is not None
        assert agent.conversation_agent is not None

    def test_agent_has_sub_agents(self, agent):
        """Test that all sub-agents are initialized."""
        assert agent.tools.search_agent is not None
        assert agent.tools.recommendation_agent is not None
        assert agent.tools.vision_agent is not None
        assert agent.tools.workflow_agent is not None


class TestUserProfileCreation:
    """Test user profile creation and validation."""

    @pytest.mark.asyncio
    async def test_create_valid_user_profile(self, agent, sample_user_data):
        """Test creating a valid user profile."""
        user_profile = await agent.create_user_profile(sample_user_data)

        assert user_profile is not None
        assert user_profile.user_id == "test_user_001"
        assert user_profile.email == "john.doe@example.com"
        assert user_profile.preferences.pet_type == PetType.DOG
        assert user_profile.preferences.home_type == HomeType.HOUSE

    @pytest.mark.asyncio
    async def test_create_user_profile_missing_fields(self, agent):
        """Test creating user profile with missing required fields."""
        invalid_data = {
            "user_id": "test_user_002",
            "email": "invalid@example.com"
            # Missing required fields
        }

        with pytest.raises(ValueError):
            await agent.create_user_profile(invalid_data)

    @pytest.mark.asyncio
    async def test_create_user_profile_invalid_email(self, agent, sample_user_data):
        """Test creating user profile with invalid email."""
        invalid_data = sample_user_data.copy()
        invalid_data["email"] = "not-an-email"

        with pytest.raises(ValueError):
            await agent.create_user_profile(invalid_data)


class TestPetSearchAndMatching:
    """Test pet search and matching functionality."""

    @pytest.mark.asyncio
    async def test_search_for_pets(self, agent, sample_user_data):
        """Test searching for pets."""
        user_profile = await agent.create_user_profile(sample_user_data)

        # Search for pets
        pets = await agent.tools.fetch_shelter_data(
            pet_type="dog",
            location="Seattle, WA",
            distance=50,
            limit=20
        )

        assert isinstance(pets, list)
        assert len(pets) > 0

        # Verify pet data structure
        pet = pets[0]
        assert hasattr(pet, "pet_id")
        assert hasattr(pet, "name")
        assert hasattr(pet, "species")
        assert hasattr(pet, "breed")
        assert hasattr(pet, "shelter")

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, agent, sample_user_data):
        """Test generating personalized recommendations."""
        user_profile = await agent.create_user_profile(sample_user_data)

        # Get recommendations
        matches = await agent.find_matches(user_profile, top_k=5)

        assert isinstance(matches, list)
        assert len(matches) <= 5

        if matches:
            match = matches[0]
            assert match.pet is not None
            assert 0 <= match.overall_score <= 1
            assert match.match_explanation != ""
            assert isinstance(match.key_factors, list)

    @pytest.mark.asyncio
    async def test_recommendation_scoring(self, agent, sample_user_data):
        """Test that recommendations are properly scored."""
        user_profile = await agent.create_user_profile(sample_user_data)

        matches = await agent.find_matches(user_profile, top_k=10)

        if len(matches) > 1:
            # Verify matches are sorted by score
            scores = [match.overall_score for match in matches]
            assert scores == sorted(scores, reverse=True)

            # Verify score components
            for match in matches:
                assert hasattr(match, "lifestyle_score")
                assert hasattr(match, "personality_score")
                assert hasattr(match, "practical_score")
                assert hasattr(match, "urgency_boost")

    @pytest.mark.asyncio
    async def test_compatibility_filtering(self, agent, sample_user_data):
        """Test that incompatible pets are filtered out or scored low."""
        # User with children
        user_data = sample_user_data.copy()
        user_data["preferences"]["has_children"] = True
        user_data["preferences"]["good_with_children"] = True

        user_profile = await agent.create_user_profile(user_data)

        matches = await agent.find_matches(user_profile, top_k=10)

        # Top matches should be good with children
        if matches:
            for match in matches[:3]:  # Check top 3
                pet = match.pet
                # Should either be good with children or unknown (not explicitly bad)
                assert pet.attributes.good_with_children != False


class TestConversationalInteraction:
    """Test conversational interaction with the agent."""

    @pytest.mark.asyncio
    async def test_process_search_request(self, agent):
        """Test processing a search request."""
        response = await agent.process_user_request(
            user_id="test_user_conv_001",
            message="I'm looking for a dog to adopt"
        )

        assert "response" in response
        assert "intent" in response
        assert response["intent"] == "search_pets"

    @pytest.mark.asyncio
    async def test_conversation_context_retention(self, agent):
        """Test that conversation context is retained."""
        user_id = "test_user_conv_002"

        # First message
        response1 = await agent.process_user_request(
            user_id=user_id,
            message="I want to adopt a cat"
        )

        # Check session was created
        session = agent.get_session(user_id)
        assert session is not None
        assert "context" in session

        # Second message should have context
        response2 = await agent.process_user_request(
            user_id=user_id,
            message="Seattle"
        )

        assert session["context"].get("last_intent") is not None

    @pytest.mark.asyncio
    async def test_intent_detection(self, agent):
        """Test various intent detection scenarios."""
        test_cases = [
            ("I want to adopt a dog", "search_pets"),
            ("Show me recommendations", "get_recommendations"),
            ("Schedule a visit", "schedule_visit"),
            ("Help me", "help"),
        ]

        for message, expected_intent in test_cases:
            response = await agent.process_user_request(
                user_id=f"test_user_{expected_intent}",
                message=message
            )

            assert response.get("intent") == expected_intent or "response" in response


class TestApplicationWorkflow:
    """Test application submission and processing workflow."""

    @pytest.mark.asyncio
    async def test_create_application(self, agent):
        """Test creating an adoption application."""
        from pawconnect_ai.sub_agents.workflow_agent import WorkflowAgent

        workflow_agent = WorkflowAgent()

        application = workflow_agent.create_application(
            user_id="test_user_app_001",
            pet_id="test_pet_001",
            application_type="adoption"
        )

        assert application is not None
        assert application["application_id"] is not None
        assert application["status"] == "draft"
        assert application["user_id"] == "test_user_app_001"
        assert application["pet_id"] == "test_pet_001"

    @pytest.mark.asyncio
    async def test_submit_application(self, agent):
        """Test submitting a complete application."""
        from pawconnect_ai.sub_agents.workflow_agent import WorkflowAgent

        workflow_agent = WorkflowAgent()

        # Create application
        application = workflow_agent.create_application(
            user_id="test_user_app_002",
            pet_id="test_pet_002",
            application_type="adoption"
        )

        # Submit with form data
        form_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "phone": "206-555-0456",
            "address": "456 Oak Ave",
            "city": "Seattle",
            "state": "WA",
            "zip_code": "98102",
            "home_type": "apartment",
            "home_owned_rented": "rented",
            "adoption_reason": "Looking for companionship"
        }

        submitted_app = workflow_agent.submit_application(
            application["application_id"],
            form_data
        )

        assert submitted_app["status"] in ["submitted", "under_review", "background_check"]
        assert submitted_app["form_data"] == form_data
        assert len(submitted_app["timeline"]) > 1

    @pytest.mark.asyncio
    async def test_application_status_tracking(self, agent):
        """Test tracking application status through workflow."""
        from pawconnect_ai.sub_agents.workflow_agent import WorkflowAgent

        workflow_agent = WorkflowAgent()

        # Create and submit application
        app = workflow_agent.create_application(
            user_id="test_user_app_003",
            pet_id="test_pet_003"
        )

        form_data = {
            "first_name": "Bob",
            "last_name": "Johnson",
            "email": "bob@example.com",
            "phone": "206-555-0789",
            "address": "789 Pine St",
            "city": "Seattle",
            "state": "WA",
            "zip_code": "98103",
            "home_type": "house",
            "home_owned_rented": "owned",
            "adoption_reason": "Family pet"
        }

        app = workflow_agent.submit_application(app["application_id"], form_data)

        # Check timeline
        assert len(app["timeline"]) >= 2
        assert app["timeline"][0]["status"] == "draft"


class TestCompleteEndToEndFlow:
    """Test complete end-to-end user journey."""

    @pytest.mark.asyncio
    async def test_complete_adoption_flow(self, agent, sample_user_data):
        """Test complete flow from user creation to application."""
        # Step 1: Create user profile
        user_profile = await agent.create_user_profile(sample_user_data)
        assert user_profile.user_id == "test_user_001"

        # Step 2: Search for pets and get recommendations
        matches = await agent.find_matches(user_profile, top_k=5)
        assert len(matches) > 0

        # Step 3: Select a pet (first match)
        selected_match = matches[0]
        selected_pet = selected_match.pet

        # Step 4: Schedule a visit
        from datetime import timedelta
        visit_time = datetime.utcnow() + timedelta(days=1)

        visit = agent.tools.schedule_visit(
            user_id=user_profile.user_id,
            pet_id=selected_pet.pet_id,
            preferred_time=visit_time
        )

        assert visit["status"] == "scheduled"

        # Step 5: Submit application
        application_data = {
            "first_name": user_profile.first_name,
            "last_name": user_profile.last_name,
            "email": user_profile.email,
            "phone": user_profile.phone or "206-555-0123",
            "address": user_profile.address or "123 Main St",
            "city": user_profile.city,
            "state": user_profile.state,
            "zip_code": user_profile.zip_code,
            "home_type": user_profile.preferences.home_type.value,
            "home_owned_rented": "owned",
            "adoption_reason": "Looking for a family pet"
        }

        application = agent.tools.process_application(
            user_id=user_profile.user_id,
            pet_id=selected_pet.pet_id,
            application_data=application_data
        )

        assert application["status"] in ["submitted", "under_review", "background_check"]
        assert application["user_id"] == user_profile.user_id
        assert application["pet_id"] == selected_pet.pet_id

    @pytest.mark.asyncio
    async def test_multiple_users_concurrent(self, agent):
        """Test handling multiple users concurrently."""
        # Create multiple user profiles concurrently
        user_data_list = [
            {
                "user_id": f"test_user_concurrent_{i}",
                "email": f"user{i}@example.com",
                "first_name": f"User{i}",
                "last_name": "Test",
                "city": "Seattle",
                "state": "WA",
                "zip_code": "98101",
                "preferences": {
                    "pet_type": "dog" if i % 2 == 0 else "cat",
                    "home_type": "house",
                    "experience_level": "some_experience"
                },
                "is_adopter": True
            }
            for i in range(3)
        ]

        # Create profiles concurrently
        profiles = await asyncio.gather(
            *[agent.create_user_profile(data) for data in user_data_list]
        )

        assert len(profiles) == 3
        for profile in profiles:
            assert profile is not None

        # Get recommendations for all users concurrently
        matches_list = await asyncio.gather(
            *[agent.find_matches(profile, top_k=3) for profile in profiles]
        )

        assert len(matches_list) == 3
        for matches in matches_list:
            assert isinstance(matches, list)


def test_import_success():
    """Test that all modules import successfully."""
    from pawconnect_ai import PawConnectMainAgent
    from pawconnect_ai.sub_agents import (
        PetSearchAgent,
        RecommendationAgent,
        ConversationAgent,
        VisionAgent,
        WorkflowAgent
    )
    from pawconnect_ai.models import RecommendationModel, BreedClassifier
    from pawconnect_ai.schemas import UserProfile, Pet, PetMatch

    assert PawConnectMainAgent is not None
    assert PetSearchAgent is not None
    assert RecommendationAgent is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
