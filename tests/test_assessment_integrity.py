import os
import sys
import json
import time
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.app import create_app
from backend.auth_routes import generate_auth_token
from backend.db import (
    get_mysql_connection,
    reset_agent_assessment,
    get_assessment_attempt,
    create_assessment_attempt
)


class TestAssessmentIntegrityBase(unittest.TestCase):
    """Base setup for assessment integrity tests."""

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-assessment-integrity-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 300
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Generate tokens for known agents and admin
        # Agent 1 (alex.morgan@university.edu -> user_id: 1, agent_id: 1)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Agent 2 (daniel.nyabuto@strathmore.edu -> user_id: 6, agent_id: 5)
        cls.agent2_token = generate_auth_token(user_id=6, role="Agent")
        cls.agent2_headers = {
            "Authorization": f"Bearer {cls.agent2_token}",
            "Content-Type": "application/json"
        }

        # Admin (admin@verifymesh.io -> user_id: 2, role: "Administrator")
        cls.admin_token = generate_auth_token(user_id=2, role="Administrator")
        cls.admin_headers = {
            "Authorization": f"Bearer {cls.admin_token}",
            "Content-Type": "application/json"
        }

        # Exam 3 details
        cls.exam_id = 3
        # Known questions for Exam 3: 13, 14, 15, 16, 17
        cls.valid_answers_exam3 = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "A"
        }

    def setUp(self):
        # Reset assessment state for test agents before each test to clear cooldowns
        reset_agent_assessment(1)
        reset_agent_assessment(6)


class TestQuestionSanitizationAndAccessControl(TestAssessmentIntegrityBase):
    """Requirement 4 & 5: Authoritative questions server-side, no scoring weights or answers leaked to browser."""

    def test_questions_endpoint_omits_correct_answers_and_point_weights(self):
        """GET /api/competency/exams/<id>/questions must return question text and options without answers or points."""
        res = self.client.get(f"/api/competency/exams/{self.exam_id}/questions", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        questions = data["data"]["questions"]
        self.assertGreater(len(questions), 0)

        for q in questions:
            # Must not expose correct_answer or points
            self.assertNotIn("correct_answer", q, "correct_answer leaked to client!")
            self.assertNotIn("points", q, "question point value leaked to client!")
            self.assertIn("question_id", q)
            self.assertIn("question_text", q)
            self.assertIn("options", q)
            for opt in q["options"]:
                self.assertIn("option_id", opt)
                self.assertIn("text", opt)
                self.assertNotIn("points", opt)
                self.assertNotIn("is_correct", opt)

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must receive HTTP 401."""
        res = self.client.get(f"/api/competency/exams/{self.exam_id}/questions")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_non_agent_role_rejected(self):
        """Requests with non-Agent roles (e.g. Administrator) must receive HTTP 403."""
        res = self.client.get(f"/api/competency/exams/{self.exam_id}/questions", headers=self.admin_headers)
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Agent role required", data["error"])


class TestClientSuppliedScoresRejection(TestAssessmentIntegrityBase):
    """Requirements 3 & 8: Reject client-supplied assessment_score, sub-scores, and protected features."""

    def test_submit_rejects_client_supplied_assessment_score(self):
        """Submitting assessment_score in payload must be rejected with HTTP 400."""
        # Start an attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Attempt to forge assessment_score
        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "assessment_score": 98.5,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("strictly forbidden", data["error"])
        self.assertIn("assessment_score", data["error"])

    def test_submit_rejects_client_supplied_subscores(self):
        """Submitting communication_score, sales_skill_score, etc. must be rejected with HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        forged_features = [
            "communication_score",
            "product_knowledge_score",
            "sales_skill_score",
            "customer_service_score",
            "previous_experience_months",
            "certification_count"
        ]
        for feat in forged_features:
            res = self.client.post(
                f"/api/competency/exams/{self.exam_id}/submit",
                headers=self.agent1_headers,
                json={
                    "attempt_id": attempt_id,
                    feat: 95.0,
                    "answers": self.valid_answers_exam3
                }
            )
            self.assertEqual(res.status_code, 400, f"Expected 400 when client supplied {feat}")
            self.assertIn("strictly forbidden", res.get_json()["error"])

    def test_evaluate_endpoint_rejects_client_supplied_scores(self):
        """POST /api/competency/evaluate must reject client-supplied protected features."""
        res = self.client.post(
            "/api/competency/evaluate",
            headers=self.agent1_headers,
            json={"assessment_score": 99.0}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("strictly forbidden", res.get_json()["error"])


class TestAttemptOwnershipAndCrossAgentHijacking(TestAssessmentIntegrityBase):
    """Requirements 5 & 10: Validate attempt ownership and prevent attempt hijacking across agents."""

    def test_cannot_submit_another_agents_attempt(self):
        """Agent B cannot submit or complete an attempt started by Agent A (HTTP 403)."""
        # Agent 1 starts an attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        agent1_attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Agent 2 attempts to submit Agent 1's attempt
        hijack_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={
                "attempt_id": agent1_attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(hijack_res.status_code, 403)
        data = hijack_res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("belongs to another agent", data["error"])

    def test_nonexistent_attempt_id_rejected(self):
        """Submitting with non-existent attempt_id returns HTTP 404."""
        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": 99999999,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.get_json()["error"])

    def test_exam_mismatch_rejected(self):
        """Attempt created for exam 3 submitted to exam 1 endpoint returns HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Submit attempt to different exam endpoint
        res = self.client.post(
            "/api/competency/exams/1/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": {"18": "B", "19": "A", "20": "C", "21": "B", "22": "A"}
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("does not match exam", res.get_json()["error"])


class TestAttemptLifecycleAndCooldown(TestAssessmentIntegrityBase):
    """Requirements 5 & 10: Prevent duplicate submissions, expired attempts, and enforce cooldown."""

    def test_duplicate_submission_rejected(self):
        """A submitted attempt cannot be resubmitted (HTTP 409)."""
        # Start attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # First submission succeeds
        sub1 = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(sub1.status_code, 200)

        # Second submission of same attempt must fail with 409 Conflict
        sub2 = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(sub2.status_code, 409)
        self.assertIn("already been submitted", sub2.get_json()["error"])

    def test_expired_attempt_rejected(self):
        """Attempt submitted past its expiration timestamp is rejected with HTTP 400."""
        # Create an attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Artificially expire the attempt in MySQL
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            past_time = datetime.now() - timedelta(minutes=5)
            cur.execute("UPDATE assessment_attempts SET expires_at = %s WHERE attempt_id = %s", (past_time, attempt_id))
        conn.commit()
        conn.close()

        # Submit should be rejected
        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("expired", res.get_json()["error"].lower())

    def test_closed_status_attempt_rejected(self):
        """Attempt marked CLOSED or EXPIRED in DB cannot be submitted."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE attempt_id = %s", (attempt_id,))
        conn.commit()
        conn.close()

        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("closed", res.get_json()["error"].lower())

    def test_cooldown_enforced_on_retake(self):
        """Starting a new attempt immediately after submission returns HTTP 429 while in cooldown."""
        # Start and submit attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        sub_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(sub_res.status_code, 200)

        # Immediate retake attempt should trigger cooldown 429
        retake_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(retake_res.status_code, 429)
        data = retake_res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("cooldown is active", data["error"].lower())
        self.assertIn("cooldown_remaining_seconds", data)
        self.assertGreater(data["cooldown_remaining_seconds"], 0)

    def test_reset_clears_cooldown_for_testing(self):
        """Admin/demo reset event clears the active cooldown."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]
        sub_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(sub_res.status_code, 200)

        # Cooldown is active
        retake_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(retake_res.status_code, 429)

        # Trigger reset
        reset_ok = reset_agent_assessment(1)
        self.assertTrue(reset_ok)

        # After reset, attempt can be started again
        post_reset_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(post_reset_res.status_code, 201)
        self.assertIn("attempt_id", post_reset_res.get_json()["data"])


class TestAnswerValidationAndSanity(TestAssessmentIntegrityBase):
    """Requirement 5: Strict validation of question IDs, option IDs, and answer completeness."""

    def test_missing_answers_dictionary_rejected(self):
        """Submitting without answers dictionary returns HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Answers must be a JSON object", res.get_json()["error"])

    def test_incomplete_answers_rejected(self):
        """Submitting partial answers (e.g., only 3 out of 5 questions answered) returns HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        partial_answers = {
            "13": "A",
            "14": "B",
            "15": "A"
            # 16 and 17 missing
        }
        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": partial_answers
            }
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Incomplete submission", data["error"])
        self.assertIn("16", data["error"])
        self.assertIn("17", data["error"])

    def test_invalid_question_id_rejected(self):
        """Submitting a question ID that doesn't belong to the exam returns HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        bogus_answers = dict(self.valid_answers_exam3)
        bogus_answers["9999"] = "A"

        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": bogus_answers
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid question ID", res.get_json()["error"])

    def test_invalid_option_id_rejected(self):
        """Submitting an invalid option ID (e.g. 'Z' or 999) returns HTTP 400."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        invalid_opt_answers = dict(self.valid_answers_exam3)
        invalid_opt_answers["13"] = "Z"  # Not a valid option A, B, C, D

        res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": invalid_opt_answers
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid option ID", res.get_json()["error"])


class TestValidAssessmentFlowAndServerScoring(TestAssessmentIntegrityBase):
    """Requirements 6, 7, 11 & 12: End-to-end legitimate assessment flow, scoring, inference, and persistence."""

    def test_full_assessment_flow_server_scoring_and_persistence(self):
        """
        Legitimate agent takes exam:
        1. Initiates attempt via POST /start-attempt
        2. Submits question IDs and selected option IDs only
        3. Server calculates composite score and sub-scores
        4. Reconciles verified profile features from DB
        5. Calls ML inference engine
        6. Persists assessment attempt, exam result, and prediction in database
        """
        # Step 1: Start attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        start_data = start_res.get_json()["data"]
        attempt_id = start_data["attempt_id"]
        self.assertEqual(start_data["status"], "IN_PROGRESS")
        self.assertIn("questions", start_data)

        # Step 2: Submit answers (100% correct answers: 13=A, 14=B, 15=A, 16=B, 17=A)
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.valid_answers_exam3
            }
        )
        self.assertEqual(submit_res.status_code, 200)
        result = submit_res.get_json()
        self.assertTrue(result["success"])
        data = result["data"]

        # Step 3: Verify server-calculated scores in response
        self.assertEqual(data["composite_score"], 100.0)
        self.assertTrue(data["passed"])
        self.assertEqual(data["subscores"]["product_knowledge_score"], 100.0)
        self.assertEqual(data["subscores"]["communication_score"], 100.0)
        self.assertEqual(data["subscores"]["customer_service_score"], 100.0)

        # Verify ML prediction and model version
        self.assertIn("prediction", data)
        self.assertIn("decision_label", data["prediction"])
        self.assertIn("decision_code", data["prediction"])
        self.assertIn("model_version", data)

        # Step 4: Verify MySQL persistence
        attempt_db = get_assessment_attempt(attempt_id)
        self.assertIsNotNone(attempt_db)
        self.assertEqual(attempt_db["status"], "SUBMITTED")
        self.assertEqual(float(attempt_db["score"]), 100.0)
        self.assertEqual(attempt_db["passed"], 1)
        self.assertIsNotNone(attempt_db["exam_result_id"])
        self.assertIsNotNone(attempt_db["prediction_id"])

        # Check answers_json stored in DB
        answers_stored = json.loads(attempt_db["answers_json"]) if isinstance(attempt_db["answers_json"], str) else attempt_db["answers_json"]
        self.assertEqual(answers_stored.get("13"), "A")
        self.assertEqual(answers_stored.get("14"), "B")

        # Check subscores_json stored in DB
        subscores_stored = json.loads(attempt_db["subscores_json"]) if isinstance(attempt_db["subscores_json"], str) else attempt_db["subscores_json"]
        self.assertEqual(subscores_stored.get("communication_score"), 100.0)

        # Verify exam_results table record
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM exam_results WHERE exam_result_id = %s", (attempt_db["exam_result_id"],))
            er = cur.fetchone()
            self.assertIsNotNone(er)
            self.assertEqual(float(er["assessment_score"]), 100.0)
            self.assertEqual(er["passed"], 1)
            self.assertEqual(er["attempt_id"], attempt_id)
        conn.close()


if __name__ == "__main__":
    unittest.main()
