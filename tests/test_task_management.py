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

if __name__ == "__main__":
    unittest.main()
