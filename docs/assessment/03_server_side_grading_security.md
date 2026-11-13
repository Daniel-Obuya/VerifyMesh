# Phase 3 — Secure Question Delivery & Server-Side Grading Report

**Document ID:** `docs/assessment/03_server_side_grading_security.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Executive Summary

Phase 3 establishes rigorous anti-tampering and cryptographic boundaries for assessment delivery and scoring in VerifyMesh. 

Prior to Phase 3:
1. Client applications could theoretically craft payloads containing pre-calculated `score`, `passed`, or protected feature fields.
2. Direct attempt manipulation or cross-agent attempt scoring was vulnerable if ownership validation was not strictly enforced at the database transaction layer.

Phase 3 enforces **Zero-Trust Client Scoring**:
- Question delivery payloads strictly strip correct answers, points formulas, and internal evaluation logic.
- Assessment scoring is performed 100% server-side inside atomic database transactions.
- Client-submitted protected fields or scores trigger immediate HTTP 400 rejection.
- Attempt ownership and expiration boundaries are authoritatively enforced.

---

## 2. Secure Question Delivery

When questions are requested via `GET /api/competency/topics/<id>/questions` or initialized via `POST /api/competency/topics/<id>/start-attempt`:

### Information Provided to Client:
- `question_id`: Unique database identifier.
- `topic_id`: Competency topic association.
- `question_text`: Clinical or operational scenario prompt.
- `question_type`: Question format (`MULTIPLE_CHOICE`).
- `points`: Numeric maximum points available for the item.
- `options`: List of option choices with randomized display letters (`A`, `B`, `C`, `D`) and text.
- `question_order`: Shuffled presentation sequence frozen in `question_snapshot_json`.

### Information Strictly Redacted:
- `correct_answer`: Stripped from SQL projection.
- `display_to_original`: Translation map kept in backend snapshot only.
- `points_breakdown` / `weightings`: Internal scoring logic remains server-side.

---

## 3. Server-Side Grading Protocol

When an agent completes an assessment and submits via `POST /api/competency/topics/<id>/submit`:

```
[Agent POST Payload]
{
  "attempt_id": 104,
  "task_id": 4,
  "answers": {
    "9": "B",
    "10": "D",
    "11": "A"
  }
}
      │
      ▼
[1. Security Inspection] ──── Check for forbidden keys (assessment_score, passed, etc.)
      │ (Clean)
      ▼
[2. Authentication & Ownership] ── Verify JWT claims & attempt.agent_id == agent.agent_id
      │ (Authorized)
      ▼
[3. State Validation] ─────── Verify attempt.status == 'IN_PROGRESS' and NOW() < expires_at
      │ (Valid)
      ▼
[4. Question & Option Validation] ── Verify all QIDs belong to topic and options in ['A'..'D']
      │ (Validated)
      ▼
[5. Authoritative Grading] ── Re-map display letters via snapshot & compare with correct_answer
      │ (Scored)
      ▼
[6. Atomic Persistence] ───── Insert agent_topic_results & update assessment_attempts.status='SUBMITTED'
      │ (Committed)
      ▼
[7. Return Graded Result] ─── Return composite score, passed status, and topic summary
```

---

## 4. Anti-Tampering & Defensive Rules

1. **Rejection of Client-Supplied Scores:**
   Any request containing keys from `FORBIDDEN_PROTECTED_FEATURES` (`assessment_score`, `passed`, `stage2_decision`, `confidence`, etc.) immediately fails with HTTP 400:
   ```json
   {
     "success": false,
     "error": "Client-supplied assessment scores or protected model features are strictly forbidden: assessment_score. Scores are calculated server-side only."
   }
   ```
2. **Attempt Ownership Isolation:**
   Attempts belong exclusively to the candidate who initiated them. An agent cannot read, update, autosave, or submit another agent's attempt (`HTTP 403 / 400`).
3. **Idempotent Submission Recovery:**
   If a network dropout causes the client to retry a submission for an already-finalized attempt, the server returns the existing graded result with HTTP 200 without creating duplicate records or recalculating scores.

---

## 5. Verification & Test Evidence

Automated regression coverage implemented in `tests/test_phase3_grading_and_autosave.py`:
- `test_01_question_delivery_never_leaks_correct_answers`: Verified `correct_answer` is 100% stripped.
- `test_02_client_cannot_submit_scores_or_protected_features`: Verified HTTP 400 rejection on tampered scores.
- `test_03_attempt_ownership_validation`: Verified cross-agent attempt protection.

**Test Result:** **PASS (All tests green, 0 errors).**

