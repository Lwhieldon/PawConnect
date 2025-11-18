"""
Unit tests for Pet Search Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from pawconnect_ai.sub_agents.pet_search_agent import PetSearchAgent
from pawconnect_ai.schemas.pet_data import Pet, PetType, PetSize, PetAge, Gender
from pawconnect_ai.config import settings


class TestPetSearchAgent:
    """Unit tests for PetSearchAgent class."""

    @pytest.fixture
    def search_agent(self):
        """Create a PetSearchAgent instance for testing."""
        settings.mock_apis = True
        settings.testing_mode = True
        return PetSearchAgent()

    @pytest.mark.asyncio
    async def test_search_pets_with_type(self, search_agent):
        """Test searching for pets with specific type."""
        pets = await search_agent.search_pets(
            pet_type="dog",
            location="Seattle, WA",
            limit=10
        )

        assert isinstance(pets, list)
        assert len(pets) > 0
        for pet in pets:
            assert isinstance(pet, Pet)
            assert pet.species == PetType.DOG

    @pytest.mark.asyncio
    async def test_search_pets_with_filters(self, search_agent):
        """Test searching with multiple filters."""
        pets = await search_agent.search_pets(
            pet_type="cat",
            location="98101",
            distance=25,
            limit=5
        )

        assert isinstance(pets, list)
        assert len(pets) <= 5

    @pytest.mark.asyncio
    async def test_search_pets_caching(self, search_agent):
        """Test that search results are cached."""
        # First call - should hit API
        pets1 = await search_agent.search_pets(
            pet_type="dog",
            location="Seattle, WA"
        )

        # Second call - should use cache
        pets2 = await search_agent.search_pets(
            pet_type="dog",
            location="Seattle, WA"
        )

        assert len(pets1) == len(pets2)
        assert pets1[0].pet_id == pets2[0].pet_id

    @pytest.mark.asyncio
    async def test_search_pets_empty_result(self, search_agent):
        """Test search with no results."""
        # Mock the _search_rescuegroups method to return empty list
        search_agent._search_rescuegroups = AsyncMock(return_value=[])

        pets = await search_agent.search_pets(
            pet_type="unicorn",
            location="Antarctica"
        )

        assert isinstance(pets, list)
        assert len(pets) == 0

    @pytest.mark.asyncio
    async def test_get_pet_by_id_found(self, search_agent):
        """Test retrieving a specific pet by ID."""
        # Get a pet from search
        pets = await search_agent.search_pets(limit=1)
        assert len(pets) > 0

        pet_id = pets[0].pet_id

        # Retrieve by ID
        pet = await search_agent.get_pet_by_id(pet_id)

        assert pet is not None
        assert pet.pet_id == pet_id

    @pytest.mark.asyncio
    async def test_get_pet_by_id_not_found(self, search_agent):
        """Test retrieving non-existent pet."""
        pet = await search_agent.get_pet_by_id("invalid_id_12345")
        assert pet is None

    def test_clear_cache(self, search_agent):
        """Test clearing the search cache."""
        # Add something to cache
        search_agent.cache["test_key"] = "test_value"
        assert len(search_agent.cache) > 0

        # Clear cache
        search_agent.clear_cache()
        assert len(search_agent.cache) == 0

    @pytest.mark.asyncio
    async def test_search_pets_with_invalid_params(self, search_agent):
        """Test search with invalid parameters."""
        pets = await search_agent.search_pets(
            pet_type="dog",
            location="",  # Empty location
            limit=-1  # Invalid limit
        )

        # Should return empty list for invalid params
        assert isinstance(pets, list)

    def test_get_mock_pets(self, search_agent):
        """Test mock pet generation."""
        mock_pets = search_agent._get_mock_pets(pet_type="dog", limit=5)

        assert isinstance(mock_pets, list)
        assert len(mock_pets) <= 5
        for pet in mock_pets:
            assert isinstance(pet, Pet)
            assert pet.species == PetType.DOG

    def test_get_mock_pets_filtered_by_type(self, search_agent):
        """Test mock pets filtered by type."""
        dog_pets = search_agent._get_mock_pets(pet_type="dog", limit=10)
        cat_pets = search_agent._get_mock_pets(pet_type="cat", limit=10)

        # Verify all returned pets match the requested type
        for pet in dog_pets:
            assert pet.species == PetType.DOG

        for pet in cat_pets:
            assert pet.species == PetType.CAT

    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_agent):
        """Test error handling in search."""
        # Mock to raise exception
        with patch.object(
            search_agent,
            '_search_rescuegroups',
            side_effect=Exception("API Error")
        ):
            pets = await search_agent.search_pets(
                pet_type="dog",
                location="Seattle, WA"
            )

            # Should return empty list on error
            assert isinstance(pets, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
