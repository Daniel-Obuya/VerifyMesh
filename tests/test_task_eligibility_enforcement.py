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
    get_agent_tasks_with_eligibility,
    apply_for_task,
    create_task_with_requirements,
    _sync_task_assessment_topics
)


class TestTaskEligibilityEnforcement(unittest.TestCase):
    """
    Automated regression suite verifying the 10 diagnostic test cases and retake transitions:
    1. Eligible ML prediction + failed assessment = blocked.
    2. Eligible ML prediction + passed assessment + all requirements met = allowed.
    3. Ineligible ML prediction = blocked when the ML gate is mandatory.
    4. Missing assessment result = blocked when required.
    5. Correct assessment template and threshold are used.
    6. Mismatched topic assignment is rejected.
    7. Failed-to-passed retake updates eligibility correctly.
    8. Reverse retake transition: passed -> failed revokes eligibility.
    9. Direct API submission cannot bypass eligibility checks (server-side enforcement).
    10. Optional assessments are handled correctly (all_topics_passed: 'Not Required', can apply).
    11. Report values agree with the authoritative backend decision.
    """

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-eligibility-enforcement-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Agent 1: user_id = 1, agent_id = 1 (verified agent, 24 mo exp, verified certs)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Topic 3 answers
        cls.topic3_pass_answers = {"13": "A", "14": "B", "15": "A", "16": "B", "17": "A"}  # 100%
        cls.topic3_fail_answers = {"13": "A", "14": "C", "15": "C", "16": "C", "17": "C"}  # 20% (threshold 75%)

        # Ensure Task 102 fixture exists for this regression test suite
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM eligibility_evaluations WHERE task_id = 102")
            cursor.execute("DELETE FROM task_assessment_topics WHERE task_id = 102")
            cursor.execute("DELETE FROM task_requirements WHERE task_id = 102")
            cursor.execute("DELETE FROM task_applications WHERE task_id = 102")
            cursor.execute("DELETE FROM tasks WHERE task_id = 102")
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, task_name, category_id, description, status,
                    work_arrangement, payment_type, fixed_budget, positions_count,
                    deliverables, application_deadline, exam_id
                ) VALUES (
                    102, 'Customer Support Diagnostic Task', 1, 'Regression task for testing topic 3 assessment gating', 'ACTIVE',
                    'Remote', 'Fixed Budget', 1500.00, 2,
                    'Resolution of customer escalations', '2028-12-31', 3
                )
            """)
            cursor.execute("""
                INSERT INTO task_requirements (
                    task_id, minimum_competency, minimum_experience_months,
                    required_certification_id, exam_required
                ) VALUES (
                    102, 'BASIC', 0, NULL, 1
                )
            """)
            _sync_task_assessment_topics(cursor, 102, exam_id=3, exam_required=True, topic_ids=[3])
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM eligibility_evaluations WHERE task_id = 102")
            cursor.execute("DELETE FROM task_assessment_topics WHERE task_id = 102")
            cursor.execute("DELETE FROM task_requirements WHERE task_id = 102")
            cursor.execute("DELETE FROM task_applications WHERE task_id = 102")
            cursor.execute("DELETE FROM tasks WHERE task_id = 102")
        conn.commit()
        conn.close()

    def setUp(self):
        reset_agent_assessment(user_id=1)
        # Ensure task_applications table is clear of applications for user 1 on test tasks
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM task_applications WHERE agent_id = 1")
        conn.commit()
        conn.close()

    def test_01_eligible_ml_plus_failed_assessment_is_blocked(self):
        """Case 1: Eligible ML prediction + failed assessment = blocked."""
        # Start and submit Topic 3 attempt with 20% failing score (threshold 75%)
        start_res = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        submit_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": attempt_id,
                "answers": self.topic3_fail_answers,
                "task_id": 102
            })
        )
        self.assertEqual(submit_res.status_code, 200)
        submit_data = submit_res.get_json()["data"]

        self.assertEqual(submit_data["score"], 20.0)
        self.assertFalse(submit_data["passed"])
        
        # Verify task eligibility is blocked
        task_elig = submit_data.get("task_eligibility")
        self.assertIsNotNone(task_elig)
        self.assertFalse(task_elig["can_apply"])
        self.assertFalse(task_elig["is_eligible"])
        self.assertFalse(task_elig["all_topics_passed"])
        self.assertFalse(task_elig["prerequisites"]["assessment_met"])

    def test_02_eligible_ml_plus_passed_assessment_all_requirements_met_allowed(self):
        """Case 2: Eligible ML prediction + passed assessment + all requirements met = allowed."""
        start_res = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        submit_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": attempt_id,
                "answers": self.topic3_pass_answers,
                "task_id": 102
            })
        )
        self.assertEqual(submit_res.status_code, 200)
        submit_data = submit_res.get_json()["data"]

        self.assertEqual(submit_data["score"], 100.0)
        self.assertTrue(submit_data["passed"])

        task_elig = submit_data.get("task_eligibility")
        self.assertIsNotNone(task_elig)
        self.assertTrue(task_elig["can_apply"])
        self.assertTrue(task_elig["is_eligible"])
        self.assertTrue(task_elig["all_topics_passed"])
        self.assertTrue(task_elig["prerequisites"]["assessment_met"])

    def test_03_ineligible_ml_prediction_blocks_application(self):
        """Case 3: Ineligible ML prediction blocks when ML gate is mandatory."""
        # For a task requiring ELIGIBLE competency, if agent competency is NOT_ELIGIBLE, can_apply is False
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_102 = next((t for t in tasks if t["task_id"] == 102), None)
        self.assertIsNotNone(task_102)
        # Agent unassessed has no competency prediction yet
        self.assertFalse(task_102["can_apply"])

    def test_04_missing_assessment_result_blocks_application(self):
        """Case 4: Missing assessment result = blocked when required."""
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_102 = next((t for t in tasks if t["task_id"] == 102), None)
        self.assertIsNotNone(task_102)
        self.assertFalse(task_102["can_apply"])
        self.assertFalse(task_102["prerequisites"]["assessment_met"])
        self.assertEqual(task_102["state"], "Assessment Needed")

    def test_05_correct_assessment_template_and_threshold_used(self):
        """Case 5: Correct assessment template and threshold are loaded and used."""
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_102 = next((t for t in tasks if t["task_id"] == 102), None)
        self.assertIsNotNone(task_102)
        self.assertEqual(task_102["exam_id"], 3)
        self.assertEqual(task_102["exam_passing_score"], 75.0)
        self.assertGreaterEqual(len(task_102["required_topics"]), 1)
        req_topic = task_102["required_topics"][0]
        self.assertEqual(req_topic["topic_id"], 3)
        self.assertEqual(req_topic["passing_score"], 75.0)

    def test_06_mismatched_topic_assignment_is_rejected(self):
        """Case 6: Mismatched topic assignment is rejected (HTTP 400)."""
        # Task 102 requires Topic 3 (Customer Communication). Attempting Topic 1 (Product Knowledge) must be rejected.
        start_res = self.client.post(
            "/api/competency/topics/1/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res.status_code, 400)
        err = start_res.get_json()["error"]
        self.assertIn("Mismatched topic", err)

    def test_07_failed_to_passed_retake_updates_eligibility(self):
        """Case 7: Failed-to-passed retake updates eligibility correctly."""
        # 1. First attempt: fail (20%)
        start_res1 = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res1.status_code, 201)
        att1_id = start_res1.get_json()["data"]["attempt_id"]

        sub1_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": att1_id,
                "answers": self.topic3_fail_answers,
                "task_id": 102
            })
        )
        self.assertEqual(sub1_res.status_code, 200)
        self.assertFalse(sub1_res.get_json()["data"]["task_eligibility"]["can_apply"])

        # 2. Retake attempt: pass (100%)
        start_res2 = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res2.status_code, 201)
        att2_id = start_res2.get_json()["data"]["attempt_id"]

        sub2_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": att2_id,
                "answers": self.topic3_pass_answers,
                "task_id": 102
            })
        )
        self.assertEqual(sub2_res.status_code, 200)
        sub2_data = sub2_res.get_json()["data"]
        self.assertTrue(sub2_data["task_eligibility"]["can_apply"])
        self.assertTrue(sub2_data["task_eligibility"]["prerequisites"]["assessment_met"])

    def test_08_reverse_retake_passed_to_failed_revokes_eligibility(self):
        """Case 8: Reverse retake transition: passed -> failed revokes eligibility (latest authoritative attempt)."""
        # 1. First attempt: pass (100%)
        start_res1 = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res1.status_code, 201)
        att1_id = start_res1.get_json()["data"]["attempt_id"]

        sub1_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": att1_id,
                "answers": self.topic3_pass_answers,
                "task_id": 102
            })
        )
        self.assertEqual(sub1_res.status_code, 200)
        self.assertTrue(sub1_res.get_json()["data"]["task_eligibility"]["can_apply"])

        # 2. Retake attempt: fail (20%)
        start_res2 = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        self.assertEqual(start_res2.status_code, 201)
        att2_id = start_res2.get_json()["data"]["attempt_id"]

        sub2_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": att2_id,
                "answers": self.topic3_fail_answers,
                "task_id": 102
            })
        )
        self.assertEqual(sub2_res.status_code, 200)
        sub2_data = sub2_res.get_json()["data"]
        # Eligibility MUST be revoked because latest attempt failed
        self.assertFalse(sub2_data["task_eligibility"]["can_apply"])
        self.assertFalse(sub2_data["task_eligibility"]["prerequisites"]["assessment_met"])
        self.assertEqual(sub2_data["task_eligibility"]["state"], "Assessment Needed")

    def test_09_direct_api_submission_blocked_when_ineligible(self):
        """Case 9: Direct API application submission cannot bypass eligibility checks."""
        # Attempt to apply directly to Task 102 without passing the assessment
        apply_res = self.client.post(
            "/api/competency/tasks/102/apply",
            headers=self.agent1_headers,
            data=json.dumps({"notes": "Bypassing frontend button"})
        )
        self.assertEqual(apply_res.status_code, 400)
        err = apply_res.get_json()["error"]
        self.assertIn("Cannot apply", err)

        # Confirm via db function directly
        with self.assertRaises(ValueError):
            apply_for_task(user_id=1, task_id=102)

    def test_10_optional_assessments_handled_correctly(self):
        """Case 10: Optional assessments handled correctly (all_topics_passed: 'Not Required')."""
        # Create a test task with exam_required = 0
        task_data = {
            "task_name": "Optional Assessment Task Test",
            "category_id": 1,
            "description": "Task with no mandatory assessment.",
            "status": "ACTIVE",
            "work_arrangement": "Remote",
            "payment_type": "Fixed Budget",
            "fixed_budget": 5000.0,
            "positions_count": 1,
            "deliverables": "Test Deliverables",
            "application_deadline": "2027-12-31",
            "minimum_competency": "BASIC",
            "minimum_experience_months": 0,
            "exam_required": False
        }
        res = create_task_with_requirements(task_data, admin_user_id=2)
        new_task_id = res["task_id"]

        try:
            tasks = get_agent_tasks_with_eligibility(user_id=1)
            target = next((t for t in tasks if t["task_id"] == new_task_id), None)
            self.assertIsNotNone(target)
            self.assertEqual(target["all_topics_passed"], "Not Required")
            self.assertEqual(target["exam_status"], "Not Required")
            self.assertTrue(target["can_apply"])
        finally:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM task_requirements WHERE task_id = %s", (new_task_id,))
                cursor.execute("DELETE FROM tasks WHERE task_id = %s", (new_task_id,))
            conn.commit()
            conn.close()

    def test_11_report_values_agree_with_authoritative_backend_decision(self):
        """Case 11: Assessment report values agree with authoritative backend decision."""
        start_res = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 102})
        )
        att_id = start_res.get_json()["data"]["attempt_id"]

        sub_res = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": att_id,
                "answers": self.topic3_fail_answers,
                "task_id": 102
            })
        )
        self.assertEqual(sub_res.status_code, 200)

        # Query GET /api/competency/attempts/:id
        detail_res = self.client.get(f"/api/competency/attempts/{att_id}", headers=self.agent1_headers)
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.get_json()["data"]

        # Ensure values in report payload are accurate
        self.assertEqual(detail_data["score"], 20.0)
        self.assertFalse(detail_data["passed"])
        self.assertEqual(detail_data["passing_score"], 75.0)
        self.assertFalse(detail_data["task_eligibility"]["all_topics_passed"])
        self.assertFalse(detail_data["task_eligibility"]["can_apply"])
        self.assertEqual(detail_data["task_eligibility"]["state"], "Assessment Needed")


if __name__ == "__main__":
    unittest.main()
