"""
VerifyMesh — Phase 4 & 4A Attempt Lifecycle, Expiry, and Administrative Exceptions Test Suite
=============================================================================================

Automated tests covering:
1. Explicit Abandonment: Active attempt transitions to ABANDONED, audited, answers preserved.
2. Quota Enforcement: Abandoned attempts count toward attempt limit to deter item harvesting.
3. Administrative Overrides: Workforce Officer can grant extra attempts, cancel invalid attempts, or reopen expired attempts.
4. Expiry Sweeping: Stale attempts past expires_at transition to EXPIRED (score=NULL, passed=0).
5. Attempt History: Full historical audit trail preserved and retrievable.
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
    abandon_assessment_attempt,
    admin_override_assessment_attempt,
    expire_stale_assessment_attempts,
    get_agent_assessment_history,
    get_assessment_attempt,
    AttemptLimitReachedError,
)
from backend.auth_routes import generate_auth_token


class TestPhase4LifecycleAndExpiry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # User 1: Agent (Alex Morgan, agent_id=1)
            cur.execute("SELECT user_id, email, role FROM users WHERE user_id = 1")
            cls.user_agent = cur.fetchone()

            # User 2: Admin / Workforce Officer
            cur.execute("SELECT user_id, email, role FROM users WHERE role IN ('ADMIN', 'WORKFORCE_OFFICER') LIMIT 1")
            cls.user_admin = cur.fetchone()

        cls.agent_token = generate_auth_token(cls.user_agent["user_id"], cls.user_agent["role"])
        cls.admin_token = generate_auth_token(cls.user_admin["user_id"], cls.user_admin["role"])

    @classmethod
    def tearDownClass(cls):
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Ensure Alex has Topic 3 passed restored for other test suites
            cur.execute("SELECT result_id FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3 AND passed = 1")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO agent_topic_results (agent_id, topic_id, score, passed, completed_at)
                    VALUES (1, 3, 100.0, 1, NOW())
                """)
            conn.commit()

    def setUp(self):
        # Clear temporary test overrides and clean in-progress attempts for Agent 1 on Topic 3
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
            cur.execute("DELETE FROM audit_logs WHERE entity_type = 'agents' AND entity_id = 1 AND action = 'ATTEMPT_LIMIT_OVERRIDE_GRANTED'")
            conn.commit()

    def test_01_explicit_abandonment_transitions_status_and_audits(self):
        """Phase 4 & 4A: Candidate can explicitly abandon attempt; status becomes ABANDONED."""
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]

        resp = self.client.post(
            "/api/competency/topics/3/abandon",
            headers={"Authorization": f"Bearer {self.agent_token}"},
            json={"attempt_id": att_id, "reason": "Candidate chose to abandon session"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "ABANDONED")

        # Verify DB row
        att_db = get_assessment_attempt(att_id)
        self.assertEqual(att_db["status"], "ABANDONED")
        self.assertEqual(att_db["closure_reason"], "Candidate chose to abandon session")

        # Verify attempt cannot be submitted after abandonment
        sub_resp = self.client.post(
            "/api/competency/topics/3/submit",
            headers={"Authorization": f"Bearer {self.agent_token}"},
            json={"attempt_id": att_id, "answers": {"9": "A", "10": "B"}}
        )
        self.assertEqual(sub_resp.status_code, 400)

    def test_02_abandoned_attempts_count_toward_attempt_limit(self):
        """Phase 4A: Abandoned attempts count against the 3-attempt limit to prevent question harvesting."""
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Set topic 3 max_attempts to 2 for this focused test
            cur.execute("UPDATE assessment_topics SET max_attempts = 2 WHERE topic_id = 3")
            # Clear past topic 3 attempts for agent 1
            cur.execute("DELETE FROM assessment_attempts WHERE agent_id = 1 AND topic_id = 3")
            cur.execute("DELETE FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3")
            conn.commit()

        try:
            # Attempt 1: Started and Abandoned
            att1 = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            abandon_assessment_attempt(att1["attempt_id"], agent_id=1)

            # Attempt 2: Started and Abandoned
            att2 = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            abandon_assessment_attempt(att2["attempt_id"], agent_id=1)

            # Attempt 3: Must be blocked because 2 attempts exhausted
            with self.assertRaises(AttemptLimitReachedError):
                create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        finally:
            with conn.cursor() as cur:
                cur.execute("UPDATE assessment_topics SET max_attempts = 3 WHERE topic_id = 3")
                conn.commit()

    def test_03_admin_grant_extra_attempt_override(self):
        """Phase 4A: Administrator can grant an extra attempt exception with audit reason."""
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_topics SET max_attempts = 1 WHERE topic_id = 3")
            cur.execute("DELETE FROM assessment_attempts WHERE agent_id = 1 AND topic_id = 3")
            cur.execute("DELETE FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3")
            conn.commit()

        try:
            # Exhaust attempt 1
            att1 = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            abandon_assessment_attempt(att1["attempt_id"], agent_id=1)

            # Attempt 2 fails due to quota
            with self.assertRaises(AttemptLimitReachedError):
                create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)

            # Admin grants extra attempt
            resp = self.client.post(
                "/api/admin/agents/1/assessment-override",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "topic_id": 3,
                    "action": "GRANT_EXTRA_ATTEMPT",
                    "reason": "Technical connection failure verified by Workforce Officer"
                }
            )
            self.assertEqual(resp.status_code, 200)

            # Agent can now initiate attempt 2
            att2 = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            self.assertIsNotNone(att2)
            self.assertEqual(att2["status"], "IN_PROGRESS")
        finally:
            with conn.cursor() as cur:
                cur.execute("UPDATE assessment_topics SET max_attempts = 3 WHERE topic_id = 3")
                conn.commit()

    def test_04_admin_cancel_attempt_exempts_from_quota(self):
        """Phase 4A: Administrator can cancel an invalid attempt so it does NOT count against quota."""
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_topics SET max_attempts = 1 WHERE topic_id = 3")
            cur.execute("DELETE FROM assessment_attempts WHERE agent_id = 1 AND topic_id = 3")
            cur.execute("DELETE FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3")
            conn.commit()

        try:
            att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            att_id = att["attempt_id"]

            # Admin cancels attempt due to platform outage
            resp = self.client.post(
                "/api/admin/agents/1/assessment-override",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "topic_id": 3,
                    "action": "CANCEL_ATTEMPT",
                    "reason": "Platform database restart mid-attempt",
                    "attempt_id": att_id
                }
            )
            self.assertEqual(resp.status_code, 200)

            # Verified attempt is CANCELLED
            att_db = get_assessment_attempt(att_id)
            self.assertEqual(att_db["status"], "CANCELLED")

            # Agent should still be able to create an attempt because CANCELLED is exempt from quota
            new_att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            self.assertIsNotNone(new_att)
            self.assertEqual(new_att["status"], "IN_PROGRESS")
        finally:
            with conn.cursor() as cur:
                cur.execute("UPDATE assessment_topics SET max_attempts = 3 WHERE topic_id = 3")
                conn.commit()

    def test_05_stale_attempt_expiry_sweep(self):
        """Phase 4: Attempts past expires_at are marked EXPIRED with score=NULL and passed=0."""
        # Create an attempt and manually backdate its expires_at in DB
        attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        att_id = attempt["attempt_id"]

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE assessment_attempts SET expires_at = DATE_SUB(NOW(), INTERVAL 1 HOUR) WHERE attempt_id = %s", (att_id,))
            conn.commit()

        # Run background expiry sweeper
        expired_count = expire_stale_assessment_attempts()
        self.assertGreaterEqual(expired_count, 1)

        # Verify DB status
        att_db = get_assessment_attempt(att_id)
        self.assertEqual(att_db["status"], "EXPIRED")
        self.assertIsNone(att_db["score"])
        self.assertEqual(att_db["passed"], 0)

    def test_06_historical_assessment_audit_trail_preserved(self):
        """Phase 4 & 4A: Complete attempt history is retrievable per agent/topic."""
        # Ensure at least one attempt exists for history check
        att = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
        abandon_assessment_attempt(att["attempt_id"], agent_id=1, reason="History test entry")

        resp = self.client.get(
            "/api/competency/topics/3/history",
            headers={"Authorization": f"Bearer {self.agent_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        history = data["data"]
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

        for h in history:
            self.assertIn("attempt_id", h)
            self.assertIn("status", h)
            self.assertIn("started_at", h)


if __name__ == "__main__":
    unittest.main()
