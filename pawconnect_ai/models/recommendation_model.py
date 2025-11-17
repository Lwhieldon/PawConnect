"""
Recommendation model for pet matching.
Uses a hybrid approach combining collaborative filtering and content-based recommendations.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from loguru import logger

from ..schemas.pet_data import Pet
from ..schemas.user_profile import UserProfile
from ..utils.helpers import calculate_urgency_score


class RecommendationModel:
    """
    ML model for generating pet recommendations.
    Uses feature engineering and scoring algorithms.
    """

    def __init__(self, model_version: str = "1.0"):
        """Initialize the recommendation model."""
        self.model_version = model_version
        self.weights = {
            "lifestyle": 0.40,
            "personality": 0.30,
            "practical": 0.20,
            "urgency": 0.10,
        }

    def extract_user_features(self, user: UserProfile) -> Dict[str, Any]:
        """
        Extract feature vector from user profile.

        Args:
            user: User profile

        Returns:
            Dictionary of user features
        """
        prefs = user.preferences

        features = {
            # Demographic features
            "has_children": 1 if prefs.has_children else 0,
            "has_other_pets": 1 if prefs.has_other_pets else 0,
            "has_yard": 1 if prefs.has_yard else 0,
            "yard_fenced": 1 if prefs.yard_fenced else 0,

            # Home type encoding
            "home_is_house": 1 if prefs.home_type.value == "house" else 0,
            "home_is_apartment": 1 if prefs.home_type.value == "apartment" else 0,

            # Experience level (0-3 scale)
            "experience_level": {
                "first_time": 0,
                "some_experience": 1,
                "experienced": 2,
                "expert": 3,
            }.get(prefs.experience_level.value, 1),

            # Time availability
            "hours_alone": prefs.hours_alone,
            "exercise_commitment": prefs.exercise_commitment,

            # Activity level (0-2 scale)
            "activity_level": {
                "low": 0,
                "moderate": 1,
                "high": 2,
            }.get(prefs.activity_level, 1),

            # Requirements
            "needs_good_with_children": 1 if prefs.good_with_children else 0,
            "needs_good_with_dogs": 1 if prefs.good_with_dogs else 0,
            "needs_good_with_cats": 1 if prefs.good_with_cats else 0,
            "needs_house_trained": 1 if prefs.house_trained else 0,
            "needs_hypoallergenic": 1 if prefs.hypoallergenic else 0,
            "special_needs_ok": 1 if prefs.special_needs_ok else 0,
        }

        return features

    def extract_pet_features(self, pet: Pet) -> Dict[str, Any]:
        """
        Extract feature vector from pet profile.

        Args:
            pet: Pet profile

        Returns:
            Dictionary of pet features
        """
        features = {
            # Size encoding (0-3 scale)
            "size": {
                "small": 0,
                "medium": 1,
                "large": 2,
                "extra_large": 3,
            }.get(pet.size.value, 1),

            # Age encoding (0-3 scale)
            "age": {
                "baby": 0,
                "young": 1,
                "adult": 2,
                "senior": 3,
            }.get(pet.age.value, 2),

            # Energy level (0-2 scale)
            "energy_level": {
                "low": 0,
                "moderate": 1,
                "high": 2,
            }.get(pet.attributes.energy_level, 1),

            # Behavioral attributes
            "good_with_children": self._to_score(pet.attributes.good_with_children),
            "good_with_dogs": self._to_score(pet.attributes.good_with_dogs),
            "good_with_cats": self._to_score(pet.attributes.good_with_cats),
            "house_trained": 1 if pet.attributes.house_trained else 0,
            "special_needs": 1 if pet.attributes.special_needs else 0,
            "spayed_neutered": 1 if pet.attributes.spayed_neutered else 0,

            # Urgency
            "days_in_shelter": pet.days_in_shelter or 0,
            "is_urgent": 1 if pet.is_urgent else 0,
            "urgency_score": calculate_urgency_score(pet),
        }

        return features

    def _to_score(self, value: Any) -> float:
        """Convert boolean/None to score."""
        if value is True:
            return 1.0
        elif value is False:
            return -1.0
        else:
            return 0.0  # Unknown

    def calculate_lifestyle_score(
        self, user_features: Dict[str, Any], pet_features: Dict[str, Any]
    ) -> float:
        """
        Calculate lifestyle compatibility score.

        Args:
            user_features: User feature dictionary
            pet_features: Pet feature dictionary

        Returns:
            Lifestyle compatibility score (0-1)
        """
        score = 0.0
        total_weight = 0.0

        # Home type and size compatibility
        if user_features["home_is_apartment"]:
            # Penalize large pets in apartments
            if pet_features["size"] <= 1:  # Small or medium
                score += 1.0
                total_weight += 1.0
            else:
                score += 0.3
                total_weight += 1.0

        # Yard compatibility for dogs
        if user_features["has_yard"]:
            if pet_features["size"] >= 2:  # Large or extra large
                score += 1.0
                total_weight += 1.0
        else:
            if pet_features["size"] >= 2:
                score += 0.5  # Potential concern
                total_weight += 1.0

        # Time availability vs energy level
        hours_alone = user_features["hours_alone"]
        energy_level = pet_features["energy_level"]

        if hours_alone <= 4:
            # Good for high energy pets
            if energy_level >= 1:
                score += 0.9
            else:
                score += 0.7
            total_weight += 1.0
        elif hours_alone <= 8:
            # Better for moderate energy
            if energy_level == 1:
                score += 1.0
            elif energy_level == 0:
                score += 0.8
            else:
                score += 0.5
            total_weight += 1.0
        else:
            # Better for low energy pets
            if energy_level == 0:
                score += 1.0
            else:
                score += 0.4
            total_weight += 1.0

        # Exercise commitment vs energy level
        exercise = user_features["exercise_commitment"]
        if exercise >= 60 and energy_level >= 1:
            score += 1.0
            total_weight += 1.0
        elif exercise <= 30 and energy_level == 0:
            score += 1.0
            total_weight += 1.0
        elif abs(exercise - 30) < 15 and energy_level == 1:
            score += 1.0
            total_weight += 1.0
        else:
            score += 0.6
            total_weight += 1.0

        return score / total_weight if total_weight > 0 else 0.5

    def calculate_personality_score(
        self, user_features: Dict[str, Any], pet_features: Dict[str, Any]
    ) -> float:
        """
        Calculate personality compatibility score.

        Args:
            user_features: User feature dictionary
            pet_features: Pet feature dictionary

        Returns:
            Personality compatibility score (0-1)
        """
        score = 0.0
        total_checks = 0

        # Children compatibility
        if user_features["has_children"]:
            total_checks += 1
            if pet_features["good_with_children"] > 0:
                score += 1.0
            elif pet_features["good_with_children"] == 0:
                score += 0.5  # Unknown
            # Negative score handled by returning low score

        # Other pets compatibility
        if user_features["has_other_pets"]:
            # Simplified - in real implementation would check specific pet types
            total_checks += 2
            if pet_features["good_with_dogs"] >= 0:
                score += 0.5 + (pet_features["good_with_dogs"] * 0.5)
            if pet_features["good_with_cats"] >= 0:
                score += 0.5 + (pet_features["good_with_cats"] * 0.5)

        # Activity level match
        total_checks += 1
        user_activity = user_features["activity_level"]
        pet_energy = pet_features["energy_level"]
        activity_diff = abs(user_activity - pet_energy)

        if activity_diff == 0:
            score += 1.0  # Perfect match
        elif activity_diff == 1:
            score += 0.6  # Close match
        else:
            score += 0.3  # Mismatch

        # Experience level vs pet needs
        total_checks += 1
        experience = user_features["experience_level"]

        if pet_features["special_needs"]:
            # Special needs pets need experienced owners
            if experience >= 2:
                score += 1.0
            elif experience == 1:
                score += 0.5
            else:
                score += 0.2
        elif pet_features["energy_level"] >= 2:
            # High energy pets benefit from experience
            if experience >= 1:
                score += 1.0
            else:
                score += 0.6
        else:
            # Easy pets good for beginners
            score += 1.0

        return score / total_checks if total_checks > 0 else 0.5

    def calculate_practical_score(
        self, user_features: Dict[str, Any], pet_features: Dict[str, Any]
    ) -> float:
        """
        Calculate practical constraints score.

        Args:
            user_features: User feature dictionary
            pet_features: Pet feature dictionary

        Returns:
            Practical compatibility score (0-1)
        """
        score = 1.0  # Start with perfect score, deduct for violations
        violations = []

        # Hard requirements
        if user_features["needs_good_with_children"]:
            if pet_features["good_with_children"] < 0:
                score -= 0.5
                violations.append("Not good with children")
            elif pet_features["good_with_children"] == 0:
                score -= 0.2  # Unknown is risky

        if user_features["needs_good_with_dogs"]:
            if pet_features["good_with_dogs"] < 0:
                score -= 0.5
                violations.append("Not good with dogs")
            elif pet_features["good_with_dogs"] == 0:
                score -= 0.2

        if user_features["needs_good_with_cats"]:
            if pet_features["good_with_cats"] < 0:
                score -= 0.5
                violations.append("Not good with cats")
            elif pet_features["good_with_cats"] == 0:
                score -= 0.2

        if user_features["needs_house_trained"]:
            if not pet_features["house_trained"]:
                score -= 0.3
                violations.append("Not house trained")

        # Special needs matching
        if pet_features["special_needs"]:
            if not user_features["special_needs_ok"]:
                score -= 0.4
                violations.append("Has special needs")

        # Age preferences (seniors need committed owners)
        if pet_features["age"] == 3:  # Senior
            if user_features["experience_level"] == 0:
                score -= 0.2

        return max(score, 0.0)  # Can't be negative

    def calculate_compatibility_score(
        self, user: UserProfile, pet: Pet
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate overall compatibility score between user and pet.

        Args:
            user: User profile
            pet: Pet profile

        Returns:
            Tuple of (overall_score, score_components)
        """
        try:
            # Extract features
            user_features = self.extract_user_features(user)
            pet_features = self.extract_pet_features(pet)

            # Calculate component scores
            lifestyle_score = self.calculate_lifestyle_score(user_features, pet_features)
            personality_score = self.calculate_personality_score(user_features, pet_features)
            practical_score = self.calculate_practical_score(user_features, pet_features)

            # Calculate urgency boost
            urgency_boost = pet_features["urgency_score"]

            # Calculate weighted overall score
            overall_score = (
                lifestyle_score * self.weights["lifestyle"]
                + personality_score * self.weights["personality"]
                + practical_score * self.weights["practical"]
                + urgency_boost * self.weights["urgency"]
            )

            scores = {
                "overall_score": round(overall_score, 3),
                "lifestyle_score": round(lifestyle_score, 3),
                "personality_score": round(personality_score, 3),
                "practical_score": round(practical_score, 3),
                "urgency_boost": round(urgency_boost, 3),
            }

            return overall_score, scores

        except Exception as e:
            logger.error(f"Error calculating compatibility score: {e}")
            # Return neutral score on error
            return 0.5, {
                "overall_score": 0.5,
                "lifestyle_score": 0.5,
                "personality_score": 0.5,
                "practical_score": 0.5,
                "urgency_boost": 0.0,
            }

    def rank_pets(
        self, user: UserProfile, pets: List[Pet], top_k: int = 10
    ) -> List[Tuple[Pet, Dict[str, float]]]:
        """
        Rank a list of pets for a user.

        Args:
            user: User profile
            pets: List of pet profiles
            top_k: Number of top results to return

        Returns:
            List of (pet, scores) tuples, sorted by overall score
        """
        scored_pets = []

        for pet in pets:
            overall_score, scores = self.calculate_compatibility_score(user, pet)
            scored_pets.append((pet, scores))

        # Sort by overall score descending
        scored_pets.sort(key=lambda x: x[1]["overall_score"], reverse=True)

        return scored_pets[:top_k]
