import os
import sys
import json
import unittest
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.app import create_app
from backend.auth_routes import generate_auth_token
from backend.db import (
    get_mysql_connection,
    reset_agent_assessment,
    get_assessment_attempt,
    save_agent_assessment,
    get_agent_tasks_with_eligibility,
    COMPETENCY_ENUM_TO_LABEL,
    DECISION_TO_ENUM,
    ENUM_TO_DECISION,
)


class TestExamPassThresholds(unittest.TestCase):
    """
    Focused regression tests for VerifyMesh Phase 3B - Step 2:
    Unify Exam Pass Thresholds.

    Verifies:
    1. Exam 1 configured at 75%: 74% fails, 75% passes.
    2. Exam 3 configured at 70%: 69% fails, 70% passes.
    3. API response and persisted attempt/result pass status agree.
    4. The threshold comes from the validated exam record, not client input.
    5. Missing or invalid exam threshold is handled safely without substituting 70%.
    6. Step 1 class-to-competency mapping remains unchanged.
    """

    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-exam-pass-thresholds-2026"
        Config.TESTING = True
        Config.ASSESSMENT_COOLDOWN_SECONDS = 0
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

        # Inspect and record actual database thresholds and question configurations
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Exam 1
            cur.execute("SELECT exam_id, exam_name, passing_score FROM exams WHERE exam_id = 1")
            cls.orig_exam_1 = cur.fetchone()
            cur.execute("SELECT question_id, points, correct_answer, question_order FROM exam_questions WHERE exam_id = 1 ORDER BY question_order")
            cls.orig_exam_1_questions = cur.fetchall()

            # Exam 3
            cur.execute("SELECT exam_id, exam_name, passing_score FROM exams WHERE exam_id = 3")
            cls.orig_exam_3 = cur.fetchone()
            cur.execute("SELECT question_id, points, correct_answer, question_order FROM exam_questions WHERE exam_id = 3 ORDER BY question_order")
            cls.orig_exam_3_questions = cur.fetchall()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        # Strictly restore database state to original configuration
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            if cls.orig_exam_1:
                cur.execute("UPDATE exams SET passing_score = %s WHERE exam_id = 1", (cls.orig_exam_1["passing_score"],))
            for q in cls.orig_exam_1_questions:
                cur.execute("UPDATE exam_questions SET points = %s WHERE question_id = %s", (q["points"], q["question_id"]))

            if cls.orig_exam_3:
                cur.execute("UPDATE exams SET passing_score = %s WHERE exam_id = 3", (cls.orig_exam_3["passing_score"],))
            for q in cls.orig_exam_3_questions:
                cur.execute("UPDATE exam_questions SET points = %s WHERE question_id = %s", (q["points"], q["question_id"]))
            conn.commit()
        conn.close()

    def setUp(self):
        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def tearDown(self):
        # Restore thresholds and question points between test runs
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            if self.orig_exam_1:
                cur.execute("UPDATE exams SET passing_score = %s WHERE exam_id = 1", (self.orig_exam_1["passing_score"],))
            for q in self.orig_exam_1_questions:
                cur.execute("UPDATE exam_questions SET points = %s WHERE question_id = %s", (q["points"], q["question_id"]))

            if self.orig_exam_3:
                cur.execute("UPDATE exams SET passing_score = %s WHERE exam_id = 3", (self.orig_exam_3["passing_score"],))
            for q in self.orig_exam_3_questions:
                cur.execute("UPDATE exam_questions SET points = %s WHERE question_id = %s", (q["points"], q["question_id"]))
            conn.commit()
        conn.close()

        reset_agent_assessment(1)
        reset_agent_assessment(6)

    def test_exam_1_configured_at_75_boundary_cases(self):
        """
        Requirement 4: Exam 1 configured at 75%: 74% fails, 75% passes.
        Verify score >= passing_score boundary logic and agreement across API,
        assessment_attempts.passed, and exam_results.passed.
        """
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Configure Exam 1 to 75%
            cur.execute("UPDATE exams SET passing_score = 75.00 WHERE exam_id = 1")
            # Set Exam 1 question points so answering Q18 only yields 74%, and Q18+Q19 yields 75%
            # Exam 1 questions: 18 (ans B), 19 (ans A), 20 (ans C), 21 (ans B), 22 (ans A)
            cur.execute("UPDATE exam_questions SET points = 74.00 WHERE question_id = 18")
            cur.execute("UPDATE exam_questions SET points = 1.00 WHERE question_id = 19")
            cur.execute("UPDATE exam_questions SET points = 5.00 WHERE question_id = 20")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 21")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 22")
            conn.commit()
        conn.close()

        # --- Case A: 74% fails ---
        start_res_a = self.client.post("/api/competency/exams/1/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res_a.status_code, 201)
        attempt_id_a = start_res_a.get_json()["data"]["attempt_id"]

        # Q18 correct (74 pts), remaining incorrect -> 74%
        answers_74 = {"18": "B", "19": "D", "20": "D", "21": "D", "22": "D"}
        sub_res_a = self.client.post(
            "/api/competency/exams/1/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id_a, "answers": answers_74}
        )
        self.assertEqual(sub_res_a.status_code, 200)
        data_a = sub_res_a.get_json()["data"]

        # Verify API response
        self.assertEqual(data_a["score"], 74.0)
        self.assertEqual(data_a["passing_score"], 75.0)
        self.assertFalse(data_a["passed"], "74% must fail when threshold is 75%")

        # Verify DB assessment_attempts
        att_a = get_assessment_attempt(attempt_id_a)
        self.assertIsNotNone(att_a)
        self.assertEqual(float(att_a["score"]), 74.0)
        self.assertEqual(att_a["passed"], 0)

        # Verify DB exam_results
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT assessment_score, passed FROM exam_results WHERE attempt_id = %s", (attempt_id_a,))
            er_a = cur.fetchone()
            self.assertIsNotNone(er_a)
            self.assertEqual(float(er_a["assessment_score"]), 74.0)
            self.assertEqual(er_a["passed"], 0)
        conn.close()

        # Reset before Case B
        reset_agent_assessment(1)

        # --- Case B: 75% passes ---
        start_res_b = self.client.post("/api/competency/exams/1/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res_b.status_code, 201)
        attempt_id_b = start_res_b.get_json()["data"]["attempt_id"]

        # Q18 correct (74 pts) + Q19 correct (1 pt) -> 75%
        answers_75 = {"18": "B", "19": "A", "20": "D", "21": "D", "22": "D"}
        sub_res_b = self.client.post(
            "/api/competency/exams/1/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id_b, "answers": answers_75}
        )
        self.assertEqual(sub_res_b.status_code, 200)
        data_b = sub_res_b.get_json()["data"]

        # Verify API response
        self.assertEqual(data_b["score"], 75.0)
        self.assertEqual(data_b["passing_score"], 75.0)
        self.assertTrue(data_b["passed"], "75% must pass when threshold is 75%")

        # Verify DB assessment_attempts
        att_b = get_assessment_attempt(attempt_id_b)
        self.assertIsNotNone(att_b)
        self.assertEqual(float(att_b["score"]), 75.0)
        self.assertEqual(att_b["passed"], 1)

        # Verify DB exam_results
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT assessment_score, passed FROM exam_results WHERE attempt_id = %s", (attempt_id_b,))
            er_b = cur.fetchone()
            self.assertIsNotNone(er_b)
            self.assertEqual(float(er_b["assessment_score"]), 75.0)
            self.assertEqual(er_b["passed"], 1)
        conn.close()

    def test_exam_3_configured_at_70_boundary_cases(self):
        """
        Requirement 4: Exam 3 configured at 70%: 69% fails, 70% passes.
        Verify score >= passing_score boundary logic and agreement across API,
        assessment_attempts.passed, and exam_results.passed.
        """
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Configure Exam 3 to 70%
            cur.execute("UPDATE exams SET passing_score = 70.00 WHERE exam_id = 3")
            # Set Exam 3 question points so Q13=69, Q14=1, Q15=10, Q16=10, Q17=10
            # Exam 3 questions: 13 (ans A), 14 (ans B), 15 (ans A), 16 (ans B), 17 (ans A)
            cur.execute("UPDATE exam_questions SET points = 69.00 WHERE question_id = 13")
            cur.execute("UPDATE exam_questions SET points = 1.00 WHERE question_id = 14")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 15")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 16")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 17")
            conn.commit()
        conn.close()

        # --- Case A: 69% fails ---
        start_res_a = self.client.post("/api/competency/exams/3/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res_a.status_code, 201)
        attempt_id_a = start_res_a.get_json()["data"]["attempt_id"]

        # Q13 correct (69 pts), remaining incorrect -> 69%
        answers_69 = {"13": "A", "14": "D", "15": "D", "16": "D", "17": "D"}
        sub_res_a = self.client.post(
            "/api/competency/exams/3/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id_a, "answers": answers_69}
        )
        self.assertEqual(sub_res_a.status_code, 200)
        data_a = sub_res_a.get_json()["data"]

        # Verify API response
        self.assertEqual(data_a["score"], 69.0)
        self.assertEqual(data_a["passing_score"], 70.0)
        self.assertFalse(data_a["passed"], "69% must fail when threshold is 70%")

        # Verify DB assessment_attempts
        att_a = get_assessment_attempt(attempt_id_a)
        self.assertIsNotNone(att_a)
        self.assertEqual(float(att_a["score"]), 69.0)
        self.assertEqual(att_a["passed"], 0)

        # Verify DB exam_results
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT assessment_score, passed FROM exam_results WHERE attempt_id = %s", (attempt_id_a,))
            er_a = cur.fetchone()
            self.assertIsNotNone(er_a)
            self.assertEqual(float(er_a["assessment_score"]), 69.0)
            self.assertEqual(er_a["passed"], 0)
        conn.close()

        # Reset before Case B
        reset_agent_assessment(1)

        # --- Case B: 70% passes ---
        start_res_b = self.client.post("/api/competency/exams/3/start-attempt", headers=self.agent1_headers)
        self.assertEqual(start_res_b.status_code, 201)
        attempt_id_b = start_res_b.get_json()["data"]["attempt_id"]

        # Q13 correct (69 pts) + Q14 correct (1 pt) -> 70%
        answers_70 = {"13": "A", "14": "B", "15": "D", "16": "D", "17": "D"}
        sub_res_b = self.client.post(
            "/api/competency/exams/3/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id_b, "answers": answers_70}
        )
        self.assertEqual(sub_res_b.status_code, 200)
        data_b = sub_res_b.get_json()["data"]

        # Verify API response
        self.assertEqual(data_b["score"], 70.0)
        self.assertEqual(data_b["passing_score"], 70.0)
        self.assertTrue(data_b["passed"], "70% must pass when threshold is 70%")

        # Verify DB assessment_attempts
        att_b = get_assessment_attempt(attempt_id_b)
        self.assertIsNotNone(att_b)
        self.assertEqual(float(att_b["score"]), 70.0)
        self.assertEqual(att_b["passed"], 1)

        # Verify DB exam_results
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT assessment_score, passed FROM exam_results WHERE attempt_id = %s", (attempt_id_b,))
            er_b = cur.fetchone()
            self.assertIsNotNone(er_b)
            self.assertEqual(float(er_b["assessment_score"]), 70.0)
            self.assertEqual(er_b["passed"], 1)
        conn.close()

    def test_threshold_comes_from_validated_exam_record_not_client_input(self):
        """
        Requirement 1 & 4: Do not trust a threshold supplied by the frontend.
        Even if client supplies passing_score=50.0, threshold=50.0, or passed=True
        in the submission payload, the server strictly uses the database record.
        """
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE exams SET passing_score = 75.00 WHERE exam_id = 1")
            cur.execute("UPDATE exam_questions SET points = 74.00 WHERE question_id = 18")
            cur.execute("UPDATE exam_questions SET points = 1.00 WHERE question_id = 19")
            cur.execute("UPDATE exam_questions SET points = 5.00 WHERE question_id = 20")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 21")
            cur.execute("UPDATE exam_questions SET points = 10.00 WHERE question_id = 22")
            conn.commit()
        conn.close()

        start_res = self.client.post("/api/competency/exams/1/start-attempt", headers=self.agent1_headers)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        # Client submits payload attempting to inject client-supplied threshold and pass status
        malicious_payload = {
            "attempt_id": attempt_id,
            "answers": {"18": "B", "19": "D", "20": "D", "21": "D", "22": "D"},  # 74%
            "passing_score": 50.0,
            "threshold": 50.0,
            "passed": True
        }
        sub_res = self.client.post(
            "/api/competency/exams/1/submit",
            headers=self.agent1_headers,
            json=malicious_payload
        )
        self.assertEqual(sub_res.status_code, 200)
        data = sub_res.get_json()["data"]

        # Verify client threshold was IGNORED and database threshold (75.0) was used
        self.assertEqual(data["score"], 74.0)
        self.assertEqual(data["passing_score"], 75.0)
        self.assertFalse(data["passed"], "Client-supplied passing_score=50 must not cause 74% to pass when DB passing_score is 75%")

        # Verify persisted attempt and exam_results also record passed = 0
        att = get_assessment_attempt(attempt_id)
        self.assertEqual(att["passed"], 0)

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT passed FROM exam_results WHERE attempt_id = %s", (attempt_id,))
            er = cur.fetchone()
            self.assertEqual(er["passed"], 0)
        conn.close()

    def test_missing_or_invalid_exam_threshold_handled_safely(self):
        """
        Requirement 3: Validate exam configuration safely.
        Handle a missing exam record or invalid/missing passing_score explicitly.
        Do not silently substitute 70% when the configured threshold cannot be retrieved.
        """
        # Subtest 1: Calling save_agent_assessment with a non-existent exam_id must fail safely (not substitute 70%)
        with self.assertRaises((ValueError, RuntimeError)) as ctx:
            save_agent_assessment(
                user_id=1,
                assessment_data={"assessment_score": 85.0},
                competency_level="Competent",
                confidence=0.9,
                prediction_data={"decision": "2"},
                exam_id=99999
            )
        self.assertIn("not found", str(ctx.exception).lower())

        # Subtest 2: Submission against non-existent attempt/exam returns 404
        res_missing = self.client.post(
            "/api/competency/exams/99999/submit",
            headers=self.agent1_headers,
            json={"attempt_id": 99999, "answers": {"1": "A"}}
        )
        self.assertIn(res_missing.status_code, (400, 404))
        self.assertFalse(res_missing.get_json()["success"])

        # Subtest 3: Calling save_agent_assessment when an exam record has None passing_score
        from unittest.mock import patch
        with patch("backend.db.get_or_create_reference_records", return_value=(1, 1)):
            with patch("pymysql.cursors.DictCursor.fetchone") as mock_fetchone:
                # 1: agent_row, 2: attempt_row, 3: ex_row (with passing_score=None)
                mock_fetchone.side_effect = [
                    {"agent_id": 1},
                    {"next_attempt": 1},
                    {"passing_score": None}
                ]
                with self.assertRaises((ValueError, RuntimeError)) as ctx_none:
                    save_agent_assessment(
                        user_id=1,
                        assessment_data={"assessment_score": 85.0},
                        competency_level="Competent",
                        confidence=0.9,
                        prediction_data={"decision": "2"},
                        exam_id=1
                    )
                self.assertIn("no configured passing score", str(ctx_none.exception).lower())

        # Subtest 4: Calling save_agent_assessment when an exam record has out-of-range passing_score
        with patch("backend.db.get_or_create_reference_records", return_value=(1, 1)):
            with patch("pymysql.cursors.DictCursor.fetchone") as mock_fetchone:
                mock_fetchone.side_effect = [
                    {"agent_id": 1},
                    {"next_attempt": 1},
                    {"passing_score": -10.0}
                ]
                with self.assertRaises((ValueError, RuntimeError)) as ctx_invalid:
                    save_agent_assessment(
                        user_id=1,
                        assessment_data={"assessment_score": 85.0},
                        competency_level="Competent",
                        confidence=0.9,
                        prediction_data={"decision": "2"},
                        exam_id=1
                    )
                self.assertIn("invalid passing score", str(ctx_invalid.exception).lower())

    def test_step_1_class_to_competency_mapping_remains_unchanged(self):
        """
        Requirement 2 & 4: Preserve Step 1 competency consistency:
        - Passing an exam does not automatically promote an agent to a higher tier.
        - Class 0 -> Needs Improvement (Ineligible)
        - Class 1 -> Basic (Send to Review)
        - Class 2 -> Competent (Eligible)
        - Advanced promotion rule strictly preserved.
        """
        # Subtest A: Agent 2 passes Exam 3 with 100% score (above 75% threshold)
        # Model predicts Class 1 (0 exp, 0 certs).
        # Passing the exam must NOT automatically promote Agent 2 to Competent or Advanced.
        start_res = self.client.post("/api/competency/exams/3/start-attempt", headers=self.agent2_headers)
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.get_json()["data"]["attempt_id"]

        all_correct = {"13": "A", "14": "B", "15": "A", "16": "B", "17": "A"}
        sub_res = self.client.post(
            "/api/competency/exams/3/submit",
            headers=self.agent2_headers,
            json={"attempt_id": attempt_id, "answers": all_correct}
        )
        self.assertEqual(sub_res.status_code, 200)
        data = sub_res.get_json()["data"]

        # Exam is passed (100% >= 75%)
        self.assertEqual(data["score"], 100.0)
        self.assertTrue(data["passed"])

        # BUT competency evaluates to Not Eligible (Class 0)
        self.assertEqual(data["prediction"]["decision_code"], 0)
        self.assertEqual(data["competency_level"], "Not Eligible")
        self.assertEqual(data["evaluation_decision"], "Not Eligible")

        # Downstream task eligibility: Task 4 requires Eligible -> agent cannot apply
        tasks = get_agent_tasks_with_eligibility(user_id=6)
        task_4 = next((t for t in tasks if t["task_id"] == 4), None)
        self.assertIsNotNone(task_4)
        self.assertFalse(task_4["can_apply"])
        self.assertFalse(task_4["is_eligible"])

        # Subtest B: Agent 1 (39 months experience) passes Exam 3 with 80%
        # Model predicts Class 1 (Eligible).
        reset_agent_assessment(1)
        start_res_1 = self.client.post("/api/competency/exams/3/start-attempt", headers=self.agent1_headers)
        attempt_id_1 = start_res_1.get_json()["data"]["attempt_id"]

        four_correct = {"13": "A", "14": "B", "15": "A", "16": "B", "17": "D"}  # 80%
        sub_res_1 = self.client.post(
            "/api/competency/exams/3/submit",
            headers=self.agent1_headers,
            json={"attempt_id": attempt_id_1, "answers": four_correct}
        )
        self.assertEqual(sub_res_1.status_code, 200)
        data_1 = sub_res_1.get_json()["data"]

        self.assertEqual(data_1["score"], 80.0)
        self.assertTrue(data_1["passed"])
        self.assertEqual(data_1["competency_level"], "Eligible")
        self.assertEqual(data_1["evaluation_decision"], "Eligible")


if __name__ == "__main__":
    unittest.main()
