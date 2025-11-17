"""
Pet Search Agent - Data Retrieval Specialist
Queries multiple data sources to fetch available pets.
"""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from ..config import settings
from ..schemas.pet_data import Pet
from ..utils.api_clients import petfinder_client
from ..utils.helpers import parse_petfinder_response
from ..utils.validators import validate_search_params


class PetSearchAgent:
    """
    Specialized agent for searching and retrieving pet data from multiple sources.
    """

    def __init__(self):
        """Initialize the pet search agent."""
        self.petfinder = petfinder_client
        self.cache = {}  # Simple in-memory cache

    async def search_pets(
        self,
        pet_type: Optional[str] = None,
        location: Optional[str] = None,
        distance: int = 50,
        limit: int = 100,
        **kwargs
    ) -> List[Pet]:
        """
        Search for pets across multiple data sources.

        Args:
            pet_type: Type of pet (dog, cat, etc.)
            location: ZIP code or city, state
            distance: Search radius in miles
            limit: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of Pet objects
        """
        # Validate parameters
        is_valid, error_msg = validate_search_params(pet_type, location, distance, limit)
        if not is_valid:
            logger.warning(f"Invalid search parameters: {error_msg}")
            return []

        # Check cache
        cache_key = f"{pet_type}:{location}:{distance}:{limit}"
        if cache_key in self.cache:
            logger.info("Returning cached search results")
            return self.cache[cache_key]

        try:
            logger.info(
                f"Searching for pets: type={pet_type}, location={location}, "
                f"distance={distance}, limit={limit}"
            )

            # Search Petfinder API
            pets = await self._search_petfinder(
                pet_type=pet_type,
                location=location,
                distance=distance,
                limit=limit,
                **kwargs
            )

            # Cache results
            self.cache[cache_key] = pets

            logger.info(f"Found {len(pets)} pets")
            return pets

        except Exception as e:
            logger.error(f"Error searching for pets: {e}")
            return []

    async def _search_petfinder(
        self,
        pet_type: Optional[str] = None,
        location: Optional[str] = None,
        distance: int = 50,
        limit: int = 100,
        **kwargs
    ) -> List[Pet]:
        """Search Petfinder API for pets."""
        try:
            # Make API request
            response = await self.petfinder.search_pets(
                pet_type=pet_type,
                location=location,
                distance=distance,
                limit=limit,
                **kwargs
            )

            # Parse response into Pet objects
            pet_data_list = parse_petfinder_response(response)

            pets = []
            for pet_data in pet_data_list:
                try:
                    pet = Pet(**pet_data)
                    pets.append(pet)
                except Exception as e:
                    logger.warning(f"Failed to create Pet object: {e}")
                    continue

            return pets

        except Exception as e:
            logger.error(f"Petfinder API error: {e}")
            # Return mock data in case of error if in testing mode
            if settings.testing_mode or settings.mock_apis:
                return self._get_mock_pets(pet_type, limit)
            return []

    def _get_mock_pets(self, pet_type: Optional[str], limit: int) -> List[Pet]:
        """Get mock pet data for testing."""
        from ..schemas.pet_data import (
            Pet, PetType, PetSize, PetAge, Gender,
            PetAttributes, ShelterInfo, PetStatus
        )

        mock_pets = [
            Pet(
                pet_id="mock_001",
                name="Max",
                species=PetType.DOG,
                breed="Labrador Retriever",
                age=PetAge.ADULT,
                size=PetSize.LARGE,
                gender=Gender.MALE,
                description="Max is a friendly and energetic dog who loves to play fetch.",
                attributes=PetAttributes(
                    good_with_children=True,
                    good_with_dogs=True,
                    good_with_cats=False,
                    house_trained=True,
                    spayed_neutered=True,
                    energy_level="high"
                ),
                shelter=ShelterInfo(
                    organization_id="shelter_001",
                    name="Seattle Animal Shelter",
                    city="Seattle",
                    state="WA",
                    zip_code="98101",
                    latitude=47.6062,
                    longitude=-122.3321
                ),
                status=PetStatus.AVAILABLE,
                days_in_shelter=45
            ),
            Pet(
                pet_id="mock_002",
                name="Luna",
                species=PetType.CAT,
                breed="Domestic Shorthair",
                age=PetAge.YOUNG,
                size=PetSize.SMALL,
                gender=Gender.FEMALE,
                description="Luna is a sweet and affectionate cat who enjoys cuddles.",
                attributes=PetAttributes(
                    good_with_children=True,
                    good_with_dogs=False,
                    good_with_cats=True,
                    house_trained=True,
                    spayed_neutered=True,
                    energy_level="moderate"
                ),
                shelter=ShelterInfo(
                    organization_id="shelter_002",
                    name="PAWS Seattle",
                    city="Lynnwood",
                    state="WA",
                    zip_code="98036",
                    latitude=47.8209,
                    longitude=-122.3151
                ),
                status=PetStatus.AVAILABLE,
                days_in_shelter=12
            ),
            Pet(
                pet_id="mock_003",
                name="Charlie",
                species=PetType.DOG,
                breed="Golden Retriever",
                age=PetAge.SENIOR,
                size=PetSize.LARGE,
                gender=Gender.MALE,
                description="Charlie is a gentle senior dog looking for a quiet home.",
                attributes=PetAttributes(
                    good_with_children=True,
                    good_with_dogs=True,
                    good_with_cats=True,
                    house_trained=True,
                    spayed_neutered=True,
                    special_needs=False,
                    energy_level="low"
                ),
                shelter=ShelterInfo(
                    organization_id="shelter_001",
                    name="Seattle Animal Shelter",
                    city="Seattle",
                    state="WA",
                    zip_code="98101",
                    latitude=47.6062,
                    longitude=-122.3321
                ),
                status=PetStatus.AVAILABLE,
                days_in_shelter=120,
                is_urgent=True,
                urgency_reason="Senior dog needs home soon"
            ),
        ]

        # Filter by type if specified
        if pet_type:
            mock_pets = [p for p in mock_pets if p.species.value == pet_type.lower()]

        return mock_pets[:limit]

    async def get_pet_by_id(self, pet_id: str) -> Optional[Pet]:
        """
        Retrieve a specific pet by ID.

        Args:
            pet_id: Pet identifier

        Returns:
            Pet object or None if not found
        """
        try:
            # In mock mode, return from mock pets
            if settings.testing_mode or settings.mock_apis:
                mock_pets = self._get_mock_pets(None, 10)
                for pet in mock_pets:
                    if pet.pet_id == pet_id:
                        return pet
                return None

            # Extract external ID if it's a prefixed ID
            external_id = pet_id.replace("pf_", "")

            response = await self.petfinder.get_pet(external_id)

            # Parse response
            pet_data_list = parse_petfinder_response({"animals": [response.get("animal", {})]})

            if pet_data_list:
                return Pet(**pet_data_list[0])

            return None

        except Exception as e:
            logger.error(f"Error retrieving pet {pet_id}: {e}")
            return None

    def clear_cache(self):
        """Clear the search cache."""
        self.cache.clear()
        logger.info("Search cache cleared")
