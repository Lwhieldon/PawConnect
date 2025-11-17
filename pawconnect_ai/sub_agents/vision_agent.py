"""
Vision Agent - Image Analysis Specialist
Analyzes pet photos using computer vision.
"""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from ..config import settings
from ..schemas.pet_data import VisionAnalysis, Pet
from ..models.breed_classifier import BreedClassifier
from ..utils.api_clients import google_cloud_client


class VisionAgent:
    """
    Specialized agent for analyzing pet images using computer vision.
    """

    def __init__(self):
        """Initialize the vision agent."""
        self.classifier = BreedClassifier()
        self.google_client = google_cloud_client

    async def analyze_pet_image(
        self,
        image_url: str,
        pet_type: Optional[str] = None
    ) -> VisionAnalysis:
        """
        Analyze a pet image to extract breed, age, and other characteristics.

        Args:
            image_url: URL of the pet image
            pet_type: Optional pet type hint (dog, cat, etc.)

        Returns:
            VisionAnalysis object with extracted information
        """
        try:
            logger.info(f"Analyzing pet image: {image_url}")

            # Skip analysis if Vision API is disabled or in mock mode
            if not settings.vision_api_enabled or settings.mock_apis:
                return self._get_mock_analysis(pet_type)

            # Call Google Cloud Vision API
            vision_data = await self.google_client.analyze_image(image_url)

            # Use breed classifier to analyze results
            analysis = self.classifier.analyze_vision_results(vision_data, pet_type)

            logger.info(
                f"Vision analysis complete: breed={analysis.primary_breed}, "
                f"confidence={analysis.breed_confidence}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing pet image: {e}")
            return VisionAnalysis(model_version=self.classifier.model_version)

    async def analyze_multiple_images(
        self,
        image_urls: list[str],
        pet_type: Optional[str] = None
    ) -> list[VisionAnalysis]:
        """
        Analyze multiple pet images concurrently.

        Args:
            image_urls: List of image URLs
            pet_type: Optional pet type hint

        Returns:
            List of VisionAnalysis objects
        """
        tasks = [
            self.analyze_pet_image(url, pet_type)
            for url in image_urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        analyses = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in batch analysis: {result}")
                analyses.append(VisionAnalysis(model_version=self.classifier.model_version))
            else:
                analyses.append(result)

        return analyses

    def enhance_pet_profile(
        self,
        pet: Pet,
        vision_analysis: VisionAnalysis
    ) -> Pet:
        """
        Enhance a pet profile with vision analysis data.

        Args:
            pet: Original pet object
            vision_analysis: Vision analysis results

        Returns:
            Enhanced Pet object
        """
        try:
            # Create a copy of the pet
            pet_dict = pet.dict()

            # Enhance with vision analysis
            enhanced_dict = self.classifier.enhance_pet_data(pet_dict, vision_analysis)

            # Create new Pet object
            return Pet(**enhanced_dict)

        except Exception as e:
            logger.error(f"Error enhancing pet profile: {e}")
            return pet

    def _get_mock_analysis(self, pet_type: Optional[str] = None) -> VisionAnalysis:
        """Get mock vision analysis for testing."""
        if pet_type == "dog":
            return VisionAnalysis(
                detected_breeds=[
                    {"breed": "Labrador Retriever", "confidence": 0.85},
                    {"breed": "Golden Retriever", "confidence": 0.72}
                ],
                primary_breed="Labrador Retriever",
                breed_confidence=0.85,
                estimated_age="adult",
                age_confidence=0.78,
                coat_color=["yellow", "brown"],
                emotional_state="friendly",
                visible_health_markers=["healthy coat", "alert"],
                model_version=self.classifier.model_version
            )
        elif pet_type == "cat":
            return VisionAnalysis(
                detected_breeds=[
                    {"breed": "Domestic Shorthair", "confidence": 0.80}
                ],
                primary_breed="Domestic Shorthair",
                breed_confidence=0.80,
                estimated_age="young",
                age_confidence=0.75,
                coat_color=["gray", "white"],
                emotional_state="calm",
                visible_health_markers=["healthy coat"],
                model_version=self.classifier.model_version
            )
        else:
            return VisionAnalysis(model_version=self.classifier.model_version)

    def classify_breed_from_labels(
        self,
        labels: list[Dict[str, Any]],
        pet_type: str = "dog"
    ) -> tuple[Optional[str], float]:
        """
        Classify breed from image labels.

        Args:
            labels: Image labels from vision API
            pet_type: Type of pet

        Returns:
            Tuple of (breed_name, confidence)
        """
        return self.classifier.classify_breed(labels, pet_type)
