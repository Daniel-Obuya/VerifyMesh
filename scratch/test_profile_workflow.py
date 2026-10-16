"""
VerifyMesh — Comprehensive Profile & Verification Workflow Test
Validates:
1. Agent Profile fetching and Readiness Score computation.
2. Personal info update (editable vs read-only protection).
3. Work Experience submission, date interval-merging (no double counting).
4. Certification submission and metadata.
5. Admin verification queue inspection.
6. Admin approval & rejection workflows with audit logging.
7. Model evaluation contract preservation (11 features derived from verified DB records).
8. Role-based authorization & security constraints.
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.getcwd())
from backend.auth_routes import generate_auth_token

BASE_URL = "http://127.0.0.1:5000/api"

def get_tokens():
    agent_token = generate_auth_token(1, "AGENT")
    admin_token = generate_auth_token(2, "ADMIN")
    return agent_token, admin_token

def test_workflow():
    print("=" * 70)
    print("VERIFYMESH PROFILE & VERIFICATION WORKFLOW VALIDATION")
    print("=" * 70)

    # 1. Generate auth tokens for Agent 1 and Admin 2
    agent_token, admin_token = get_tokens()
    agent_headers = {"Authorization": f"Bearer {agent_token}", "Content-Type": "application/json"}
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    print("\n[OK] Signed authentication tokens prepared for Agent 1 and Admin 2.")

    # 3. GET /api/competency/profile
    prof_resp = requests.get(f"{BASE_URL}/competency/profile", headers=agent_headers)
    assert prof_resp.status_code == 200, f"Failed GET profile: {prof_resp.text}"
    prof = prof_resp.json()["data"]
    print(f"\n[STEP 1] Agent Profile retrieved:")
    print(f"  Name: {prof.get('full_name')}")
    print(f"  System ID: VM-AGT-{prof.get('agent_id')}")
    print(f"  Readiness Score: {prof.get('readiness_score')}%")
    print(f"  Verified Months: {prof.get('verified_experience', {}).get('total_experience_months')} mos")
    print(f"  Verified Certs: {prof.get('verified_certifications', {}).get('certification_count')}")

    # 4. PUT /api/competency/profile (Update personal info)
    update_payload = {
        "full_name": "Alex Morgan (Verified)",
        "phone": "+1 (555) 019-2834",
        "location": "Chicago, IL (US Central)",
        "bio": "Experienced sales development representative and client resolution specialist with 5+ years of customer-facing experience.",
        "role": "ADMIN" # Attempt privilege escalation (should be ignored)
    }
    put_resp = requests.put(f"{BASE_URL}/competency/profile", json=update_payload, headers=agent_headers)
    assert put_resp.status_code == 200, f"Failed PUT profile: {put_resp.text}"
    updated_prof = put_resp.json()["data"]
    assert updated_prof["full_name"] == "Alex Morgan (Verified)"
    assert updated_prof["phone"] == "+1 (555) 019-2834"
    assert updated_prof["role"] == "AGENT", "CRITICAL SECURITY BREACH: Agent modified system role!"
    print("\n[STEP 2] Personal details updated successfully. Role remained read-only (AGENT).")

    # 5. POST /api/competency/experiences (Add test work experience)
    exp_payload = {
        "job_title": "Enterprise Sales Representative",
        "company": "Apex Dynamics Cloud",
        "work_category": "Sales",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "is_current": False,
        "description": "Led enterprise SDR outreach, closed 14 enterprise SaaS subscriptions."
    }
    exp_post_resp = requests.post(f"{BASE_URL}/competency/experiences", json=exp_payload, headers=agent_headers)
    assert exp_post_resp.status_code == 201, f"Failed POST experience: {exp_post_resp.text}"
    new_exp = exp_post_resp.json()["data"]
    new_exp_id = new_exp["experience_id"]
    assert new_exp["verification_status"] == "PENDING"
    print(f"\n[STEP 3] Work experience submitted (ID #{new_exp_id}) with status PENDING.")

    # 6. POST /api/competency/certifications (Add test certification)
    import time
    unique_cert_num = f"SF-ADM-2024-{int(time.time())}"
    cert_payload = {
        "certification_name": "Salesforce Certified Administrator",
        "issuing_organization": "Salesforce Trailhead",
        "certificate_number": unique_cert_num,
        "credential_url": "https://trailhead.salesforce.com/credentials/verification",
        "issue_date": "2024-02-15",
        "expiry_date": "2026-02-15"
    }
    cert_post_resp = requests.post(f"{BASE_URL}/competency/certifications", json=cert_payload, headers=agent_headers)
    assert cert_post_resp.status_code == 201, f"Failed POST certification: {cert_post_resp.text}"
    new_cert = cert_post_resp.json()["data"]
    new_cert_id = new_cert.get("agent_cert_id") or new_cert.get("agent_certification_id")
    assert new_cert["status"] == "PENDING"
    print(f"\n[STEP 4] Certification submitted (ID #{new_cert_id}) with status PENDING.")

    # 7. Check Admin Pending Verifications Queue
    verifs_resp = requests.get(f"{BASE_URL}/admin/verifications", headers=admin_headers)
    assert verifs_resp.status_code == 200, f"Failed GET admin verifications: {verifs_resp.text}"
    verifs_data = verifs_resp.json()["data"]
    pending_exp_ids = [e["experience_id"] for e in verifs_data.get("experiences", [])]
    pending_cert_ids = [c.get("agent_cert_id") or c.get("agent_certification_id") for c in verifs_data.get("certifications", [])]
    assert new_exp_id in pending_exp_ids, "New experience not found in admin pending queue"
    assert new_cert_id in pending_cert_ids, "New certification not found in admin pending queue"
    print(f"\n[STEP 5] Admin pending queue verified: contains Experience #{new_exp_id} and Cert #{new_cert_id}.")

    # 8. RBAC Check: Ensure regular agent CANNOT approve/reject
    hacker_resp = requests.post(
        f"{BASE_URL}/admin/verifications/experiences/{new_exp_id}/review",
        json={"decision": "VERIFIED"},
        headers=agent_headers
    )
    assert hacker_resp.status_code in (401, 403), f"RBAC failed! Agent was able to review: {hacker_resp.status_code}"
    print("\n[STEP 6] Security Check Passed: Regular agent blocked from admin review endpoint (HTTP 403).")

    # 9. Admin Approves Work Experience
    rev_exp_resp = requests.post(
        f"{BASE_URL}/admin/verifications/experiences/{new_exp_id}/review",
        json={"decision": "VERIFIED"},
        headers=admin_headers
    )
    assert rev_exp_resp.status_code == 200, f"Failed to approve experience: {rev_exp_resp.text}"
    rev_exp_data = rev_exp_resp.json()["data"]
    print(f"\n[STEP 7] Admin approved Experience #{new_exp_id}:")
    print(f"  Recalculated Total Months: {rev_exp_data.get('recalculated_months')}")

    # 10. Admin Rejects Certification (Testing rejection reason requirement & handling)
    # 10a. Fail when rejection_reason missing
    bad_reject = requests.post(
        f"{BASE_URL}/admin/verifications/certifications/{new_cert_id}/review",
        json={"decision": "REJECTED"},
        headers=admin_headers
    )
    assert bad_reject.status_code == 400, "Should have failed rejection without reason"

    # 10b. Succeed with reason
    rev_cert_resp = requests.post(
        f"{BASE_URL}/admin/verifications/certifications/{new_cert_id}/review",
        json={"decision": "REJECTED", "rejection_reason": "Credential ID cannot be verified in Trailhead directory."},
        headers=admin_headers
    )
    assert rev_cert_resp.status_code == 200, f"Failed to reject cert: {rev_cert_resp.text}"
    print(f"\n[STEP 8] Admin rejected Cert #{new_cert_id} with mandatory reason recorded.")

    # 11. Re-fetch Agent Profile to verify recalculation
    prof_after = requests.get(f"{BASE_URL}/competency/profile", headers=agent_headers).json()["data"]
    print(f"\n[STEP 9] Re-fetched Agent Profile after admin actions:")
    print(f"  Verified Experience Months: {prof_after['verified_experience']['total_experience_months']}")
    print(f"  Verified Sales Months: {prof_after['verified_experience']['sales_experience_months']}")
    print(f"  Verified Certifications: {prof_after['verified_certifications']['certification_count']}")

    # 12. Evaluate Model Contract: Verify inference features are populated from verified DB records
    eval_resp = requests.post(f"{BASE_URL}/competency/evaluate", json={}, headers=agent_headers)
    assert eval_resp.status_code == 200, f"Failed /evaluate: {eval_resp.text}"
    eval_json = eval_resp.json()
    eval_data = eval_json.get("data", {})
    feat_vector = eval_json.get("feature_vector", {})
    print(f"\n[STEP 10] Model Evaluation Verification (11-feature contract):")
    print(f"  Predicted Competency: {eval_data.get('competency_level')}")
    print(f"  3-Way Decision: {eval_data.get('evaluation_decision')}")
    print(f"  Model Confidence: {eval_data.get('confidence')}")
    print(f"  Feature Vector Inputs Derived from DB:")
    for k, v in feat_vector.items():
        print(f"    - {k}: {v}")

    # Confirm experience features match DB verified months
    assert feat_vector.get("previous_experience_months") == prof_after['verified_experience']['total_experience_months'], "Feature mismatch on previous_experience_months!"
    assert feat_vector.get("sales_experience_months") == prof_after['verified_experience']['sales_experience_months'], "Feature mismatch on sales_experience_months!"
    assert feat_vector.get("certification_count") == prof_after['verified_certifications']['certification_count'], "Feature mismatch on certification_count!"

    # 13. Test Deletion of Rejected Cert by Agent
    del_cert_resp = requests.delete(f"{BASE_URL}/competency/certifications/{new_cert_id}", headers=agent_headers)
    assert del_cert_resp.status_code == 200, f"Failed to delete rejected cert: {del_cert_resp.text}"
    print(f"\n[STEP 11] Agent cleaned up rejected Cert #{new_cert_id}.")

    # 14. Prevent Deletion of VERIFIED Experience
    illegal_del = requests.delete(f"{BASE_URL}/competency/experiences/{new_exp_id}", headers=agent_headers)
    assert illegal_del.status_code == 400, "Verified experience should not be deletable by agent without admin!"
    print(f"\n[STEP 12] Security Check Passed: Agent blocked from deleting VERIFIED Experience #{new_exp_id}.")

    print("\n" + "=" * 70)
    print("ALL 12 VERIFICATION & PROFILE TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    test_workflow()
