import os
import unittest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

from src.stage2_feature_engineering import STAGE2_V2_FEATURES, LEGACY_28_FEATURES
from src.task_suitability_inference import (
    TaskSuitabilityInference,
    task_suitability_engine,
    v2_suitability_engine,
    legacy_rf_suitability_engine,
)
from backend.db import build_task_suitability_features, get_task_applicants, get_mysql_connection


class TestTaskSuitabilityOptimizedRF(unittest.TestCase):
    """
    Test Suite for Stage 2 Task-Specific Suitability Prediction Pipeline & Two-Stage Architecture:
    1. Historical v2 pipeline and metadata integrity (verifymesh_stage2_suitability_pipeline_v2.joblib, tau = 0.60).
    2. Exact 5-feature input contract (STAGE2_V2_FEATURES) & 28-feature legacy compatibility.
    3. Strict decision threshold boundary testing (tau = 0.60) & 3-tier advisory classification.
    4. Deterministic Stage 1 gatekeeper prerequisite enforcement.
    5. Advisory presentation, factor-level explanations, and administrative assignment autonomy.
    6. Safe failure handling and preserved legacy Random Forest regression testing.
    """

    def setUp(self):
        self.engine = v2_suitability_engine
        self.expected_features = list(STAGE2_V2_FEATURES)
        self.legacy_features = list(LEGACY_28_FEATURES)

    def test_01_model_loading_and_single_active_model_contract(self):
        """Verify model pipeline is loaded into memory with exactly 5 features and active v2 metadata."""
        info = self.engine.get_info()
        self.assertTrue(info["model_loaded"])
        self.assertEqual(info["model_file"], "verifymesh_stage2_suitability_pipeline_v2.joblib")
        self.assertEqual(info["model_name"], "VerifyMesh_Stage2_Suitability_LR_v2")
        self.assertEqual(info["model_version"], "2.0.0")
        self.assertEqual(info["features_count"], 5)
        self.assertEqual(info["expected_features"], self.expected_features)
        self.assertEqual(info["model_sha256"], "96361a682f333e31e07f6910d501b73fb2e4240ab41cff6bfee08c28d23c6816")
        self.assertTrue(info["is_advisory"])
        self.assertIn("Suitable (1)", info["classes"])
        self.assertIn("Not Suitable (0)", info["classes"])

    def test_02_calibrated_threshold_loaded_from_metadata(self):
        """Verify calibrated decision threshold tau = 0.60 and moderate threshold 0.48 are loaded from JSON."""
        self.assertEqual(self.engine.threshold, 0.60)
        self.assertEqual(self.engine.moderate_threshold, 0.48)
        self.assertEqual(self.engine.positive_class, 1)
        self.assertEqual(self.engine.negative_class, 0)
        self.assertEqual(self.engine.metadata.get("threshold"), 0.60)

    def test_03_feature_vector_builder_schema_and_types(self):
        """Verify build_task_suitability_features returns exact 5 Stage 2 features and 28 legacy features."""
        task_data = {
            "category_name": "Enterprise Sales",
            "minimum_experience_months": 12,
            "exam_passing_score": 75.0,
            "exam_required": True,
        }
        agent_data = {
            "experience_months": 24,
            "sales_experience_months": 12,
            "customer_service_experience_months": 12,
        }
        certs = [
            {"certification_name": "Certified Sales Professional", "status": "VERIFIED"},
            {"certification_name": "Technical Cloud Architect", "status": "ACTIVE"},
        ]
        topic_scores = {
            1: 80.0,  # product knowledge
            2: 85.0,  # sales
            3: 90.0,  # communication
            4: 88.0,  # customer service
        }

        features = build_task_suitability_features(
            agent_data=agent_data,
            task_data=task_data,
            certs=certs,
            topic_scores=topic_scores,
            latest_score=85.0,
            strict=True,
        )

        # Check all 5 Stage 2 v2 features are present
        for k in self.expected_features:
            self.assertIn(k, features)
            self.assertIsInstance(features[k], (int, float))

        # Check all 28 legacy features are present for backward compatibility
        for k in self.legacy_features:
            self.assertIn(k, features)
            self.assertIsInstance(features[k], (int, float))

        # Check mathematical derivatives
        self.assertEqual(features["difficulty_tier"], 2.0)
        self.assertEqual(features["experience_surplus_months"], 12.0)
        self.assertAlmostEqual(features["exp_surplus_tanh"], np.tanh(12.0 / 12.0), places=4)
        self.assertIsInstance(features["weighted_skill_margin"], float)
        self.assertIsInstance(features["min_skill_margin"], float)
        self.assertIsInstance(features["weakest_link_deficit"], float)

    def test_04_missing_or_invalid_feature_validation(self):
        """Verify predict rejects payloads with missing or non-numeric features or NaN/Inf."""
        valid_sample = {
            "weighted_skill_margin": 10.0,
            "min_skill_margin": 5.0,
            "weakest_link_deficit": 0.0,
            "exp_surplus_tanh": 0.5,
            "difficulty_tier": 2.0,
        }

        # 1. Missing feature
        incomplete = dict(valid_sample)
        del incomplete["weakest_link_deficit"]
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(incomplete)
        self.assertIn("Missing required task suitability feature keys", str(ctx.exception))

        # 2. Non-numeric feature
        invalid_type = dict(valid_sample)
        invalid_type["difficulty_tier"] = "HIGH"
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(invalid_type)
        self.assertIn("must be numeric", str(ctx.exception))

        # 3. NaN feature
        nan_input = dict(valid_sample)
        nan_input["min_skill_margin"] = float("nan")
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(nan_input)
        self.assertIn("finite number", str(ctx.exception))

        # 4. Inf feature
        inf_input = dict(valid_sample)
        inf_input["exp_surplus_tanh"] = float("inf")
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(inf_input)
        self.assertIn("finite number", str(ctx.exception))

    def test_05_threshold_boundary_decision_classification(self):
        """
        Verify strict decision threshold boundary:
        P(1) >= 0.60 -> Strong Fit (Class 1)
        0.48 <= P(1) < 0.60 -> Moderate Fit (Class 0)
        P(1) < 0.48 -> Needs Review (Class 0)
        """
        valid_sample = {
            "weighted_skill_margin": 10.0,
            "min_skill_margin": 5.0,
            "weakest_link_deficit": 0.0,
            "exp_surplus_tanh": 0.5,
            "difficulty_tier": 2.0,
        }

        # Case A: Below moderate threshold (0.40) -> Needs Review, class 0
        with patch.object(self.engine.model, "predict_proba", return_value=np.array([[0.60, 0.40]])):
            res_review = self.engine.predict(valid_sample)
            self.assertEqual(res_review["predicted_class"], 0)
            self.assertEqual(res_review["suitability_label"], "Not Suitable")
            self.assertEqual(res_review["advisory_tier"], "Needs Review")
            self.assertEqual(res_review["advisory_tier_code"], "needs_review")
            self.assertEqual(res_review["applied_threshold"], 0.60)

        # Case B: Between moderate and strong (0.55) -> Moderate Fit, class 0
        with patch.object(self.engine.model, "predict_proba", return_value=np.array([[0.45, 0.55]])):
            res_mod = self.engine.predict(valid_sample)
            self.assertEqual(res_mod["predicted_class"], 0)
            self.assertEqual(res_mod["suitability_label"], "Not Suitable")
            self.assertEqual(res_mod["advisory_tier"], "Moderate Fit")
            self.assertEqual(res_mod["advisory_tier_code"], "moderate")

        # Case C: Exactly at threshold (0.60) -> Strong Fit, class 1
        with patch.object(self.engine.model, "predict_proba", return_value=np.array([[0.40, 0.60]])):
            res_exact = self.engine.predict(valid_sample)
            self.assertEqual(res_exact["predicted_class"], 1)
            self.assertEqual(res_exact["suitability_label"], "Suitable")
            self.assertEqual(res_exact["advisory_tier"], "Strong Fit")
            self.assertEqual(res_exact["advisory_tier_code"], "strong")

        # Case D: Above threshold (0.75) -> Strong Fit, class 1
        with patch.object(self.engine.model, "predict_proba", return_value=np.array([[0.25, 0.75]])):
            res_strong = self.engine.predict(valid_sample)
            self.assertEqual(res_strong["predicted_class"], 1)
            self.assertEqual(res_strong["suitability_label"], "Suitable")
            self.assertEqual(res_strong["advisory_tier"], "Strong Fit")
            self.assertEqual(res_strong["advisory_tier_code"], "strong")

    def test_06_real_pipeline_inference_execution(self):
        """Execute unmocked inference through the loaded Scikit-learn Pipeline with real features."""
        sample_input = {
            "weighted_skill_margin": 14.5,
            "min_skill_margin": 8.0,
            "weakest_link_deficit": 0.0,
            "exp_surplus_tanh": 0.7616,
            "difficulty_tier": 2.0,
        }

        output = self.engine.predict(sample_input)
        self.assertIn("suitability_score", output)
        self.assertIn("suitability_percent", output)
        self.assertIn("predicted_class", output)
        self.assertIn(output["predicted_class"], [0, 1])
        self.assertIn(output["suitability_label"], ["Suitable", "Not Suitable"])
        self.assertIn(output["advisory_tier"], ["Strong Fit", "Moderate Fit", "Needs Review"])
        self.assertEqual(output["applied_threshold"], 0.60)
        self.assertEqual(output["moderate_threshold"], 0.48)
        self.assertTrue(output["is_advisory"])
        self.assertIn("probabilities", output)
        self.assertAlmostEqual(output["probabilities"]["Not Suitable"] + output["probabilities"]["Suitable"], 1.0, places=2)
        self.assertEqual(len(output["engineered_features"]), 5)
        self.assertEqual(len(output["contributing_factors"]), 5)
        self.assertEqual(output["model_name"], "VerifyMesh_Stage2_Suitability_LR_v2")

    def test_07_advisory_status_and_synthetic_disclaimer(self):
        """Verify that predictions explicitly carry advisory labels and synthetic data disclaimers."""
        sample_input = {
            "weighted_skill_margin": 5.0,
            "min_skill_margin": 2.0,
            "weakest_link_deficit": 0.0,
            "exp_surplus_tanh": 0.2,
            "difficulty_tier": 1.0,
        }
        output = self.engine.predict(sample_input)
        self.assertTrue(output["is_advisory"])
        self.assertIn("Administrator retains final assignment authority", output["disclaimer"])
        self.assertIn("synthetic simulation data", output["synthetic_data_disclaimer"])

    def test_08_stage1_gatekeeper_enforcement(self):
        """Verify that Stage 2 refuses to predict for candidates marked ineligible by Stage 1."""
        valid_sample = {
            "weighted_skill_margin": 14.5,
            "min_skill_margin": 8.0,
            "weakest_link_deficit": 0.0,
            "exp_surplus_tanh": 0.76,
            "difficulty_tier": 2.0,
            "is_eligible": False,
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(valid_sample)
        self.assertIn("Stage 1 Gate Failed", str(ctx.exception))

        valid_sample2 = dict(valid_sample)
        del valid_sample2["is_eligible"]
        valid_sample2["meets_prerequisites"] = False
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(valid_sample2)
        self.assertIn("Stage 1 Gate Failed", str(ctx.exception))

    def test_09_preserved_legacy_rf_engine(self):
        """Verify the preserved legacy Random Forest engine loads 28 features with tau = 0.61."""
        rf_info = legacy_rf_suitability_engine.get_info()
        self.assertTrue(rf_info["model_loaded"])
        self.assertEqual(rf_info["model_file"], "verifymesh_final_optimized_pipeline.joblib")
        self.assertEqual(rf_info["features_count"], 28)
        self.assertEqual(rf_info["decision_threshold"], 0.61)


if __name__ == "__main__":
    unittest.main()
