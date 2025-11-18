"""
Evaluation script for the PawConnect recommendation model.
Measures recommendation quality using various metrics.
"""

import json
import asyncio
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
from loguru import logger

from pawconnect_ai.agent import PawConnectMainAgent
from pawconnect_ai.schemas.user_profile import UserProfile
from pawconnect_ai.schemas.pet_data import PetMatch


class RecommendationEvaluator:
    """Evaluates recommendation model performance."""

    def __init__(self):
        """Initialize the evaluator."""
        self.agent = PawConnectMainAgent()
        self.metrics = {
            "precision_at_5": [],
            "recall_at_10": [],
            "mrr": [],  # Mean Reciprocal Rank
            "ndcg": []  # Normalized Discounted Cumulative Gain
        }

    async def load_test_cases(self, file_path: str) -> List[Dict[str, Any]]:
        """Load test cases from JSON file."""
        logger.info(f"Loading test cases from {file_path}")

        path = Path(file_path)
        if not path.exists():
            logger.error(f"Test cases file not found: {file_path}")
            return []

        with open(path, 'r') as f:
            test_cases = json.load(f)

        logger.info(f"Loaded {len(test_cases)} test cases")
        return test_cases

    async def evaluate_single_case(
        self,
        test_case: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Evaluate a single test case.

        Args:
            test_case: Test case with user profile and ground truth matches

        Returns:
            Dictionary of metric scores for this case
        """
        user_data = test_case["user_profile"]
        ground_truth_pet_ids = set(test_case["relevant_pet_ids"])

        # Create user profile
        user_profile = UserProfile(**user_data)

        # Get recommendations
        try:
            recommendations = await self.agent.find_matches(
                user_profile=user_profile,
                top_k=10
            )
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return {
                "precision_at_5": 0.0,
                "recall_at_10": 0.0,
                "mrr": 0.0,
                "ndcg": 0.0
            }

        # Extract recommended pet IDs
        recommended_pet_ids = [match.pet.pet_id for match in recommendations]

        # Calculate metrics
        metrics = {
            "precision_at_5": self._calculate_precision_at_k(
                recommended_pet_ids[:5],
                ground_truth_pet_ids
            ),
            "recall_at_10": self._calculate_recall_at_k(
                recommended_pet_ids[:10],
                ground_truth_pet_ids
            ),
            "mrr": self._calculate_mrr(
                recommended_pet_ids,
                ground_truth_pet_ids
            ),
            "ndcg": self._calculate_ndcg(
                recommended_pet_ids,
                ground_truth_pet_ids,
                k=10
            )
        }

        return metrics

    def _calculate_precision_at_k(
        self,
        recommended: List[str],
        relevant: set
    ) -> float:
        """
        Calculate Precision@K.

        Precision@K = (# of recommended items @K that are relevant) / K
        """
        if not recommended:
            return 0.0

        relevant_in_top_k = sum(1 for pet_id in recommended if pet_id in relevant)
        return relevant_in_top_k / len(recommended)

    def _calculate_recall_at_k(
        self,
        recommended: List[str],
        relevant: set
    ) -> float:
        """
        Calculate Recall@K.

        Recall@K = (# of relevant items found @K) / (total # of relevant items)
        """
        if not relevant:
            return 0.0

        relevant_in_top_k = sum(1 for pet_id in recommended if pet_id in relevant)
        return relevant_in_top_k / len(relevant)

    def _calculate_mrr(
        self,
        recommended: List[str],
        relevant: set
    ) -> float:
        """
        Calculate Mean Reciprocal Rank.

        MRR = 1 / rank of first relevant item
        """
        for rank, pet_id in enumerate(recommended, 1):
            if pet_id in relevant:
                return 1.0 / rank
        return 0.0

    def _calculate_ndcg(
        self,
        recommended: List[str],
        relevant: set,
        k: int = 10
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain@K.

        DCG = sum(relevance_i / log2(i + 1)) for i in positions
        NDCG = DCG / IDCG (ideal DCG)
        """
        # Calculate DCG
        dcg = 0.0
        for i, pet_id in enumerate(recommended[:k], 1):
            relevance = 1.0 if pet_id in relevant else 0.0
            dcg += relevance / np.log2(i + 1)

        # Calculate IDCG (ideal DCG if all relevant items were at top)
        ideal_relevances = [1.0] * min(len(relevant), k)
        idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))

        # Return NDCG
        return dcg / idcg if idcg > 0 else 0.0

    async def evaluate_all(
        self,
        test_cases_file: str = "eval/test_cases.json"
    ) -> Dict[str, float]:
        """
        Evaluate all test cases and compute aggregate metrics.

        Args:
            test_cases_file: Path to test cases JSON file

        Returns:
            Dictionary of average metric scores
        """
        logger.info("Starting recommendation evaluation")

        # Load test cases
        test_cases = await self.load_test_cases(test_cases_file)

        if not test_cases:
            logger.error("No test cases loaded")
            return {}

        # Evaluate each case
        all_metrics = {
            "precision_at_5": [],
            "recall_at_10": [],
            "mrr": [],
            "ndcg": []
        }

        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Evaluating case {i}/{len(test_cases)}")

            metrics = await self.evaluate_single_case(test_case)

            for metric_name, value in metrics.items():
                all_metrics[metric_name].append(value)

        # Calculate averages
        avg_metrics = {
            metric_name: np.mean(values) if values else 0.0
            for metric_name, values in all_metrics.items()
        }

        # Log results
        logger.info("Evaluation Results:")
        logger.info(f"  Precision@5: {avg_metrics['precision_at_5']:.4f}")
        logger.info(f"  Recall@10: {avg_metrics['recall_at_10']:.4f}")
        logger.info(f"  MRR: {avg_metrics['mrr']:.4f}")
        logger.info(f"  NDCG@10: {avg_metrics['ndcg']:.4f}")

        return avg_metrics

    def save_results(
        self,
        metrics: Dict[str, float],
        output_file: str = "eval/evaluation_results.json"
    ):
        """Save evaluation results to file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        logger.info(f"Results saved to {output_file}")


async def main():
    """Run evaluation."""
    evaluator = RecommendationEvaluator()

    # Run evaluation
    metrics = await evaluator.evaluate_all()

    # Save results
    evaluator.save_results(metrics)

    # Print summary
    print("\n" + "="*60)
    print("RECOMMENDATION MODEL EVALUATION RESULTS")
    print("="*60)
    print(f"Precision@5:  {metrics['precision_at_5']:.4f}")
    print(f"Recall@10:    {metrics['recall_at_10']:.4f}")
    print(f"MRR:          {metrics['mrr']:.4f}")
    print(f"NDCG@10:      {metrics['ndcg']:.4f}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
