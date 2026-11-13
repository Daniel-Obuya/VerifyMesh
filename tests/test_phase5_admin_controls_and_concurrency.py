"""
VerifyMesh — Phase 5 & 5A Admin Controls, Audit Logging, Versioning & Concurrency Test Suite
=============================================================================================

Automated tests covering:
1. Admin Authorization: Non-admins blocked with HTTP 403; admins authorized via backend.
2. Assessment Topic Versioning: Admin updates increment version without mutating historical attempts.
3. Audit Trail: Topic creation and configuration changes record structured audit events.
4. Multi-Tab Concurrency: Simultaneous submissions resolve idempotently without duplicate records.
5. Cross-Tab Stale Autosave Rejection: Newer revisions cannot be clobbered by delayed older tabs.
"""

import os
import sys
import json
import unittest
import threading
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.db import (
    get_mysql_connection,
    create_assessment_attempt,
    get_assessment_attempt,
    save_attempt_draft_answers,
)
from backend.auth_routes import generate_auth_token


class TestPhase5AdminControlsAndConcurrency(unittest.TestCase):
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

    def test_01_admin_authorization_enforced_on_backend(self):
        """Phase 5: Non-admins cannot access admin assessment endpoints."""
        # Agent tries to view admin topics
        resp = self.client.get(
            "/api/admin/assessments/topics",
            headers={"Authorization": f"Bearer {self.agent_token}"}
        )
        self.assertEqual(resp.status_code, 403)

        # Admin accesses admin topics
        admin_resp = self.client.get(
            "/api/admin/assessments/topics",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(admin_resp.status_code, 200)
        data = admin_resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["data"]), 0)

    def test_02_topic_configuration_update_increments_version_and_audits(self):
        """Phase 5: Admin updates increment topic version and preserve audit log trail."""
        # 1. Admin creates a fixture topic
        create_payload = {
            "topic_name": "Phase 5 Governance Test Topic",
            "category_id": 1,
            "description": "Topic for versioning test",
            "passing_score": 70.0,
            "estimated_minutes": 15,
            "max_attempts": 3
        }
        res_create = self.client.post(
            "/api/admin/assessments/topics",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=create_payload
        )
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.get_json()["data"]
        topic_id = created_data["topic_id"]
        self.assertEqual(created_data["version"], 1)

        conn = get_mysql_connection()
        try:
            # 2. Candidate initiates attempt under Version 1
            att1 = create_assessment_attempt(agent_id=1, exam_id=1, topic_id=topic_id)
            self.assertEqual(att1["topic_version"], 1, "Attempt must record Version 1")

            # 3. Admin updates configuration: raise passing score from 70 to 80
            update_payload = {
                "passing_score": 80.0,
                "max_attempts": 4
            }
            res_update = self.client.put(
                f"/api/admin/assessments/topics/{topic_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json=update_payload
            )
            self.assertEqual(res_update.status_code, 200)

            # 4. Verify topic version is now 2
            with conn.cursor() as cur:
                cur.execute("SELECT version, passing_score FROM assessment_topics WHERE topic_id = %s", (topic_id,))
                top_row = cur.fetchone()
                self.assertEqual(top_row["version"], 2)
                self.assertEqual(float(top_row["passing_score"]), 80.0)

                # 5. Verify audit log was recorded
                cur.execute("""
                    SELECT description FROM audit_logs 
                    WHERE entity_type = 'assessment_topics' AND entity_id = %s AND action = 'ASSESSMENT_TOPIC_UPDATED'
                    ORDER BY log_id DESC LIMIT 1
                """, (topic_id,))
                log_row = cur.fetchone()
                self.assertIsNotNone(log_row)
                log_data = json.loads(log_row["description"])
                self.assertEqual(log_data["previous_version"], 1)
                self.assertEqual(log_data["new_version"], 2)
                self.assertEqual(log_data["previous_passing_score"], 70.0)
                self.assertEqual(log_data["new_passing_score"], 80.0)

            # 6. Historical attempt must still remain locked to Version 1
            att_check = get_assessment_attempt(att1["attempt_id"])
            self.assertEqual(att_check["topic_version"], 1)

        finally:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM assessment_attempts WHERE topic_id = %s", (topic_id,))
                cur.execute("DELETE FROM audit_logs WHERE entity_type = 'assessment_topics' AND entity_id = %s", (topic_id,))
                cur.execute("DELETE FROM assessment_topics WHERE topic_id = %s", (topic_id,))
                conn.commit()

    def test_03_multi_tab_concurrency_simultaneous_submission(self):
        """Phase 5A: Two simultaneous submissions resolve idempotently without conflict."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
                cur.execute("UPDATE assessment_attempts SET submitted_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
                cur.execute("UPDATE exam_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND exam_id = 3")
                cur.execute("UPDATE agent_topic_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
                conn.commit()

            # Create active attempt
            attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            att_id = attempt["attempt_id"]

            # Fetch questions for valid answers
            with conn.cursor() as cur:
                cur.execute("SELECT question_id FROM exam_questions WHERE topic_id = 3")
                q_ids = [str(r["question_id"]) for r in cur.fetchall()]
            sample_answers = {qid: "A" for qid in q_ids}

            results = []

            def submit_tab(tab_name):
                client = self.app.test_client()
                resp = client.post(
                    "/api/competency/topics/3/submit",
                    headers={"Authorization": f"Bearer {self.agent_token}"},
                    json={"attempt_id": att_id, "answers": sample_answers}
                )
                results.append((tab_name, resp.status_code, resp.get_json()))

            try:
                # Spawn two concurrent threads simulating simultaneous clicks from 2 tabs
                t1 = threading.Thread(target=submit_tab, args=("Tab 1",))
                t2 = threading.Thread(target=submit_tab, args=("Tab 2",))
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                self.assertEqual(len(results), 2)
                status_codes = [r[1] for r in results]
                # Both must succeed with 200 (one normal completion, one idempotent return)
                self.assertEqual(status_codes, [200, 200], f"Expected both submissions to return HTTP 200, got {status_codes}")

                # Scores returned by both tabs must be identical
                score1 = results[0][2]["data"]["score"]
                score2 = results[1][2]["data"]["score"]
                self.assertEqual(score1, score2)

                # Verify exactly ONE row in agent_topic_results for this attempt
                conn.commit()
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM agent_topic_results WHERE attempt_id = %s", (att_id,))
                    cnt = cur.fetchone()["cnt"]
                    self.assertEqual(cnt, 1, "Only one authoritative result row must exist in agent_topic_results")
            finally:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM agent_topic_results WHERE attempt_id = %s", (att_id,))
                    cur.execute("DELETE FROM exam_results WHERE attempt_id = %s", (att_id,))
                    cur.execute("DELETE FROM assessment_attempts WHERE attempt_id = %s", (att_id,))
                    conn.commit()
        finally:
            conn.close()

    def test_04_cross_tab_stale_autosave_protection(self):
        """Phase 5A: Delayed autosave from an older tab does not clobber newer answers."""
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE assessment_attempts SET status = 'CLOSED' WHERE agent_id = 1 AND topic_id = 3 AND status = 'IN_PROGRESS'")
                cur.execute("UPDATE assessment_attempts SET submitted_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
                cur.execute("UPDATE exam_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND exam_id = 3")
                cur.execute("UPDATE agent_topic_results SET completed_at = DATE_SUB(NOW(), INTERVAL 10 MINUTE) WHERE agent_id = 1 AND topic_id = 3")
                conn.commit()

            attempt = create_assessment_attempt(agent_id=1, exam_id=3, topic_id=3)
            att_id = attempt["attempt_id"]

            # Tab 1: Saves Q9='B' at Revision 3
            save_attempt_draft_answers(att_id, agent_id=1, answers={"9": "B"}, incoming_version=3)

            # Tab 2: Delayed network packet from earlier session sends Q9='A' at Revision 1
            success, ver, _, msg = save_attempt_draft_answers(att_id, agent_id=1, answers={"9": "A"}, incoming_version=1)
            self.assertTrue(success)
            self.assertIn("stale", msg.lower())

            # DB must still hold Tab 1's choice 'B'
            att_db = get_assessment_attempt(att_id)
            saved = json.loads(att_db["answers_json"]) if isinstance(att_db["answers_json"], str) else att_db["answers_json"]
            self.assertEqual(saved.get("9"), "B", "Stale tab must not overwrite newer answer")
        finally:
            conn.close()

    def test_05_hard_prerequisites_blocks_assessment_start(self):
        """Hard-Prerequisites First: Agent lacking experience (23 < 24 months) is blocked with 403."""
        token_user6 = generate_auth_token(6, "Agent")
        
        # User 6 attempts to start Topic 1 assessment for Task 2 (requires 24 months)
        resp = self.client.post(
            "/api/competency/topics/1/start-attempt",
            headers={"Authorization": f"Bearer {token_user6}"},
            json={"task_id": 2}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Hard prerequisites not met", data["error"])
        self.assertEqual(data["state"], "Requires 24 Months Exp")


if __name__ == "__main__":
    unittest.main()

