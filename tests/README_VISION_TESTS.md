# Vision Agent Test Files

Quick reference for running Vision Agent tests.

## Test Files

1. **test_vision_manual.py** - Basic Vision Agent functionality test
2. **test_vision_integration.py** - Full PawConnect integration test
3. **test_vision_real_api.py** - Real Google Cloud Vision API test

## Running Tests

### Option 1: Run with pytest (from project root)

```bash
# All vision tests
python -m pytest tests/test_vision*.py -v

# Specific test
python -m pytest tests/test_vision_manual.py -v
python -m pytest tests/test_vision_integration.py -v -s
python -m pytest tests/test_vision_real_api.py -v -s
```

### Option 2: Run directly as scripts (from tests folder)

```bash
cd tests
python test_vision_manual.py
python test_vision_integration.py
python test_vision_real_api.py
```

### Option 3: Run directly as scripts (from project root)

```bash
python tests/test_vision_manual.py
python tests/test_vision_integration.py
python tests/test_vision_real_api.py
```

## Test Status

✅ All 3 tests passing
✅ Work with pytest
✅ Work as standalone scripts
✅ Work from any directory

## What Each Test Does

### test_vision_manual.py
- Tests basic image analysis (dog and cat)
- Tests batch processing (3 images)
- Uses mock data (no API needed)

### test_vision_integration.py
- Tests PawConnectTools integration
- Tests pet profile enhancement
- Tests error handling
- Uses mock data (no API needed)

### test_vision_real_api.py
- Tests real Google Cloud Vision API
- Requires GCP credentials
- Set `GOOGLE_APPLICATION_CREDENTIALS` env var
- Enable Vision API in GCP project

## More Information

See: `docs/VISION_AGENT_TESTING_GUIDE.md` for detailed documentation
