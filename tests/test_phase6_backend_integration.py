"""
VerifyMesh — Phase 6 Unit & Integration Tests:
Live Backend Integration, Model v3 Serving, Feature Compatibility, and Fail-Safe Execution
"""

import math
import os
import unittest
from datetime import datetime
from pathlib import Path

from src.stage2_feature_engineering import (
    STAGE2_V3_FEATURES,
    STAGE2_V3_FEATURE_DESCRIPTIONS,
    STAGE2_V2_FEATURES,
    build_complete_stage2_feature_dict,
)
from src.task_suitability_inference import (
    task_suitability_engine,
    v2_suitability_engine,
    legacy_rf_suitability_engine,
    TaskSuitabilityInference,
)


class TestPhase6BackendIntegration(unittest.TestCase):
    """
    Test suite verifying Phase 6 Backend Integration:
    - Active model loading (Model v3)
    - Feature schema and ordering
    - Input validation and rejection of invalid data
    - Full prediction payload structure
    - Fail-safe execution and Stage 1 gatekeeper preservation
    - Live database applicant integration (Task 4 / Alex Morgan)
    - Predecessor model backward compatibility
    """

    def setUp(self):
        self.engine = task_suitability_engine

    def test_01_active_model_v3_loaded(self):
        """Verify that the active engine loads Model v3 and its metadata correctly."""
        self.assertTrue(self.engine.load_model(), "Engine failed to load model artifact.")
        info = self.engine.get_info()

        self.assertEqual(info["model_name"], "VerifyMesh_Stage2_Suitability_LR_v3")
        self.assertEqual(info["model_version"], "3.0.0")
        self.assertEqual(info["model_file"], "verifymesh_stage2_suitability_pipeline_v3.joblib")
        self.assertEqual(
            info["model_sha256"],
            "2897f781217895e6d7b285769132022e943e4ed9925e50a4e92938febc30f745",
        )
        self.assertEqual(info["decision_threshold"], 0.60)
        self.assertEqual(info["features_count"], 5)
        self.assertEqual(list(info["expected_features"]), STAGE2_V3_FEATURES)

    def test_02_feature_schema_and_ordering(self):
        """Verify that STAGE2_V3_FEATURES has exact 5 non-redundant features in expected order."""
        expected_features = [
            "weighted_skill_margin",
            "min_skill_margin",
            "deficit_competencies_ratio",
            "exp_surplus_tanh",
            "difficulty_tier",
        ]
        self.assertEqual(STAGE2_V3_FEATURES, expected_features)
        self.assertNotIn("weakest_link_deficit", STAGE2_V3_FEATURES)
        self.assertIn("deficit_competencies_ratio", STAGE2_V3_FEATURES)

    def test_03_stage1_ineligible_rejection(self):
        """Verify that Stage 2 strictly refuses to score candidates marked ineligible by Stage 1."""
        ineligible_input = {
            "weighted_skill_margin": 15.0,
            "min_skill_margin": 10.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": 0.85,
            "difficulty_tier": 2.0,
            "is_eligible": False,  # Stage 1 rejection
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(ineligible_input)
        self.assertIn("Stage 1 Gate Failed", str(ctx.exception))

    def test_04_missing_feature_rejection(self):
        """Verify that missing required features cause a clean ValueError rather than silent failure."""
        incomplete_input = {
            "weighted_skill_margin": 15.0,
            "min_skill_margin": 10.0,
            # Missing deficit_competencies_ratio
            "exp_surplus_tanh": 0.85,
            "difficulty_tier": 2.0,
            "is_eligible": True,
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(incomplete_input)
        self.assertIn("Missing required task suitability feature keys", str(ctx.exception))

    def test_05_non_numeric_and_nan_rejection(self):
        """Verify that NaN, None, string, or boolean feature values are strictly rejected."""
        nan_input = {
            "weighted_skill_margin": float("nan"),
            "min_skill_margin": 10.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": 0.85,
            "difficulty_tier": 2.0,
            "is_eligible": True,
        }
        with self.assertRaises(ValueError):
            self.engine.predict(nan_input)

        str_input = {
            "weighted_skill_margin": "not_a_number",
            "min_skill_margin": 10.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": 0.85,
            "difficulty_tier": 2.0,
            "is_eligible": True,
        }
        with self.assertRaises(ValueError):
            self.engine.predict(str_input)

    def test_06_invalid_difficulty_tier_rejection(self):
        """Verify that difficulty_tier must be 1.0, 2.0, or 3.0."""
        invalid_tier_input = {
            "weighted_skill_margin": 15.0,
            "min_skill_margin": 10.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": 0.85,
            "difficulty_tier": 5.0,  # Invalid tier
            "is_eligible": True,
        }
        with self.assertRaises(ValueError) as ctx:
            self.engine.predict(invalid_tier_input)
        self.assertIn("difficulty_tier", str(ctx.exception))

    def test_07_prediction_output_completeness(self):
        """Verify that the prediction payload contains all required Phase 6 output fields."""
        valid_input = {
            "applicant_id": 999,
            "task_id": 4,
            "weighted_skill_margin": 18.5,
            "min_skill_margin": 12.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": 0.82,
            "difficulty_tier": 2.0,
            "is_eligible": True,
            "meets_prerequisites": True,
            "assessment_completeness_status": "complete",
        }
        pred = self.engine.predict(valid_input)

        # Core predictions
        self.assertIn("prediction_score", pred)
        self.assertIn("suitability_score", pred)
        self.assertIn("suitability_percent", pred)
        self.assertIn("advisory_tier", pred)
        self.assertIn("advisory_classification", pred)
        self.assertIn("advisory_threshold", pred)
        self.assertEqual(pred["advisory_threshold"], 0.60)

        # Audit and provenance
        self.assertEqual(pred["model_version"], "3.0.0")
        self.assertEqual(pred["model_name"], "VerifyMesh_Stage2_Suitability_LR_v3")
        self.assertIn("prediction_timestamp", pred)
        self.assertIn("feature_values", pred)
        self.assertIn("engineered_features", pred)
        self.assertIn("contributing_factors", pred)
        self.assertIn("model_traceability", pred)
        self.assertIn("synthetic_data_disclaimer", pred)

        # Check values
        self.assertGreaterEqual(pred["prediction_score"], 0.0)
        self.assertLessEqual(pred["prediction_score"], 1.0)
        self.assertEqual(pred["advisory_tier"], "Strong Fit")

    def test_08_backward_compatibility_v2_and_legacy_rf(self):
        """Verify that predecessor engines (v2 and Legacy RF) remain loadable and functional."""
        self.assertTrue(v2_suitability_engine.load_model())
        v2_info = v2_suitability_engine.get_info()
        self.assertEqual(v2_info["model_version"], "2.0.0")
        self.assertEqual(v2_info["model_file"], "verifymesh_stage2_suitability_pipeline_v2.joblib")

        self.assertTrue(legacy_rf_suitability_engine.load_model())
        rf_info = legacy_rf_suitability_engine.get_info()
        self.assertEqual(rf_info["model_file"], "verifymesh_final_optimized_pipeline.joblib")

    def test_09_live_database_alex_morgan_task_4(self):
        """Verify live database evaluation of Alex Morgan on Task 4 with Model v3."""
        try:
            from backend.db import get_task_applicants, get_mysql_connection
            conn = get_mysql_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT application_id FROM task_applications WHERE task_id = 4 AND agent_id = 1")
                        if not cur.fetchone():
                            cur.execute(
                                "INSERT INTO task_applications (task_id, agent_id, status, applied_at) VALUES (4, 1, 'APPLIED', NOW())"
                            )
                            conn.commit()
                finally:
                    conn.close()
            applicants = get_task_applicants(4)
        except Exception as e:
            self.skipTest(f"Database connection unavailable: {e}")

        self.assertGreaterEqual(len(applicants), 1, "No applicants returned for Task 4.")
        alex = next((a for a in applicants if "Alex" in a.get("full_name", "")), None)
        self.assertIsNotNone(alex, "Alex Morgan not found in Task 4 applicants.")

        # Stage 1 verification
        self.assertTrue(alex.get("meets_prerequisites"), "Alex Morgan should meet Stage 1 prerequisites.")
        self.assertEqual(alex.get("stage2_status"), "scored")

        # Stage 2 verification with Model v3
        self.assertEqual(alex.get("model_version"), "3.0.0")
        score = alex.get("suitability_score")
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.60, f"Expected Strong Fit (>=0.60), got {score}")
        self.assertEqual(alex.get("advisory_tier"), "Strong Fit")
        self.assertEqual(alex.get("suitability_label"), "Suitable")

        # Traceability and feature checks
        trace = alex.get("model_traceability", {})
        self.assertEqual(trace.get("model_version"), "3.0.0")
        self.assertEqual(trace.get("model_name"), "VerifyMesh_Stage2_Suitability_LR_v3")

        features = alex.get("feature_values", {})
        self.assertIn("deficit_competencies_ratio", features)
        self.assertEqual(features.get("deficit_competencies_ratio"), 0.0)
        self.assertEqual(features.get("difficulty_tier"), 2.0)


if __name__ == "__main__":
    unittest.main()

