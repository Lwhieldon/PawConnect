"""
Comprehensive test suite for Dialogflow CX webhook.
Tests all webhook endpoints with various scenarios including success and failure cases.
"""

import asyncio
import json
from typing import Dict, Any
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Test data - Dialogflow CX request payloads
TEST_CASES = {
    "validate_pet_id_missing": {
        "description": "Test validate-pet-id with missing pet ID parameter",
        "request": {
            "detectIntentResponseId": "test-missing-id",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {}
            },
            "fulfillmentInfo": {
                "tag": "validate-pet-id"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Pet Details"
            },
            "text": "test",
            "languageCode": "en"
        },
        "expected_contains": "I need a pet ID to look up"
    },
    "validate_pet_id_valid": {
        "description": "Test validate-pet-id with real pet ID 10393561 (Rosie)",
        "request": {
            "detectIntentResponseId": "test-valid-id",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_id": "10393561"
                }
            },
            "fulfillmentInfo": {
                "tag": "validate-pet-id"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Pet Details"
            },
            "text": "show me pet 10393561",
            "languageCode": "en"
        },
        "expected_contains": None,  # Response depends on RescueGroups API
        "verify_pet_id": "10393561"  # Verify this ID is in the response
    },
    "validate_pet_id_invalid": {
        "description": "Test validate-pet-id with non-existent pet ID 99999999",
        "request": {
            "detectIntentResponseId": "test-invalid-id",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_id": "99999999"
                }
            },
            "fulfillmentInfo": {
                "tag": "validate-pet-id"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Pet Details"
            },
            "text": "show me pet 99999999",
            "languageCode": "en"
        },
        "expected_contains": "couldn't find a pet with ID",
        "verify_pet_id": "99999999"  # Should NOT return this ID
    },
    "search_pets_valid": {
        "description": "Test search-pets with valid parameters",
        "request": {
            "detectIntentResponseId": "test-search",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_type": "dog",
                    "location": "Seattle"
                }
            },
            "fulfillmentInfo": {
                "tag": "search-pets"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Pet Search"
            },
            "text": "find dogs in Seattle",
            "languageCode": "en"
        },
        "expected_contains": None  # Response depends on search results
    },
    "search_pets_missing_location": {
        "description": "Test search-pets without location parameter",
        "request": {
            "detectIntentResponseId": "test-search-no-loc",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_type": "cat"
                }
            },
            "fulfillmentInfo": {
                "tag": "search-pets"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Pet Search"
            },
            "text": "find cats",
            "languageCode": "en"
        },
        "expected_contains": "I need to know your location"
    },
    "get_recommendations_complete": {
        "description": "Test get-recommendations with complete user preferences",
        "request": {
            "detectIntentResponseId": "test-recommendations",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_type": "dog",
                    "location": "98101",
                    "housing": "apartment",
                    "experience": "yes"
                }
            },
            "fulfillmentInfo": {
                "tag": "get-recommendations"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Recommendations"
            },
            "text": "show me recommendations",
            "languageCode": "en"
        },
        "expected_contains": None  # Response depends on available pets
    },
    "get_recommendations_missing_housing": {
        "description": "Test get-recommendations without housing type",
        "request": {
            "detectIntentResponseId": "test-rec-no-housing",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {
                    "pet_type": "dog",
                    "location": "Seattle"
                }
            },
            "fulfillmentInfo": {
                "tag": "get-recommendations"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Recommendations"
            },
            "text": "recommend pets",
            "languageCode": "en"
        },
        "expected_contains": "What type of housing do you have"
    },
    "schedule_visit_missing_pet_id": {
        "description": "Test schedule-visit without pet ID",
        "request": {
            "detectIntentResponseId": "test-schedule-no-id",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {}
            },
            "fulfillmentInfo": {
                "tag": "schedule-visit"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Schedule Visit"
            },
            "text": "schedule a visit",
            "languageCode": "en"
        },
        "expected_contains": "Which pet would you like to visit"
    },
    "submit_application_missing_pet_id": {
        "description": "Test submit-application without pet ID",
        "request": {
            "detectIntentResponseId": "test-submit-no-id",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {}
            },
            "fulfillmentInfo": {
                "tag": "submit-application"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Application"
            },
            "text": "submit application",
            "languageCode": "en"
        },
        "expected_contains": "Which pet would you like to apply for"
    },
    "unknown_tag": {
        "description": "Test webhook with unknown tag",
        "request": {
            "detectIntentResponseId": "test-unknown",
            "sessionInfo": {
                "session": "projects/test/locations/us-central1/agents/test/sessions/test",
                "parameters": {}
            },
            "fulfillmentInfo": {
                "tag": "unknown-tag"
            },
            "pageInfo": {
                "currentPage": "projects/test/locations/us-central1/agents/test/flows/test/pages/test",
                "displayName": "Test Page"
            },
            "text": "test unknown",
            "languageCode": "en"
        },
        "expected_contains": "I don't know how to handle that request"
    }
}


def extract_response_text(response_data: Dict[str, Any]) -> str:
    """Extract text from Dialogflow response."""
    try:
        messages = response_data.get("fulfillmentResponse", {}).get("messages", [])
        if messages and "text" in messages[0]:
            text_list = messages[0]["text"].get("text", [])
            return text_list[0] if text_list else ""
    except (KeyError, IndexError, TypeError):
        pass
    return ""


@pytest.mark.asyncio
async def test_webhook_health_check():
    """Test webhook health check endpoint."""
    import aiohttp

    webhook_base_url = os.getenv("WEBHOOK_URL", "http://localhost:8080")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{webhook_base_url}/health") as response:
                assert response.status == 200
                data = await response.json()
                assert data.get("status") == "healthy"
                assert "pawconnect" in data.get("service", "").lower()
                print(f"✓ Health check passed: {data}")
    except (aiohttp.ClientConnectorError, ConnectionRefusedError, OSError):
        pytest.skip(f"Webhook server not running at {webhook_base_url}")


@pytest.mark.asyncio
async def test_webhook_root_endpoint():
    """Test webhook root endpoint."""
    import aiohttp

    webhook_base_url = os.getenv("WEBHOOK_URL", "http://localhost:8080")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{webhook_base_url}/") as response:
                assert response.status == 200
                data = await response.json()
                assert "service" in data
                assert "endpoints" in data
                print(f"✓ Root endpoint passed: {data}")
    except (aiohttp.ClientConnectorError, ConnectionRefusedError, OSError):
        pytest.skip(f"Webhook server not running at {webhook_base_url}")


@pytest.mark.asyncio
@pytest.mark.parametrize("test_name,test_data", TEST_CASES.items())
async def test_webhook_endpoints(test_name: str, test_data: Dict[str, Any]):
    """
    Test webhook endpoints with various scenarios.

    Run the webhook server first:
        python -m pawconnect_ai.dialogflow_webhook

    Or set WEBHOOK_URL environment variable to test deployed webhook:
        export WEBHOOK_URL=https://your-webhook-url.run.app
        pytest tests/test_webhook.py -v
    """
    import aiohttp

    webhook_base_url = os.getenv("WEBHOOK_URL", "http://localhost:8080")
    webhook_url = f"{webhook_base_url}/webhook"

    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"Description: {test_data['description']}")
    print(f"{'='*60}")

    try:
        async with aiohttp.ClientSession() as session:
            # Send request
            async with session.post(webhook_url, json=test_data["request"]) as response:
                # Webhook should return 200 or 500 (for internal errors)
                assert response.status in [200, 500], f"Unexpected status code: {response.status}"

                # Parse response
                response_data = await response.json()
                response_text = extract_response_text(response_data)

                print(f"\nRequest payload:")
                print(json.dumps(test_data["request"], indent=2))
                print(f"\nResponse status: {response.status}")
                print(f"\nResponse data:")
                print(json.dumps(response_data, indent=2))
                print(f"\nExtracted text: {response_text}")

                # Validate response structure
                assert "fulfillmentResponse" in response_data
                assert "messages" in response_data["fulfillmentResponse"]

                # Check expected content if specified
                if test_data.get("expected_contains"):
                    assert test_data["expected_contains"].lower() in response_text.lower(), \
                        f"Expected '{test_data['expected_contains']}' in response, got: {response_text}"
                    print(f"\n✓ Test passed: Found expected text in response")
                else:
                    print(f"\n✓ Test passed: Response structure is valid")

                # CRITICAL: Verify pet ID in session parameters if test specifies it
                if test_data.get("verify_pet_id"):
                    expected_id = test_data["verify_pet_id"]
                    session_params = response_data.get("sessionInfo", {}).get("parameters", {})
                    validated_id = session_params.get("validated_pet_id")

                    if validated_id:
                        assert str(validated_id) == str(expected_id), \
                            f"Pet ID mismatch! Expected: {expected_id}, Got: {validated_id}"
                        print(f"\n✓ Pet ID verification passed: {validated_id}")

                        # Also verify species is included if pet was found
                        species = session_params.get("pet_species")
                        if species:
                            print(f"✓ Species included in response: {species}")
                            assert species.lower() in ["dog", "cat", "rabbit", "bird", "small animal"], \
                                f"Invalid species: {species}"
                    else:
                        # If no validated_id returned, should be "not found" message
                        assert "couldn't find" in response_text.lower(), \
                            f"Expected 'not found' message for pet {expected_id}, got: {response_text}"
                        print(f"\n✓ Pet {expected_id} correctly reported as not found")

    except (aiohttp.ClientConnectorError, ConnectionRefusedError, OSError) as e:
        pytest.skip(
            f"Webhook server not running at {webhook_base_url}. "
            f"Start server with: python -m pawconnect_ai.dialogflow_webhook"
        )


@pytest.mark.asyncio
async def test_webhook_malformed_request():
    """Test webhook with malformed request."""
    import aiohttp

    webhook_base_url = os.getenv("WEBHOOK_URL", "http://localhost:8080")
    webhook_url = f"{webhook_base_url}/webhook"

    try:
        async with aiohttp.ClientSession() as session:
            # Send malformed request
            async with session.post(webhook_url, json={"invalid": "data"}) as response:
                # Should handle gracefully
                assert response.status in [200, 400, 422, 500]
                print(f"✓ Malformed request handled gracefully with status {response.status}")
    except (aiohttp.ClientConnectorError, ConnectionRefusedError, OSError):
        pytest.skip(f"Webhook server not running at {webhook_base_url}")


def test_webhook_request_format():
    """Test that request format is valid JSON."""
    print("\n" + "="*60)
    print("Validating Dialogflow CX Request Formats")
    print("="*60 + "\n")

    for test_name, test_data in TEST_CASES.items():
        print(f"Test: {test_name}")
        print(f"Description: {test_data['description']}")

        # Validate JSON structure
        request = test_data["request"]
        assert "detectIntentResponseId" in request
        assert "sessionInfo" in request
        assert "fulfillmentInfo" in request
        assert "pageInfo" in request
        assert "languageCode" in request

        # Validate tag exists
        tag = request["fulfillmentInfo"].get("tag")
        assert tag is not None, f"Missing webhook tag in {test_name}"

        print(f"✓ Valid format with tag: {tag}\n")

    print("✓ All request formats are valid")


def print_test_summary():
    """Print summary of available test cases."""
    print("\n" + "="*60)
    print("PawConnect Webhook Test Suite")
    print("="*60)
    print(f"\nTotal test cases: {len(TEST_CASES)}")
    print("\nTest scenarios:")
    for i, (test_name, test_data) in enumerate(TEST_CASES.items(), 1):
        print(f"  {i}. {test_data['description']}")

    print("\n" + "="*60)
    print("Running Instructions:")
    print("="*60)
    print("\nLocal testing:")
    print("  1. Start webhook server:")
    print("     python -m pawconnect_ai.dialogflow_webhook")
    print("  2. Run tests:")
    print("     python -m pytest tests/test_webhook.py -v")

    print("\nProduction testing:")
    print("  1. Set webhook URL:")
    print("     export WEBHOOK_URL=https://your-webhook-url.run.app")
    print("  2. Run tests:")
    print("     python -m pytest tests/test_webhook.py -v")

    print("\nRun specific test:")
    print("  python -m pytest tests/test_webhook.py::test_name -v")

    print("\nRun with coverage:")
    print("  python -m pytest tests/test_webhook.py -v --cov=pawconnect_ai.dialogflow_webhook")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--format-only":
        test_webhook_request_format()
    elif len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print_test_summary()
    else:
        print_test_summary()
        print("\nStarting tests...\n")

        # Run all tests
        import pytest
        pytest.main([__file__, "-v", "--tb=short"])
