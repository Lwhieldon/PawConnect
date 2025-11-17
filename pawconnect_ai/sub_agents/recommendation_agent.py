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
