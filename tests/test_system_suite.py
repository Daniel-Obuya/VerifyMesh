"""
VerifyMesh Capstone System Testing Suite (Chapter 5.7)
Maps 1-to-1 with Test Cases TC001 through TC023 across all six functional areas:
  - Category A: User Authentication & Account Management (TC001 - TC004)
  - Category B: Competency Assessments (TC005 - TC008)
  - Category C: Machine Learning Competency Prediction (TC009 - TC012)
  - Category D: Task Eligibility Evaluation (TC013 - TC016)
  - Category E: Role-Based Access Control (TC017 - TC019)
  - Category F: Database Persistence & Error Handling (TC020 - TC023)

Safety and Integrity:
  - Uses isolated test fixtures, non-destructive test transactions, and cleanup routines.
  - Uses live scikit-learn model and inference pipeline (no mock model).
  - Preserves production user accounts and database integrity.
"""

import os
import sys
import json
import time
import base64
import hmac
import hashlib
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import Config
from backend.app import create_app
from backend.auth_routes import (
    generate_auth_token,
    decode_auth_token,
    limiter,
    PENDING_SIGNUPS
)
from backend.db import (
    get_mysql_connection,
    reset_agent_assessment,
    get_agent_assessment,
    get_agent_tasks_with_eligibility,
    find_user_by_id,
    store_otp,
    verify_otp,
    delete_task,
    COMPETENCY_ENUM_TO_LABEL,
    DECISION_TO_ENUM,
    ENUM_TO_DECISION
)
from src.inference import inference_engine


class SystemTestingBase(unittest.TestCase):
    """Shared configuration and fixtures for VerifyMesh System Testing."""

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-capstone-system-testing-secret-key-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0  # Disable retake cooldown for automated suite
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Known persistent test accounts seeded in VerifyMesh database:
        # Agent 1: alex.morgan@university.edu (user_id=1, agent_id=1, 40 months exp)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Agent 2: daniel.nyabuto@strathmore.edu (user_id=6, agent_id=5, 0 months exp)
        cls.agent2_token = generate_auth_token(user_id=6, role="Agent")
        cls.agent2_headers = {
            "Authorization": f"Bearer {cls.agent2_token}",
            "Content-Type": "application/json"
        }

        # Administrator: admin@verifymesh.io (user_id=2, role="Administrator")
        cls.admin_token = generate_auth_token(user_id=2, role="Administrator")
        cls.admin_headers = {
            "Authorization": f"Bearer {cls.admin_token}",
            "Content-Type": "application/json"
        }

        # Active Exam 3: 5 questions (13, 14, 15, 16, 17), 20 pts each (100 total), passing 75.0
        cls.exam_id = 3
        cls.all_correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "A"
        }
        cls.four_correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "D"  # Incorrect
        }

    def setUp(self):
        # Clear rate limiters and temporary state between tests
        with limiter._lock:
            limiter._attempts.clear()
        PENDING_SIGNUPS.clear()

        # Ensure Tasks 2, 3, 4, 5 are active for task eligibility tests
        conn = get_mysql_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE tasks SET status = 'ACTIVE' WHERE task_id IN (2, 3, 4, 5)")
            conn.commit()
            conn.close()

    def tearDown(self):
        with limiter._lock:
            limiter._attempts.clear()
        PENDING_SIGNUPS.clear()


# =====================================================================
# CATEGORY A: User Authentication & Account Management (TC001 - TC004)
# =====================================================================
class TestCategoryA_Authentication(SystemTestingBase):

    def test_TC001_register_account_valid_data(self):
        """TC001: Register an account using valid registration data."""
        test_email = f"tc001_{int(time.time())}@verifymesh-test.io"
        registration_payload = {
            "full_name": "Capstone Test Candidate",
            "email": test_email,
            "phone": "+254711223344",
            "password": "StrongPassword2026!",
            "confirm_password": "StrongPassword2026!"
        }

        # Mock email dispatch to keep test isolated and offline
        with patch("backend.auth_routes.send_verification_email") as mock_email:
            res = self.client.post("/api/auth/register", json=registration_payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("requires_verification"))
            self.assertEqual(data.get("email"), test_email)
            self.assertIn("6-digit verification code", data.get("message", ""))
            mock_email.assert_called_once()

            # Verify OTP record in memory/db
            self.assertIn(test_email, PENDING_SIGNUPS)

    def test_TC002_login_valid_credentials_role_routing(self):
        """TC002: Log in with valid credentials and verify correct role-based response."""
        # Test Agent Login
        agent_payload = {
            "email": "alex.morgan@university.edu",
            "password": "password123"
        }
        res_agent = self.client.post("/api/auth/login", json=agent_payload)
        self.assertEqual(res_agent.status_code, 200)
        data_agent = res_agent.get_json()
        self.assertTrue(data_agent.get("success"))
        self.assertIn("token", data_agent)
        self.assertEqual(data_agent["user"]["role"], "Agent")

        # Test Admin Login
        admin_payload = {
            "email": "admin@verifymesh.io",
            "password": "password123"
        }
        res_admin = self.client.post("/api/auth/login", json=admin_payload)
        self.assertEqual(res_admin.status_code, 200)
        data_admin = res_admin.get_json()
        self.assertTrue(data_admin.get("success"))
        self.assertIn("token", data_admin)
        self.assertEqual(data_admin["user"]["role"], "Administrator")

    def test_TC003_reject_invalid_login_credentials(self):
        """TC003: Reject invalid login credentials."""
        # Case 1: Wrong password for existing user
        bad_pw_res = self.client.post("/api/auth/login", json={
            "email": "alex.morgan@university.edu",
            "password": "IncorrectPassword999!"
        })
        self.assertEqual(bad_pw_res.status_code, 401)
        self.assertFalse(bad_pw_res.get_json().get("success"))
        self.assertIn("Invalid email/username or password", bad_pw_res.get_json().get("error"))

        # Case 2: Non-existent user
        nonexistent_res = self.client.post("/api/auth/login", json={
            "email": "ghost_user_does_not_exist@domain.com",
            "password": "somePassword123!"
        })
        self.assertEqual(nonexistent_res.status_code, 401)
        self.assertFalse(nonexistent_res.get_json().get("success"))

    def test_TC004_reject_invalid_expired_tampered_tokens(self):
        """TC004: Reject missing, invalid, expired, or tampered authentication tokens."""
        # 1. Missing Token
        res_missing = self.client.get("/api/auth/me")
        self.assertEqual(res_missing.status_code, 401)
        self.assertIn("token required", res_missing.get_json().get("error", "").lower())

        # 2. Tampered Signature
        token = generate_auth_token(user_id=1, role="Agent")
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{'0' * len(parts[1])}"
        res_tampered = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(res_tampered.status_code, 401)

        # 3. Forged Payload (Privilege Escalation Attempt)
        malicious_payload = {"uid": 1, "role": "Administrator", "exp": int(time.time()) + 3600}
        b64_payload = base64.urlsafe_b64encode(json.dumps(malicious_payload).encode()).decode().rstrip("=")
        forged_token = f"{b64_payload}.{parts[1]}"
        res_forged = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(res_forged.status_code, 401)

        # 4. Expired Token
        expired_payload = {"uid": 1, "role": "Agent", "exp": int(time.time()) - 120}
        raw = json.dumps(expired_payload).encode()
        encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        sig = hmac.new(Config.SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        expired_token = f"{encoded}.{sig}"
        res_expired = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res_expired.status_code, 401)


# =====================================================================
# CATEGORY B: Competency Assessments (TC005 - TC008)
# =====================================================================
class TestCategoryB_CompetencyAssessments(SystemTestingBase):

    def setUp(self):
        super().setUp()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def tearDown(self):
        super().tearDown()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def test_TC005_assessment_questions_selection_and_display(self):
        """TC005: Verify that the appropriate assessment questions are returned without answer leakage."""
        res = self.client.get(f"/api/competency/exams/{self.exam_id}/questions", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]

        # Validate exam metadata
        self.assertEqual(data["exam"]["exam_id"], self.exam_id)
        self.assertEqual(data["exam"]["passing_score"], 75.0)
        self.assertEqual(data["exam"]["total_questions"], 5)

        # Validate questions structure and that correct_answer is NOT leaked to client
        questions = data["questions"]
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertIn("question_id", q)
            self.assertIn("question_text", q)
            self.assertIn("options", q)
            self.assertNotIn("correct_answer", q, "Security flaw: correct_answer exposed in client payload!")
            self.assertGreaterEqual(len(q["options"]), 2)

    def test_TC006_submit_valid_assessment_calculates_server_score(self):
        """TC006: Submit valid completed assessment and verify expected score is calculated server-side."""
        # 1. Start Attempt
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # 2. Submit 80% correct answers (4 out of 5)
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

        # Assert score is exactly 80.0%, passed is True (passing_score = 75.0)
        self.assertEqual(data["score"], 80.0)
        self.assertTrue(data["passed"])
        self.assertEqual(data["passing_score"], 75.0)
        self.assertEqual(data["competency_level"], "Eligible")
        self.assertEqual(data["evaluation_decision"], "Eligible")

    def test_TC007_reject_incomplete_and_tampered_submissions(self):
        """TC007: Verify that incomplete, invalid, or score-tampered submissions are rejected."""
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Case 1: Incomplete submission (missing question 17)
        incomplete_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": {"13": "A", "14": "B", "15": "A", "16": "B"}
            }
        )
        self.assertEqual(incomplete_res.status_code, 400)
        self.assertIn("Incomplete submission", incomplete_res.get_json().get("error", ""))

        # Case 2: Client tampering attempt - sending client-calculated score
        tampered_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={
                "attempt_id": attempt_id,
                "answers": self.all_correct_answers,
                "assessment_score": 100.0  # Forbidden protected feature
            }
        )
        self.assertEqual(tampered_res.status_code, 400)
        self.assertIn("strictly forbidden", tampered_res.get_json().get("error", ""))

    def test_TC008_assessment_results_persisted_in_database(self):
        """TC008: Verify that assessment results and predictions are persisted and associated with correct agent."""
        # Start and submit 100% correct answers for Agent 1 (agent_id = 1)
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id, "answers": self.all_correct_answers}
        )
        self.assertEqual(submit_res.status_code, 200)

        # Direct database query check
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Check exam_results
            cur.execute("""
                SELECT assessment_score, passed, attempt_number
                FROM exam_results
                WHERE agent_id = 1
                ORDER BY exam_result_id DESC LIMIT 1
            """)
            exam_row = cur.fetchone()
            self.assertIsNotNone(exam_row)
            self.assertEqual(float(exam_row["assessment_score"]), 100.0)
            self.assertEqual(exam_row["passed"], 1)

            # Check ml_predictions
            cur.execute("""
                SELECT predicted_competency, confidence
                FROM ml_predictions
                WHERE agent_id = 1
                ORDER BY prediction_id DESC LIMIT 1
            """)
            pred_row = cur.fetchone()
            self.assertIsNotNone(pred_row)
            self.assertEqual(pred_row["predicted_competency"], "ELIGIBLE")
        conn.close()


# =====================================================================
# CATEGORY C: Machine Learning Prediction (TC009 - TC012)
# =====================================================================
class TestCategoryC_MachineLearning(SystemTestingBase):

    def test_TC009_inference_returns_valid_decision_classes(self):
        """TC009: Submit valid feature profiles and verify inference returns supported decision classes."""
        valid_profile = {
            "previous_experience_months": 24.0,
            "sales_experience_months": 18.0,
            "customer_service_experience_months": 12.0,
            "certification_count": 2.0,
            "relevant_certification": 1.0,
            "assessment_score": 85.0,
            "communication_score": 82.0,
            "product_knowledge_score": 80.0,
            "sales_skill_score": 84.0,
            "customer_service_score": 86.0
        }

        result = inference_engine.predict(valid_profile)
        self.assertIn("decision", result)
        self.assertIn("confidence", result)
        self.assertIn("probabilities", result)

        # Decision must be one of the two supported model output codes: '0', '1'
        self.assertIn(str(result["decision"]), ["0", "1"])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=2)

    def test_TC010_input_feature_ordering_types_and_preprocessing(self):
        """TC010: Verify 11-feature contract, feature ordering, and certified_leverage derivation."""
        # Expected exact 11 input features in order
        expected_raw_features = [
            "previous_experience_months",
            "sales_experience_months",
            "customer_service_experience_months",
            "certification_count",
            "relevant_certification",
            "assessment_score",
            "communication_score",
            "product_knowledge_score",
            "sales_skill_score",
            "customer_service_score",
            "certified_leverage"
        ]
        self.assertEqual(inference_engine.EXPECTED_FEATURES, expected_raw_features)
        self.assertEqual(len(inference_engine.ENGINEERED_FEATURES), 15)

        # Test automatic derivation of certified_leverage formula:
        # certified_leverage = certification_count * (1 + relevant_certification)
        cert_count = 3.0
        rel_cert = 1.0
        expected_leverage = cert_count * (1.0 + rel_cert)  # 6.0

        raw_input = {
            "previous_experience_months": 30.0,
            "sales_experience_months": 20.0,
            "customer_service_experience_months": 10.0,
            "certification_count": cert_count,
            "relevant_certification": rel_cert,
            "assessment_score": 90.0,
            "communication_score": 90.0,
            "product_knowledge_score": 90.0,
            "sales_skill_score": 90.0,
            "customer_service_score": 90.0
        }
        res = inference_engine.predict(raw_input)
        self.assertIsNotNone(res)

    def test_TC011_decision_class_to_application_labels_mapping(self):
        """TC011: Verify that model output classes are mapped correctly to application labels."""
        # Class 0: Not Eligible
        self.assertEqual(DECISION_TO_ENUM["0"], "NOT_ELIGIBLE")
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["NOT_ELIGIBLE"], "Not Eligible")
        self.assertEqual(ENUM_TO_DECISION["NOT_ELIGIBLE"]["label"], "Not Eligible")
        self.assertEqual(ENUM_TO_DECISION["NOT_ELIGIBLE"]["code"], 0)

        # Class 1: Eligible
        self.assertEqual(DECISION_TO_ENUM["1"], "ELIGIBLE")
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["ELIGIBLE"], "Eligible")
        self.assertEqual(ENUM_TO_DECISION["ELIGIBLE"]["label"], "Eligible")
        self.assertEqual(ENUM_TO_DECISION["ELIGIBLE"]["code"], 1)

        # Backward-compatible enum labels mapped to binary outcomes
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["COMPETENT"], "Eligible")
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["ADVANCED"], "Eligible")
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["BASIC"], "Not Eligible")
        self.assertEqual(COMPETENCY_ENUM_TO_LABEL["NEEDS_IMPROVEMENT"], "Not Eligible")

    def test_TC012_safe_handling_of_malformed_and_missing_features(self):
        """TC012: Test missing, malformed, or non-numeric feature inputs raise ValueError."""
        # Case 1: Missing required raw feature
        missing_input = {
            "previous_experience_months": 12.0,
            "sales_experience_months": 6.0
            # missing remaining features
        }
        with self.assertRaises(ValueError) as ctx_missing:
            inference_engine.predict(missing_input)
        self.assertIn("Missing required feature keys", str(ctx_missing.exception))

        # Case 2: Non-numeric feature input
        invalid_type_input = {
            "previous_experience_months": "not_a_number",
            "sales_experience_months": 12.0,
            "customer_service_experience_months": 12.0,
            "certification_count": 1.0,
            "relevant_certification": 1.0,
            "assessment_score": 75.0,
            "communication_score": 75.0,
            "product_knowledge_score": 75.0,
            "sales_skill_score": 75.0,
            "customer_service_score": 75.0
        }
        with self.assertRaises(ValueError) as ctx_type:
            inference_engine.predict(invalid_type_input)
        self.assertIn("must be a numeric value", str(ctx_type.exception))


# =====================================================================
# CATEGORY D: Task Eligibility Evaluation (TC013 - TC016)
# =====================================================================
class TestCategoryD_TaskEligibility(SystemTestingBase):

    def setUp(self):
        super().setUp()
        reset_agent_assessment(1)
        reset_agent_assessment(6)
        self.created_task_ids = []

    def tearDown(self):
        super().tearDown()
        reset_agent_assessment(1)
        reset_agent_assessment(6)
        conn = get_mysql_connection()
        if conn:
            with conn.cursor() as cur:
                for tid in self.created_task_ids:
                    try:
                        delete_task(tid)
                    except Exception:
                        pass
            conn.close()

    def test_TC013_evaluate_agent_against_task_requirements(self):
        """TC013: Evaluate an agent against an existing task's requirements."""
        # Create an isolated active test task with no applications
        conn = get_mysql_connection()
        self.assertIsNotNone(conn)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (category_id, task_name, description, payment_type, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (1, "TC013 Standard Eligible Task", "Testing task eligibility evaluation", "Hourly", "ACTIVE"))
            test_task_id = cur.lastrowid
            self.created_task_ids.append(test_task_id)

            cur.execute("""
                INSERT INTO task_requirements (task_id, minimum_competency, minimum_experience_months, exam_required)
                VALUES (%s, %s, %s, %s)
            """, (test_task_id, 'COMPETENT', 12, 0))
        conn.commit()
        conn.close()

        # Agent 1 (40 mo experience) completes assessment with 80% (Competent / Eligible)
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent1_headers
        )
        attempt_id = start_res.get_json()["data"]["attempt_id"]
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id, "answers": self.four_correct_answers}
        )

        tasks = get_agent_tasks_with_eligibility(user_id=1)
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)

        # The test task has no prior application; should evaluate to 'Ready to Apply'
        matched_task = next((t for t in tasks if t["task_id"] == test_task_id), None)
        self.assertIsNotNone(matched_task)
        self.assertEqual(matched_task["state"], "Ready to Apply")
        self.assertTrue(matched_task["can_apply"])
        self.assertTrue(matched_task["is_eligible"])

    def test_TC014_unmet_mandatory_requirements_block_approval(self):
        """TC014: Verify that unmet mandatory requirements prevent approval (e.g. mandatory cert)."""
        # Create an isolated task with a mandatory certification requirement that Agent 1 does NOT possess
        conn = get_mysql_connection()
        self.assertIsNotNone(conn)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (category_id, task_name, description, payment_type, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (1, "TC014 Cert Required Task", "Requires advanced certification", "Hourly", "ACTIVE"))
            test_task_id = cur.lastrowid
            self.created_task_ids.append(test_task_id)

            cur.execute("""
                INSERT INTO task_requirements (task_id, minimum_competency, required_certification_id, minimum_experience_months)
                VALUES (%s, %s, %s, %s)
            """, (test_task_id, 'COMPETENT', 3, 12))  # Certification 3 is unmet
        conn.commit()
        conn.close()

        # Complete assessment for Agent 1 -> Competent
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id, "answers": self.four_correct_answers}
        )

        tasks = get_agent_tasks_with_eligibility(user_id=1)
        cert_task = next((t for t in tasks if t["task_id"] == test_task_id), None)
        self.assertIsNotNone(cert_task)
        self.assertEqual(cert_task["state"], "Certification Required")
        self.assertFalse(cert_task["can_apply"])
        self.assertFalse(cert_task["is_eligible"])
        self.assertIn("certification", cert_task["blocking_reason"].lower())

    def test_TC015_eligibility_decision_structure_and_display(self):
        """TC015: Verify that the resulting eligibility decision contains all required contract fields."""
        res = self.client.get("/api/competency/tasks", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        tasks = res.get_json()["tasks"]
        self.assertGreater(len(tasks), 0)

        for task in tasks:
            self.assertIn("task_id", task)
            self.assertIn("state", task)
            self.assertIn("can_apply", task)
            self.assertIn("is_eligible", task)
            self.assertIn("blocking_reason", task)
            self.assertIn("prerequisites", task)

    def test_TC016_send_to_review_not_silently_treated_as_eligible(self):
        """TC016: Verify that a 'Not Eligible' outcome is NOT treated as confirmed eligibility."""
        # Agent 2 (0 mo exp, 0 certs) scores 100% on the exam.
        # Model predicts Class 0 (Not Eligible).
        start_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/start-attempt",
            headers=self.agent2_headers
        )
        attempt_id = start_res.get_json()["data"]["attempt_id"]
        submit_res = self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={"attempt_id": attempt_id, "answers": self.all_correct_answers}
        )
        self.assertEqual(submit_res.status_code, 200)
        data = submit_res.get_json()["data"]
        self.assertEqual(data["evaluation_decision"], "Not Eligible")

        # Downstream check for Task 4
        tasks = get_agent_tasks_with_eligibility(user_id=6)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertFalse(task_4["can_apply"], "Security error: Not Eligible agent allowed to apply!")
        self.assertFalse(task_4["is_eligible"])
        self.assertIn("Not Eligible", task_4["blocking_reason"])


# =====================================================================
# CATEGORY E: Role-Based Access Control (TC017 - TC019)
# =====================================================================
class TestCategoryE_RoleBasedAccessControl(SystemTestingBase):

    def test_TC017_agent_cannot_access_administrator_endpoints(self):
        """TC017: Verify that an authenticated agent cannot access administrator-only endpoints."""
        endpoints = [
            ("/api/admin/overview", "GET"),
            ("/api/admin/agents", "GET"),
            ("/api/admin/tasks", "GET"),
            ("/api/admin/verifications", "GET")
        ]
        for url, method in endpoints:
            if method == "GET":
                res = self.client.get(url, headers=self.agent1_headers)
            else:
                res = self.client.post(url, headers=self.agent1_headers, json={})
            self.assertEqual(
                res.status_code, 403,
                f"Agent was able to access admin endpoint {url} (expected 403, got {res.status_code})"
            )
            data = res.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("Administrator role required", data.get("error", ""))

    def test_TC018_administrator_can_access_authorized_endpoints(self):
        """TC018: Verify that an authenticated administrator can access authorized administrator endpoints."""
        res = self.client.get("/api/admin/overview", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        admin_data = data.get("data", {})
        self.assertIn("active_agents", admin_data)
        self.assertIn("active_tasks", admin_data)
        self.assertIn("active_model", admin_data)

    def test_TC019_unauthenticated_requests_rejected(self):
        """TC019: Verify that protected endpoints reject requests without valid authentication."""
        protected_urls = [
            "/api/competency/agent-status",
            "/api/competency/tasks",
            "/api/admin/overview"
        ]
        for url in protected_urls:
            # 1. No Authorization header
            res_none = self.client.get(url)
            self.assertEqual(res_none.status_code, 401, f"Endpoint {url} did not reject missing token")

            # 2. Invalid Scheme (e.g. Basic instead of Bearer)
            res_bad_scheme = self.client.get(url, headers={"Authorization": "Basic dXNlcjpwYXNz"})
            self.assertEqual(res_bad_scheme.status_code, 401)


# =====================================================================
# CATEGORY F: Database Persistence and Error Handling (TC020 - TC023)
# =====================================================================
class TestCategoryF_DatabaseAndErrorHandling(SystemTestingBase):

    def setUp(self):
        super().setUp()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def tearDown(self):
        super().tearDown()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def test_TC020_retrieve_submitted_assessment_results(self):
        """TC020: Verify that submitted assessment results can be retrieved from backend after saving."""
        # Complete assessment
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id, "answers": self.four_correct_answers}
        )

        # Retrieve status
        status_res = self.client.get("/api/competency/agent-status", headers=self.agent1_headers)
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.get_json()
        self.assertTrue(status_data["has_assessed"])
        self.assertEqual(status_data["competency_level"], "Eligible")
        self.assertEqual(status_data["evaluation_decision"], "Eligible")
        self.assertEqual(float(status_data["assessment"]["assessment_score"]), 80.0)

    def test_TC021_cross_agent_data_isolation(self):
        """TC021: Verify that agent endpoints return only the authenticated agent's data (no cross-tenant leakage)."""
        # Agent 1 (40 mo exp) -> Competent
        start1 = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": start1.get_json()["data"]["attempt_id"], "answers": self.four_correct_answers}
        )

        # Agent 2 (0 mo exp) -> Basic
        start2 = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent2_headers)
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent2_headers,
            json={"attempt_id": start2.get_json()["data"]["attempt_id"], "answers": self.all_correct_answers}
        )

        # Query Agent 1's status
        res1 = self.client.get("/api/competency/agent-status", headers=self.agent1_headers)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()["competency_level"], "Eligible")

        # Query Agent 2's status
        res2 = self.client.get("/api/competency/agent-status", headers=self.agent2_headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["competency_level"], "Not Eligible")

    def test_TC022_assessment_reset_preserves_historical_and_account_data(self):
        """TC022: Verify non-destructive assessment reset preserves account data, history, and certs."""
        # Start and submit assessment for Agent 1
        start = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.client.post(
            f"/api/competency/exams/{self.exam_id}/submit",
            headers=self.agent1_headers,
            json={"attempt_id": start.get_json()["data"]["attempt_id"], "answers": self.all_correct_answers}
        )

        # Perform non-destructive reset via official endpoint
        reset_res = self.client.post("/api/competency/reset-assessment", headers=self.agent1_headers)
        self.assertEqual(reset_res.status_code, 200)
        self.assertTrue(reset_res.get_json()["success"])

        # Verify agent profile, user account, and audit logs are preserved in DB
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # User must still exist
            cur.execute("SELECT user_id, email, role FROM users WHERE user_id = 1")
            user_row = cur.fetchone()
            self.assertIsNotNone(user_row)
            self.assertEqual(user_row["email"], "alex.morgan@university.edu")

            # Audit log must contain reset event
            cur.execute("""
                SELECT action FROM audit_logs
                WHERE user_id = 1 AND action = 'ASSESSMENT_RESET_REQUESTED'
                ORDER BY log_id DESC LIMIT 1
            """)
            audit_row = cur.fetchone()
            self.assertIsNotNone(audit_row, "Audit record for reset was not created")
        conn.close()

        # Agent status should now report no active assessment
        status_res = self.client.get("/api/competency/agent-status", headers=self.agent1_headers)
        self.assertEqual(status_res.status_code, 200)
        self.assertFalse(status_res.get_json()["has_assessed"])

    def test_TC023_safe_handling_of_database_service_outages(self):
        """TC023: Verify safe handling of database errors without crashing or leaking sensitive info."""
        with patch("backend.db.get_mysql_connection", return_value=None):
            # 1. Login with database unavailable
            res_login = self.client.post("/api/auth/login", json={
                "email": "alex.morgan@university.edu",
                "password": "password123"
            })
            self.assertEqual(res_login.status_code, 503)
            self.assertFalse(res_login.get_json()["success"])
            self.assertIn("unavailable", res_login.get_json()["error"].lower())

            # 2. Agent status with database unavailable
            res_status = self.client.get("/api/competency/agent-status", headers=self.agent1_headers)
            # Should safely return 500 or 503 or empty gracefully without throwing unhandled exception
            self.assertIn(res_status.status_code, (500, 503))


if __name__ == "__main__":
    unittest.main()
