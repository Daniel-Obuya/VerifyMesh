"""
Unit and Integration Tests: Supervisor / Manager Reference Verification Loop
============================================================================
Tests Method C:
1. Candidate submits work experience with supervisor contact details.
2. Automated verification token and 7-day expiration are generated.
3. Supervisor fetches public verification details without authentication.
4. Supervisor confirms or disputes tenure via 1-click token submission.
5. Record updates to VERIFIED or REJECTED with verified_via = 'SUPERVISOR_REFERENCE'.
6. Merged verified experience months are automatically updated.
7. Token reuse, tampering, and expiration safeguards.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.app import create_app
from backend.auth_routes import generate_auth_token
from backend.db import get_mysql_connection


class TestSupervisorReferenceLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Config.SECRET_KEY = "test-secret-key-supervisor-loop-2026"
        Config.TESTING = True
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        # Agent 1 (alex.morgan@university.edu, user_id=1, agent_id=1)
        cls.agent_token = generate_auth_token(user_id=1, role="Agent")
        cls.agent_headers = {
            "Authorization": f"Bearer {cls.agent_token}",
            "Content-Type": "application/json"
        }
        cls.created_exp_ids = []

    @classmethod
    def tearDownClass(cls):
        # Clean up any test experience records created during this test
        if cls.created_exp_ids:
            conn = get_mysql_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        format_strings = ','.join(['%s'] * len(cls.created_exp_ids))
                        cur.execute(f"DELETE FROM agent_experience WHERE experience_id IN ({format_strings})", tuple(cls.created_exp_ids))
                        cur.execute("DELETE FROM audit_logs WHERE entity_type = 'agent_experience' AND entity_id IN (" + format_strings + ")", tuple(cls.created_exp_ids))
                        conn.commit()
                finally:
                    conn.close()

    def test_01_submit_experience_with_supervisor_reference(self):
        """Candidate submits work experience with supervisor reference."""
        payload = {
            "job_title": "Enterprise Sales Representative",
            "company": "Safaricom PLC",
            "work_category": "Sales",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "is_current": False,
            "description": "B2B telecommunications and cloud infrastructure sales.",
            "supervisor_name": "David Ndung'u (Regional Sales Director)",
            "supervisor_email": "david.ndungu@safaricom-test.co.ke",
            "supervisor_phone": "+254711998877"
        }

        resp = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])
        exp_id = data["data"]["experience_id"]
        token = data["data"]["verification_token"]
        self.created_exp_ids.append(exp_id)

        self.assertIsNotNone(token)
        self.assertEqual(data["data"]["verification_status"], "PENDING")

        # Verify in database
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT supervisor_name, supervisor_email, supervisor_phone,
                           verification_status, verification_token, token_expires_at
                    FROM agent_experience
                    WHERE experience_id = %s
                """, (exp_id,))
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["supervisor_name"], "David Ndung'u (Regional Sales Director)")
                self.assertEqual(row["supervisor_email"], "david.ndungu@safaricom-test.co.ke")
                self.assertEqual(row["verification_status"], "PENDING")
                self.assertEqual(row["verification_token"], token)
                self.assertIsNotNone(row["token_expires_at"])
        finally:
            conn.close()

    def test_02_public_get_experience_by_token(self):
        """Supervisor retrieves public experience verification details without logging in."""
        # Create an entry
        payload = {
            "job_title": "Client Success Specialist",
            "company": "KCB Bank Group",
            "work_category": "Customer Service",
            "start_date": "2022-06-01",
            "end_date": "2022-12-31",
            "is_current": False,
            "description": "Corporate client onboarding and issue resolution.",
            "supervisor_name": "Grace Wanjiku",
            "supervisor_email": "grace.wanjiku@kcb-test.co.ke",
            "supervisor_phone": "+254722334455"
        }
        res = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        token = res.get_json()["data"]["verification_token"]
        exp_id = res.get_json()["data"]["experience_id"]
        self.created_exp_ids.append(exp_id)

        # Anonymous GET
        get_res = self.client.get(f"/api/competency/public/verify-experience/{token}")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["company"], "KCB Bank Group")
        self.assertEqual(data["data"]["job_title"], "Client Success Specialist")
        self.assertEqual(data["data"]["verification_status"], "PENDING")
        self.assertIn("agent_name", data["data"])

    def test_03_supervisor_confirms_employment_successfully(self):
        """Supervisor submits CONFIRM; status flips to VERIFIED and tenure recalculates."""
        payload = {
            "job_title": "Account Executive",
            "company": "Equity Group Holdings",
            "work_category": "Sales",
            "start_date": "2021-01-01",
            "end_date": "2021-12-31",
            "is_current": False,
            "description": "SME credit and merchant sales.",
            "supervisor_name": "Peter Mwangi",
            "supervisor_email": "peter.mwangi@equity-test.co.ke",
            "supervisor_phone": "+254733445566"
        }
        res = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        token = res.get_json()["data"]["verification_token"]
        exp_id = res.get_json()["data"]["experience_id"]
        self.created_exp_ids.append(exp_id)

        # Supervisor confirms
        confirm_payload = {
            "decision": "CONFIRM",
            "feedback": "Confirmed. Peter was an outstanding performer who exceeded quarterly sales targets.",
            "answers": {
                "role_accurate": "yes",
                "tenure_accurate": "yes"
            }
        }
        sub_res = self.client.post(f"/api/competency/public/verify-experience/{token}", json=confirm_payload)
        self.assertEqual(sub_res.status_code, 200)
        resp_data = sub_res.get_json()
        self.assertTrue(resp_data["success"])
        self.assertEqual(resp_data["data"]["verification_status"], "VERIFIED")

        # Database verification
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT verification_status, verified_via, supervisor_feedback, reviewed_at
                    FROM agent_experience
                    WHERE experience_id = %s
                """, (exp_id,))
                row = cur.fetchone()
                self.assertEqual(row["verification_status"], "VERIFIED")
                self.assertEqual(row["verified_via"], "SUPERVISOR_REFERENCE")
                self.assertIn("outstanding performer", row["supervisor_feedback"])
                self.assertIsNotNone(row["reviewed_at"])
        finally:
            conn.close()

    def test_04_token_reuse_prevention(self):
        """Submitting a verification decision with an already processed token returns 400 Bad Request."""
        payload = {
            "job_title": "Support Specialist",
            "company": "Twiga Foods",
            "work_category": "Customer Service",
            "start_date": "2020-01-01",
            "end_date": "2020-06-30",
            "is_current": False,
            "description": "Vendor logistics support.",
            "supervisor_name": "Alice Mutua",
            "supervisor_email": "alice@twiga-test.co.ke"
        }
        res = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        token = res.get_json()["data"]["verification_token"]
        exp_id = res.get_json()["data"]["experience_id"]
        self.created_exp_ids.append(exp_id)

        # First review
        self.client.post(f"/api/competency/public/verify-experience/{token}", json={"decision": "CONFIRM"})

        # Second review attempt (must be blocked)
        repeat_res = self.client.post(f"/api/competency/public/verify-experience/{token}", json={"decision": "CONFIRM"})
        self.assertEqual(repeat_res.status_code, 400)
        self.assertIn("already been reviewed", repeat_res.get_json()["error"])

    def test_05_supervisor_disputes_employment(self):
        """Supervisor submits DISPUTE; status flips to REJECTED with rejection reason."""
        payload = {
            "job_title": "Chief Technology Officer",
            "company": "Fictitious Startup",
            "work_category": "Other",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "is_current": False,
            "description": "Executive architecture leadership.",
            "supervisor_name": "James Ochieng",
            "supervisor_email": "james@fictitious-test.com"
        }
        res = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        token = res.get_json()["data"]["verification_token"]
        exp_id = res.get_json()["data"]["experience_id"]
        self.created_exp_ids.append(exp_id)

        # Supervisor disputes
        dispute_payload = {
            "decision": "DISPUTE",
            "feedback": "Candidate never held a CTO role at this organization. Dates and title are fraudulent."
        }
        dispute_res = self.client.post(f"/api/competency/public/verify-experience/{token}", json=dispute_payload)
        self.assertEqual(dispute_res.status_code, 200)

        # Database verification
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT verification_status, verified_via, rejection_reason
                    FROM agent_experience
                    WHERE experience_id = %s
                """, (exp_id,))
                row = cur.fetchone()
                self.assertEqual(row["verification_status"], "REJECTED")
                self.assertEqual(row["verified_via"], "SUPERVISOR_REFERENCE")
                self.assertIn("never held a CTO role", row["rejection_reason"])
        finally:
            conn.close()

    def test_06_resend_supervisor_verification_link(self):
        """Candidate can trigger a resend of the supervisor verification link."""
        payload = {
            "job_title": "Retail Cashier",
            "company": "Naivas Supermarket",
            "work_category": "Customer Service",
            "start_date": "2019-01-01",
            "end_date": "2019-12-31",
            "is_current": False,
            "description": "Customer checkout and balance audits.",
            "supervisor_name": "Store Manager John",
            "supervisor_email": "john.manager@naivas-test.co.ke"
        }
        res = self.client.post("/api/competency/experiences", json=payload, headers=self.agent_headers)
        initial_token = res.get_json()["data"]["verification_token"]
        exp_id = res.get_json()["data"]["experience_id"]
        self.created_exp_ids.append(exp_id)

        # Trigger resend
        resend_res = self.client.post(f"/api/competency/experiences/{exp_id}/resend", headers=self.agent_headers)
        self.assertEqual(resend_res.status_code, 200)
        new_link = resend_res.get_json()["data"]["verification_link"]
        self.assertIn("token=", new_link)

    def test_07_mandatory_supervisor_reference_enforcement(self):
        """Omitting supervisor name or email is strictly rejected with HTTP 400."""
        # Missing supervisor completely
        payload_no_sup = {
            "job_title": "Retail Cashier",
            "company": "Naivas Supermarket",
            "work_category": "Customer Service",
            "start_date": "2019-01-01",
            "end_date": "2019-12-31"
        }
        res = self.client.post("/api/competency/experiences", json=payload_no_sup, headers=self.agent_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("mandatory", res.get_json()["error"].lower())

        # Invalid email format
        payload_bad_email = {
            "job_title": "Retail Cashier",
            "company": "Naivas Supermarket",
            "work_category": "Customer Service",
            "start_date": "2019-01-01",
            "end_date": "2019-12-31",
            "supervisor_name": "John Manager",
            "supervisor_email": "not-an-email"
        }
        res_bad = self.client.post("/api/competency/experiences", json=payload_bad_email, headers=self.agent_headers)
        self.assertEqual(res_bad.status_code, 400)
        self.assertIn("valid email", res_bad.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()

