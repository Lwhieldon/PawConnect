"""
Test Vision Agent with real Google Cloud Vision API
Prerequisites:
1. Google Cloud credentials configured (GOOGLE_APPLICATION_CREDENTIALS env var)
2. Vision API enabled in your GCP project
3. settings.vision_api_enabled = True

Run with: python test_vision_real_api.py
Or with pytest: pytest tests/test_vision_real_api.py -s
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
async def test_real_vision_api():
    """Test the Vision Agent with real Google Cloud Vision API."""

    # Disable mock mode to use real API
    settings.mock_apis = False
    settings.vision_api_enabled = True

    # Initialize the agent
    vision_agent = VisionAgent()

    print("=" * 60)
    print("Testing Vision Agent with REAL Google Cloud Vision API")
    print("=" * 60)
    print(f"GCP Project: {settings.gcp_project_id}")
    print(f"Mock APIs: {settings.mock_apis}")
    print(f"Vision API Enabled: {settings.vision_api_enabled}")
    print("=" * 60)

    # Example: Use a publicly accessible dog image
    # Replace with your own image URL or use one from RescueGroups

    # Option 1: Wikimedia Commons (stable, public domain)
    test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Labrador_on_Quantock_%282175262184%29.jpg/800px-Labrador_on_Quantock_%282175262184%29.jpg"

    # Option 2: Use an image from RescueGroups (from actual search results)
    # test_image_url = "https://cdn.rescuegroups.org/4264/pictures/animals/10552/10552500/38813998.jpg"

    # Option 3: Another Wikimedia Commons dog image
    # test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Golden_Retriever_standing_Tucker.jpg/800px-Golden_Retriever_standing_Tucker.jpg"

    print(f"\nAnalyzing image: {test_image_url}")
    print("This will call the real Google Cloud Vision API...")
    print("(This may take a few seconds)")

    try:
        analysis = await vision_agent.analyze_pet_image(
            image_url=test_image_url,
            pet_type="dog"
        )

        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        print(f"\nDetected Breeds:")
        for breed_info in analysis.detected_breeds:
            print(f"  - {breed_info['breed']}: {breed_info['confidence']:.2%}")

        print(f"\nPrimary Breed: {analysis.primary_breed}")
        print(f"Breed Confidence: {analysis.breed_confidence:.2%}" if analysis.breed_confidence else "N/A")

        print(f"\nEstimated Age: {analysis.estimated_age}")
        print(f"Age Confidence: {analysis.age_confidence:.2%}" if analysis.age_confidence else "N/A")

        print(f"\nCoat Colors: {analysis.coat_color}")
        print(f"Emotional State: {analysis.emotional_state}")
        print(f"Visible Health Markers: {analysis.visible_health_markers}")

        print(f"\nModel Version: {analysis.model_version}")
        print(f"Analyzed At: {analysis.analyzed_at}")

        print("\n" + "=" * 60)
        print("SUCCESS: Real API test completed!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("ERROR: Failed to analyze image with real API")
        print("=" * 60)
        print(f"Error: {e}")
        print("\nPossible causes:")
        print("1. Google Cloud credentials not configured")
        print("2. Vision API not enabled in GCP project")
        print("3. Invalid image URL")
        print("4. Network connectivity issues")
        print("\nTo fix:")
        print("- Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("- Run: gcloud auth application-default login")
        print("- Enable Vision API in GCP Console")

if __name__ == "__main__":
    asyncio.run(test_real_vision_api())
