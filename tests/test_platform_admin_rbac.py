"""
VerifyMesh — Platform Administrator & Role Separation RBAC Tests
Verifies strict separation of duties:
1. Platform Admin has exclusive access to /api/platform-admin/*
2. Workforce Officer and Agent accounts receive strict 403 Forbidden on /api/platform-admin/*
3. User role modifications, account suspension, and anti-lockout safeguards
4. Genuine audit log streaming and system health telemetry
5. ML Model v3 governance specifications
"""

import json
import unittest
from backend.app import create_app
from backend.auth_routes import generate_auth_token
import backend.db as db

class TestPlatformAdminRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # User 76 is John Nyabuto (PLATFORM_ADMIN)
        cls.admin_token = generate_auth_token(76, 'PLATFORM_ADMIN')
        cls.admin_headers = {'Authorization': f'Bearer {cls.admin_token}'}

        # User 1 is Alex Morgan (AGENT)
        cls.agent_token = generate_auth_token(1, 'AGENT')
        cls.agent_headers = {'Authorization': f'Bearer {cls.agent_token}'}

        # User 2 is Robert Otieno (WORKFORCE_OFFICER)
        cls.officer_token = generate_auth_token(2, 'WORKFORCE_OFFICER')
        cls.officer_headers = {'Authorization': f'Bearer {cls.officer_token}'}

    @classmethod
    def tearDownClass(cls):
        pass

    def test_01_platform_admin_overview_success(self):
        """Platform Admin can access platform overview KPIs and active Model v3 metadata."""
        r = self.client.get('/api/platform-admin/overview', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("users", data.get("data", {}))
        self.assertIn("operations", data.get("data", {}))
        self.assertIn("active_model", data.get("data", {}))
        self.assertEqual(data["data"]["active_model"]["model_version"], "3.0.0")

    def test_02_agent_forbidden_on_platform_admin(self):
        """Agents are strictly rejected with 403 Forbidden on Platform Admin endpoints."""
        r = self.client.get('/api/platform-admin/overview', headers=self.agent_headers)
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("Platform Administrator privileges required", data.get("error", ""))

    def test_03_workforce_officer_forbidden_on_platform_admin(self):
        """Workforce Officers are strictly rejected with 403 Forbidden on Platform Admin endpoints."""
        r = self.client.get('/api/platform-admin/overview', headers=self.officer_headers)
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("Platform Administrator privileges required", data.get("error", ""))

    def test_04_user_management_and_anti_lockout(self):
        """Platform Admin can list users, update roles, but cannot lock themselves out."""
        # 1. List users
        r = self.client.get('/api/platform-admin/users', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        users = r.get_json().get("data", [])
        self.assertGreater(len(users), 0)

        # 2. Anti-lockout: Admin cannot demote self
        r_self_demote = self.client.patch('/api/platform-admin/users/76/role', headers=self.admin_headers, json={'role': 'AGENT'})
        self.assertEqual(r_self_demote.status_code, 400)
        self.assertIn("Anti-lockout", r_self_demote.get_json().get("error", ""))

        # 3. Anti-lockout: Admin cannot suspend self
        r_self_suspend = self.client.patch('/api/platform-admin/users/76/status', headers=self.admin_headers, json={'is_active': False})
        self.assertEqual(r_self_suspend.status_code, 400)
        self.assertIn("Anti-lockout", r_self_suspend.get_json().get("error", ""))

    def test_05_audit_logs_streaming(self):
        """Platform Admin can query real audit events from MySQL audit_logs."""
        r = self.client.get('/api/platform-admin/audit-logs?limit=10', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreater(len(data.get("data", [])), 0)
        self.assertIn("action", data["data"][0])
        self.assertIn("created_at", data["data"][0])

    def test_06_system_health_telemetry(self):
        """Platform Admin can inspect MySQL health, latency, uptime, and table row metrics."""
        r = self.client.get('/api/platform-admin/system-health', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data.get("status"), "HEALTHY")
        self.assertTrue(data.get("database", {}).get("connected"))
        self.assertIn("latency_ms", data.get("database", {}))
        self.assertIn("uptime_seconds", data.get("server", {}))
        self.assertIn("tables", data.get("database", {}))

    def test_07_ml_governance_specifications(self):
        """Platform Admin can review Model v3 real metadata metrics, confusion matrix, and production usage."""
        r = self.client.get('/api/platform-admin/ml-model', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json().get("data", {})
        meta = data.get("model_metadata", {})
        self.assertEqual(meta.get("model_name"), "VerifyMesh_Stage2_Suitability_LR_v3")
        self.assertEqual(meta.get("features_count"), 5)
        self.assertEqual(meta.get("decision_threshold"), 0.60)
        self.assertEqual(meta.get("model_sha256"), "2897f781217895e6d7b285769132022e943e4ed9925e50a4e92938febc30f745")
        self.assertNotIn("model_path", meta)
        self.assertTrue(meta.get("available_for_predictions"))
        # Real metadata metrics (Corrected_LR_v3_Hardened)
        test_metrics = data.get("training_and_evaluation", {}).get("test_metrics", {})
        self.assertAlmostEqual(test_metrics.get("accuracy", 0), 0.65176, places=3)
        self.assertAlmostEqual(test_metrics.get("roc_auc", 0), 0.6767, places=3)
        # Production usage from MySQL
        prod = data.get("production_usage", {})
        self.assertGreater(prod.get("total_ml_predictions", 0), 0)

    def test_08_workforce_officer_has_access_to_workforce_portal(self):
        """Workforce Officer can access the operational workforce dashboard routes."""
        r = self.client.get('/api/admin/overview', headers=self.officer_headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("total_agents", r.get_json().get("data", {}))

    def test_09_user_profile_detail_and_verification_summary(self):
        """Platform Admin can inspect an individual user's profile and verification summary."""
        r = self.client.get('/api/platform-admin/users/1', headers=self.admin_headers)
        self.assertEqual(r.status_code, 200)
        data = r.get_json().get("data", {})
        self.assertEqual(data.get("profile", {}).get("email"), "alex.morgan@university.edu")
        self.assertIsNotNone(data.get("verification_summary"))

if __name__ == '__main__':
    unittest.main()
