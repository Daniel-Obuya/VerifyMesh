"""
Tests for task deactivation and deletion.
"""
import unittest
from backend.db import get_mysql_connection, delete_task, set_task_status

class TestTaskManagement(unittest.TestCase):
    def setUp(self):
        self.conn = get_mysql_connection()
        self.created_task_ids = []

    def tearDown(self):
        for task_id in self.created_task_ids:
            try:
                delete_task(task_id)
            except Exception:
                pass
        if self.conn:
            self.conn.close()

    def test_task_deactivation_and_deletion(self):
        if not self.conn:
            self.skipTest("Database not connected")

        cursor = self.conn.cursor()
        # Create a test task
        cursor.execute(
            """
            INSERT INTO tasks (category_id, task_name, description, payment_type, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (1, "Test Deactivation Task", "Testing task deactivation and deletion", "Hourly", "ACTIVE")
        )
        self.conn.commit()
        task_id = cursor.lastrowid
        self.created_task_ids.append(task_id)

        # 1. Verify it appears in active tasks
        cursor.execute("SELECT status FROM tasks WHERE task_id = %s", (task_id,))
        row = cursor.fetchone()
        self.assertEqual(row["status"], "ACTIVE")

        # 2. Deactivate the task
        success = set_task_status(task_id, "INACTIVE", admin_user_id=1)
        self.assertTrue(success)

        self.conn.commit()
        cursor.execute("SELECT status FROM tasks WHERE task_id = %s", (task_id,))
        row = cursor.fetchone()
        self.assertEqual(row["status"], "INACTIVE")

        # 3. Agent tasks should only return ACTIVE tasks
        cursor.execute("SELECT task_id FROM tasks WHERE status = 'ACTIVE' AND task_id = %s", (task_id,))
        active_row = cursor.fetchone()
        self.assertIsNone(active_row, "Deactivated task must not appear in active tasks query")

        # 4. Delete the task
        del_success = delete_task(task_id, admin_user_id=1)
        self.assertTrue(del_success)

        self.conn.commit()
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = %s", (task_id,))
        deleted_row = cursor.fetchone()
        self.assertIsNone(deleted_row, "Deleted task must not exist in tasks table")

        # 5. Calling delete on non-existent task raises error
        with self.assertRaises((ValueError, RuntimeError)):
            delete_task(task_id, admin_user_id=1)

    def test_admin_delete_task_api_endpoint(self):
        if not self.conn:
            self.skipTest("Database not connected")
        from backend.app import create_app
        from backend.auth_routes import generate_auth_token

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (category_id, task_name, description, payment_type, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (1, "API Delete Test Task", "For testing DELETE /api/admin/tasks/<id>", "Hourly", "ACTIVE")
        )
        self.conn.commit()
        task_id = cursor.lastrowid
        self.created_task_ids.append(task_id)

        token = generate_auth_token(user_id=2, role="Administrator")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Non-admin should be rejected
        agent_token = generate_auth_token(user_id=1, role="Agent")
        bad_res = client.delete(f"/api/admin/tasks/{task_id}", headers={"Authorization": f"Bearer {agent_token}"})
        self.assertEqual(bad_res.status_code, 403)

        # 2. Admin should succeed
        res = client.delete(f"/api/admin/tasks/{task_id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        # 3. Verify task no longer exists in DB
        self.conn.commit()
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = %s", (task_id,))
        self.assertIsNone(cursor.fetchone())

        # 4. Deleting already deleted task returns 404
        res_404 = client.delete(f"/api/admin/tasks/{task_id}", headers=headers)
        self.assertEqual(res_404.status_code, 404)

    def test_admin_task_applications_workflow(self):
        """
        Verify end-to-end task application review, status transitions, and assignment:
        1. Agent applies to a task.
        2. Admin lists applicants and sees full profile + requirements checklist.
        3. Admin updates status to 'Shortlisted'.
        4. Admin assigns the task to the applicant (atomic status update to 'Assigned' and task status to 'COMPLETED').
        5. Agent retrieves their live application and assignment status via /api/competency/applications.
        """
        if not self.conn:
            self.skipTest("Database not connected")
        from backend.app import create_app
        from backend.auth_routes import generate_auth_token

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        cursor = self.conn.cursor()

        # Create a test task requiring 0 exp, no certs, no exam
        cursor.execute(
            """
            INSERT INTO tasks (category_id, task_name, description, payment_type, fixed_budget, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (1, "E2E Assignment Test Task", "Task for testing review and assignment", "Fixed Budget", 25000.00, "ACTIVE")
        )
        self.conn.commit()
        task_id = cursor.lastrowid
        self.created_task_ids.append(task_id)

        # Insert minimal requirement
        cursor.execute(
            """
            INSERT INTO task_requirements (task_id, minimum_competency, minimum_experience_months, exam_required)
            VALUES (%s, 'ELIGIBLE', 0, 0)
            """,
            (task_id,)
        )
        self.conn.commit()

        admin_token = generate_auth_token(user_id=2, role="Administrator")
        admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

        agent_token = generate_auth_token(user_id=1, role="Agent")
        agent_headers = {"Authorization": f"Bearer {agent_token}", "Content-Type": "application/json"}

        # 1. Agent submits application
        apply_res = client.post(
            f"/api/competency/tasks/{task_id}/apply",
            headers=agent_headers,
            json={"notes": "Ready to commence implementation immediately."}
        )
        self.assertEqual(apply_res.status_code, 201)
        app_id = apply_res.get_json()["data"]["application_id"]

        # 2. Admin retrieves task applicants
        apps_res = client.get(f"/api/admin/tasks/{task_id}/applications", headers=admin_headers)
        self.assertEqual(apps_res.status_code, 200)
        apps_data = apps_res.get_json()["data"]
        self.assertGreaterEqual(len(apps_data), 1)

        target_app = next((a for a in apps_data if a["application_id"] == app_id), None)
        self.assertIsNotNone(target_app)
        self.assertEqual(target_app["status"], "Application Submitted")
        self.assertEqual(target_app["notes"], "Ready to commence implementation immediately.")
        self.assertIn("prerequisites", target_app)

        # 3. Admin updates status to 'Shortlisted'
        status_res = client.post(
            f"/api/admin/applications/{app_id}/status",
            headers=admin_headers,
            json={"status": "Shortlisted", "notes": "Shortlisted for exemplary portfolio."}
        )
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.get_json()["data"]["status"], "Shortlisted")

        # 4. Admin assigns the task to applicant
        assign_res = client.post(
            f"/api/admin/applications/{app_id}/assign",
            headers=admin_headers
        )
        self.assertEqual(assign_res.status_code, 200)
        self.assertEqual(assign_res.get_json()["data"]["status"], "Assigned")
        self.assertEqual(assign_res.get_json()["data"]["task_status"], "COMPLETED")

        # Verify DB states
        cursor.execute("SELECT status FROM task_applications WHERE application_id = %s", (app_id,))
        self.assertEqual(cursor.fetchone()["status"], "Assigned")

        cursor.execute("SELECT status FROM tasks WHERE task_id = %s", (task_id,))
        self.assertEqual(cursor.fetchone()["status"], "COMPLETED")

        # 5. Agent tracks live application status via GET /api/competency/applications
        agent_apps_res = client.get("/api/competency/applications", headers=agent_headers)
        self.assertEqual(agent_apps_res.status_code, 200)
        agent_apps = agent_apps_res.get_json()["data"]
        agent_target = next((a for a in agent_apps if a["application_id"] == app_id), None)
        self.assertIsNotNone(agent_target)
        self.assertEqual(agent_target["status"], "Assigned")
        self.assertEqual(agent_target["task_status"], "COMPLETED")

    def test_assign_blocked_when_prerequisites_unmet(self):
        """Verify assignment is strictly blocked on server if applicant lacks required experience."""
        if not self.conn:
            self.skipTest("Database not connected")
        from backend.app import create_app
        from backend.auth_routes import generate_auth_token

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        cursor = self.conn.cursor()

        # Create a task requiring 120 months experience (Agent 1 only has 24 or 36)
        cursor.execute(
            """
            INSERT INTO tasks (category_id, task_name, description, payment_type, fixed_budget, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (1, "High Experience Task", "Requires 120 months", "Fixed Budget", 100000.00, "ACTIVE")
        )
        self.conn.commit()
        task_id = cursor.lastrowid
        self.created_task_ids.append(task_id)

        cursor.execute(
            """
            INSERT INTO task_requirements (task_id, minimum_competency, minimum_experience_months, exam_required)
            VALUES (%s, 'ELIGIBLE', 120, 0)
            """,
            (task_id,)
        )
        self.conn.commit()

        # Manually insert application to simulate bypass or state change
        cursor.execute(
            """
            INSERT INTO task_applications (agent_id, task_id, status, notes)
            VALUES (1, %s, 'Application Submitted', 'Trying to assign without experience')
            """,
            (task_id,)
        )
        self.conn.commit()
        app_id = cursor.lastrowid

        admin_token = generate_auth_token(user_id=2, role="Administrator")
        admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

        # Attempt to assign
        assign_res = client.post(
            f"/api/admin/applications/{app_id}/assign",
            headers=admin_headers
        )
        self.assertEqual(assign_res.status_code, 400)
        self.assertIn("experience", assign_res.get_json()["error"].lower())

        # Verify application status was NOT changed to Assigned
        cursor.execute("SELECT status FROM task_applications WHERE application_id = %s", (app_id,))
        self.assertEqual(cursor.fetchone()["status"], "Application Submitted")


if __name__ == "__main__":
    unittest.main()

