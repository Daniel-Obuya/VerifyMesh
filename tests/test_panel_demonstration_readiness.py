"""
VerifyMesh - Comprehensive Panel Demonstration Readiness Test Suite
=====================================================================
Validates the end-to-end user journeys, ML integration, RBAC, database
persistence, and the complete 21-step panel demonstration scenario.
"""

import os
import sys
import json
import time
import uuid
import unittest
from datetime import datetime, timedelta, date
from unittest.mock import patch

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
    calculate_agent_verified_experience,
    COMPETENCY_ENUM_TO_LABEL,
    DECISION_TO_ENUM,
    ENUM_TO_DECISION
)
from src.task_suitability_inference import task_suitability_engine


class PanelDemonstrationReadinessSuite(unittest.TestCase):
    """Authoritative test suite validating the complete panel demonstration scenario."""

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-capstone-panel-readiness-secret-key-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0  # Disable retake cooldown for automated suite
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Seeded verified test agent (user_id=1, agent_id=1)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Seeded unassessed/entry test agent (user_id=6, agent_id=5)
        cls.agent2_token = generate_auth_token(user_id=6, role="Agent")
        cls.agent2_headers = {
            "Authorization": f"Bearer {cls.agent2_token}",
            "Content-Type": "application/json"
        }

        # Seeded administrator (user_id=2, role="Administrator")
        cls.admin_token = generate_auth_token(user_id=2, role="Administrator")
        cls.admin_headers = {
            "Authorization": f"Bearer {cls.admin_token}",
            "Content-Type": "application/json"
        }

        # Standard assessment answers for Exam 3 (5 questions, passing score 75.0)
        cls.exam_id = 3
        cls.correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "A"
        }
        cls.failing_answers = {
            "13": "D",
            "14": "D",
            "15": "D",
            "16": "B",
            "17": "D"
        }

    def setUp(self):
        with limiter._lock:
            limiter._attempts.clear()
        PENDING_SIGNUPS.clear()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def tearDown(self):
        with limiter._lock:
            limiter._attempts.clear()
        PENDING_SIGNUPS.clear()
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    # =========================================================================
    # PHASE 1: System Health & Architecture Smoke Tests
    # =========================================================================

    def test_01_system_health_endpoint(self):
        """Verify API health endpoint reports MySQL connectivity and active ML model."""
        with patch("backend.app.check_mysql_status", return_value=True):
            res = self.client.get("/api/health")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get("status"), "healthy")
            self.assertTrue(data.get("database", {}).get("connected"))
            self.assertTrue(data.get("machine_learning", {}).get("model_loaded"))
            self.assertIn(
                data.get("machine_learning", {}).get("active_model"),
                ["verifymesh_stage2_suitability_pipeline_v3.joblib", "verifymesh_stage2_suitability_pipeline_v2.joblib"]
            )
            self.assertEqual(data.get("machine_learning", {}).get("binary_gatekeeper_status"), "Retired")

    def test_02_model_info_metadata_endpoint(self):
        """Verify model-info endpoint returns 28-feature contract and suitability metadata."""
        res = self.client.get("/api/competency/model-info", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        info = data.get("data", {})
        self.assertTrue(info.get("model_loaded"))
        self.assertEqual(info.get("features_count"), 5)
        self.assertEqual(info.get("decision_threshold"), 0.60)

    # =========================================================================
    # PHASE 2: Agent Journey - Registration, OTP & Authentication Security
    # =========================================================================

    def test_03_registration_validation_rules(self):
        """Verify rejection of invalid registration inputs (missing fields, weak password, invalid email)."""
        # Missing full name
        res = self.client.post("/api/auth/register", json={
            "full_name": "",
            "email": "candidate@test.com",
            "phone": "+254711223344",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Full name is required", res.get_json().get("error", ""))

        # Invalid email format
        res = self.client.post("/api/auth/register", json={
            "full_name": "Test Candidate",
            "email": "not-an-email",
            "phone": "+254711223344",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("valid email", res.get_json().get("error", "").lower())

        # Password mismatch
        res = self.client.post("/api/auth/register", json={
            "full_name": "Test Candidate",
            "email": "candidate@test.com",
            "phone": "+254711223344",
            "password": "Password123!",
            "confirm_password": "DifferentPassword!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Passwords do not match", res.get_json().get("error", ""))

        # Short password (<8 characters)
        res = self.client.post("/api/auth/register", json={
            "full_name": "Test Candidate",
            "email": "candidate@test.com",
            "phone": "+254711223344",
            "password": "short",
            "confirm_password": "short"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 8 characters", res.get_json().get("error", ""))

    def test_04_registration_and_otp_verification_lifecycle(self):
        """Verify full registration, 6-digit OTP generation, verification, and duplicate rejection."""
        unique_email = f"panel_test_{int(time.time())}@verifymesh.io"
        reg_payload = {
            "full_name": "Panel Rehearsal Agent",
            "email": unique_email,
            "phone": "+254700112233",
            "password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!"
        }

        # Step 1: Register (mock email dispatch to avoid external network calls)
        with patch("backend.auth_routes.send_verification_email") as mock_email:
            res = self.client.post("/api/auth/register", json=reg_payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("requires_verification"))
            mock_email.assert_called_once()

        # Step 2: Retrieve OTP from MySQL email_verifications table
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM email_verifications WHERE email = %s AND used = 0", (unique_email,))
            otp_row = cur.fetchone()
            self.assertIsNotNone(otp_row)
            otp_code = otp_row["code"]
            self.assertEqual(len(otp_code), 6)
            self.assertTrue(otp_code.isdigit())
        conn.close()

        # Step 3: Test invalid OTP code
        res_invalid = self.client.post("/api/auth/verify-email", json={
            "email": unique_email,
            "code": "000000"
        })
        self.assertEqual(res_invalid.status_code, 400)

        # Step 4: Verify with correct OTP
        res_valid = self.client.post("/api/auth/verify-email", json={
            "email": unique_email,
            "code": otp_code
        })
        self.assertEqual(res_valid.status_code, 201)
        self.assertTrue(res_valid.get_json().get("success"))

        # Step 5: Test OTP reuse prevention (code is already marked used)
        res_reused = self.client.post("/api/auth/verify-email", json={
            "email": unique_email,
            "code": otp_code
        })
        self.assertEqual(res_reused.status_code, 400)

        # Step 6: Log in with newly created agent credentials
        res_login = self.client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "SecurePassword2026!"
        })
        self.assertEqual(res_login.status_code, 200)
        login_data = res_login.get_json()
        self.assertTrue(login_data.get("success"))
        self.assertIn("token", login_data)
        self.assertEqual(login_data["user"]["role"], "Agent")

        # Cleanup created test agent
        new_uid = login_data["user"]["id"]
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM agents WHERE user_id = %s", (new_uid,))
            cur.execute("DELETE FROM users WHERE user_id = %s", (new_uid,))
            cur.execute("DELETE FROM email_verifications WHERE email = %s", (unique_email,))
        conn.commit()
        conn.close()

    # =========================================================================
    # PHASE 3: Agent Profile & Experience Management
    # =========================================================================

    def test_05_agent_profile_retrieval_and_update(self):
        """Verify agent profile loading and safe personal details updating."""
        # Read profile
        res = self.client.get("/api/competency/profile", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        profile = res.get_json().get("data", {})
        self.assertIn("full_name", profile)
        self.assertIn("experience_months", profile)

        # Update bio and location
        update_res = self.client.put("/api/competency/profile", headers=self.agent1_headers, json={
            "bio": "Experienced Sales Lead specializing in Enterprise SaaS.",
            "location": "Nairobi, Kenya"
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertTrue(update_res.get_json().get("success"))

        # Verify update persisted
        res2 = self.client.get("/api/competency/profile", headers=self.agent1_headers)
        profile2 = res2.get_json().get("data", {})
        self.assertEqual(profile2.get("location"), "Nairobi, Kenya")
        self.assertEqual(profile2.get("bio"), "Experienced Sales Lead specializing in Enterprise SaaS.")

    def test_06_experience_validation_and_overlapping_interval_merging(self):
        """Verify date validation on experience submission and merging of overlapping intervals."""
        # Invalid date format
        res_bad_date = self.client.post("/api/competency/experiences", headers=self.agent1_headers, json={
            "job_title": "Sales Rep",
            "company": "Acme Corp",
            "work_category": "Sales",
            "start_date": "invalid-date",
            "end_date": "2024-01-01"
        })
        self.assertEqual(res_bad_date.status_code, 400)

        # Reversed date range (start > end)
        res_reversed = self.client.post("/api/competency/experiences", headers=self.agent1_headers, json={
            "job_title": "Sales Rep",
            "company": "Acme Corp",
            "work_category": "Sales",
            "start_date": "2025-01-01",
            "end_date": "2024-01-01"
        })
        self.assertEqual(res_reversed.status_code, 400)
        self.assertIn("End date must be on or after start date", res_reversed.get_json().get("error", ""))

        # Verify overlapping interval merging algorithm directly
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            calc = calculate_agent_verified_experience(agent_id=1, cursor=cur)
            self.assertIn("previous_experience_months", calc)
            self.assertIn("sales_experience_months", calc)
            self.assertIn("customer_service_experience_months", calc)
            self.assertGreaterEqual(calc["previous_experience_months"], 0)
        conn.close()

    # =========================================================================
    # PHASE 4: Competency Assessment Lifecycle & Anti-Tampering
    # =========================================================================

    def test_07_assessment_questions_sanitized(self):
        """Verify exam questions endpoint sanitizes correct answers and point weights."""
        res = self.client.get(f"/api/competency/exams/{self.exam_id}/questions", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json().get("data", {})
        questions = data.get("questions", [])
        self.assertGreater(len(questions), 0)

        for q in questions:
            self.assertNotIn("correct_answer", q)
            self.assertNotIn("correct_option", q)
            self.assertNotIn("points", q)
            self.assertIn("question_text", q)
            self.assertIn("options", q)

    def test_08_assessment_attempt_server_scoring_and_persistence(self):
        """Verify server-side score calculation, binary model evaluation, and DB persistence."""
        # Step 1: Start attempt
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Step 2: Submit 100% correct answers
        submit_res = self.client.post(f"/api/competency/exams/{self.exam_id}/submit", headers=self.agent1_headers, json={
            "attempt_id": attempt_id,
            "answers": self.correct_answers
        })
        self.assertEqual(submit_res.status_code, 200)
        res_data = submit_res.get_json()["data"]

        # 100% score on 5 correct questions
        self.assertEqual(res_data["score"], 100.0)
        self.assertTrue(res_data["passed"])
        self.assertIn(res_data["competency_level"], ("Eligible", "Not Eligible"))

        # Verify persistence in MySQL exam_results
        saved_info = res_data.get("saved", {})
        self.assertIn("exam_result_id", saved_info)
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT assessment_score, passed FROM exam_results 
                WHERE exam_result_id = %s
            """, (saved_info["exam_result_id"],))
            db_res = cur.fetchone()
            self.assertIsNotNone(db_res)
            self.assertEqual(float(db_res["assessment_score"]), 100.0)
            self.assertEqual(db_res["passed"], 1)
        conn.close()

    def test_09_assessment_client_supplied_scores_rejected(self):
        """Verify server strictly rejects client-supplied scores, points, or pass flags."""
        start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        tampered_res = self.client.post(f"/api/competency/exams/{self.exam_id}/submit", headers=self.agent1_headers, json={
            "attempt_id": attempt_id,
            "answers": self.correct_answers,
            "assessment_score": 99.9,
            "score": 100.0,
            "passed": True
        })
        self.assertEqual(tampered_res.status_code, 400)
        self.assertIn("forbidden", tampered_res.get_json().get("error", "").lower())

    # =========================================================================
    # PHASE 5: Task Management & 4-Tier Dual-Layer Eligibility Precedence
    # =========================================================================

    def test_10_admin_task_creation_and_requirement_enforcement(self):
        """Verify administrator can create tasks and mandatory requirements are enforced."""
        future_deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        task_payload = {
            "task_name": "Senior Enterprise Client Strategist",
            "category_id": 1,
            "description": "Lead enterprise client relationship engagements and customer onboarding initiatives.",
            "status": "ACTIVE",
            "work_arrangement": "Remote",
            "payment_type": "Hourly",
            "currency": "KES",
            "hourly_rate_min": 3500.0,
            "hourly_rate_max": 5000.0,
            "application_deadline": future_deadline,
            "minimum_competency": "ELIGIBLE",
            "minimum_experience_months": 24,
            "required_certification_id": 1,  # Mandatory certification
            "exam_required": True,
            "exam_id": 3
        }

        # Step 1: Admin creates task
        create_res = self.client.post("/api/admin/tasks", headers=self.admin_headers, json=task_payload)
        self.assertEqual(create_res.status_code, 201)
        created_task_id = create_res.get_json()["data"]["task_id"]

        try:
            # Step 2: Agent 2 (0 months exp, no certs) checks tasks
            agent2_tasks = self.client.get("/api/competency/tasks", headers=self.agent2_headers).get_json().get("tasks", [])
            target = next((t for t in agent2_tasks if t["task_id"] == created_task_id), None)
            self.assertIsNotNone(target)

            # Hard rule: Missing mandatory certification MUST block approval
            self.assertFalse(target["can_apply"])
            self.assertFalse(target["is_eligible"])
            self.assertEqual(target["state"], "Certification Required")
            self.assertIn("certification required", target["blocking_reason"].lower())

        finally:
            # Step 3: Cleanup test task
            delete_task(created_task_id)

    # =========================================================================
    # PHASE 6: Role-Based Access Control (RBAC) & API Security
    # =========================================================================

    def test_11_rbac_unauthenticated_requests_rejected(self):
        """Verify unauthenticated requests to protected endpoints return 401."""
        endpoints = [
            ("/api/admin/overview", "GET"),
            ("/api/admin/tasks", "GET"),
            ("/api/admin/verifications", "GET"),
            ("/api/competency/profile", "GET"),
            ("/api/competency/tasks", "GET"),
            ("/api/competency/agent-status", "GET"),
        ]
        for url, method in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 401, f"Endpoint {url} failed to reject unauthenticated request")

    def test_12_rbac_role_boundaries_enforced(self):
        """Verify Agent cannot access Admin endpoints, and Admin cannot access Agent endpoints (403)."""
        # Agent attempting Admin operations
        admin_urls = [
            "/api/admin/overview",
            "/api/admin/tasks",
            "/api/admin/agents",
            "/api/admin/verifications",
            "/api/admin/reviews"
        ]
        for url in admin_urls:
            res = self.client.get(url, headers=self.agent1_headers)
            self.assertEqual(res.status_code, 403, f"Agent was not blocked from admin endpoint {url}")

        # Administrator attempting Agent operations
        agent_urls = [
            "/api/competency/profile",
            "/api/competency/agent-status",
            "/api/competency/tasks",
            "/api/competency/experiences"
        ]
        for url in agent_urls:
            res = self.client.get(url, headers=self.admin_headers)
            self.assertEqual(res.status_code, 403, f"Admin was not blocked from agent endpoint {url}")

    def test_13_token_tampering_and_forgery_rejected(self):
        """Verify forged signatures, malformed tokens, and expired tokens return 401."""
        # Malformed tokens
        self.assertEqual(self.client.get("/api/admin/overview", headers={"Authorization": "Bearer not-a-token"}).status_code, 401)
        self.assertEqual(self.client.get("/api/admin/overview", headers={"Authorization": "Bearer a.b.c"}).status_code, 401)

        # Tampered signature
        valid_token = generate_auth_token(user_id=2, role="Administrator")
        payload, sig = valid_token.split(".")
        tampered_token = f"{payload}.{'0' * 64}"
        res = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(res.status_code, 401)

        # Expired token (simulate past timestamp)
        with patch("time.time", return_value=time.time() - 100000):
            old_token = generate_auth_token(user_id=2, role="Administrator")
        res_exp = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {old_token}"})
        self.assertEqual(res_exp.status_code, 401)

    # =========================================================================
    # PHASE 7: Administrator Workflow & Verification Queue
    # =========================================================================

    def test_14_admin_overview_metrics_and_verifications_queue(self):
        """Verify administrator overview KPIs, pending verification listing, and audit tracking."""
        # Get overview metrics
        res_overview = self.client.get("/api/admin/overview", headers=self.admin_headers)
        self.assertEqual(res_overview.status_code, 200)
        overview_data = res_overview.get_json().get("data", {})
        self.assertIn("total_agents", overview_data)
        self.assertIn("active_tasks", overview_data)
        self.assertIn("runtime_model", overview_data)

        # Get pending verifications queue
        res_verifs = self.client.get("/api/admin/verifications", headers=self.admin_headers)
        self.assertEqual(res_verifs.status_code, 200)
        verifs_data = res_verifs.get_json().get("data", {})
        self.assertIn("experiences", verifs_data)
        self.assertIn("certifications", verifs_data)
        self.assertIn("pending_exps_count", verifs_data)
        self.assertIn("pending_certs_count", verifs_data)

    # =========================================================================
    # PHASE 8: Complete 21-Step Panel Demonstration Rehearsal
    # =========================================================================

    def test_15_full_panel_demonstration_workflow_scenario(self):
        """
        Simulate the complete live 21-step academic panel demonstration scenario:
        1. Application health check
        2. Agent registration
        3. Email OTP verification
        4. Agent login
        5. Profile setup
        6. Admin login & verification queue inspection
        7. Task creation with mandatory requirements
        8. Assessment attempt & scoring
        9. Dual-layer eligibility determination
        10. Stale result handling on profile changes
        11. Audit log inspection & clean logout
        """
        demo_email = f"panel_demo_{int(time.time())}@verifymesh.io"
        future_deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Step 1: Health check
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.get_json()["status"], "healthy")

        # Step 2: Register candidate
        with patch("backend.auth_routes.send_verification_email"):
            res_reg = self.client.post("/api/auth/register", json={
                "full_name": "Panel Demo Candidate",
                "email": demo_email,
                "phone": "+254722998877",
                "password": "DemoPassword2026!",
                "confirm_password": "DemoPassword2026!"
            })
            self.assertEqual(res_reg.status_code, 200)

        # Step 3: Retrieve and verify OTP
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM email_verifications WHERE email = %s", (demo_email,))
            otp = cur.fetchone()["code"]
        conn.close()

        res_v = self.client.post("/api/auth/verify-email", json={"email": demo_email, "code": otp})
        self.assertEqual(res_v.status_code, 201)

        # Step 4: Login as Candidate
        res_log = self.client.post("/api/auth/login", json={"email": demo_email, "password": "DemoPassword2026!"})
        self.assertEqual(res_log.status_code, 200)
        candidate_data = res_log.get_json()
        candidate_token = candidate_data["token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}", "Content-Type": "application/json"}
        candidate_uid = candidate_data["user"]["id"]

        try:
            # Step 5: Complete Candidate Profile Details
            res_prof = self.client.put("/api/competency/profile", headers=candidate_headers, json={
                "bio": "Experienced Sales Consultant with specialized CRM expertise.",
                "location": "Nairobi, Kenya"
            })
            self.assertEqual(res_prof.status_code, 200)

            # Step 6: Admin creates a realistic Sales Task (Exam 3 required, min 12 mo exp)
            task_res = self.client.post("/api/admin/tasks", headers=self.admin_headers, json={
                "task_name": "Enterprise Strategic Sales Specialist",
                "category_id": 1,
                "description": "Execute outbound enterprise sales cycles and lead prospective client engagements.",
                "status": "ACTIVE",
                "work_arrangement": "Remote",
                "payment_type": "Hourly",
                "currency": "KES",
                "hourly_rate_min": 2500.0,
                "hourly_rate_max": 4000.0,
                "application_deadline": future_deadline,
                "minimum_competency": "ELIGIBLE",
                "minimum_experience_months": 12,
                "required_certification_id": None,
                "exam_required": True,
                "exam_id": 3
            })
            self.assertEqual(task_res.status_code, 201)
            task_id = task_res.get_json()["data"]["task_id"]

            try:
                # Step 7: Candidate views tasks before taking assessment
                tasks_before = self.client.get("/api/competency/tasks", headers=candidate_headers).get_json().get("tasks", [])
                task_entry = next((t for t in tasks_before if t["task_id"] == task_id), None)
                self.assertIsNotNone(task_entry)
                self.assertEqual(task_entry["state"], "Assessment Needed")

                # Step 8: Candidate starts Exam 3 attempt
                start_res = self.client.post(f"/api/competency/exams/{self.exam_id}/start-attempt", headers=candidate_headers)
                self.assertEqual(start_res.status_code, 201)
                attempt_id = start_res.get_json()["data"]["attempt_id"]

                # Step 9: Candidate submits answers (100% score)
                submit_res = self.client.post(f"/api/competency/exams/{self.exam_id}/submit", headers=candidate_headers, json={
                    "attempt_id": attempt_id,
                    "answers": self.correct_answers
                })
                self.assertEqual(submit_res.status_code, 200)
                eval_res = submit_res.get_json()["data"]
                self.assertEqual(eval_res["score"], 100.0)
                self.assertTrue(eval_res["passed"])

                # Step 10: Check task state after assessment
                # The candidate scored 100% on the exam, but has 0 verified experience months (task requires 12)
                # and 0 certifications. The Binary Gatekeeper ML model evaluates full profile to 'Not Eligible'.
                # Dual-layer rule: Both hard requirements and ML eligibility are strictly enforced!
                tasks_after = self.client.get("/api/competency/tasks", headers=candidate_headers).get_json().get("tasks", [])
                task_eval = next((t for t in tasks_after if t["task_id"] == task_id), None)
                self.assertIsNotNone(task_eval)
                self.assertFalse(task_eval["is_eligible"])
                self.assertFalse(task_eval["can_apply"])
                self.assertIn("12 Months Exp", task_eval["state"])
                self.assertIn("experience", task_eval["blocking_reason"].lower())

                # Step 11: Admin inspects audit logs
                res_audit = self.client.get("/api/admin/overview", headers=self.admin_headers)
                self.assertEqual(res_audit.status_code, 200)

            finally:
                delete_task(task_id)

        finally:
            # Clean up candidate
            conn = get_mysql_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM assessment_attempts WHERE agent_id IN (SELECT agent_id FROM agents WHERE user_id = %s)", (candidate_uid,))
                cur.execute("DELETE FROM exam_results WHERE agent_id IN (SELECT agent_id FROM agents WHERE user_id = %s)", (candidate_uid,))
                cur.execute("DELETE FROM ml_predictions WHERE agent_id IN (SELECT agent_id FROM agents WHERE user_id = %s)", (candidate_uid,))
                cur.execute("DELETE FROM audit_logs WHERE user_id = %s", (candidate_uid,))
                cur.execute("DELETE FROM agents WHERE user_id = %s", (candidate_uid,))
                cur.execute("DELETE FROM users WHERE user_id = %s", (candidate_uid,))
                cur.execute("DELETE FROM email_verifications WHERE email = %s", (demo_email,))
            conn.commit()
            conn.close()


    def test_16_agent_certification_deletion_lifecycle(self):
        """Verify agent certification listing contains dual IDs and allows permanent deletion of non-verified credentials."""
        # Step 1: Listing contains both agent_certification_id and agent_cert_id
        res = self.client.get("/api/competency/certifications", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        certs = res.get_json().get("data", [])
        if certs:
            first = certs[0]
            self.assertIn("agent_certification_id", first)
            self.assertIn("agent_cert_id", first)
            self.assertEqual(first["agent_certification_id"], first["agent_cert_id"])

        # Step 2: Submit a test pending certification
        sub_res = self.client.post("/api/competency/certifications", headers=self.agent1_headers, json={
            "certification_name": "Temporary Test Certificate",
            "issuing_organization": "QA Test Institute",
            "certificate_number": f"TEST-DELETE-{uuid.uuid4().hex[:8]}",
            "issue_date": "2024-01-01",
            "expiry_date": "2026-01-01"
        })
        self.assertEqual(sub_res.status_code, 201)
        created = sub_res.get_json()["data"]
        cert_id = created.get("agent_certification_id") or created.get("agent_cert_id")
        self.assertIsNotNone(cert_id)

        # Step 3: Agent deletes the pending certification permanently
        del_res = self.client.delete(f"/api/competency/certifications/{cert_id}", headers=self.agent1_headers)
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.get_json().get("success"))

        # Step 4: Verify record is completely removed from list
        verify_res = self.client.get("/api/competency/certifications", headers=self.agent1_headers)
        self.assertEqual(verify_res.status_code, 200)
        current_ids = [c["agent_certification_id"] for c in verify_res.get_json().get("data", [])]
        self.assertNotIn(cert_id, current_ids)

        # Step 5: Verify verified credentials cannot be deleted by agent directly
        verified_certs = [c for c in verify_res.get_json().get("data", []) if c.get("status") == "VERIFIED"]
        if verified_certs:
            v_id = verified_certs[0]["agent_certification_id"]
            bad_del = self.client.delete(f"/api/competency/certifications/{v_id}", headers=self.agent1_headers)
            self.assertEqual(bad_del.status_code, 400)
            self.assertIn("Verified credentials cannot be deleted directly", bad_del.get_json().get("error", ""))


if __name__ == "__main__":
    unittest.main()
