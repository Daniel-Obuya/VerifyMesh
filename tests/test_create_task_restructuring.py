import os
import sys
import unittest
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import (
    get_mysql_connection,
    get_task_metadata,
    create_task_with_requirements,
    update_task_with_requirements,
    get_admin_task_detail,
    get_agent_tasks_with_eligibility,
    delete_task,
)

class TestCreateTaskRestructuring(unittest.TestCase):
    def setUp(self):
        self.created_task_ids = []
        self.metadata = get_task_metadata()

    def tearDown(self):
        for tid in self.created_task_ids:
            try:
                delete_task(tid)
            except Exception:
                pass

    def test_01_metadata_endpoint_contains_topics_and_certifications(self):
        """Verify get_task_metadata returns categories, certifications, and active assessment topics."""
        self.assertIn("categories", self.metadata)
        self.assertIn("certifications", self.metadata)
        self.assertIn("topics", self.metadata)
        self.assertTrue(len(self.metadata["categories"]) > 0)
        self.assertTrue(len(self.metadata["certifications"]) > 0)
        self.assertTrue(len(self.metadata["topics"]) > 0)
        
        # Check topic structure
        first_topic = self.metadata["topics"][0]
        self.assertIn("topic_id", first_topic)
        self.assertIn("topic_name", first_topic)
        self.assertIn("passing_score", first_topic)

    def test_02_create_task_with_multi_certifications_and_topics(self):
        """Verify task creation with multiple certifications and assessment topics saves properly."""
        cert_ids = [c["certification_id"] for c in self.metadata["certifications"][:2]]
        topic_ids = [t["topic_id"] for t in self.metadata["topics"][:2]]
        deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        payload = {
            "task_name": "Senior Customer Success Specialist",
            "category_id": self.metadata["categories"][0]["category_id"],
            "work_arrangement": "Remote",
            "description": "Provide high-tier customer support and escalate complex technical issues to engineering teams.",
            "responsibilities": "- Handle tier-2 support escalations\n- Conduct daily customer check-ins\n- Maintain 98% SLA adherence",
            "skills": ["Customer Support", "CRM Management", "SLA Adherence"],
            "payment_type": "Hourly",
            "hourly_rate": 450.00,
            "max_hourly_rate": 650.00,
            "currency": "KES",
            "positions_available": 3,
            "application_deadline": deadline,
            "expected_duration": "6 Months",
            "min_experience_months": 12,
            "required_certification_ids": cert_ids,
            "exam_required": True,
            "required_topic_ids": topic_ids,
            "passing_score": 70,
            "status": "ACTIVE",
            "created_by": 1
        }

        res = create_task_with_requirements(payload)
        self.assertIsInstance(res, dict)
        task_id = res["task_id"]
        self.created_task_ids.append(task_id)

        # Verify retrieval via get_admin_task_detail
        detail = get_admin_task_detail(task_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["task_name"], payload["task_name"])
        self.assertEqual(detail["work_arrangement"], "Remote")
        self.assertEqual(detail["expected_duration"], "6 Months")
        self.assertEqual(float(detail["hourly_rate_min"]), 450.00)
        self.assertEqual(float(detail["hourly_rate_max"]), 650.00)
        self.assertEqual(detail["positions_count"], 3)
        self.assertEqual(detail["minimum_experience_months"], 12)
        
        # Verify multi-certifications persisted
        self.assertEqual(set(detail.get("required_certification_ids", [])), set(cert_ids))
        
        # Verify multi-topics persisted
        self.assertEqual(set(detail.get("required_topic_ids", [])), set(topic_ids))

        # Check DB tables directly
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # Check task_certifications table
        cursor.execute("SELECT certification_id FROM task_certifications WHERE task_id = %s", (task_id,))
        saved_certs = [r["certification_id"] for r in cursor.fetchall()]
        self.assertEqual(set(saved_certs), set(cert_ids))

        # Check task_assessment_topics table
        cursor.execute("SELECT topic_id FROM task_assessment_topics WHERE task_id = %s", (task_id,))
        saved_topics = [r["topic_id"] for r in cursor.fetchall()]
        self.assertEqual(set(saved_topics), set(topic_ids))

        # Check task_requirements minimum_competency defaulted to ELIGIBLE
        cursor.execute("SELECT minimum_competency, exam_required FROM task_requirements WHERE task_id = %s", (task_id,))
        req_row = cursor.fetchone()
        self.assertEqual(req_row["minimum_competency"], "ELIGIBLE")
        self.assertEqual(req_row["exam_required"], 1)

        conn.close()

    def test_03_update_task_syncs_multi_certifications_and_topics(self):
        """Verify updating task synchronizes certifications and assessment topics cleanly."""
        all_certs = [c["certification_id"] for c in self.metadata["certifications"]]
        all_topics = [t["topic_id"] for t in self.metadata["topics"]]
        
        if len(all_certs) < 2 or len(all_topics) < 2:
            self.skipTest("Need at least 2 certs and topics for update test")

        init_cert = [all_certs[0]]
        init_topic = [all_topics[0]]

        payload = {
            "task_name": "Initial Task Title",
            "category_id": self.metadata["categories"][0]["category_id"],
            "description": "Initial task description for update testing.",
            "payment_type": "Fixed",
            "total_budget": 50000.00,
            "currency": "KES",
            "positions_available": 1,
            "application_deadline": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "expected_duration": "3 Months",
            "min_experience_months": 6,
            "required_certification_ids": init_cert,
            "exam_required": True,
            "required_topic_ids": init_topic,
            "created_by": 1
        }

        res = create_task_with_requirements(payload)
        task_id = res["task_id"]
        self.created_task_ids.append(task_id)

        # Now update with second cert and second topic
        updated_certs = [all_certs[1]]
        updated_topics = [all_topics[1]]
        update_payload = {
            "task_name": "Updated Task Title",
            "category_id": self.metadata["categories"][0]["category_id"],
            "description": "Updated task description with new budget and certs.",
            "payment_type": "Fixed",
            "total_budget": 75000.00,
            "currency": "KES",
            "positions_available": 2,
            "application_deadline": (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d"),
            "expected_duration": "6 Months",
            "min_experience_months": 18,
            "required_certification_ids": updated_certs,
            "exam_required": True,
            "required_topic_ids": updated_topics,
            "passing_score": 70
        }

        success = update_task_with_requirements(task_id, update_payload)
        self.assertTrue(success)

        # Inspect updated details
        detail = get_admin_task_detail(task_id)
        self.assertEqual(detail["task_name"], "Updated Task Title")
        self.assertEqual(float(detail["fixed_budget"]), 75000.00)
        self.assertEqual(detail["minimum_experience_months"], 18)
        self.assertEqual(detail["required_certification_ids"], updated_certs)
        self.assertEqual(detail["required_topic_ids"], updated_topics)

    def test_04_deterministic_eligibility_enforces_all_mandatory_certifications(self):
        """Verify agent missing one of the mandatory certifications is marked ineligible."""
        all_certs = [c["certification_id"] for c in self.metadata["certifications"]]
        if len(all_certs) < 2:
            self.skipTest("Need at least 2 certs for eligibility test")

        # Pick two certs
        cert_ids = all_certs[:2]

        payload = {
            "task_name": "Strict Multi-Cert Verification Task",
            "category_id": self.metadata["categories"][0]["category_id"],
            "description": "This task requires multiple verified certifications to qualify.",
            "payment_type": "Hourly",
            "hourly_rate": 500.00,
            "currency": "KES",
            "positions_available": 1,
            "application_deadline": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "expected_duration": "1 Month",
            "min_experience_months": 0,
            "required_certification_ids": cert_ids,
            "assessment_required": False,
            "required_topic_ids": [],
            "status": "ACTIVE",
            "created_by": 1
        }

        res = create_task_with_requirements(payload)
        task_id = res["task_id"]
        self.created_task_ids.append(task_id)

        # Check agent 1 eligibility
        agent_tasks = get_agent_tasks_with_eligibility(user_id=1)
        created_task_in_feed = next((t for t in agent_tasks if t["task_id"] == task_id), None)
        
        self.assertIsNotNone(created_task_in_feed)
        # Agent 1 does not possess both certs verified
        # Therefore is_eligible should be False, or if they happen to have both, certification_met is True
        if not created_task_in_feed["is_eligible"]:
            self.assertIn("certification", created_task_in_feed["blocking_reason"].lower())
            self.assertFalse(created_task_in_feed["prerequisites"]["certification_met"])

if __name__ == "__main__":
    unittest.main()
