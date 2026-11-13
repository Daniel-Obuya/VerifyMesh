# Phase 4 — Attempt Lifecycle & Integrity Controls Report

**Document ID:** `docs/assessment/04_attempt_lifecycle_and_integrity.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Executive Summary

Phase 4 implements a deterministic, state-machine driven assessment attempt lifecycle in VerifyMesh. The lifecycle eliminates attempt replay, prevents out-of-order submission states, safeguards against question harvesting, and guarantees that assessment outcomes are permanently traceable and tamper-proof.

Prior to Phase 4:
1. Attempt states lacked explicit abandonment, cancellation, and admin exception handling.
2. Incomplete or timed-out attempts were vulnerable to inconsistent status resolution.
3. Multi-attempt quotas were not isolated per topic.

Phase 4 introduces an expanded state machine supported by MySQL Migration 009, strict ownership validation, server-side expiration sweeps, and tamper-resistant audit trails.

---

## 2. Assessment Attempt State Machine

Assessment attempts progress through explicit, mutually exclusive lifecycle states:

```
                  ┌──────────────────────┐
                  │     NOT_STARTED      │
                  └──────────┬───────────┘
                             │ Candidate clicks "Start Assessment"
                             ▼
                  ┌──────────────────────┐
       ┌──────────┤     IN_PROGRESS      ├──────────┐
       │          └──────────┬───────────┘          │
       │ Candidate           │                      │ Attempt window
       │ submits answers     │ Candidate clicks     │ expires
       │                     │ "Abandon Attempt"    │ (expires_at < NOW())
       ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  SUBMITTED   │      │  ABANDONED   │      │   EXPIRED    │
└──────┬───────┘      └──────────────┘      └──────────────┘
       │ Graded server-side                         ▲
       ├─────────────────┐                          │ Admin reopens
       ▼                 ▼                          │ (+30 min)
┌──────────────┐  ┌──────────────┐                  │
│    PASSED    │  │    FAILED    │                  │
└──────────────┘  └──────────────┘                  │
                                                    │
Admin cancels corrupted attempt                     │
────────────────────────────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  CANCELLED   │ (Exempt from candidate quota)
              └──────────────┘
```

### State Definitions:
1. **`IN_PROGRESS`**: Active attempt created. Authoritative `started_at` and `expires_at` stored in MySQL. Question snapshot frozen. Resumable.
2. **`SUBMITTED`**: All scenario questions answered and submitted. Server-side grading executed and locked. Attempt cannot be modified.
3. **`ABANDONED`**: Candidate explicitly forfeited the attempt. Preserves snapshot and saved answers for audit. Counts toward quota.
4. **`EXPIRED`**: Assessment window elapsed (`NOW() > expires_at`). Graded as `score = NULL, passed = 0`. Cannot be submitted.
5. **`CANCELLED`**: Workforce Officer cancelled the attempt due to platform/connection failure. Exempt from attempt quotas.

---

## 3. Database Schema Migration 009

Migration `009_assessment_lifecycle_statuses.sql` applied non-destructive DDL expansions:

```sql
-- 1. Expand attempt status ENUM
ALTER TABLE assessment_attempts
  MODIFY COLUMN status ENUM('IN_PROGRESS','SUBMITTED','EXPIRED','CLOSED','ABANDONED','CANCELLED')
  COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'IN_PROGRESS';

-- 2. Add closure_reason for audit traceability
ALTER TABLE assessment_attempts
  ADD COLUMN closure_reason VARCHAR(255) NULL AFTER last_saved_at;
```

---

## 4. Anti-Replay & Submission Safeguards

1. **Replay Rejection:**
   Attempts in `SUBMITTED`, `EXPIRED`, `ABANDONED`, or `CANCELLED` states cannot be re-submitted or modified via `/submit` or `/autosave` (returns HTTP 400).
2. **Idempotent Submission Recovery:**
   If network failure causes duplicate submission of an already `SUBMITTED` attempt, the backend returns the stored result with HTTP 200 without duplicate database inserts.
3. **Question Snapshot Immutability:**
   Every attempt freezes `question_snapshot_json` at creation. Shuffled option letters (`A`, `B`, `C`, `D`) are reconciled exclusively against this snapshot during server grading.

---

## 5. Verification & Test Evidence

Automated test suite [`tests/test_phase4_lifecycle_and_expiry.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_phase4_lifecycle_and_expiry.py):
- `test_01_explicit_abandonment_transitions_status_and_audits`: **PASS**.
- `test_02_abandoned_attempts_count_toward_attempt_limit`: **PASS**.
- `test_03_admin_grant_extra_attempt_override`: **PASS**.
- `test_04_admin_cancel_attempt_exempts_from_quota`: **PASS**.
- `test_05_stale_attempt_expiry_sweep`: **PASS**.
- `test_06_historical_assessment_audit_trail_preserved`: **PASS**.

**Overall Test Suite (Phases 2, 3, 4):** **19 of 19 tests passed (100% OK in 14.73s).**

