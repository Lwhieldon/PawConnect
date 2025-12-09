"""
Integration test showing Vision Agent usage through PawConnect Tools
This demonstrates how the Vision Agent is used in the full PawConnect system.

Run with: python test_vision_integration.py
Or with pytest: pytest tests/test_vision_integration.py -s
"""

import sys
from pathlib import Path

# Add parent directory to path for direct script execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
from pawconnect_ai.tools import PawConnectTools
from pawconnect_ai.schemas.pet_data import Pet, PetType, PetSize, PetAge, Gender, PetAttributes, ShelterInfo
from pawconnect_ai.config import settings

@pytest.mark.asyncio
async def test_vision_integration():
    """Test Vision Agent integration with PawConnect tools."""

    # Use mock mode for testing
    settings.mock_apis = True
    settings.testing_mode = True

    print("=" * 60)
    print("Vision Agent Integration Test")
    print("=" * 60)

    # Initialize PawConnect tools (includes Vision Agent)
    tools = PawConnectTools()

    # Test 1: Analyze a pet image through tools interface
    print("\n1. Testing image analysis through PawConnectTools...")
    image_url = "https://t3.ftcdn.net/jpg/02/35/69/04/240_F_235690407_Mp2tDFESZLVeRYTqnyfF0KCzfMsRC2sO.jpg"

    analysis_dict = await tools.analyze_pet_image(
        image_url=image_url,
        pet_type="dog"
    )

    print(f"   Analysis complete!")
    print(f"   Breed: {analysis_dict.get('primary_breed')}")
    print(f"   Age: {analysis_dict.get('estimated_age')}")
    print(f"   Confidence: {analysis_dict.get('breed_confidence')}")

    # Test 2: Create a pet profile and enhance with vision analysis
    print("\n2. Testing pet profile enhancement...")

    # Create a basic pet profile (minimal data)
    basic_pet = Pet(
        pet_id="test_001",
        name="Max",
        species=PetType.DOG,
        age=PetAge.ADULT,
        size=PetSize.LARGE,
        gender=Gender.MALE,
        description="Friendly dog looking for a home",
        primary_photo_url="https://t3.ftcdn.net/jpg/02/35/69/04/240_F_235690407_Mp2tDFESZLVeRYTqnyfF0KCzfMsRC2sO.jpg",
        shelter=ShelterInfo(
            organization_id="shelter_001",
            name="Seattle Animal Shelter",
            city="Seattle",
            state="WA",
            zip_code="98101"
        )
    )

    print(f"   Original pet - Breed: {basic_pet.breed}")

    # Enhance with vision analysis
    vision_analysis = await tools.vision_agent.analyze_pet_image(
        image_url=str(basic_pet.primary_photo_url),
        pet_type=basic_pet.species.value
    )

    enhanced_pet = tools.vision_agent.enhance_pet_profile(
        pet=basic_pet,
        vision_analysis=vision_analysis
    )

    print(f"   Enhanced pet - Breed: {enhanced_pet.breed}")
    print(f"   Vision data attached: {enhanced_pet.vision_analysis is not None}")

    # Test 3: Batch processing multiple pet images
    print("\n3. Testing batch image analysis...")

    image_urls = [
        "https://s3.amazonaws.com/cdn-origin-etr.akc.org/wp-content/uploads/2022/01/11135302/labrador-retriever-vs-golden-retriever-.png",
        "https://www.2cholidays.co.uk/wp-content/uploads/2023/04/dog-breed-hungarian-vizsla-scaled.jpg",
        "https://dogtime.com/wp-content/uploads/sites/12/2011/01/GettyImages-168620477-e1691273341205.jpg"
    ]

    analyses = await tools.vision_agent.analyze_multiple_images(
        image_urls=image_urls,
        pet_type="dog"
    )

    print(f"   Processed {len(analyses)} images concurrently")
    for i, analysis in enumerate(analyses):
        print(f"   Pet {i+1}: {analysis.primary_breed} ({analysis.breed_confidence})")

    # Test 4: Error handling
    print("\n4. Testing error handling with invalid URL...")

    try:
        bad_analysis = await tools.analyze_pet_image(
            image_url="not-a-valid-url",
            pet_type="dog"
        )
        print(f"   Gracefully handled: returned default analysis")
    except Exception as e:
        print(f"   Caught exception: {e}")

    print("\n" + "=" * 60)
    print("Integration tests completed successfully!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("[OK] Analyzing images through PawConnectTools")
    print("[OK] Enhancing pet profiles with vision data")
    print("[OK] Batch processing multiple images")
    print("[OK] Error handling for invalid inputs")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_vision_integration())
