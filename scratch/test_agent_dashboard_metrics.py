import os
import sys
import unittest

from backend.db import get_mysql_connection, get_agent_tasks_with_eligibility, get_agent_assessment
from backend.auth_routes import generate_auth_token

def test_agent_dashboard_metrics():
    print("============================================================")
    print("VERIFYING AGENT DASHBOARD WORK OVERVIEW METRICS")
    print("============================================================")

    # 1. Test Assessed Agent (User ID 1 - Alex Morgan)
    tasks_agent1 = get_agent_tasks_with_eligibility(1)
    status_agent1 = get_agent_assessment(1)
    
    print(f"\n--- Agent 1 (Alex Morgan - Assessed) ---")
    print(f"Has Assessed: {bool(status_agent1 and status_agent1.get('competency_level'))}")
    print(f"Competency Level: {status_agent1.get('competency_level') if status_agent1 else 'None'}")
    print(f"Evaluation Decision: {status_agent1.get('evaluation_decision') if status_agent1 else 'None'}")
    print(f"Total Published Tasks in Catalog: {len(tasks_agent1)}")
    
    available_agent1 = [t for t in tasks_agent1 if t.get('can_apply') or t.get('state') == 'Ready to Apply']
    under_review_agent1 = [t for t in tasks_agent1 if t.get('application_status') in ('Application Submitted', 'Under Review') or t.get('state') == 'Under Review']
    assigned_agent1 = [t for t in tasks_agent1 if t.get('application_status') in ('Assigned', 'Accepted') or t.get('state') == 'Assigned']
    
    print(f"Available Opportunities Count: {len(available_agent1)}")
    print(f"Applications Under Review Count: {len(under_review_agent1)}")
    print(f"Assigned Work Count: {len(assigned_agent1)}")
    
    assert len(tasks_agent1) > 0, "Agent 1 should see active tasks"
    assert len(available_agent1) >= 1, "Agent 1 should have at least 1 ready to apply task"
    print("[PASS] Agent 1 authoritative metrics verified.")

    # 2. Test Unassessed Agent (User ID 6 - Daniel Nyabuto)
    tasks_agent6 = get_agent_tasks_with_eligibility(6)
    status_agent6 = get_agent_assessment(6)

    print(f"\n--- Agent 6 (Daniel Nyabuto - Unassessed) ---")
    print(f"Has Assessed: {bool(status_agent6 and status_agent6.get('competency_level'))}")
    print(f"Competency Level: {status_agent6.get('competency_level') if status_agent6 else 'Not Yet Assessed'}")
    
    available_agent6 = [t for t in tasks_agent6 if t.get('can_apply') or t.get('state') == 'Ready to Apply']
    print(f"Available Opportunities Count: {len(available_agent6)}")
    
    # For an unassessed agent, tasks require assessment, so available count must be 0
    assert len(available_agent6) == 0, "Unassessed agent must have 0 ready to apply tasks until assessed"
    assert status_agent6 is None, "Agent 6 must not have an active assessment record"
    print("[PASS] Unassessed agent metrics verified (0 opportunities, triggers 'Assessment Needed' state).")

    # 3. Simulate Task Application and verify Under Review & Assigned transitions
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # Check if agent 1 has task 4 (Technical Support Agent)
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = 1")
            agent_id = cursor.fetchone()["agent_id"]
            
            # Clean any old test applications for task 4
            cursor.execute("DELETE FROM task_applications WHERE agent_id = %s AND task_id = 4", (agent_id,))
            conn.commit()

            # Insert application in 'Application Submitted' status
            cursor.execute("""
                INSERT INTO task_applications (task_id, agent_id, status, applied_at, notes)
                VALUES (4, %s, 'Application Submitted', NOW(), 'Automated test application')
            """, (agent_id,))
            conn.commit()

            # Re-evaluate tasks
            t_submitted = get_agent_tasks_with_eligibility(1)
            under_rev = [t for t in t_submitted if t.get('application_status') in ('Application Submitted', 'Under Review') or t.get('state') == 'Under Review']
            assert len(under_rev) == 1, "Under review count must reflect 1 after submitting application"
            print("[PASS] Transition to 'Application Submitted' updates under_review count to 1.")

            # Update status to 'Assigned'
            cursor.execute("""
                UPDATE task_applications SET status = 'Assigned' WHERE agent_id = %s AND task_id = 4
            """, (agent_id,))
            conn.commit()

            t_assigned = get_agent_tasks_with_eligibility(1)
            assigned_count = [t for t in t_assigned if t.get('application_status') in ('Assigned', 'Accepted') or t.get('state') == 'Assigned']
            assert len(assigned_count) == 1, "Assigned work count must reflect 1"
            print("[PASS] Transition to 'Assigned' updates assigned work count to 1.")

            # Cleanup
            cursor.execute("DELETE FROM task_applications WHERE agent_id = %s AND task_id = 4", (agent_id,))
            conn.commit()
            print("[CLEANUP] Successfully cleaned up test application.")
    finally:
        conn.close()

    print("\n============================================================")
    print("ALL AGENT DASHBOARD METRIC TESTS PASSED SUCCESSFULLY!")
    print("============================================================")

if __name__ == "__main__":
    test_agent_dashboard_metrics()
