"""
Manual test script for Vision Agent
Run with: python test_vision_manual.py
Or with pytest: pytest tests/test_vision_manual.py
"""

import sys
from pathlib import Path

# Add parent directory to path for direct script execution
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
from pawconnect_ai.sub_agents.vision_agent import VisionAgent
from pawconnect_ai.config import settings

@pytest.mark.asyncio
async def test_vision_agent():
    """Test the Vision Agent with mock data."""

    # Enable mock mode (no API calls needed)
    settings.mock_apis = True
    settings.testing_mode = True

    # Initialize the agent
    vision_agent = VisionAgent()

    print("=" * 60)
    print("Testing Vision Agent")
    print("=" * 60)

    # Test 1: Analyze a dog image
    print("\n1. Analyzing dog image...")
    dog_analysis = await vision_agent.analyze_pet_image(
        image_url="https://example.com/dog.jpg",
        pet_type="dog"
    )
    print(f"   Primary Breed: {dog_analysis.primary_breed}")
    print(f"   Confidence: {dog_analysis.breed_confidence}")
    print(f"   Age: {dog_analysis.estimated_age}")
    print(f"   Colors: {dog_analysis.coat_color}")
    print(f"   Emotional State: {dog_analysis.emotional_state}")
    print(f"   Health Markers: {dog_analysis.visible_health_markers}")

    # Test 2: Analyze a cat image
    print("\n2. Analyzing cat image...")
    cat_analysis = await vision_agent.analyze_pet_image(
        image_url="https://example.com/cat.jpg",
        pet_type="cat"
    )
    print(f"   Primary Breed: {cat_analysis.primary_breed}")
    print(f"   Confidence: {cat_analysis.breed_confidence}")
    print(f"   Age: {cat_analysis.estimated_age}")
    print(f"   Colors: {cat_analysis.coat_color}")
    print(f"   Emotional State: {cat_analysis.emotional_state}")

    # Test 3: Batch analysis
    print("\n3. Analyzing multiple images (batch)...")
    image_urls = [
        "https://example.com/dog1.jpg",
        "https://example.com/dog2.jpg",
        "https://example.com/dog3.jpg"
    ]

    analyses = await vision_agent.analyze_multiple_images(
        image_urls=image_urls,
        pet_type="dog"
    )

    print(f"   Processed {len(analyses)} images")
    for i, analysis in enumerate(analyses):
        print(f"   Image {i+1}: {analysis.primary_breed} ({analysis.breed_confidence})")

    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_vision_agent())
