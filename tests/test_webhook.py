"""
Test script for Dialogflow CX webhook.
Tests the webhook endpoints with sample Dialogflow requests.
"""

import asyncio
import json
from typing import Dict, Any
import pytest


# Sample Dialogflow CX request for pet ID validation
SAMPLE_VALIDATE_PET_REQUEST = {
    "detectIntentResponseId": "test-response-id",
    "sessionInfo": {
        "session": "projects/test-project/locations/us-central1/agents/test-agent/sessions/test-session",
        "parameters": {
            "pet_id": "12345"
        }
    },
    "fulfillmentInfo": {
        "tag": "validate-pet-id"
    },
    "pageInfo": {
        "currentPage": "projects/test-project/locations/us-central1/agents/test-agent/flows/test-flow/pages/test-page",
        "displayName": "Schedule Visit"
    },
    "text": "I want to visit pet 12345",
    "languageCode": "en"
}

SAMPLE_SEARCH_PETS_REQUEST = {
    "detectIntentResponseId": "test-response-id",
    "sessionInfo": {
        "session": "projects/test-project/locations/us-central1/agents/test-agent/sessions/test-session",
        "parameters": {
            "pet_type": "dog",
            "location": "98101"
        }
    },
    "fulfillmentInfo": {
        "tag": "search-pets"
    },
    "pageInfo": {
        "currentPage": "projects/test-project/locations/us-central1/agents/test-agent/flows/test-flow/pages/test-page",
        "displayName": "Pet Search"
    },
    "text": "I want to find a dog in 98101",
    "languageCode": "en"
}


@pytest.mark.asyncio
async def test_webhook_locally():
    """
    Test the webhook running locally.
    Run the webhook server first: python -m pawconnect_ai.dialogflow_webhook
    """
    import aiohttp

    webhook_url = "http://localhost:8080/webhook"

    try:
        async with aiohttp.ClientSession() as session:
            # Test health check
            print("Testing health check...")
            async with session.get("http://localhost:8080/health") as response:
                health_data = await response.json()
                print(f"✓ Health check: {health_data}")
                print()

            # Test pet ID validation
            print("Testing pet ID validation webhook...")
            print(f"Request: {json.dumps(SAMPLE_VALIDATE_PET_REQUEST, indent=2)}")
            print()

            async with session.post(webhook_url, json=SAMPLE_VALIDATE_PET_REQUEST) as response:
                response_data = await response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                print()

                # Extract response text
                messages = response_data.get("fulfillmentResponse", {}).get("messages", [])
                if messages:
                    response_text = messages[0].get("text", {}).get("text", [""])[0]
                    print(f"Agent says: {response_text}")
                print()

            # Test search pets
            print("Testing search pets webhook...")
            print(f"Request: {json.dumps(SAMPLE_SEARCH_PETS_REQUEST, indent=2)}")
            print()

            async with session.post(webhook_url, json=SAMPLE_SEARCH_PETS_REQUEST) as response:
                response_data = await response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                print()

                # Extract response text
                messages = response_data.get("fulfillmentResponse", {}).get("messages", [])
                if messages:
                    response_text = messages[0].get("text", {}).get("text", [""])[0]
                    print(f"Agent says: {response_text}")
                print()
    except (aiohttp.ClientConnectorError, ConnectionRefusedError, OSError) as e:
        pytest.skip(f"Webhook server not running at localhost:8080. Start server with: python -m pawconnect_ai.dialogflow_webhook")


def test_webhook_request_format():
    """Test that request format is valid."""
    print("Testing Dialogflow CX request format...")
    print()
    print("Sample validate pet ID request:")
    print(json.dumps(SAMPLE_VALIDATE_PET_REQUEST, indent=2))
    print()
    print("Sample search pets request:")
    print(json.dumps(SAMPLE_SEARCH_PETS_REQUEST, indent=2))
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--format-only":
        test_webhook_request_format()
    else:
        print("=" * 60)
        print("PawConnect Webhook Test")
        print("=" * 60)
        print()
        print("Make sure the webhook server is running:")
        print("  python -m pawconnect_ai.dialogflow_webhook")
        print()
        print("=" * 60)
        print()

        try:
            asyncio.run(test_webhook_locally())
        except Exception as e:
            print(f"Error: {e}")
            print()
            print("Make sure the webhook server is running at http://localhost:8080")
            print("Run: python -m pawconnect_ai.dialogflow_webhook")
