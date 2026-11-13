"""
VerifyMesh — Phase 2 Database Queries and Task-Specific Assessment Mapping Test Suite
===================================================================================

Automated regression suite verifying tests A through G as specified in Phase 2:
  Test A: Alex's old Product Knowledge score of 20% is NOT retrieved when evaluating Task 4.
  Test B: Customer Communication is retrieved correctly for Task 4 (score = 100%).
  Test C: A task requiring Sales retrieves appropriate Sales results and isolates from other topics.
  Test D: A task requiring multiple topics retrieves all configured topics and excludes unrelated topics.
  Test E: An unassessed required topic is correctly flagged as NOT_ASSESSED and blocks Stage 1 gate.
  Test F: An invalidated or reset attempt is NOT used as a valid competency result.
  Test G: One applicant's assessment history cannot contaminate another applicant's prediction.
"""

import os
import sys
import unittest
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import (
    get_mysql_connection,
    get_task_applicants,
    build_task_suitability_features,
    COMPETENCY_STATE_ASSESSED_AND_PASSED,
    COMPETENCY_STATE_ASSESSED_AND_FAILED,
    COMPETENCY_STATE_NOT_ASSESSED,
    COMPETENCY_STATE_NOT_REQUIRED,
)


class TestPhase2DatabaseAssessmentMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Ensure baseline tasks 2, 4, 5 exist
            baseline_tasks = [
                (2, 1, 'Enterprise Onboarding Lead', 'Lead enterprise onboarding initiatives.', 'ACTIVE', 3, 24, 0),
                (4, 2, 'Technical Support Agent', 'Provide high-quality technical assistance.', 'ACTIVE', 3, 12, 0),
                (5, 1, 'Product Consultant', 'Provide pre-sales and technical consulting.', 'ACTIVE', 1, 18, 2),
            ]
            for tid, cat, tname, desc, st, eid, exp, cert in baseline_tasks:
                cur.execute("SELECT task_id FROM tasks WHERE task_id = %s", (tid,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO tasks (task_id, category_id, task_name, description, status, exam_id, work_arrangement, positions_count, deliverables, payment_type, currency)
                        VALUES (%s, %s, %s, %s, %s, %s, 'Remote', 1, 'Deliverables', 'Fixed Budget', 'KES')
                    """, (tid, cat, tname, desc, st, eid))
                cur.execute("SELECT requirement_id FROM task_requirements WHERE task_id = %s", (tid,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO task_requirements (task_id, minimum_competency, required_certification_id, minimum_experience_months, exam_required)
                        VALUES (%s, 'BASIC', %s, %s, 1)
                    """, (tid, cert if cert > 0 else None, exp))

            # Ensure Alex's latest Topic 3 result is passed with 100%
            cur.execute("DELETE FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3 AND passed = 0")
            cur.execute("SELECT result_id FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 3 AND passed = 1")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO agent_topic_results (agent_id, topic_id, score, passed, completed_at)
                    VALUES (1, 3, 100.0, 1, NOW())
                """)

            # Ensure Alex application exists for Task 4
            cur.execute("""
                SELECT application_id FROM task_applications
                WHERE task_id = 4 AND agent_id = 1
            """)
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO task_applications (task_id, agent_id, status, applied_at, updated_at, notes)
                    VALUES (4, 1, 'Application Submitted', NOW(), NOW(), 'Phase 2 Test Candidate')
                """)

            # Ensure Task 4 has explicit task_assessment_topics mapping for Topic 3
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 4")
            cur.execute("""
                INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                VALUES (4, 3, 1)
            """)

            # Ensure Task 5 has explicit mapping for Topic 2 (Sales)
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 5")
            cur.execute("""
                INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                VALUES (5, 2, 1)
            """)

            # Ensure Task 2 has multi-topic mapping for Topics 1, 3, 4
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 2")
            cur.execute("""
                INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                VALUES (2, 1, 1), (2, 3, 1), (2, 4, 1)
            """)

            # Ensure any reset request for User 1 is cleared for test run
            cur.execute("DELETE FROM audit_logs WHERE user_id = 1 AND action = 'ASSESSMENT_RESET_REQUESTED'")

            # Temporarily isolate any agent 1 topic 4 results so Test E & F reliably test unassessed state
            cur.execute("SELECT * FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 4")
            cls._saved_topic_4_results = cur.fetchall()
            cur.execute("DELETE FROM agent_topic_results WHERE agent_id = 1 AND topic_id = 4")

            # Ensure a fixture task 999 exists for isolated reset/cross-contamination testing
            cur.execute("DELETE FROM task_applications WHERE task_id = 999")
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 999")
            cur.execute("DELETE FROM task_requirements WHERE task_id = 999")
            cur.execute("DELETE FROM tasks WHERE task_id = 999")
            cur.execute("""
                INSERT INTO tasks (
                    task_id, category_id, task_name, description, status,
                    work_arrangement, positions_count, deliverables, payment_type, currency
                ) VALUES (
                    999, 2, 'Phase 2 Multi-Topic Fixture Task', 'Test harness task', 'ACTIVE',
                    'Remote', 1, 'Deliverables', 'Fixed Budget', 'KES'
                )
            """)
            cur.execute("""
                INSERT INTO task_requirements (task_id, minimum_competency, minimum_experience_months, exam_required)
                VALUES (999, 'BASIC', 6, 1)
            """)
            cur.execute("""
                INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                VALUES (999, 3, 1), (999, 4, 1)
            """)

            # Ensure Agent 2 (User 2) application exists on Task 999 for cross-contamination testing
            cur.execute("SELECT agent_id FROM agents WHERE agent_id = 2")
            if cur.fetchone():
                cur.execute("""
                    INSERT INTO task_applications (task_id, agent_id, status, applied_at, updated_at)
                    VALUES (999, 2, 'Application Submitted', NOW(), NOW())
                """)
            cur.execute("""
                INSERT INTO task_applications (task_id, agent_id, status, applied_at, updated_at)
                VALUES (999, 1, 'Application Submitted', NOW(), NOW())
            """)

            conn.commit()

    @classmethod
    def tearDownClass(cls):
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM task_applications WHERE task_id = 999")
            cur.execute("DELETE FROM task_assessment_topics WHERE task_id = 999")
            cur.execute("DELETE FROM task_requirements WHERE task_id = 999")
            cur.execute("DELETE FROM tasks WHERE task_id = 999")
            cur.execute("DELETE FROM task_applications WHERE task_id = 5 AND agent_id = 1")

            if hasattr(cls, "_saved_topic_4_results") and cls._saved_topic_4_results:
                for row in cls._saved_topic_4_results:
                    r_id = row["result_id"] if isinstance(row, dict) else row[0]
                    ag_id = row["agent_id"] if isinstance(row, dict) else row[1]
                    t_id = row["topic_id"] if isinstance(row, dict) else row[2]
                    at_id = row["attempt_id"] if isinstance(row, dict) else row[3]
                    sc = row["score"] if isinstance(row, dict) else row[4]
                    ps = row["passed"] if isinstance(row, dict) else row[5]
                    ans = row["answers_json"] if isinstance(row, dict) else row[6]
                    cat = row["completed_at"] if isinstance(row, dict) else row[7]
                    cur.execute("""
                        INSERT INTO agent_topic_results (
                            result_id, agent_id, topic_id, attempt_id, score, passed, answers_json, completed_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE score = VALUES(score)
                    """, (r_id, ag_id, t_id, at_id, sc, ps, ans, cat))
            conn.commit()

    def test_A_alex_product_knowledge_20_percent_not_retrieved_for_task_4(self):
        """Test A: Alex's old Product Knowledge score of 20% is NOT retrieved when evaluating Task 4."""
        applicants = get_task_applicants(4)
        alex = next((a for a in applicants if a["agent_id"] == 1), None)
        self.assertIsNotNone(alex, "Alex Morgan (agent_id=1) must be returned in Task 4 applicants")

        comp_states = alex["competency_states"]
        # Topic 1 (Product Knowledge) must be classified as NOT_REQUIRED
        self.assertIn(1, comp_states)
        self.assertEqual(comp_states[1]["state"], COMPETENCY_STATE_NOT_REQUIRED)
        self.assertIsNone(comp_states[1]["score"], "Topic 1 score must be None for Task 4")

        # Weakest link deficit must NOT be penalized by the 20% score
        engineered = alex["engineered_features"]
        self.assertIsNotNone(engineered)
        self.assertEqual(engineered["weakest_link_deficit"], 0.0, "Weakest link deficit must be 0.0, not -50.0")
        self.assertGreaterEqual(engineered["min_skill_margin"], 0.0, "Min skill margin must be non-negative")

    def test_B_customer_communication_retrieved_correctly_for_task_4(self):
        """Test B: Customer Communication is retrieved correctly for Task 4."""
        applicants = get_task_applicants(4)
        alex = next((a for a in applicants if a["agent_id"] == 1), None)
        self.assertIsNotNone(alex)

        comp_states = alex["competency_states"]
        # Topic 3 (Customer Communication) is configured for Task 4
        self.assertIn(3, comp_states)
        self.assertEqual(comp_states[3]["state"], COMPETENCY_STATE_ASSESSED_AND_PASSED)
        self.assertEqual(float(comp_states[3]["score"]), 100.0)
        self.assertTrue(comp_states[3]["passed"])
        self.assertTrue(comp_states[3]["is_mandatory"])

        # Alex passes Stage 1 and receives high Stage 2 suitability
        self.assertTrue(alex["meets_prerequisites"])
        self.assertEqual(alex["stage2_status"], "scored")
        self.assertGreater(float(alex["suitability_score"]), 0.70)
        self.assertIn(alex["advisory_tier"], ["Recommended", "Strong Fit"])

    def test_C_task_requiring_sales_retrieves_sales_topic(self):
        """Test C: A task requiring Sales retrieves the appropriate Sales results."""
        conn = get_mysql_connection()
        inserted_app = False
        try:
            with conn.cursor() as cur:
                # Temporarily add Alex to Task 5
                cur.execute("SELECT application_id FROM task_applications WHERE task_id = 5 AND agent_id = 1")
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO task_applications (task_id, agent_id, status, applied_at, updated_at)
                        VALUES (5, 1, 'Application Submitted', NOW(), NOW())
                    """)
                    conn.commit()
                    inserted_app = True

            applicants = get_task_applicants(5)
            alex = next((a for a in applicants if a["agent_id"] == 1), None)
            self.assertIsNotNone(alex)

            # Task 5 only requires Topic 2 (Sales)
            self.assertEqual(alex["required_topic_ids"], [2])
            comp_states = alex["competency_states"]

            # Topics 1, 3, 4 must be NOT_REQUIRED
            self.assertEqual(comp_states[1]["state"], COMPETENCY_STATE_NOT_REQUIRED)
            self.assertEqual(comp_states[3]["state"], COMPETENCY_STATE_NOT_REQUIRED)
            self.assertEqual(comp_states[4]["state"], COMPETENCY_STATE_NOT_REQUIRED)

            # Topic 2 is the ONLY evaluated topic
            self.assertIn(comp_states[2]["state"], [COMPETENCY_STATE_NOT_ASSESSED, COMPETENCY_STATE_ASSESSED_AND_PASSED, COMPETENCY_STATE_ASSESSED_AND_FAILED])
        finally:
            if inserted_app:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM task_applications WHERE task_id = 5 AND agent_id = 1")
                    conn.commit()

    def test_D_multi_topic_task_retrieves_all_configured_and_excludes_unrelated(self):
        """Test D: A task requiring multiple topics retrieves all configured topics and excludes unrelated topics."""
        applicants = get_task_applicants(999)
        alex = next((a for a in applicants if a["agent_id"] == 1), None)
        self.assertIsNotNone(alex)

        # Task 999 configures Topics 3 and 4
        self.assertEqual(set(alex["required_topic_ids"]), {3, 4})
        comp_states = alex["competency_states"]

        # Topics 1 and 2 must be strictly NOT_REQUIRED
        self.assertEqual(comp_states[1]["state"], COMPETENCY_STATE_NOT_REQUIRED)
        self.assertEqual(comp_states[2]["state"], COMPETENCY_STATE_NOT_REQUIRED)

        # Topics 3 and 4 are required
        self.assertNotEqual(comp_states[3]["state"], COMPETENCY_STATE_NOT_REQUIRED)
        self.assertNotEqual(comp_states[4]["state"], COMPETENCY_STATE_NOT_REQUIRED)

    def test_E_unassessed_required_topic_correctly_flagged(self):
        """Test E: An unassessed required topic is correctly flagged and blocks Stage 1."""
        applicants = get_task_applicants(999)
        alex = next((a for a in applicants if a["agent_id"] == 1), None)
        self.assertIsNotNone(alex)

        comp_states = alex["competency_states"]
        # Topic 4 is required on Task 999, but Alex has no valid submitted attempt for Topic 4
        self.assertEqual(comp_states[4]["state"], COMPETENCY_STATE_NOT_ASSESSED)
        self.assertIsNone(comp_states[4]["score"])
        self.assertFalse(comp_states[4]["passed"])

        # Stage 1 gatekeeper must fail because mandatory Topic 4 is unassessed
        self.assertFalse(alex["meets_prerequisites"])
        self.assertEqual(alex["stage2_status"], "ineligible_not_scored")
        self.assertIsNone(alex["suitability_score"])

    def test_F_invalidated_or_reset_attempt_not_used(self):
        """Test F: An invalidated or reset attempt is NOT used as a valid competency result."""
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            # Insert a simulated attempt with status 'IN_PROGRESS' for Topic 4
            cur.execute("""
                INSERT INTO assessment_attempts (
                    attempt_uuid, agent_id, exam_id, topic_id, task_id,
                    attempt_number, status, started_at, expires_at
                ) VALUES (
                    UUID(), 1, 3, 4, 999, 9999, 'IN_PROGRESS', NOW(), DATE_ADD(NOW(), INTERVAL 30 MINUTE)
                )
            """)
            att_id = cur.lastrowid
            # Record an agent_topic_result pointing to this IN_PROGRESS attempt with a fake 95% score
            cur.execute("""
                INSERT INTO agent_topic_results (
                    agent_id, topic_id, attempt_id, score, passed, completed_at
                ) VALUES (
                    1, 4, %s, 95.0, 1, NOW()
                )
            """, (att_id,))
            res_id = cur.lastrowid
            conn.commit()

        try:
            # Query applicants: the IN_PROGRESS attempt must be rejected by (att.status = 'SUBMITTED')
            applicants = get_task_applicants(999)
            alex = next((a for a in applicants if a["agent_id"] == 1), None)
            self.assertIsNotNone(alex)
            # Topic 4 must remain NOT_ASSESSED despite the IN_PROGRESS attempt
            self.assertEqual(alex["competency_states"][4]["state"], COMPETENCY_STATE_NOT_ASSESSED)
            self.assertIsNone(alex["competency_states"][4]["score"])
        finally:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agent_topic_results WHERE result_id = %s", (res_id,))
                cur.execute("DELETE FROM assessment_attempts WHERE attempt_id = %s", (att_id,))
                conn.commit()

    def test_G_cross_applicant_isolation(self):
        """Test G: One applicant's assessment history cannot contaminate another applicant's prediction."""
        applicants = get_task_applicants(999)
        alex = next((a for a in applicants if a["agent_id"] == 1), None)
        agent2 = next((a for a in applicants if a["agent_id"] == 2), None)

        self.assertIsNotNone(alex)
        if agent2:
            # Alex has 100% on Topic 3
            self.assertEqual(alex["competency_states"][3]["state"], COMPETENCY_STATE_ASSESSED_AND_PASSED)
            self.assertEqual(float(alex["competency_states"][3]["score"]), 100.0)

            # Agent 2 must NOT inherit Alex's score on Topic 3
            if agent2["competency_states"][3]["score"] is not None:
                self.assertNotEqual(
                    agent2["competency_states"][3]["attempt_id"],
                    alex["competency_states"][3]["attempt_id"],
                    "Agent 2 must have their own independent attempt ID"
                )


if __name__ == "__main__":
    unittest.main()

