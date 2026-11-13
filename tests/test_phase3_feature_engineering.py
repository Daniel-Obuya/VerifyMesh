"""
VerifyMesh — Phase 3 Feature Engineering & Domain Decoupling Test Suite
========================================================================

Validates the redesigned task-specific feature engineering module:
- One-topic task evaluation
- Multi-topic task evaluation with normalized weights
- Handling of missing required assessments
- Exclusion of unrelated historical assessments
- Negative competency margin handling & distinct weakness metrics
- All-positive competency margins
- Competency exactly at minimum threshold (zero margin)
- Alex Morgan Task 4 exact feature vector recalculation
- Backward compatibility for callers without explicit topic requirements
"""

import math
import os
import sys
import unittest
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.stage2_feature_engineering import (
    resolve_domain_weights,
    resolve_subskill_minimums,
    build_complete_stage2_feature_dict,
    STAGE2_V2_FEATURES,
    LEGACY_28_FEATURES,
)


class TestPhase3FeatureEngineering(unittest.TestCase):

    def test_01_one_topic_task_normalization_and_margins(self):
        """Test one-topic task: weights normalize to 1.0, margin is single-topic alone."""
        # Technical Support task requiring only Customer Communication
        raw_input = {
            "task_category": "Customer Support Escalations",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 75.0,
            "task_min_comm": 75.0,
            "required_topic_ids": [3],  # Topic 3: comm
            "applicant_relevant_exp": 40.0,
            "applicant_comm_score": 100.0,
            "applicant_assessment_score": 100.0,
            # Unrelated historical score that must NOT enter calculations
            "applicant_prod_score": 20.0,
            "applicant_sales_score": 30.0,
            "applicant_cs_score": 40.0,
        }

        features = build_complete_stage2_feature_dict(raw_input)

        # Single topic margin: 100 - 75 = +25.0
        self.assertEqual(features["min_skill_margin"], 25.0)
        self.assertEqual(features["weighted_skill_margin"], 25.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)
        self.assertEqual(features["deficit_competencies_count"], 0.0)
        self.assertEqual(features["deficit_competencies_ratio"], 0.0)

        # Domain weights normalized to 1.0 for comm
        weights = resolve_domain_weights("Customer Support Escalations", required_competencies=["comm"])
        self.assertEqual(weights["comm"], 1.0)
        self.assertEqual(weights["prod"], 0.0)
        self.assertEqual(weights["sales"], 0.0)
        self.assertEqual(weights["cs"], 0.0)

    def test_02_multi_topic_task_normalized_weights(self):
        """Test multi-topic task: weights normalize to sum 1.0 across only required topics."""
        # Task requires Product Knowledge (prod) and Customer Service (cs)
        raw_weights = resolve_domain_weights(
            "Customer Support Escalations", required_competencies=["prod", "cs"]
        )
        self.assertAlmostEqual(sum(raw_weights.values()), 1.0)
        self.assertEqual(raw_weights["comm"], 0.0)
        self.assertEqual(raw_weights["sales"], 0.0)
        self.assertGreater(raw_weights["prod"], 0.0)
        self.assertGreater(raw_weights["cs"], 0.0)

        # Base weights in Customer Support Escalations: prod=0.20, cs=0.45 (sum=0.65)
        # Normalized: prod = 0.20/0.65 = 0.3077, cs = 0.45/0.65 = 0.6923
        self.assertAlmostEqual(raw_weights["prod"], 0.20 / 0.65, places=4)
        self.assertAlmostEqual(raw_weights["cs"], 0.45 / 0.65, places=4)

        raw_input = {
            "task_category": "Customer Support Escalations",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 70.0,
            "task_min_prod": 70.0,
            "task_min_cs": 70.0,
            "required_topic_ids": [1, 4],  # prod and cs
            "applicant_relevant_exp": 24.0,
            "applicant_assessment_score": 80.0,
            "applicant_prod_score": 80.0,  # gap = +10.0
            "applicant_cs_score": 90.0,    # gap = +20.0
            # Unrelated topics
            "applicant_comm_score": 10.0,
            "applicant_sales_score": 10.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        # Min margin among required topics is +10.0 (prod gap)
        self.assertEqual(features["min_skill_margin"], 10.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)

        # Weighted margin = (0.20/0.65)*10 + (0.45/0.65)*20 = 3.0769 + 13.8462 = 16.9231
        expected_weighted = (0.20 / 0.65) * 10.0 + (0.45 / 0.65) * 20.0
        self.assertAlmostEqual(features["weighted_skill_margin"], round(expected_weighted, 4), places=2)

    def test_03_unrelated_historical_assessments_completely_excluded(self):
        """Test that an unrelated low score on a non-required topic never penalizes candidate."""
        raw_input = {
            "task_category": "Enterprise Sales",
            "difficulty_tier": 1.0,
            "task_min_exp": 6.0,
            "task_min_assessment": 70.0,
            "task_min_sales": 70.0,
            "required_competencies": ["sales"],
            "applicant_relevant_exp": 18.0,
            "applicant_sales_score": 85.0,  # gap = +15.0
            "applicant_assessment_score": 85.0,
            # Historical low scores in completely different domains
            "applicant_prod_score": 15.0,
            "applicant_comm_score": 25.0,
            "applicant_cs_score": 20.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        self.assertEqual(features["min_skill_margin"], 15.0)
        self.assertEqual(features["weighted_skill_margin"], 15.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)
        self.assertEqual(features["deficit_competencies_count"], 0.0)
        self.assertEqual(features["deficit_competencies_ratio"], 0.0)

    def test_04_applicant_with_negative_required_competency_margin(self):
        """Test that a deficit in a REQUIRED competency is faithfully recorded."""
        raw_input = {
            "task_category": "Customer Support Escalations",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 75.0,
            "task_min_comm": 75.0,
            "required_competencies": ["comm"],
            "applicant_relevant_exp": 12.0,
            "applicant_comm_score": 60.0,  # deficit: 60 - 75 = -15.0
            "applicant_assessment_score": 60.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        self.assertEqual(features["min_skill_margin"], -15.0)
        self.assertEqual(features["weakest_link_deficit"], -15.0)
        self.assertEqual(features["weighted_skill_margin"], -15.0)
        self.assertEqual(features["deficit_competencies_count"], 1.0)
        self.assertEqual(features["deficit_competencies_ratio"], 1.0)

    def test_05_applicant_with_all_positive_required_margins(self):
        """Test candidate exceeding all requirements: zero deficit, positive margins."""
        raw_input = {
            "task_category": "Enterprise Sales",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 70.0,
            "task_min_sales": 70.0,
            "task_min_comm": 70.0,
            "required_competencies": ["sales", "comm"],
            "applicant_relevant_exp": 24.0,
            "applicant_sales_score": 90.0,  # gap = +20.0
            "applicant_comm_score": 85.0,   # gap = +15.0
            "applicant_assessment_score": 88.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        self.assertEqual(features["min_skill_margin"], 15.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)
        self.assertGreater(features["weighted_skill_margin"], 15.0)
        self.assertEqual(features["deficit_competencies_count"], 0.0)
        self.assertEqual(features["deficit_competencies_ratio"], 0.0)

    def test_06_applicant_competency_exactly_at_minimum(self):
        """Test candidate scoring exactly at the minimum required score: 0.0 margin, 0.0 deficit."""
        raw_input = {
            "task_category": "Customer Support Escalations",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 75.0,
            "task_min_comm": 75.0,
            "required_competencies": ["comm"],
            "applicant_relevant_exp": 12.0,
            "applicant_comm_score": 75.0,  # margin = 0.0
            "applicant_assessment_score": 75.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        self.assertEqual(features["min_skill_margin"], 0.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)
        self.assertEqual(features["weighted_skill_margin"], 0.0)
        self.assertEqual(features["deficit_competencies_count"], 0.0)
        self.assertEqual(features["deficit_competencies_ratio"], 0.0)

    def test_07_alex_morgan_exact_task4_recalculation(self):
        """Test Alex Morgan's exact recalculation on Task 4 with authoritative DB parameters."""
        raw_input = {
            "task_category": "Customer Support Escalations",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 75.0,
            "task_min_comm": 75.0,
            "required_topic_ids": [3],
            "applicant_relevant_exp": 40.0,
            "applicant_comm_score": 100.0,
            "applicant_assessment_score": 100.0,
            "applicant_cert_count": 2.0,
            "applicant_has_cs_cert": 1.0,
            # Historical unrelated scores
            "applicant_prod_score": 20.0,
            "applicant_sales_score": 74.0,
            "applicant_cs_score": 100.0,
        }
        features = build_complete_stage2_feature_dict(raw_input)

        # Expected calculations:
        # Communication margin = 100 - 75 = +25.0
        # Weighted margin = 1.0 * (+25.0) = +25.0
        # Min margin = +25.0 (NOT -50.0!)
        # Weakest link deficit = 0.0 (NOT -50.0!)
        # Experience surplus = 40 - 12 = 28 months -> tanh(28/12) = 0.9814
        self.assertEqual(features["min_skill_margin"], 25.0)
        self.assertEqual(features["weighted_skill_margin"], 25.0)
        self.assertEqual(features["weakest_link_deficit"], 0.0)
        self.assertEqual(features["deficit_competencies_count"], 0.0)
        self.assertEqual(features["deficit_competencies_ratio"], 0.0)
        self.assertAlmostEqual(features["exp_surplus_tanh"], math.tanh(28.0 / 12.0), places=4)
        self.assertEqual(features["difficulty_tier"], 2.0)

    def test_08_backward_compatibility_when_required_topics_unspecified(self):
        """Ensure full backward compatibility for legacy callers not passing required_topic_ids."""
        legacy_input = {
            "task_category": "Enterprise Sales",
            "difficulty_tier": 2.0,
            "task_min_exp": 12.0,
            "task_min_assessment": 70.0,
            "task_min_comm": 70.0,
            "task_min_prod": 70.0,
            "task_min_sales": 70.0,
            "task_min_cs": 70.0,
            "applicant_relevant_exp": 24.0,
            "applicant_comm_score": 80.0,
            "applicant_prod_score": 75.0,
            "applicant_sales_score": 85.0,
            "applicant_cs_score": 70.0,
            "applicant_assessment_score": 80.0,
        }
        features = build_complete_stage2_feature_dict(legacy_input)

        # Check all 5 Stage 2 v2 features exist
        for k in STAGE2_V2_FEATURES:
            self.assertIn(k, features)
            self.assertIsInstance(features[k], (int, float))

        # Check all 28 legacy features exist
        for k in LEGACY_28_FEATURES:
            self.assertIn(k, features)
            self.assertIsInstance(features[k], (int, float))

        # Check distinct deficit representations exist
        self.assertIn("deficit_competencies_count", features)
        self.assertIn("deficit_competencies_ratio", features)


if __name__ == "__main__":
    unittest.main()

