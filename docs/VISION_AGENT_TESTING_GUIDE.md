# Vision Agent Testing Guide

Complete guide for testing the PawConnect Vision Agent.

## Overview

The Vision Agent analyzes pet images using Google Cloud Vision API to extract:
- Breed information with confidence scores
- Age estimation (baby, young, adult, senior)
- Coat colors
- Emotional state (friendly, fearful, energetic, calm)
- Visible health markers

## Testing Methods

### Quick Test (All Tests)

Run all Vision Agent tests at once:

```bash
# Run all vision tests
python -m pytest tests/test_vision*.py -v

# Run all vision tests with output
python -m pytest tests/test_vision*.py -v -s

# Run unit tests only
python -m pytest tests/unit/test_vision_agent.py -v
```

### 1. Unit Tests (Fastest)

Run the existing unit tests in mock mode:

```bash
# Run all Vision Agent tests
python -m pytest tests/unit/test_vision_agent.py -v

# Run specific test
python -m pytest tests/unit/test_vision_agent.py::TestVisionAgent::test_analyze_pet_image -v

# Run with coverage
python -m pytest tests/unit/test_vision_agent.py --cov=pawconnect_ai.sub_agents.vision_agent
```

**Status:** 6/10 tests passing (4 tests reference old implementation)

**Passing Tests:**
- ✅ test_analyze_pet_image - Basic analysis
- ✅ test_analyze_multiple_images - Batch processing
- ✅ test_analyze_with_invalid_url - Error handling
- ✅ test_analyze_cat_image - Cat detection
- ✅ test_vision_analysis_creation - Data model
- ✅ test_batch_analysis_error_handling - Concurrent errors

### 2. Manual Script Test (Mock Mode)

Quick manual testing without API credentials:

```bash
# Run with pytest
python -m pytest tests/test_vision_manual.py -v -s

# Or run directly
cd tests && python test_vision_manual.py
```

This script tests:
- Dog image analysis
- Cat image analysis
- Batch processing of multiple images

**Output Example:**
```
Primary Breed: Labrador Retriever
Confidence: 0.85
Age: adult
Colors: ['yellow', 'brown']
Emotional State: friendly
Health Markers: ['healthy coat', 'alert']
```

### 3. Integration Test

Test Vision Agent with full PawConnect system:

```bash
# Run with pytest (recommended, shows output)
python -m pytest tests/test_vision_integration.py -v -s

# Or run directly
cd tests && python test_vision_integration.py
```

This demonstrates:
- Analysis through PawConnectTools interface
- Enhancing pet profiles with vision data
- Batch processing
- Error handling

### 4. Real API Test

Test with actual Google Cloud Vision API:

```bash
# Run with pytest (recommended)
python -m pytest tests/test_vision_real_api.py -v -s

# Or run directly
cd tests && python test_vision_real_api.py
```

**Prerequisites:**
1. Google Cloud credentials configured
2. Vision API enabled in GCP project
3. Environment variable set: `GOOGLE_APPLICATION_CREDENTIALS`

**Setup:**
```bash
# Set credentials
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\credentials\gcp-key.json

# Or use gcloud CLI
gcloud auth application-default login

# Enable Vision API
gcloud services enable vision.googleapis.com
```

## Code Examples

### Direct Vision Agent Usage

```python
import asyncio
from pawconnect_ai.sub_agents.vision_agent import VisionAgent
from pawconnect_ai.config import settings

async def analyze_image():
    # Mock mode (no API needed)
    settings.mock_apis = True

    vision_agent = VisionAgent()

    # Analyze single image
    analysis = await vision_agent.analyze_pet_image(
        image_url="https://example.com/dog.jpg",
        pet_type="dog"
    )

    print(f"Breed: {analysis.primary_breed}")
    print(f"Confidence: {analysis.breed_confidence}")

    # Analyze multiple images
    analyses = await vision_agent.analyze_multiple_images(
        image_urls=[
            "https://example.com/dog1.jpg",
            "https://example.com/dog2.jpg"
        ],
        pet_type="dog"
    )

asyncio.run(analyze_image())
```

### Through PawConnect Tools

```python
from pawconnect_ai.tools import PawConnectTools

tools = PawConnectTools()

# Analyze image
analysis_dict = await tools.analyze_pet_image(
    image_url="https://example.com/dog.jpg",
    pet_type="dog"
)

# Returns dictionary with all analysis fields
```

### Enhance Pet Profile

```python
from pawconnect_ai.sub_agents.vision_agent import VisionAgent

vision_agent = VisionAgent()

# Get vision analysis
vision_analysis = await vision_agent.analyze_pet_image(
    image_url=pet.primary_photo_url,
    pet_type=pet.species.value
)

# Enhance pet with vision data
enhanced_pet = vision_agent.enhance_pet_profile(
    pet=pet,
    vision_analysis=vision_analysis
)

# Now pet has breed, age, color filled in if detected
```

## Architecture Flow

```
User/Test
    ↓
VisionAgent.analyze_pet_image(url, pet_type)
    ↓
GoogleCloudClient.analyze_image(url)
    ↓
[Google Cloud Vision API]
    ↓ returns labels, objects, colors, etc.
BreedClassifier.analyze_vision_results(data)
    ↓
- Extract breeds from labels
- Estimate age from visual cues
- Extract colors from RGB values
- Detect emotional state
- Identify health markers
    ↓
VisionAnalysis object
```

## Key Files

- **VisionAgent:** `pawconnect_ai/sub_agents/vision_agent.py:16`
- **BreedClassifier:** `pawconnect_ai/models/breed_classifier.py:12`
- **GoogleCloudClient:** `pawconnect_ai/utils/api_clients.py:234`
- **VisionAnalysis Schema:** `pawconnect_ai/schemas/pet_data.py:120`
- **Unit Tests:** `tests/unit/test_vision_agent.py:13`

## Troubleshooting

### Tests Won't Run

**Error:** `ModuleNotFoundError: No module named 'email_validator'`

**Fix:**
```bash
pip install email-validator
```

### Real API Test Fails

**Error:** `google.auth.exceptions.DefaultCredentialsError`

**Fix:**
```bash
# Option 1: Set credentials file
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\gcp-key.json

# Option 2: Use gcloud auth
gcloud auth application-default login

# Verify
gcloud auth application-default print-access-token
```

### Vision API Not Enabled

**Error:** `PERMISSION_DENIED: Cloud Vision API has not been used`

**Fix:**
```bash
gcloud services enable vision.googleapis.com
```

## Mock vs Real Mode

### Mock Mode (Default for Testing)
```python
settings.mock_apis = True
settings.vision_api_enabled = False
```
- No API calls
- Returns predefined results
- Fast and free
- Good for development/testing

### Real API Mode
```python
settings.mock_apis = False
settings.vision_api_enabled = True
```
- Calls Google Cloud Vision API
- Returns actual image analysis
- Requires credentials
- Costs per API call (~$1.50 per 1000 images)

## Next Steps

1. **Run unit tests** to verify core functionality
2. **Try manual script** to see Vision Agent in action
3. **Test integration** to understand how it fits in PawConnect
4. **Configure GCP** if you need real API testing
5. **Review code** in the key files listed above

## Support

- Vision Agent code: `pawconnect_ai/sub_agents/vision_agent.py`
- Google Cloud setup: `docs/DEPLOYMENT.md`
- Architecture overview: `docs/ARCHITECTURE.md`
