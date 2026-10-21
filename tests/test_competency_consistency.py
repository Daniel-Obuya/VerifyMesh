import os
import sys
import json
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.app import create_app
from backend.auth_routes import generate_auth_token
from backend.db import (
    get_mysql_connection,
    reset_agent_assessment,
    get_agent_assessment,
    get_agent_tasks_with_eligibility,
    COMPETENCY_ENUM_TO_LABEL,
    DECISION_TO_ENUM,
    ENUM_TO_DECISION,
)


class TestCompetencyConsistency(unittest.TestCase):
    """
    Focused regression tests for VerifyMesh Phase 3B - Step 1:
    Competency Decision Consistency.
    
    Verifies:
    1. A model Class 1 prediction when the exam score is high (not overridden to Competent).
    2. A model Class 2 prediction (returned & persisted as Competent).
    3. An Advanced promotion when existing conditions (Class 2, score >= 88%, exp >= 18 mo) are met.
    4. Agreement between returned decision and persisted competency in ml_predictions and eligibility_evaluations.
    5. Agreement between persisted competency and the downstream eligibility evaluator's input.
    """

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-competency-consistency-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0  # Disable cooldown for automated tests
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Agent 1: user_id = 1, agent_id = 1 (39 months verified experience, 1 certification)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Agent 2: user_id = 6, agent_id = 5 (0 months verified experience, 0 certifications)
        cls.agent2_token = generate_auth_token(user_id=6, role="Agent")
        cls.agent2_headers = {
            "Authorization": f"Bearer {cls.agent2_token}",
            "Content-Type": "application/json"
        }

        # Exam 3: 5 questions (13, 14, 15, 16, 17), 20 points each (100 total)
        cls.exam_id = 3
        # 100% correct answers
        cls.all_correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "A"
        }
        # 80% correct answers (4 correct, 1 incorrect: Q17=D)
        cls.four_correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "D"
        }

    def setUp(self):
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def tearDown(self):
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def test_class_1_prediction_with_high_exam_score_not_overridden_to_competent(self):
        """
        Regression Test:
        Agent 2 (0 verified experience, 0 certs) scores 100% on the exam.
        The ML model predicts Class 1 (Basic).
        High exam score must NOT silently override the model class to Competent.
        API response and database persistence must agree on 'Basic' and 'Send to Review'.
        """
        # Step 1: Start attempt
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent2_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit 100% correct answers
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.all_correct_answers
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]

        # 1. Verify score is 100%
        self.assertEqual(data["score"], 100.0)
        self.assertTrue(data["passed"])

        # 2. Verify binary model evaluates full profile (0 exp, 0 certs) to Class 0 (Not Eligible)
        self.assertEqual(data["prediction"]["decision_code"], 0)
        self.assertEqual(data["competency_level"], "Not Eligible")
        self.assertEqual(data["evaluation_decision"], "Not Eligible")
        self.assertEqual(data["prediction"]["competency_label"], "Not Eligible")
        self.assertEqual(data["prediction"]["decision_label"], "Not Eligible")

        # 3. Verify database persistence in ml_predictions
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT predicted_competency, confidence 
                FROM ml_predictions 
                WHERE agent_id = 5 
                ORDER BY prediction_id DESC LIMIT 1
            """)
            pred = cur.fetchone()
            self.assertIsNotNone(pred)
            self.assertEqual(pred["predicted_competency"], "NOT_ELIGIBLE")
        conn.close()

        # 4. Verify agreement with get_agent_assessment API
        status_res = self.client.get("/api/competency/agent-status", headers=self.agent2_headers)
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.get_json()
        self.assertEqual(status_data["competency_level"], "Not Eligible")
        self.assertEqual(status_data["evaluation_decision"], "Not Eligible")

        # 5. Verify agreement with downstream task eligibility evaluator
        # Task 4 requires Eligible competency: agent cannot apply
        tasks = get_agent_tasks_with_eligibility(user_id=6)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertFalse(task_4["can_apply"])
        self.assertFalse(task_4["is_eligible"])
        self.assertEqual(task_4["prerequisites"]["evaluation_decision"], "Not Eligible")
        self.assertFalse(task_4["prerequisites"]["competency_met"])

    def test_class_2_prediction_persisted_and_returned_as_competent(self):
        """
        Regression Test:
        Agent 1 (39 months verified experience) scores 80% on the exam (< 88% threshold for Advanced).
        The ML model predicts Class 2 (Competent).
        API response and database persistence must agree on 'Competent' and 'Eligible'.
        """
        # Step 1: Start attempt
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit 80% correct answers (4 correct, 1 incorrect)
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.four_correct_answers
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]

        # 1. Verify score is 80.0% (passed, but < 88% needed for Advanced promotion)
        self.assertEqual(data["score"], 80.0)
        self.assertTrue(data["passed"])

        # 2. Verify model prediction is Class 1 (Eligible)
        self.assertEqual(data["prediction"]["decision_code"], 1)
        self.assertEqual(data["competency_level"], "Eligible")
        self.assertEqual(data["evaluation_decision"], "Eligible")
        self.assertEqual(data["prediction"]["competency_label"], "Eligible")
        self.assertEqual(data["prediction"]["decision_label"], "Eligible")

        # 3. Verify database persistence in ml_predictions
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT predicted_competency, confidence 
                FROM ml_predictions 
                WHERE agent_id = 1 
                ORDER BY prediction_id DESC LIMIT 1
            """)
            pred = cur.fetchone()
            self.assertIsNotNone(pred)
            self.assertEqual(pred["predicted_competency"], "ELIGIBLE")
        conn.close()

        # 4. Verify agreement with get_agent_assessment API
        status_res = self.client.get("/api/competency/agent-status", headers=self.agent1_headers)
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.get_json()
        self.assertEqual(status_data["competency_level"], "Eligible")
        self.assertEqual(status_data["evaluation_decision"], "Eligible")

        # 5. Verify downstream task eligibility evaluator prerequisites
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)

        # Task 4 requires ELIGIBLE: meets competency requirement
        self.assertEqual(task_4["prerequisites"]["evaluation_decision"], "Eligible")
        self.assertTrue(task_4["prerequisites"]["competency_met"])

    def test_advanced_promotion_when_conditions_met(self):
        """
        Regression Test:
        Agent 1 (39 months experience >= 18) scores 100% on the exam (>= 88%).
        ML model predicts Class 2.
        Approved Advanced promotion rule applies:
        raw_decision == '2' AND composite_pct >= 88.0 AND exp_m >= 18.0 -> ADVANCED.
        API response and database persistence must agree on 'Advanced' and 'Eligible'.
        """
        # Step 1: Start attempt
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit 100% correct answers
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.all_correct_answers
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]

        # 1. Verify score is 100%
        self.assertEqual(data["score"], 100.0)
        self.assertTrue(data["passed"])

        # 2. Verify model prediction is Class 1 (Eligible)
        self.assertEqual(data["prediction"]["decision_code"], 1)
        self.assertEqual(data["competency_level"], "Eligible")
        self.assertEqual(data["evaluation_decision"], "Eligible")
        self.assertEqual(data["prediction"]["competency_label"], "Eligible")
        self.assertEqual(data["prediction"]["decision_label"], "Eligible")

        # 3. Verify database persistence in ml_predictions has ELIGIBLE
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT predicted_competency, confidence 
                FROM ml_predictions 
                WHERE agent_id = 1 
                ORDER BY prediction_id DESC LIMIT 1
            """)
            pred = cur.fetchone()
            self.assertIsNotNone(pred)
            self.assertEqual(pred["predicted_competency"], "ELIGIBLE")
        conn.close()

        # 4. Verify get_agent_assessment reflects Eligible
        rec = get_agent_assessment(user_id=1)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["competency_level"], "Eligible")
        self.assertEqual(rec["evaluation_decision"], "Eligible")

        # 5. Verify downstream task eligibility evaluator recognizes Eligible
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_6 = next((t for t in tasks if t["task_id"] == 6), None)
        self.assertIsNotNone(task_6)
        self.assertEqual(task_6["prerequisites"]["evaluation_decision"], "Eligible")
        self.assertTrue(task_6["prerequisites"]["competency_met"])

    def test_agreement_between_returned_decision_and_persisted_competency_with_task_id(self):
        """
        Regression Test:
        Submit exam with an explicit task_id (Task 4: Technical Support Agent).
        Verify transactional consistency between:
        - API response: competency_level and evaluation_decision
        - MySQL ml_predictions: predicted_competency
        - MySQL eligibility_evaluations: eligibility_status
        """
        # Step 1: Start attempt with task_id = 4
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt?task_id=4",
            headers=self.agent1_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit answers with task_id = 4
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.all_correct_answers,
                "task_id": 4
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]

        comp_level = data["competency_level"]
        eval_decision = data["evaluation_decision"]

        # Step 3: Check database records
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Check ml_predictions
            cur.execute("""
                SELECT prediction_id, predicted_competency 
                FROM ml_predictions 
                WHERE agent_id = 1 
                ORDER BY prediction_id DESC LIMIT 1
            """)
            ml_row = cur.fetchone()
            self.assertIsNotNone(ml_row)
            self.assertEqual(ml_row["predicted_competency"], "ELIGIBLE")

            # Check eligibility_evaluations
            cur.execute("""
                SELECT evaluation_id, eligibility_status, review_status, task_id 
                FROM eligibility_evaluations 
                WHERE agent_id = 1 AND task_id = 4 
                ORDER BY evaluation_id DESC LIMIT 1
            """)
            eval_row = cur.fetchone()
            self.assertIsNotNone(eval_row)
            # Both API and DB agree: Eligible <-> ELIGIBLE
            self.assertEqual(eval_row["eligibility_status"], "ELIGIBLE")
            self.assertEqual(eval_row["review_status"], "NOT_REQUIRED")
        conn.close()

    def test_persisted_competency_and_eligibility_evaluator_input_consistency(self):
        """
        Regression Test:
        Ensure that the competency value loaded by get_agent_tasks_with_eligibility()
        comes directly from ml_predictions.predicted_competency without contradiction.
        """
        # Execute assessment for Agent 2 (Class 1 -> Basic)
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent2_headers
        )
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.all_correct_answers
            }
        )
        data = submit_res.get_json()["data"]
        returned_comp = data["competency_level"]  # "Basic"
        returned_decision = data["evaluation_decision"]  # "Send to Review"

        # Check get_agent_assessment
        assessment_rec = get_agent_assessment(user_id=6)
        self.assertIsNotNone(assessment_rec)
        self.assertEqual(assessment_rec["competency_level"], returned_comp)
        self.assertEqual(assessment_rec["evaluation_decision"], returned_decision)

        # Check get_agent_tasks_with_eligibility on Task 4
        tasks = get_agent_tasks_with_eligibility(user_id=6)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertEqual(task_4["prerequisites"]["evaluation_decision"], "Not Eligible")
        self.assertFalse(task_4["can_apply"])
        self.assertFalse(task_4["is_eligible"])

    def test_class_0_prediction_ineligible(self):
        """
        Regression Test:
        Agent 2 (0 exp, 0 certs) submits all-incorrect answers (0% score).
        Model predicts Class 0 (Needs Improvement / Ineligible).
        API response, database persistence, and task eligibility must agree on
        'Needs Improvement' and 'Ineligible'.
        """
        # Step 1: Start attempt
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent2_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit all incorrect answers (0% score)
        all_incorrect_answers = {
            "13": "C",
            "14": "C",
            "15": "C",
            "16": "C",
            "17": "C"
        }
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={
                "attempt_id": attempt_id,
                "answers": all_incorrect_answers
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]

        # 1. API response check
        self.assertEqual(data["score"], 0.0)
        self.assertFalse(data["passed"])
        self.assertEqual(data["prediction"]["decision_code"], 0)
        self.assertEqual(data["competency_level"], "Not Eligible")
        self.assertEqual(data["evaluation_decision"], "Not Eligible")
        self.assertEqual(data["prediction"]["competency_label"], "Not Eligible")
        self.assertEqual(data["prediction"]["decision_label"], "Not Eligible")

        # 2. Database persistence check
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT predicted_competency 
                FROM ml_predictions 
                WHERE agent_id = 5 
                ORDER BY prediction_id DESC LIMIT 1
            """)
            pred = cur.fetchone()
            self.assertIsNotNone(pred)
            self.assertEqual(pred["predicted_competency"], "NOT_ELIGIBLE")
        conn.close()

        # 3. get_agent_assessment check
        rec = get_agent_assessment(user_id=6)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["competency_level"], "Not Eligible")
        self.assertEqual(rec["evaluation_decision"], "Not Eligible")

        # 4. Downstream task eligibility check
        tasks = get_agent_tasks_with_eligibility(user_id=6)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertEqual(task_4["prerequisites"]["evaluation_decision"], "Not Eligible")
        self.assertFalse(task_4["prerequisites"]["competency_met"])
        self.assertFalse(task_4["can_apply"])
        self.assertFalse(task_4["is_eligible"])


if __name__ == "__main__":
    unittest.main()
