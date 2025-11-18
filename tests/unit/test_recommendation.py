"""
Unit tests for Recommendation Agent.
"""

import pytest
from unittest.mock import Mock, patch

from pawconnect_ai.sub_agents.recommendation_agent import RecommendationAgent
from pawconnect_ai.schemas.user_profile import UserProfile, UserPreferences, HomeType, ExperienceLevel
from pawconnect_ai.schemas.pet_data import Pet, PetType, PetSize, PetAge, Gender, PetAttributes, ShelterInfo, PetStatus


class TestRecommendationAgent:
    """Unit tests for RecommendationAgent class."""

    @pytest.fixture
    def recommendation_agent(self):
        """Create a RecommendationAgent instance for testing."""
        return RecommendationAgent()

    @pytest.fixture
    def sample_user_profile(self):
        """Create a sample user profile for testing."""
        return UserProfile(
            user_id="test_user_001",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            city="Seattle",
            state="WA",
            zip_code="98101",
            preferences=UserPreferences(
                pet_type=PetType.DOG,
                home_type=HomeType.APARTMENT,
                has_yard=False,
                has_children=False,
                has_other_pets=False,
                experience_level=ExperienceLevel.FIRST_TIME,
                activity_level="moderate",
                preferred_size=PetSize.SMALL,
                preferred_age=PetAge.ADULT,
                house_trained=True
            ),
            is_adopter=True
        )

    @pytest.fixture
    def sample_pets(self):
        """Create sample pets for testing."""
        return [
            Pet(
                pet_id="pet_001",
                name="Buddy",
                species=PetType.DOG,
                breed="Beagle",
                age=PetAge.ADULT,
                size=PetSize.SMALL,
                gender=Gender.MALE,
                attributes=PetAttributes(
                    good_with_children=True,
                    good_with_dogs=True,
                    good_with_cats=False,
                    house_trained=True,
                    energy_level="moderate"
                ),
                shelter=ShelterInfo(
                    organization_id="shelter_001",
                    name="Test Shelter",
                    city="Seattle",
                    state="WA",
                    zip_code="98101"
                ),
                status=PetStatus.AVAILABLE
            ),
            Pet(
                pet_id="pet_002",
                name="Max",
                species=PetType.DOG,
                breed="Golden Retriever",
                age=PetAge.YOUNG,
                size=PetSize.LARGE,
                gender=Gender.MALE,
                attributes=PetAttributes(
                    good_with_children=True,
                    good_with_dogs=True,
                    good_with_cats=True,
                    house_trained=False,
                    energy_level="high"
                ),
                shelter=ShelterInfo(
                    organization_id="shelter_001",
                    name="Test Shelter",
                    city="Seattle",
                    state="WA",
                    zip_code="98101"
                ),
                status=PetStatus.AVAILABLE
            )
        ]

    def test_calculate_compatibility_score(self, recommendation_agent, sample_user_profile, sample_pets):
        """Test compatibility score calculation."""
        pet = sample_pets[0]  # Buddy - small, adult, house-trained

        score = recommendation_agent.calculate_compatibility_score(
            user_profile=sample_user_profile,
            pet=pet
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a good match

    def test_rank_pets(self, recommendation_agent, sample_user_profile, sample_pets):
        """Test ranking pets by compatibility."""
        ranked_matches = recommendation_agent.rank_pets(
            user_profile=sample_user_profile,
            pets=sample_pets
        )

        assert len(ranked_matches) == len(sample_pets)
        # Check that matches are sorted by score
        for i in range(len(ranked_matches) - 1):
            assert ranked_matches[i].overall_score >= ranked_matches[i + 1].overall_score

    def test_filter_by_preferences(self, recommendation_agent, sample_user_profile, sample_pets):
        """Test filtering pets by user preferences."""
        # Should filter out large dogs for apartment dweller
        filtered_pets = recommendation_agent._filter_by_preferences(
            pets=sample_pets,
            preferences=sample_user_profile.preferences
        )

        # Buddy (small) should pass, Max (large) might not
        assert len(filtered_pets) > 0

    def test_lifestyle_compatibility(self, recommendation_agent, sample_user_profile):
        """Test lifestyle compatibility scoring."""
        pet = Pet(
            pet_id="pet_test",
            name="Test Pet",
            species=PetType.DOG,
            breed="Test Breed",
            age=PetAge.ADULT,
            size=PetSize.SMALL,
            gender=Gender.MALE,
            attributes=PetAttributes(
                house_trained=True,
                energy_level="moderate"
            ),
            shelter=ShelterInfo(
                organization_id="test",
                name="Test",
                city="Seattle",
                state="WA",
                zip_code="98101"
            ),
            status=PetStatus.AVAILABLE
        )

        score = recommendation_agent._calculate_lifestyle_score(
            user_profile=sample_user_profile,
            pet=pet
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_personality_compatibility(self, recommendation_agent, sample_user_profile):
        """Test personality compatibility scoring."""
        pet = Pet(
            pet_id="pet_test",
            name="Test Pet",
            species=PetType.DOG,
            breed="Test Breed",
            age=PetAge.ADULT,
            size=PetSize.SMALL,
            gender=Gender.MALE,
            attributes=PetAttributes(
                good_with_children=True,
                good_with_dogs=True,
                energy_level="moderate"
            ),
            shelter=ShelterInfo(
                organization_id="test",
                name="Test",
                city="Seattle",
                state="WA",
                zip_code="98101"
            ),
            status=PetStatus.AVAILABLE
        )

        score = recommendation_agent._calculate_personality_score(
            user_profile=sample_user_profile,
            pet=pet
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_urgency_boost(self, recommendation_agent):
        """Test urgency boost for at-risk pets."""
        urgent_pet = Pet(
            pet_id="urgent_pet",
            name="Urgent Pet",
            species=PetType.DOG,
            breed="Test",
            age=PetAge.SENIOR,
            size=PetSize.MEDIUM,
            gender=Gender.MALE,
            attributes=PetAttributes(),
            shelter=ShelterInfo(
                organization_id="test",
                name="Test",
                city="Seattle",
                state="WA",
                zip_code="98101"
            ),
            status=PetStatus.AVAILABLE,
            is_urgent=True,
            days_in_shelter=200
        )

        boost = recommendation_agent._calculate_urgency_boost(urgent_pet)

        assert isinstance(boost, float)
        assert boost > 0.0  # Should have positive boost

    def test_top_k_recommendations(self, recommendation_agent, sample_user_profile, sample_pets):
        """Test getting top-k recommendations."""
        # Add more pets to have enough for top-k
        all_pets = sample_pets * 5  # 10 pets

        ranked = recommendation_agent.rank_pets(
            user_profile=sample_user_profile,
            pets=all_pets
        )

        top_k = ranked[:3]
        assert len(top_k) == 3
        # Verify descending order
        assert top_k[0].overall_score >= top_k[1].overall_score >= top_k[2].overall_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
