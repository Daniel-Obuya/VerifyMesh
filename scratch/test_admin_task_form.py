import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from backend.auth_routes import generate_auth_token
from backend.db import get_mysql_connection, get_agent_tasks_with_eligibility

API_BASE = "http://localhost:5000"

def make_request(path, method="GET", payload=None, token=None):
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except:
            parsed = {"raw": body}
        return e.code, parsed

def run_tests():
    print("=" * 60)
    print("VERIFYING ADMIN CREATE TASK FORM ACCEPTANCE CRITERIA")
    print("=" * 60)

    # 1. Setup Auth Tokens
    # Admin (User 2: System Administrator)
    admin_token = generate_auth_token(2, "Administrator")
    # Agent (User 1: Alex Morgan)
    agent_token = generate_auth_token(1, "Agent")

    created_task_ids = []

    try:
        # ---------------------------------------------------------
        # Criteria 9: Agents cannot create or publish tasks (403)
        # ---------------------------------------------------------
        print("\n--- Criteria 9: RBAC Guard (Agents blocked from Task Creation) ---")
        status, res = make_request("/api/admin/tasks", method="POST", payload={"task_name": "Agent Hack Task"}, token=agent_token)
        assert status == 403, f"Expected 403 for Agent, got {status}: {res}"
        assert "Administrator role required" in res.get("error", ""), f"Unexpected error message: {res}"
        print(f"[PASS] Criteria 9: Agent rejected with HTTP 403: {res.get('error')}")

        # ---------------------------------------------------------
        # Criteria 5: Invalid or incomplete submissions rejected
        # ---------------------------------------------------------
        print("\n--- Criteria 5: Backend Validations on Incomplete/Invalid Input ---")
        # 5a: Missing title
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "category_id": 2, "description": "This is a detailed description of the role."
        }, token=admin_token)
        assert status == 400, f"Expected 400, got {status}: {res}"
        print(f"  [x] Missing title rejected: {res.get('error')}")

        # 5b: Generic title
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Task 1", "category_id": 2, "description": "Valid detailed description for this task."
        }, token=admin_token)
        assert status == 400 and "generic" in res.get("error", "").lower(), f"Expected generic title rejection: {res}"
        print(f"  [x] Generic title 'Task 1' rejected: {res.get('error')}")

        # 5c: Missing category
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Valid Title Here", "description": "Valid detailed description for this task."
        }, token=admin_token)
        assert status == 400 and "category" in res.get("error", "").lower(), f"Expected category rejection: {res}"
        print(f"  [x] Missing category rejected: {res.get('error')}")

        # 5d: Short description when publishing
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Senior Cloud Specialist", "category_id": 2, "description": "Too short", "status": "ACTIVE"
        }, token=admin_token)
        assert status == 400 and "description" in res.get("error", "").lower(), f"Expected description rejection: {res}"
        print(f"  [x] Short description on publish rejected: {res.get('error')}")

        # 5e: Hourly rate invalid (max < min)
        future_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Senior Cloud Specialist",
            "category_id": 2,
            "description": "Comprehensive troubleshooting and architecture advisory for enterprise clients.",
            "status": "ACTIVE",
            "payment_type": "Hourly",
            "hourly_rate_min": 5000,
            "hourly_rate_max": 2000,  # Max < Min
            "application_deadline": future_date
        }, token=admin_token)
        assert status == 400 and "hourly" in res.get("error", "").lower(), f"Expected hourly rate rejection: {res}"
        print(f"  [x] Inverted hourly rates rejected: {res.get('error')}")

        # 5f: Past deadline on publish
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Senior Cloud Specialist",
            "category_id": 2,
            "description": "Comprehensive troubleshooting and architecture advisory for enterprise clients.",
            "status": "ACTIVE",
            "payment_type": "Fixed Budget",
            "fixed_budget": 50000,
            "application_deadline": "2020-01-01"  # Past
        }, token=admin_token)
        assert status == 400 and "future date" in res.get("error", "").lower(), f"Expected deadline rejection: {res}"
        print(f"  [x] Past deadline rejected: {res.get('error')}")

        # 5g: Missing location on Hybrid
        status, res = make_request("/api/admin/tasks", method="POST", payload={
            "task_name": "Senior Cloud Specialist",
            "category_id": 2,
            "description": "Comprehensive troubleshooting and architecture advisory for enterprise clients.",
            "status": "ACTIVE",
            "work_arrangement": "Hybrid",
            "location": "",
            "payment_type": "Fixed Budget",
            "fixed_budget": 50000,
            "application_deadline": future_date
        }, token=admin_token)
        assert status == 400 and "location" in res.get("error", "").lower(), f"Expected location rejection: {res}"
        print(f"  [x] Missing location on Hybrid rejected: {res.get('error')}")

        print("[PASS] Criteria 5: All validation constraints strictly verified.")

        # ---------------------------------------------------------
        # Criteria 1: Save valid Draft
        # ---------------------------------------------------------
        print("\n--- Criteria 1 & 10: Saving Valid Draft & Isolation from Agents ---")
        draft_payload = {
            "task_name": "Draft Incident Recovery Lead",
            "category_id": 2,
            "description": "Preliminary draft for upcoming regional incident response unit.",
            "work_arrangement": "Remote",
            "payment_type": "Hourly",
            "currency": "KES",
            "hourly_rate_min": 3000,
            "hourly_rate_max": 4500,
            "status": "DRAFT"
        }
        status, res = make_request("/api/admin/tasks", method="POST", payload=draft_payload, token=admin_token)
        assert status == 201, f"Expected 201 for valid draft, got {status}: {res}"
        draft_id = res["data"]["task_id"]
        created_task_ids.append(draft_id)
        assert res["data"]["status"] == "DRAFT", f"Expected DRAFT status: {res}"
        print(f"[PASS] Criteria 1: Draft task #{draft_id} created successfully.")

        # Criteria 10: Verify draft is hidden from agent catalog
        agent_tasks = get_agent_tasks_with_eligibility(1)
        draft_in_agent_view = any(t["task_id"] == draft_id for t in agent_tasks)
        assert not draft_in_agent_view, f"CRITICAL: Draft task #{draft_id} leaked to Agent active tasks!"
        print(f"[PASS] Criteria 10: Draft task #{draft_id} is strictly HIDDEN from Agent catalog.")

        # ---------------------------------------------------------
        # Criteria 2, 3, 4, 6, 7, 8: Publish Valid Task with Full Specs
        # ---------------------------------------------------------
        print("\n--- Criteria 2, 3, 4, 6, 7, 8: Publishing Full Production Task ---")
        publish_payload = {
            "task_name": "Tier-3 Customer Escalation Specialist",
            "category_id": 2,
            "description": "Lead multi-channel resolution for enterprise client incidents, analyze root cause logs, and ensure strict SLA adherence.",
            "deliverables": "- Resolve tier-3 escalation tickets within 4-hour SLA\n- Conduct bi-weekly post-mortems\n- Mentor entry-level agents",
            "required_skills": ["Customer Support", "Technical Diagnostics", "Incident De-escalation"],
            "work_arrangement": "Hybrid",
            "location": "Nairobi Hub / East Africa Region",
            "payment_type": "Hourly",
            "currency": "KES",
            "hourly_rate_min": 3500.00,
            "hourly_rate_max": 5500.00,
            "positions_count": 3,
            "application_deadline": future_date,
            "expected_duration": "6 months",
            "minimum_competency": "COMPETENT",
            "required_certification_id": 1,  # Customer Service Certification
            "minimum_experience_months": 12,
            "exam_required": True,
            "exam_id": 3,  # Customer Support Diagnostic Assessment (Category 2)
            "status": "ACTIVE"
        }
        status, res = make_request("/api/admin/tasks", method="POST", payload=publish_payload, token=admin_token)
        assert status == 201, f"Expected 201 for publish, got {status}: {res}"
        pub_id = res["data"]["task_id"]
        created_task_ids.append(pub_id)
        assert res["data"]["status"] == "ACTIVE"
        print(f"[PASS] Criteria 2: Published task #{pub_id} created with HTTP 201.")

        # Criteria 3: Persistence after refresh (GET /api/admin/tasks/<id>)
        status, get_res = make_request(f"/api/admin/tasks/{pub_id}", method="GET", token=admin_token)
        assert status == 200, f"Expected 200 for task detail, got {status}: {get_res}"
        t_data = get_res["data"]
        assert t_data["task_name"] == "Tier-3 Customer Escalation Specialist"
        assert t_data["work_arrangement"] == "Hybrid"
        assert t_data["location"] == "Nairobi Hub / East Africa Region"
        assert float(t_data["hourly_rate_min"]) == 3500.00
        assert float(t_data["hourly_rate_max"]) == 5500.00
        assert t_data["positions_count"] == 3
        assert t_data["minimum_competency"] == "COMPETENT"
        assert t_data["required_certification_id"] == 1
        assert t_data["exam_required"] == 1
        print(f"[PASS] Criteria 3, 6, 7, 8: Task #{pub_id} verified persisted with complete structured fields.")

        # Criteria 4: Appears in Agent catalog
        agent_tasks_after = get_agent_tasks_with_eligibility(1)
        matching_agent_task = next((t for t in agent_tasks_after if t["task_id"] == pub_id), None)
        assert matching_agent_task is not None, f"Published task #{pub_id} not found in agent catalog!"
        assert "KES 3,500 - 5,500 / hr" in matching_agent_task["payout"], f"Unexpected payout format: {matching_agent_task['payout']}"
        assert matching_agent_task["work_arrangement"] == "Hybrid"
        print(f"[PASS] Criteria 4: Task #{pub_id} appeared in Agent catalog with live payout '{matching_agent_task['payout']}'.")

        # ---------------------------------------------------------
        # Criteria 12: Updating existing task
        # ---------------------------------------------------------
        print("\n--- Criteria 12: Editing / Updating Existing Task ---")
        update_payload = dict(publish_payload)
        update_payload["hourly_rate_min"] = 4000.00
        update_payload["hourly_rate_max"] = 6000.00
        update_payload["description"] = "Updated description with expanded enterprise escalation duties and higher rate."
        status, upd_res = make_request(f"/api/admin/tasks/{pub_id}", method="PUT", payload=update_payload, token=admin_token)
        assert status == 200, f"Expected 200 for update, got {status}: {upd_res}"
        
        # Verify update persisted
        status, check_res = make_request(f"/api/admin/tasks/{pub_id}", method="GET", token=admin_token)
        assert float(check_res["data"]["hourly_rate_min"]) == 4000.00
        print(f"[PASS] Criteria 12: Task #{pub_id} successfully updated with new rate KES 4,000 - 6,000.")

        print("\n" + "=" * 60)
        print("ALL ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        # Cleanup test tasks
        if created_task_ids:
            conn = get_mysql_connection()
            if conn:
                with conn.cursor() as cursor:
                    format_strings = ','.join(['%s'] * len(created_task_ids))
                    cursor.execute(f"DELETE FROM tasks WHERE task_id IN ({format_strings})", tuple(created_task_ids))
                conn.commit()
                conn.close()
                print(f"\n[CLEANUP] Deleted test fixtures: task IDs {created_task_ids}")

if __name__ == "__main__":
    run_tests()
