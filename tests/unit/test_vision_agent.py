"""
Unit tests for Vision Agent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from pawconnect_ai.sub_agents.vision_agent import VisionAgent
from pawconnect_ai.schemas.pet_data import VisionAnalysis
from pawconnect_ai.config import settings


class TestVisionAgent:
    """Unit tests for VisionAgent class."""

    @pytest.fixture
    def vision_agent(self):
        """Create a VisionAgent instance for testing."""
        settings.mock_apis = True
        settings.testing_mode = True
        return VisionAgent()

    @pytest.fixture
    def sample_image_url(self):
        """Sample image URL for testing."""
        return "https://example.com/dog.jpg"

    @pytest.mark.asyncio
    async def test_analyze_pet_image(self, vision_agent, sample_image_url):
        """Test analyzing a pet image."""
        analysis = await vision_agent.analyze_pet_image(
            image_url=sample_image_url,
            pet_type="dog"
        )

        assert isinstance(analysis, VisionAnalysis)
        assert analysis.primary_breed is not None
        assert analysis.breed_confidence is not None
        assert 0.0 <= analysis.breed_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_multiple_images(self, vision_agent):
        """Test analyzing multiple images."""
        image_urls = [
            "https://example.com/dog1.jpg",
            "https://example.com/dog2.jpg",
            "https://example.com/dog3.jpg"
        ]

        analyses = await vision_agent.analyze_multiple_images(
            image_urls=image_urls,
            pet_type="dog"
        )

        assert isinstance(analyses, list)
        assert len(analyses) == len(image_urls)
        for analysis in analyses:
            assert isinstance(analysis, VisionAnalysis)

    @pytest.mark.asyncio
    async def test_detect_breed(self, vision_agent, sample_image_url):
        """Test breed detection."""
        breed_info = await vision_agent._detect_breed(
            image_url=sample_image_url,
            pet_type="dog"
        )

        assert "primary_breed" in breed_info
        assert "confidence" in breed_info
        assert isinstance(breed_info["confidence"], float)

    @pytest.mark.asyncio
    async def test_estimate_age(self, vision_agent, sample_image_url):
        """Test age estimation."""
        age_info = await vision_agent._estimate_age(
            image_url=sample_image_url,
            pet_type="dog"
        )

        assert "estimated_age" in age_info
        assert "confidence" in age_info
        assert age_info["estimated_age"] in ["baby", "young", "adult", "senior"]

    @pytest.mark.asyncio
    async def test_analyze_with_invalid_url(self, vision_agent):
        """Test handling of invalid image URL."""
        analysis = await vision_agent.analyze_pet_image(
            image_url="invalid-url",
            pet_type="dog"
        )

        # Should still return VisionAnalysis with defaults
        assert isinstance(analysis, VisionAnalysis)

    @pytest.mark.asyncio
    async def test_analyze_with_confidence_threshold(self, vision_agent, sample_image_url):
        """Test analysis with confidence threshold filtering."""
        analysis = await vision_agent.analyze_pet_image(
            image_url=sample_image_url,
            pet_type="dog",
            confidence_threshold=0.8
        )

        if analysis.breed_confidence:
            assert analysis.breed_confidence >= 0.8 or analysis.primary_breed is None

    @pytest.mark.asyncio
    async def test_analyze_cat_image(self, vision_agent):
        """Test analyzing a cat image."""
        analysis = await vision_agent.analyze_pet_image(
            image_url="https://example.com/cat.jpg",
            pet_type="cat"
        )

        assert isinstance(analysis, VisionAnalysis)

    def test_vision_analysis_creation(self):
        """Test creating VisionAnalysis object."""
        analysis = VisionAnalysis(
            detected_breeds=[{"breed": "Labrador", "confidence": 0.95}],
            primary_breed="Labrador",
            breed_confidence=0.95,
            estimated_age="adult",
            age_confidence=0.85
        )

        assert analysis.primary_breed == "Labrador"
        assert analysis.breed_confidence == 0.95
        assert analysis.estimated_age == "adult"

    @pytest.mark.asyncio
    async def test_batch_analysis_error_handling(self, vision_agent):
        """Test error handling in batch analysis."""
        image_urls = [
            "https://example.com/valid.jpg",
            "invalid-url",
            "https://example.com/another.jpg"
        ]

        analyses = await vision_agent.analyze_multiple_images(
            image_urls=image_urls,
            pet_type="dog"
        )

        # Should handle errors gracefully and return results for valid images
        assert isinstance(analyses, list)

    @pytest.mark.asyncio
    async def test_analyze_with_mock_vision_api(self, vision_agent, sample_image_url):
        """Test with mocked Vision API."""
        with patch.object(
            vision_agent,
            '_call_vision_api',
            return_value={
                "labels": [{"description": "Dog", "score": 0.95}],
                "breed": "Labrador Retriever"
            }
        ):
            analysis = await vision_agent.analyze_pet_image(
                image_url=sample_image_url,
                pet_type="dog"
            )

            assert isinstance(analysis, VisionAnalysis)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
