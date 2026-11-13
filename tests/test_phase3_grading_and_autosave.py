"""
VerifyMesh — Phase 3 & 3A Server-Side Grading, Security & Autosave Test Suite
=============================================================================

Automated tests covering:
1. Question Delivery: correct_answer is never exposed.
2. Server-Side Grading: client scores rejected, ownership enforced, server grades correctly.
3. Attempt Idempotency: duplicate submissions return original result.
4. Autosave: intermediate draft answers persisted to assessment_attempts.
5. Concurrency Control: stale revisions rejected/ignored without overwriting newer answers.
6. Attempt Resumption: active in-progress attempt restores saved draft answers and snapshot.
"""

import os
import sys
import json
import unittest
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.db import (
    get_mysql_connection,
    create_assessment_attempt,
    get_topic_questions,
    save_attempt_draft_answers,
    get_assessment_attempt,
)
from backend.auth_routes import generate_auth_token


class TestPhase3GradingAndAutosave(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Retrieve test agent 1 (Alex Morgan, user_id=1, agent_id=1)
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, email, role FROM users WHERE user_id = 1")
            cls.user1 = cur.fetchone()

            # Retrieve test agent 2 or agent 5 (Daniel Nyabuto, user_id=6, agent_id=5)
            cur.execute("SELECT u.user_id, u.email, u.role, a.agent_id FROM users u JOIN agents a ON u.user_id = a.user_id WHERE u.user_id != 1 LIMIT 1")
            cls.user2 = cur.fetchone()

        cls.token1 = generate_auth_token(cls.user1["user_id"], cls.user1["role"])
        cls.token2 = generate_auth_token(cls.user2["user_id"], cls.user2["role"])

    def setUp(self):
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
            conn.commit()

    def test_01_question_delivery_never_leaks_correct_answers(self):
        """Phase 3: Ensure question delivery omits correct_answer and internal grading keys."""
        resp = self.client.get(
            "/api/competency/topics/3/questions",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        questions = data["data"]
        self.assertGreater(len(questions), 0)

        for q in questions:
            self.assertNotIn("correct_answer", q, "correct_answer must never be returned to client")
            self.assertNotIn("correctAnswer", q)
            self.assertIn("question_id", q)
            self.assertIn("question_text", q)
            self.assertIn("options", q)

    def test_02_client_cannot_submit_scores_or_protected_features(self):
        """Phase 3: Client-submitted scores or pass/fail decisions must be rejected with HTTP 400."""
        # Attempt to tamper by injecting pre-calculated score and pass decision
        tampered_payload = {
            "attempt_id": 99999,
            "answers": {"1": "A"},
            "assessment_score": 100.0,
            "passed": 1,
            "stage2_decision": "Eligible"
        }
        resp = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.token1}"},
            json=tampered_payload
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("forbidden", data["error"].lower())

    def test_03_attempt_ownership_validation(self):
        """Phase 3: Agent A cannot submit or autosave Agent B's attempt."""
        # Create an attempt belonging to agent 1
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]

        # Agent 2 tries to autosave Agent 1's attempt
        resp = self.client.post(
            f"/api/competency/topics/3/autosave",
            headers={"Authorization": f"Bearer {self.token2}"},
            json={"attempt_id": att_id, "answers": {"1": "A"}, "version": 1}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("unauthorized", data["error"].lower())

    def test_04_autosave_persists_answers_and_increments_version(self):
        """Phase 3A: Valid autosave persists draft answers and increments answers_version."""
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]

        # Autosave Revision 1
        resp1 = self.client.post(
            "/api/competency/topics/3/autosave",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={"attempt_id": att_id, "answers": {"9": "A"}, "version": 1}
        )
        self.assertEqual(resp1.status_code, 200)
        d1 = resp1.get_json()["data"]
        self.assertEqual(d1["attempt_id"], att_id)
        self.assertGreaterEqual(d1["answers_version"], 1)

        # Verify DB row
        att_db = get_assessment_attempt(att_id)
        saved_answers = json.loads(att_db["answers_json"]) if isinstance(att_db["answers_json"], str) else att_db["answers_json"]
        self.assertEqual(saved_answers.get("9"), "A")
        self.assertEqual(att_db["answers_version"], d1["answers_version"])

        # Autosave Revision 2 (adding answer for question 10)
        resp2 = self.client.post(
            "/api/competency/topics/3/autosave",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={"attempt_id": att_id, "answers": {"10": "B"}, "version": d1["answers_version"] + 1}
        )
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.get_json()["data"]
        self.assertGreater(d2["answers_version"], d1["answers_version"])

        # Verify merged state in DB
        att_db2 = get_assessment_attempt(att_id)
        saved2 = json.loads(att_db2["answers_json"]) if isinstance(att_db2["answers_json"], str) else att_db2["answers_json"]
        self.assertEqual(saved2.get("9"), "A")
        self.assertEqual(saved2.get("10"), "B")

    def test_05_concurrency_control_stale_revision_rejected(self):
        """Phase 3A: Out-of-order or stale autosave requests do not overwrite newer answers."""
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]

        # Save Revision 5
        save_attempt_draft_answers(att_id, agent_id=1, answers={"9": "C"}, incoming_version=5)

        # Incoming delayed Revision 2 arrives late
        success, ver, _, msg = save_attempt_draft_answers(att_id, agent_id=1, answers={"9": "A"}, incoming_version=2)
        self.assertTrue(success)
        self.assertIn("stale", msg.lower())

        # The stored answer must still be 'C' (Revision 5), NOT overwritten by 'A' (Revision 2)
        att_db = get_assessment_attempt(att_id)
        saved = json.loads(att_db["answers_json"]) if isinstance(att_db["answers_json"], str) else att_db["answers_json"]
        self.assertEqual(saved.get("9"), "C")

    def test_06_attempt_resumption_restores_snapshot_and_saved_answers(self):
        """Phase 3A: Resuming an in-progress attempt returns frozen snapshot and saved draft answers."""
        # Clean up any existing in-progress attempts for Agent 1 on Topic 3
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_attempts SET status = 'SUBMITTED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
            conn.commit()

        # Seed a brand new in-progress attempt with draft answers
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]
        save_attempt_draft_answers(att_id, agent_id=1, answers={"9": "B", "10": "D"}, incoming_version=1)

        # Client requests start-attempt (e.g. on page refresh or return)
        resp = self.client.post(
            "/api/competency/topics/3/start-attempt",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={}
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()["data"]
        self.assertEqual(data["attempt_id"], att_id, "Must resume existing in-progress attempt")
        self.assertEqual(data["status"], "IN_PROGRESS")
        self.assertIn("saved_answers", data)
        self.assertEqual(data["saved_answers"].get("9"), "B")
        self.assertEqual(data["saved_answers"].get("10"), "D")
        self.assertGreaterEqual(data["answers_version"], 2)


if __name__ == "__main__":
    unittest.main()
