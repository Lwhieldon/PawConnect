"""
Breed classification model for pet images.
Analyzes pet photos to identify breeds and characteristics.
"""

from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from ..schemas.pet_data import VisionAnalysis, PetType


class BreedClassifier:
    """
    Breed classification model using computer vision analysis.
    Combines Google Cloud Vision API with custom breed detection logic.
    """

    # Common dog breeds
    DOG_BREEDS = [
        "Labrador Retriever", "German Shepherd", "Golden Retriever",
        "French Bulldog", "Bulldog", "Poodle", "Beagle", "Rottweiler",
        "German Shorthaired Pointer", "Dachshund", "Pembroke Welsh Corgi",
        "Australian Shepherd", "Yorkshire Terrier", "Boxer", "Great Dane",
        "Siberian Husky", "Doberman Pinscher", "Cavalier King Charles Spaniel",
        "Miniature Schnauzer", "Shih Tzu", "Boston Terrier", "Pomeranian",
        "Havanese", "Shetland Sheepdog", "Bernese Mountain Dog", "Chihuahua",
        "Border Collie", "Mastiff", "Cocker Spaniel", "Pit Bull Terrier"
    ]

    # Common cat breeds
    CAT_BREEDS = [
        "Domestic Shorthair", "Domestic Longhair", "Siamese", "Persian",
        "Maine Coon", "Ragdoll", "British Shorthair", "Abyssinian",
        "Exotic Shorthair", "Scottish Fold", "Sphynx", "Devon Rex",
        "American Shorthair", "Birman", "Oriental", "Burmese",
        "Russian Blue", "Norwegian Forest Cat", "Bengal", "Tonkinese"
    ]

    # Age indicators based on visual features
    AGE_INDICATORS = {
        "baby": ["puppy", "kitten", "young", "small", "playful"],
        "young": ["adolescent", "energetic", "active"],
        "adult": ["mature", "developed", "full-grown"],
        "senior": ["old", "gray", "greying", "aged", "elderly"]
    }

    def __init__(self, model_version: str = "1.0"):
        """Initialize the breed classifier."""
        self.model_version = model_version

    def analyze_vision_results(
        self,
        vision_data: Dict[str, Any],
        pet_type: Optional[str] = None
    ) -> VisionAnalysis:
        """
        Analyze Google Cloud Vision API results to extract pet information.

        Args:
            vision_data: Raw Vision API response
            pet_type: Optional pet type hint (dog, cat, etc.)

        Returns:
            VisionAnalysis object with extracted information
        """
        try:
            # Extract breeds from labels
            detected_breeds = self._extract_breeds(vision_data, pet_type)

            primary_breed = None
            breed_confidence = None
            if detected_breeds:
                primary_breed = detected_breeds[0]["breed"]
                breed_confidence = detected_breeds[0]["confidence"]

            # Estimate age from labels
            estimated_age, age_confidence = self._estimate_age(vision_data)

            # Extract colors
            coat_colors = self._extract_colors(vision_data)

            # Detect emotional state
            emotional_state = self._detect_emotional_state(vision_data)

            # Check for visible health markers
            health_markers = self._detect_health_markers(vision_data)

            return VisionAnalysis(
                detected_breeds=detected_breeds,
                primary_breed=primary_breed,
                breed_confidence=breed_confidence,
                estimated_age=estimated_age,
                age_confidence=age_confidence,
                coat_color=coat_colors,
                visible_health_markers=health_markers,
                emotional_state=emotional_state,
                model_version=self.model_version
            )

        except Exception as e:
            logger.error(f"Error analyzing vision results: {e}")
            return VisionAnalysis(model_version=self.model_version)

    def _extract_breeds(
        self,
        vision_data: Dict[str, Any],
        pet_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract breed information from vision labels."""
        breeds = []
        labels = vision_data.get("labels", [])

        # Determine which breed list to use
        if pet_type and pet_type.lower() == "dog":
            breed_list = self.DOG_BREEDS
        elif pet_type and pet_type.lower() == "cat":
            breed_list = self.CAT_BREEDS
        else:
            # Try to detect from labels
            has_dog = any("dog" in label["description"].lower() for label in labels)
            has_cat = any("cat" in label["description"].lower() for label in labels)

            if has_dog:
                breed_list = self.DOG_BREEDS
            elif has_cat:
                breed_list = self.CAT_BREEDS
            else:
                return breeds

        # Match labels to known breeds
        for label in labels:
            description = label["description"]
            score = label["score"]

            # Check if label matches any known breed
            for breed in breed_list:
                if breed.lower() in description.lower() or description.lower() in breed.lower():
                    breeds.append({
                        "breed": breed,
                        "confidence": round(score, 3)
                    })
                    break

        # Sort by confidence and remove duplicates
        seen_breeds = set()
        unique_breeds = []
        for breed_info in sorted(breeds, key=lambda x: x["confidence"], reverse=True):
            if breed_info["breed"] not in seen_breeds:
                seen_breeds.add(breed_info["breed"])
                unique_breeds.append(breed_info)

        return unique_breeds[:3]  # Return top 3

    def _estimate_age(self, vision_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
        """Estimate age category from visual features."""
        labels = vision_data.get("labels", [])

        age_scores = {
            "baby": 0.0,
            "young": 0.0,
            "adult": 0.0,
            "senior": 0.0
        }

        for label in labels:
            description = label["description"].lower()
            score = label["score"]

            # Check against age indicators
            for age_category, indicators in self.AGE_INDICATORS.items():
                for indicator in indicators:
                    if indicator in description:
                        age_scores[age_category] += score

        # Get category with highest score
        if max(age_scores.values()) > 0:
            estimated_age = max(age_scores, key=age_scores.get)
            confidence = age_scores[estimated_age]
            return estimated_age, round(confidence, 3)

        return None, None

    def _extract_colors(self, vision_data: Dict[str, Any]) -> List[str]:
        """Extract dominant coat colors."""
        colors_data = vision_data.get("colors", [])

        if not colors_data:
            return []

        # Map RGB to color names
        color_names = []
        for color_info in colors_data[:3]:  # Top 3 colors
            rgb = color_info["color"]
            color_name = self._rgb_to_color_name(
                rgb.get("red", 0),
                rgb.get("green", 0),
                rgb.get("blue", 0)
            )
            if color_name and color_name not in color_names:
                color_names.append(color_name)

        return color_names

    def _rgb_to_color_name(self, r: int, g: int, b: int) -> Optional[str]:
        """Convert RGB values to common color name."""
        # Simplified color mapping
        if r > 200 and g > 200 and b > 200:
            return "white"
        elif r < 50 and g < 50 and b < 50:
            return "black"
        elif r > 150 and g < 100 and b < 100:
            return "red"
        elif r < 100 and g > 150 and b < 100:
            return "green"
        elif r < 100 and g < 100 and b > 150:
            return "blue"
        elif r > 150 and g > 150 and b < 100:
            return "yellow"
        elif r > 150 and g > 100 and b < 80:
            return "orange"
        elif r > 100 and g > 50 and b < 50:
            return "brown"
        elif r > 150 and g > 150 and b > 150:
            return "gray"
        else:
            return "mixed"

    def _detect_emotional_state(self, vision_data: Dict[str, Any]) -> Optional[str]:
        """Detect emotional state from labels and objects."""
        labels = vision_data.get("labels", [])

        emotional_keywords = {
            "friendly": ["happy", "smile", "friendly", "playful", "joy"],
            "fearful": ["scared", "afraid", "timid", "hiding"],
            "energetic": ["active", "energetic", "playful", "running", "jumping"],
            "calm": ["calm", "relaxed", "peaceful", "sleeping", "resting"]
        }

        emotion_scores = {emotion: 0.0 for emotion in emotional_keywords.keys()}

        for label in labels:
            description = label["description"].lower()
            score = label["score"]

            for emotion, keywords in emotional_keywords.items():
                for keyword in keywords:
                    if keyword in description:
                        emotion_scores[emotion] += score

        # Return emotion with highest score
        if max(emotion_scores.values()) > 0.3:  # Threshold
            return max(emotion_scores, key=emotion_scores.get)

        return None

    def _detect_health_markers(self, vision_data: Dict[str, Any]) -> List[str]:
        """Detect visible health indicators."""
        labels = vision_data.get("labels", [])
        markers = []

        health_keywords = {
            "healthy coat": ["shiny", "glossy", "healthy", "groomed"],
            "alert": ["alert", "attentive", "bright"],
            "good body condition": ["fit", "healthy", "strong"],
            "needs grooming": ["matted", "dirty", "unkempt"],
            "thin": ["thin", "skinny", "underweight"],
        }

        for label in labels:
            description = label["description"].lower()
            score = label["score"]

            for marker, keywords in health_keywords.items():
                for keyword in keywords:
                    if keyword in description and score > 0.5:
                        if marker not in markers:
                            markers.append(marker)
                        break

        return markers

    def classify_breed(
        self,
        image_labels: List[Dict[str, Any]],
        pet_type: str = "dog"
    ) -> Tuple[Optional[str], float]:
        """
        Classify breed from image labels.

        Args:
            image_labels: List of image labels from vision API
            pet_type: Type of pet (dog, cat, etc.)

        Returns:
            Tuple of (breed_name, confidence)
        """
        breed_list = self.DOG_BREEDS if pet_type == "dog" else self.CAT_BREEDS

        best_match = None
        best_score = 0.0

        for label in image_labels:
            description = label.get("description", "")
            score = label.get("score", 0.0)

            for breed in breed_list:
                if breed.lower() in description.lower():
                    if score > best_score:
                        best_match = breed
                        best_score = score

        return best_match, round(best_score, 3)

    def enhance_pet_data(
        self,
        pet_data: Dict[str, Any],
        vision_analysis: VisionAnalysis
    ) -> Dict[str, Any]:
        """
        Enhance pet data with vision analysis results.

        Args:
            pet_data: Original pet data dictionary
            vision_analysis: Vision analysis results

        Returns:
            Enhanced pet data dictionary
        """
        enhanced = pet_data.copy()

        # Add or update breed if detected with high confidence
        if vision_analysis.primary_breed and vision_analysis.breed_confidence > 0.7:
            if not enhanced.get("breed"):
                enhanced["breed"] = vision_analysis.primary_breed

        # Add or update age if estimated with reasonable confidence
        if vision_analysis.estimated_age and vision_analysis.age_confidence > 0.5:
            if not enhanced.get("age"):
                enhanced["age"] = vision_analysis.estimated_age

        # Add color information if available
        if vision_analysis.coat_color:
            enhanced["color"] = vision_analysis.coat_color[0]  # Primary color

        # Add vision analysis to pet data
        enhanced["vision_analysis"] = vision_analysis.dict()

        return enhanced
