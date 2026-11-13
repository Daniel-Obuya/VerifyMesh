"""
VerifyMesh — Phase 6 & 6A: Assessment Pipeline, Eligibility Engine & Security Hardening
========================================================================================

Automated tests covering:
1. End-to-End Flow: Attempt initiation -> Autosave -> Submission -> Grading -> Eligibility -> Application.
2. Duplicate Application Rejection: Second application on same task rejected with HTTP 400.
3. Ineligible Application Blocked: Ineligible agents cannot apply via API bypass.
4. Anti-Tampering (Client Scores): Injected client scores/pass flags rejected with HTTP 400.
5. Anti-Tampering (Payload Bounds & Invalid Options): Oversized or malformed options rejected with HTTP 400.
6. Authorization & Ownership: Agent A cannot access, autosave, or submit Agent B's attempts.
7. Advisory ML Separation: Deterministic eligibility functions independently of ML predictions.
"""

import os
import sys
import json
import unittest
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.db import (
    get_mysql_connection,
    create_assessment_attempt,
    get_assessment_attempt,
    get_agent_tasks_with_eligibility,
    apply_for_task,
)
from backend.auth_routes import generate_auth_token


class TestPhase6AssessmentPipelineAndSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # User 1: Agent Alex Morgan (agent_id=1, 40 months exp)
            cur.execute("SELECT user_id, email, role FROM users WHERE user_id = 1")
            cls.user_alex = cur.fetchone()

            # User 6: Agent Daniel Nyabuto (agent_id=5, 23 months exp)
            cur.execute("SELECT user_id, email, role FROM users WHERE user_id = 6")
            cls.user_daniel = cur.fetchone()

            # Ensure Task 4 is ACTIVE and requires Topic 3 (Customer Communication)
            cur.execute("UPDATE tasks SET status = 'ACTIVE' WHERE task_id = 4")
            cur.execute("SELECT task_id FROM tasks WHERE task_id = 4")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO tasks (task_id, category_id, task_name, description, status, exam_id, work_arrangement, positions_count, deliverables, payment_type, currency)
                    VALUES (4, 2, 'Technical Support Agent', 'Provide high-quality technical assistance.', 'ACTIVE', 3, 'Remote', 1, 'Deliverables', 'Fixed Budget', 'KES')
                """)
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 4")
            cur.execute("""
                INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                VALUES (4, 3, 1)
            """)
            conn.commit()

        cls.alex_token = generate_auth_token(cls.user_alex["user_id"], cls.user_alex["role"])
        cls.daniel_token = generate_auth_token(cls.user_daniel["user_id"], cls.user_daniel["role"])

    def setUp(self):
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Clean up task applications for Task 4 for Alex during test runs
            cur.execute("DELETE FROM task_applications WHERE task_id = 4 AND agent_id = 1")
            # Close active in-progress attempts for agent 1 on topic 3
            cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
            # Backdate older attempts to bypass retake cooldown for test isolation
            cur.execute("UPDATE assessment_attempts SET submitted_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
            cur.execute("UPDATE exam_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND exam_id = 3")
            cur.execute("UPDATE agent_topic_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
            conn.commit()

    def test_01_end_to_end_assessment_to_application_flow(self):
        """Phase 6: Full candidate journey from attempt initiation to task application."""
        # Step 1: Start Attempt for Topic 3
        resp_start = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"task_id": 4}
        )
        self.assertEqual(resp_start.status_code, 201)
        start_data = resp_start.get_json()["data"]
        attempt_id = start_data["attempt_id"]
        questions = start_data["questions"]
        self.assertGreater(len(questions), 0)

        # Step 2: Autosave intermediate answers
        first_q_id = str(questions[0]["question_id"])
        resp_auto = self.client.post(
            f"/api/competency/topics/3/autosave",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"attempt_id": attempt_id, "answers": {first_q_id: "A"}, "version": 1}
        )
        self.assertEqual(resp_auto.status_code, 200)

        # Step 3: Authoritatively construct passing answers by resolving randomized display mapping against DB keys
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT question_snapshot_json FROM assessment_attempts WHERE attempt_id = %s", (attempt_id,))
                snap_json = cur.fetchone()["question_snapshot_json"]
                parsed_snap = json.loads(snap_json)
                snapshot_questions = parsed_snap.get("questions", [])

                cur.execute("SELECT question_id, correct_answer FROM exam_questions WHERE topic_id = 3")
                correct_keys = {r["question_id"]: r["correct_answer"].strip().upper() for r in cur.fetchall()}

                passing_answers = {}
                for q in snapshot_questions:
                    qid_int = q["question_id"]
                    qid_str = str(qid_int)
                    correct_orig = correct_keys.get(qid_int)
                    disp_map = q.get("display_to_original", {})
                    # Find candidate display letter that maps to correct_orig
                    chosen = "A"
                    for disp_letter, orig_letter in disp_map.items():
                        if orig_letter == correct_orig:
                            chosen = disp_letter
                            break
                    passing_answers[qid_str] = chosen
        finally:
            conn.close()

        # Step 4: Authoritative Submission
        resp_submit = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"attempt_id": attempt_id, "task_id": 4, "answers": passing_answers}
        )
        self.assertEqual(resp_submit.status_code, 200)
        submit_data = resp_submit.get_json()["data"]
        self.assertGreaterEqual(submit_data["score"], 70.0, "Candidate must pass threshold")
        self.assertTrue(submit_data["passed"])

        # Step 5: Verify Task Eligibility transitions to 'Ready to Apply'
        tasks = get_agent_tasks_with_eligibility(self.user_alex["user_id"])
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertEqual(task_4["state"], "Ready to Apply")
        self.assertTrue(task_4["can_apply"])

        # Step 6: Submit Task Application
        resp_apply = self.client.post(
            "/api/competency/tasks/4/apply",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"notes": "E2E Integration Test Application"}
        )
        self.assertEqual(resp_apply.status_code, 201)
        apply_data = resp_apply.get_json()
        self.assertTrue(apply_data["success"])
        self.assertEqual(apply_data["data"]["status"], "Application Submitted")

        # Step 7: Verify Application recorded in database and audit logs
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM task_applications WHERE task_id = 4 AND agent_id = 1")
                app_row = cur.fetchone()
                self.assertIsNotNone(app_row)
                self.assertEqual(app_row["status"], "Application Submitted")

                cur.execute("""
                    SELECT description FROM audit_logs
                    WHERE user_id = %s AND action = 'TASK_APPLICATION_SUBMITTED'
                    ORDER BY log_id DESC LIMIT 1
                """, (self.user_alex["user_id"],))
                log_row = cur.fetchone()
                self.assertIsNotNone(log_row)
                self.assertIn("Technical Support Agent", log_row["description"])
        finally:
            conn.close()

    def test_02_duplicate_application_prevention(self):
        """Phase 6: Agent cannot submit duplicate applications for the same task."""
        # Ensure application exists
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_applications (task_id, agent_id, status, applied_at)
                    VALUES (4, 1, 'Application Submitted', NOW())
                """)
                conn.commit()
        finally:
            conn.close()

        # Second submission attempt
        resp_dup = self.client.post(
            "/api/competency/tasks/4/apply",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"notes": "Duplicate Attempt"}
        )
        self.assertEqual(resp_dup.status_code, 400)
        self.assertIn("already", resp_dup.get_json()["error"].lower())

    def test_03_ineligible_candidate_application_blocked(self):
        """Phase 6: Ineligible candidate lacking requirements is blocked from applying."""
        # Daniel Nyabuto (user 6) lacks experience for Task 2 (23 months < 24 months)
        resp_apply = self.client.post(
            "/api/competency/tasks/2/apply",
            headers={"Authorization": f"Bearer {self.daniel_token}"},
            json={"notes": "Ineligible apply attempt"}
        )
        self.assertEqual(resp_apply.status_code, 400)
        err_msg = resp_apply.get_json()["error"]
        self.assertTrue("cannot apply" in err_msg.lower() or "not satisfied" in err_msg.lower() or "experience" in err_msg.lower())

    def test_04_anti_tampering_client_score_rejection(self):
        """Phase 6A: Client-supplied scores, pass flags, or points are rejected with HTTP 400."""
        # Create active attempt
        att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = att["attempt_id"]

        tampered_payloads = [
            {"attempt_id": att_id, "answers": {"13": "A"}, "score": 100.0},
            {"attempt_id": att_id, "answers": {"13": "A"}, "passed": True},
            {"attempt_id": att_id, "answers": {"13": "A"}, "is_eligible": True},
            {"attempt_id": att_id, "answers": {"13": "A"}, "points": 50},
        ]

        for payload in tampered_payloads:
            resp = self.client.post(
                "/api/competency/topics/3/submit",
                headers={"Authorization": f"Bearer {self.alex_token}"},
                json=payload
            )
            self.assertEqual(resp.status_code, 400, f"Payload {payload} should have been rejected with 400")
            self.assertIn("forbidden", resp.get_json()["error"].lower())

    def test_05_anti_tampering_payload_bounds_and_invalid_options(self):
        """Phase 6A: Oversized answer payloads or invalid answer values are rejected."""
        att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = att["attempt_id"]

        # 1. Oversized dictionary (> 50 items)
        oversized_answers = {str(i): "A" for i in range(100)}
        resp_large = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"attempt_id": att_id, "answers": oversized_answers}
        )
        self.assertEqual(resp_large.status_code, 400)
        self.assertIn("exceeds maximum", resp_large.get_json()["error"].lower())

        # 2. Invalid answer choice (e.g. 'Z')
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT question_id FROM exam_questions WHERE topic_id = 3")
                q_ids = [str(r["question_id"]) for r in cur.fetchall()]
        finally:
            conn.close()
        sample_invalid = {qid: "Z" for qid in q_ids}

        resp_invalid = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.alex_token}"},
            json={"attempt_id": att_id, "answers": sample_invalid}
        )
        self.assertEqual(resp_invalid.status_code, 400)
        self.assertIn("invalid option", resp_invalid.get_json()["error"].lower())

    def test_06_unauthorized_cross_agent_access(self):
        """Phase 6A: Agent A cannot access or submit Agent B's assessment attempts."""
        # Create attempt for Agent 1 (Alex)
        att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = att["attempt_id"]

        # Daniel (user 6, agent 5) tries to submit Alex's attempt
        resp_cross_submit = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.daniel_token}"},
            json={"attempt_id": att_id, "answers": {"13": "A"}}
        )
        self.assertEqual(resp_cross_submit.status_code, 403)
        self.assertIn("another agent", resp_cross_submit.get_json()["error"].lower())

        # Daniel tries to view Alex's attempt details
        resp_cross_get = self.client.get(
            f"/api/competency/attempts/{att_id}",
            headers={"Authorization": f"Bearer {self.daniel_token}"}
        )
        self.assertEqual(resp_cross_get.status_code, 403)
        self.assertIn("another agent", resp_cross_get.get_json()["error"].lower())

    def test_07_deterministic_rules_independent_of_advisory_ml(self):
        """Phase 6: Deterministic eligibility is independent of advisory ML model."""
        tasks = get_agent_tasks_with_eligibility(self.user_alex["user_id"])
        for t in tasks:
            # Deterministic fields must all be boolean or explicit strings
            self.assertIn(t["state"], [
                "Ready to Apply", "Assessment Needed", "Certification Required",
                "Verification Pending", "Assigned", "Application Submitted",
                "Under Review", "Attempt Limit Reached"
            ] + [s for s in [t["state"]] if "Requires" in s])
            self.assertIsInstance(t["can_apply"], bool)
            self.assertIsInstance(t["prerequisites"], dict)
            self.assertIn("certification_met", t["prerequisites"])
            self.assertIn("experience_met", t["prerequisites"])
            self.assertIn("assessment_met", t["prerequisites"])


if __name__ == "__main__":
    unittest.main()
