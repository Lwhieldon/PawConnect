"""
Recommendation Agent - Matching Intelligence
Ranks and filters pets using machine learning models.
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from ..config import settings
from ..schemas.pet_data import Pet, PetMatch
from ..schemas.user_profile import UserProfile
from ..models.recommendation_model import RecommendationModel
from ..utils.helpers import format_match_explanation


class RecommendationAgent:
    """
    Specialized agent for intelligent pet matching and ranking.
    Uses ML model to score compatibility between users and pets.
    """

    def __init__(self):
        """Initialize the recommendation agent."""
        self.model = RecommendationModel()
        self.min_score = settings.recommendation_min_score
        self.top_k = settings.recommendation_top_k

    def generate_recommendations(
        self,
        user: UserProfile,
        pets: List[Pet],
        top_k: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> List[PetMatch]:
        """
        Generate personalized pet recommendations for a user.

        Args:
            user: User profile
            pets: List of candidate pets
            top_k: Number of top recommendations (default from settings)
            min_score: Minimum score threshold (default from settings)

        Returns:
            List of PetMatch objects with scores and explanations
        """
        top_k = top_k or self.top_k
        min_score = min_score or self.min_score

        try:
            logger.info(f"Generating recommendations for user {user.user_id} from {len(pets)} pets")

            # Use model to rank pets
            ranked_pets = self.model.rank_pets(user, pets, top_k=len(pets))

            # Filter by minimum score and create PetMatch objects
            matches = []
            rank = 1

            for pet, scores in ranked_pets:
                if scores["overall_score"] < min_score:
                    continue

                # Generate explanation
                explanation, key_factors, concerns = format_match_explanation(
                    pet, user, scores
                )

                # Create PetMatch
                match = PetMatch(
                    pet=pet,
                    overall_score=scores["overall_score"],
                    lifestyle_score=scores["lifestyle_score"],
                    personality_score=scores["personality_score"],
                    practical_score=scores["practical_score"],
                    urgency_boost=scores["urgency_boost"],
                    match_explanation=explanation,
                    key_factors=key_factors,
                    potential_concerns=concerns,
                    rank=rank,
                    model_version=self.model.model_version
                )

                matches.append(match)
                rank += 1

                if len(matches) >= top_k:
                    break

            logger.info(f"Generated {len(matches)} recommendations (scores >= {min_score})")
            return matches

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def score_single_pet(
        self,
        user: UserProfile,
        pet: Pet
    ) -> PetMatch:
        """
        Score a single pet for a user.

        Args:
            user: User profile
            pet: Pet to score

        Returns:
            PetMatch object with scores
        """
        try:
            overall_score, scores = self.model.calculate_compatibility_score(user, pet)

            explanation, key_factors, concerns = format_match_explanation(
                pet, user, scores
            )

            return PetMatch(
                pet=pet,
                overall_score=scores["overall_score"],
                lifestyle_score=scores["lifestyle_score"],
                personality_score=scores["personality_score"],
                practical_score=scores["practical_score"],
                urgency_boost=scores["urgency_boost"],
                match_explanation=explanation,
                key_factors=key_factors,
                potential_concerns=concerns,
                model_version=self.model.model_version
            )

        except Exception as e:
            logger.error(f"Error scoring pet: {e}")
            raise

    def explain_recommendation(self, match: PetMatch) -> Dict[str, Any]:
        """
        Generate detailed explanation of a recommendation.

        Args:
            match: PetMatch object

        Returns:
            Dictionary with detailed explanation components
        """
        return {
            "pet_name": match.pet.name,
            "overall_score": match.overall_score,
            "score_breakdown": {
                "lifestyle_compatibility": {
                    "score": match.lifestyle_score,
                    "weight": "40%",
                    "description": "How well the pet fits your lifestyle and home environment"
                },
                "personality_match": {
                    "score": match.personality_score,
                    "weight": "30%",
                    "description": "Compatibility of pet's personality with your preferences"
                },
                "practical_factors": {
                    "score": match.practical_score,
                    "weight": "20%",
                    "description": "Meeting practical requirements and constraints"
                },
                "urgency": {
                    "score": match.urgency_boost,
                    "weight": "10%",
                    "description": "Priority boost for pets needing urgent placement"
                }
            },
            "explanation": match.match_explanation,
            "strengths": match.key_factors,
            "considerations": match.potential_concerns,
            "recommendation": self._get_recommendation_level(match.overall_score)
        }

    def _get_recommendation_level(self, score: float) -> str:
        """Get recommendation level based on score."""
        if score >= 0.85:
            return "Excellent Match - Highly Recommended"
        elif score >= 0.70:
            return "Great Match - Strongly Recommended"
        elif score >= 0.60:
            return "Good Match - Recommended"
        elif score >= 0.50:
            return "Fair Match - Consider with Caution"
        else:
            return "Poor Match - Not Recommended"

    def calculate_compatibility_score(self, user_profile: UserProfile, pet: Pet) -> float:
        """
        Calculate compatibility score between a user and a pet.

        Args:
            user_profile: User profile
            pet: Pet to score

        Returns:
            Compatibility score (0-1)
        """
        overall_score, _ = self.model.calculate_compatibility_score(user_profile, pet)
        return overall_score

    def rank_pets(self, user_profile: UserProfile, pets: List[Pet]) -> List[PetMatch]:
        """
        Rank pets by compatibility with user.

        Args:
            user_profile: User profile
            pets: List of pets to rank

        Returns:
            List of PetMatch objects sorted by score
        """
        ranked_tuples = self.model.rank_pets(user_profile, pets, top_k=len(pets))

        # Convert tuples to PetMatch objects
        matches = []
        for rank, (pet, scores) in enumerate(ranked_tuples, start=1):
            # Generate match explanation with key factors and concerns
            explanation, key_factors, concerns = format_match_explanation(pet, user_profile, scores)

            match = PetMatch(
                pet=pet,
                overall_score=scores["overall_score"],
                lifestyle_score=scores.get("lifestyle_score", 0.5),
                personality_score=scores.get("personality_score", 0.5),
                practical_score=scores.get("practical_score", 0.5),
                urgency_boost=scores.get("urgency_boost", 0.0),
                match_explanation=explanation,
                key_factors=key_factors,
                potential_concerns=concerns,
                rank=rank,
                model_version=self.model.model_version
            )
            matches.append(match)

        return matches

    def _filter_by_preferences(self, pets: List[Pet], preferences) -> List[Pet]:
        """
        Filter pets based on user preferences.

        Args:
            pets: List of pets to filter
            preferences: User preferences (UserPreferences object or dict)

        Returns:
            Filtered list of pets
        """
        from ..schemas.user_profile import UserPreferences

        filtered = []

        for pet in pets:
            # Check preferred species
            if isinstance(preferences, UserPreferences):
                # Pydantic model - check pet_type
                if preferences.pet_type and pet.species.value != preferences.pet_type.value:
                    continue

                # Check preferred size
                if preferences.pet_size:
                    if pet.size not in preferences.pet_size:
                        continue

                # Check preferred age
                if preferences.pet_age:
                    if pet.age not in preferences.pet_age:
                        continue

                # Check required attributes
                if preferences.good_with_children and pet.attributes:
                    if not pet.attributes.good_with_children:
                        continue

                # Check compatibility with other pets
                if preferences.has_other_pets and preferences.other_pets and pet.attributes:
                    if "dog" in [p.lower() for p in preferences.other_pets]:
                        if not pet.attributes.good_with_dogs:
                            continue
                    if "cat" in [p.lower() for p in preferences.other_pets]:
                        if not pet.attributes.good_with_cats:
                            continue
            else:
                # Dictionary - old behavior for backward compatibility
                if preferences.get("preferred_species"):
                    if pet.species.value not in preferences["preferred_species"]:
                        continue

                if preferences.get("preferred_size"):
                    if pet.size.value not in preferences["preferred_size"]:
                        continue

                if preferences.get("preferred_age"):
                    if pet.age.value not in preferences["preferred_age"]:
                        continue

                if preferences.get("good_with_children") and pet.attributes:
                    if not pet.attributes.good_with_children:
                        continue

                if preferences.get("good_with_dogs") and pet.attributes:
                    if not pet.attributes.good_with_dogs:
                        continue

                if preferences.get("good_with_cats") and pet.attributes:
                    if not pet.attributes.good_with_cats:
                        continue

            filtered.append(pet)

        return filtered

    def _calculate_lifestyle_score(self, user_profile: UserProfile, pet: Pet) -> float:
        """
        Calculate lifestyle compatibility score.

        Args:
            user_profile: User profile
            pet: Pet to score

        Returns:
            Lifestyle score (0-1)
        """
        score = 0.0
        factors = 0

        # Home environment compatibility
        if user_profile.preferences and pet.attributes:
            # Check energy level match
            user_lifestyle = getattr(user_profile.preferences, "activity_level", "moderate")
            pet_energy = pet.attributes.energy_level or "moderate"

            energy_match = {
                ("high", "high"): 1.0,
                ("high", "moderate"): 0.7,
                ("high", "low"): 0.3,
                ("moderate", "high"): 0.7,
                ("moderate", "moderate"): 1.0,
                ("moderate", "low"): 0.7,
                ("low", "high"): 0.3,
                ("low", "moderate"): 0.7,
                ("low", "low"): 1.0,
            }
            score += energy_match.get((user_lifestyle, pet_energy), 0.5)
            factors += 1

            # Check home type compatibility
            home_type = user_profile.preferences.home_type.value if user_profile.preferences.home_type else "house"
            if home_type == "apartment":
                # Prefer smaller, lower energy pets for apartments
                if pet.size.value in ["small", "medium"] and pet_energy != "high":
                    score += 1.0
                else:
                    score += 0.5
                factors += 1
            elif home_type == "house_with_yard":
                # All pets suitable, but high energy dogs especially good
                score += 1.0
                factors += 1

        return score / factors if factors > 0 else 0.5

    def _calculate_personality_score(self, user_profile: UserProfile, pet: Pet) -> float:
        """
        Calculate personality compatibility score.

        Args:
            user_profile: User profile
            pet: Pet to score

        Returns:
            Personality score (0-1)
        """
        score = 0.0
        factors = 0

        if user_profile.preferences and pet.attributes:
            # Check compatibility with children
            has_children = user_profile.preferences.has_children
            if has_children and pet.attributes.good_with_children is not None:
                score += 1.0 if pet.attributes.good_with_children else 0.0
                factors += 1

            # Check compatibility with other dogs
            has_dogs = False
            if user_profile.preferences.has_other_pets and user_profile.preferences.other_pets:
                has_dogs = "dog" in [p.lower() for p in user_profile.preferences.other_pets]
            if has_dogs and pet.attributes.good_with_dogs is not None:
                score += 1.0 if pet.attributes.good_with_dogs else 0.0
                factors += 1

            # Check compatibility with other cats
            has_cats = False
            if user_profile.preferences.has_other_pets and user_profile.preferences.other_pets:
                has_cats = "cat" in [p.lower() for p in user_profile.preferences.other_pets]
            if has_cats and pet.attributes.good_with_cats is not None:
                score += 1.0 if pet.attributes.good_with_cats else 0.0
                factors += 1

        return score / factors if factors > 0 else 0.5

    def _calculate_urgency_boost(self, pet: Pet) -> float:
        """
        Calculate urgency boost for pets needing urgent placement.

        Args:
            pet: Pet to evaluate

        Returns:
            Urgency boost score (0-0.1)
        """
        boost = 0.0

        # Check if marked as urgent
        if pet.is_urgent:
            boost += 0.05

        # Check days in shelter
        if pet.days_in_shelter:
            if pet.days_in_shelter > 180:  # 6 months
                boost += 0.05
            elif pet.days_in_shelter > 90:  # 3 months
                boost += 0.03
            elif pet.days_in_shelter > 30:  # 1 month
                boost += 0.01

        # Senior pets get urgency boost
        if pet.age.value == "senior":
            boost += 0.02

        # Cap at 0.1 (10%)
        return min(boost, 0.1)
