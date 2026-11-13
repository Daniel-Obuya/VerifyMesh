# Phase 4A — Abandonment & Expiry Policy Implementation Report

**Document ID:** `docs/assessment/12_abandonment_and_expiry_policy.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Executive Summary

Phase 4A defines and implements configurable abandonment and expiration policies for the VerifyMesh assessment subsystem. 

Prior to Phase 4A, accidental disconnects or tab closures risked being conflated with deliberate abandonment or failing grades. Phase 4A establishes clear operational boundaries separating transient client disconnection from policy-enforced expiration and intentional candidate forfeiture.

---

## 2. Policy Distinction Matrix

| Event | Client State | Server Evaluation | Resumable? | Attempt Quota Impact | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Browser Closed** | Tab closed / Window exit | Attempt remains `IN_PROGRESS` | **Yes** (until `expires_at`) | None until finalized | Candidate can log back in and resume. |
| **Network Loss** | WiFi / Cellular disconnect | Attempt remains `IN_PROGRESS` | **Yes** (until `expires_at`) | None until finalized | Autosave holds draft choices; sync resumes on reconnect. |
| **Window Expiration** | `NOW() > expires_at` | Transitions to `EXPIRED` | **No** | **Counts** toward quota | Marked `score = NULL, passed = 0`. No false zero penalty to averages. |
| **Explicit Forfeit** | Candidate clicks "Abandon" | Transitions to `ABANDONED` | **No** | **Counts** toward quota | Forfeit logged in `audit_logs` to prevent question harvesting. |
| **Platform Outage** | Server crash / glitch | Admin marks `CANCELLED` | **No** | **Exempt** from quota | Recorded with reason; candidate quota restored. |

---

## 3. Question Harvesting Prevention (Attempt Limits)

To prevent candidates from repeatedly opening assessments to survey random question banks without completing them:
1. **Configurable Quota:** Each competency topic specifies `max_attempts` (default: 3).
2. **Quota Counter:** Counts attempts in `('SUBMITTED', 'EXPIRED', 'ABANDONED')`.
3. **Threshold Enforcement:** If attempts reach `max_attempts`, further attempt creation is blocked with `AttemptLimitReachedError` (HTTP 403).
4. **Dashboard Reflection:** The task card reflects `state = 'Attempt Limit Reached'` with an alert directing the candidate to contact a Workforce Officer.

---

## 4. Administrative Exception & Recovery Workflow

To protect candidates against legitimate hardship, technical failures, or network outages, Phase 4A implements an audited Workforce Officer exception interface:

### API Endpoint:
`POST /api/admin/agents/<int:agent_id>/assessment-override`

### Supported Operations:
1. **`GRANT_EXTRA_ATTEMPT`:**
   - Grants `+1` attempt allowance for the candidate on the specified topic.
   - Recorded in `audit_logs` (`ATTEMPT_LIMIT_OVERRIDE_GRANTED`).
   - Immediately enables the candidate to start a new assessment attempt.
2. **`REOPEN_ATTEMPT`:**
   - Extends an expired or closed attempt by 30 minutes (`expires_at = NOW() + INTERVAL 30 MINUTE`).
   - Restores status to `IN_PROGRESS`.
   - Recorded in `audit_logs` (`ATTEMPT_REOPENED_BY_ADMIN`).
3. **`CANCEL_ATTEMPT`:**
   - Marks a specific attempt as `CANCELLED`.
   - Records administrative reason in `closure_reason` and `audit_logs`.
   - The cancelled attempt is excluded from the candidate's attempt count.

---

## 5. Audit Logging & Historical Preservation

Every lifecycle transition and administrative intervention is recorded without destructive overwrites:

```sql
INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
VALUES (%s, 'ASSESSMENT_ATTEMPT_ABANDONED', 'assessment_attempts', %s, %s, NOW());
```

Candidates and administrators can retrieve the complete attempt history at any time:
- Agent API: `GET /api/competency/topics/<id>/history`
- Admin API: `GET /api/admin/agents/<id>/assessment-history`

---

## 6. Verification Summary

- Migration 009 verified on live MySQL database.
- Explicit abandonment verified with audit trail.
- Quota counting and admin overrides verified in automated regression suite.
- 100% test pass rate across `tests/test_phase4_lifecycle_and_expiry.py`.

