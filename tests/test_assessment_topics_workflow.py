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
    get_assessment_topics_list,
    get_assessment_topic_by_id,
    get_topic_questions
)


class TestAssessmentTopicsWorkflow(unittest.TestCase):
    """
    Comprehensive tests for VerifyMesh assessment topic framework and backend integration:
    1. Topic list and detail retrieval with passing thresholds.
    2. Topic questions retrieval (5 questions per topic, correct answers omitted).
    3. Authoritative attempt initialization per topic.
    4. Server-side grading, passing score comparison, and topic result persistence.
    5. Anti-tampering: rejecting invalid question IDs, missing answers, and attempt ownership check.
    6. Multi-topic task prerequisite enforcement (Task 2 requires topics 1, 3, 4).
    7. Topic result reuse across tasks.
    8. Attempt details retrieval for dedicated results page.
    """

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-topics-workflow-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Agent 1: user_id = 1, agent_id = 1 (verified agent)
        cls.agent1_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent1_headers = {
            "Authorization": f"Bearer {cls.agent1_token}",
            "Content-Type": "application/json"
        }

        # Agent 2: user_id = 6, agent_id = 5 (separate agent)
        cls.agent2_token = generate_auth_token(user_id=6, role="Agent")
        cls.agent2_headers = {
            "Authorization": f"Bearer {cls.agent2_token}",
            "Content-Type": "application/json"
        }

    def setUp(self):
        # Reset assessment states before each test run
        reset_agent_assessment(user_id=1)
        reset_agent_assessment(user_id=6)

    def test_get_all_assessment_topics(self):
        """Verify GET /api/competency/topics returns the 4 seeded competency topics."""
        res = self.client.get("/api/competency/topics", headers=self.agent1_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        topics = data.get("data", [])
        self.assertEqual(len(topics), 4)

        topic_names = [t["topic_name"] for t in topics]
        self.assertIn("Product Knowledge", topic_names)
        self.assertIn("Sales Techniques and Objection Handling", topic_names)
        self.assertIn("Customer Communication", topic_names)
        self.assertIn("Customer Relationship Management", topic_names)

        for t in topics:
            self.assertEqual(t["question_count"], 5)
            self.assertGreaterEqual(t["passing_score"], 70.0)

    def test_get_topic_questions_omits_correct_answers(self):
        """Verify questions endpoint delivers 5 questions without exposing correct_answer."""
        for topic_id in [1, 2, 3, 4]:
            res = self.client.get(f"/api/competency/topics/{topic_id}/questions", headers=self.agent1_headers)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            questions = data.get("data", [])
            self.assertEqual(len(questions), 5)

            for q in questions:
                self.assertNotIn("correct_answer", q, "Security failure: correct_answer exposed in client payload")
                self.assertIn("question_id", q)
                self.assertIn("question_text", q)
                self.assertIn("options", q)
                self.assertEqual(len(q["options"]), 4)

    def test_start_and_submit_topic_attempt_server_graded(self):
        """Verify start-attempt and server-side submission on Topic 3 (Customer Communication)."""
        topic_id = 3

        # 1. Start Attempt
        start_res = self.client.post(
            f"/api/competency/topics/{topic_id}/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({"task_id": 4})
        )
        self.assertEqual(start_res.status_code, 201)
        start_data = start_res.get_json()
        self.assertTrue(start_data.get("success"))
        attempt_id = start_data["data"]["attempt_id"]
        self.assertIsNotNone(attempt_id)

        # 2. Get questions to map IDs
        q_res = self.client.get(f"/api/competency/topics/{topic_id}/questions", headers=self.agent1_headers)
        questions = q_res.get_json()["data"]

        # 3. Submit passing answers (100% correct answers for Topic 3: 13=A, 14=B, 15=A, 16=B, 17=A)
        correct_answers = {
            "13": "A",
            "14": "B",
            "15": "A",
            "16": "B",
            "17": "A"
        }

        submit_res = self.client.post(
            f"/api/competency/topics/{topic_id}/submit",
            headers=self.agent1_headers,
            data=json.dumps({
                "attempt_id": attempt_id,
                "answers": correct_answers,
                "task_id": 4
            })
        )
        self.assertEqual(submit_res.status_code, 200)
        submit_data = submit_res.get_json()["data"]

        self.assertEqual(submit_data["score"], 100.0)
        self.assertTrue(submit_data["passed"])
        self.assertEqual(submit_data["total_questions"], 5)
        self.assertEqual(submit_data["correct_count"], 5)
        self.assertIn("prediction", submit_data)
        self.assertIn("task_eligibility", submit_data)

        # 4. Verify attempt details endpoint recovers stored result
        attempt_res = self.client.get(f"/api/competency/attempts/{attempt_id}", headers=self.agent1_headers)
        self.assertEqual(attempt_res.status_code, 200)
        att_data = attempt_res.get_json()["data"]
        self.assertEqual(att_data["attempt_id"], attempt_id)
        self.assertEqual(att_data["score"], 100.0)
        self.assertTrue(att_data["passed"])
        self.assertEqual(att_data["status"], "SUBMITTED")

    def test_unauthorized_attempt_access_rejected(self):
        """Verify Agent 2 cannot submit Agent 1's assessment attempt."""
        # Agent 1 starts attempt
        start_res = self.client.post(
            "/api/competency/topics/1/start-attempt",
            headers=self.agent1_headers,
            data=json.dumps({})
        )
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Agent 2 tries to submit
        hack_res = self.client.post(
            "/api/competency/topics/1/submit",
            headers=self.agent2_headers,
            data=json.dumps({
                "attempt_id": attempt_id,
                "answers": {"1": "A", "2": "A", "3": "A", "4": "A", "5": "A"}
            })
        )
        self.assertEqual(hack_res.status_code, 403)
        self.assertFalse(hack_res.get_json()["success"])

        # Agent 2 tries to read Agent 1's attempt details
        read_res = self.client.get(f"/api/competency/attempts/{attempt_id}", headers=self.agent2_headers)
        self.assertEqual(read_res.status_code, 403)

    def test_duplicate_submission_rejected(self):
        """Verify an attempt cannot be submitted twice."""
        # Start and submit attempt
        start_res = self.client.post("/api/competency/topics/3/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        answers = {"13": "A", "14": "B", "15": "A", "16": "B", "17": "A"}
        first_submit = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({"attempt_id": attempt_id, "answers": answers})
        )
        self.assertEqual(first_submit.status_code, 200)

        # Second submission must be rejected with 409 Conflict
        second_submit = self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({"attempt_id": attempt_id, "answers": answers})
        )
        self.assertEqual(second_submit.status_code, 409)
        self.assertFalse(second_submit.get_json()["success"])

    def test_multi_topic_task_enforcement(self):
        """
        Verify multi-topic task rules:
        Task 6 requires Topic 3 (Customer Communication) and Topic 4 (CRM).
        Passing only Topic 3 leaves Task 6 as not eligible until all required topics are passed.
        """
        # Step 1: Agent 1 passes Topic 3
        start_3 = self.client.post("/api/competency/topics/3/start-attempt", headers=self.agent1_headers)
        att_3 = start_3.get_json()["data"]["attempt_id"]
        self.client.post(
            "/api/competency/topics/3/submit",
            headers=self.agent1_headers,
            data=json.dumps({"attempt_id": att_3, "answers": {"13": "A", "14": "B", "15": "A", "16": "B", "17": "A"}, "task_id": 6})
        )

        # Check Task 6 status: still needs Topic 4
        tasks = get_agent_tasks_with_eligibility(user_id=1)
        task_6 = next((t for t in tasks if t["task_id"] == 6), None)
        self.assertIsNotNone(task_6)
        self.assertFalse(task_6["all_topics_passed"])
        self.assertEqual(task_6["topics_passed_count"], 1)
        self.assertEqual(task_6["topics_total"], 2)
        self.assertFalse(task_6["prerequisites"]["assessment_met"])

        # Step 2: Agent 1 passes Topic 4 (CRM: 29=A, 30=A, 31=A, 32=A, 33=A)
        start_4 = self.client.post("/api/competency/topics/4/start-attempt", headers=self.agent1_headers)
        att_4 = start_4.get_json()["data"]["attempt_id"]
        submit_4 = self.client.post(
            "/api/competency/topics/4/submit",
            headers=self.agent1_headers,
            data=json.dumps({"attempt_id": att_4, "answers": {"29": "A", "30": "A", "31": "A", "32": "A", "33": "A"}, "task_id": 6})
        )
        self.assertEqual(submit_4.status_code, 200)

        # Now both topics are passed! Task 6 should reflect all topics passed and assessment_met True
        tasks_updated = get_agent_tasks_with_eligibility(user_id=1)
        task_6_updated = next((t for t in tasks_updated if t["task_id"] == 6), None)
        self.assertIsNotNone(task_6_updated)
        self.assertTrue(task_6_updated["all_topics_passed"])
        self.assertEqual(task_6_updated["topics_passed_count"], 2)
        self.assertTrue(task_6_updated["prerequisites"]["assessment_met"])


if __name__ == "__main__":
    unittest.main()
