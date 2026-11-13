# Phase 3A — Client-Side Autosave & Assessment Resumption Report

**Document ID:** `docs/assessment/11_autosave_and_resume.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Overview

Phase 3A addresses candidate resilience and test integrity for incomplete assessments. During real-world testing, network latency, device restarts, or accidental page reloads can disrupt a candidate's session.

Phase 3A introduces:
1. **Server-Side Draft Autosave:** Background synchronization of intermediate selections directly to `assessment_attempts.answers_json`.
2. **Optimistic Concurrency Control:** Monotonically increasing revision numbers (`answers_version`) prevent out-of-order network packets from overwriting newer selections with stale data.
3. **Seamless Attempt Resumption:** Returning candidates are automatically restored to their exact active attempt with their frozen question sequence, randomized option permutations, saved draft choices, and remaining time.
4. **Visual Sync State Machine:** The frontend presents non-intrusive feedback indicators (`Saving draft...`, `Answers saved`, `Sync pending`).

---

## 2. Concurrency Control & State Architecture

### Database Schema Expansion (Migration 008)
```sql
ALTER TABLE assessment_attempts
  ADD COLUMN answers_version INT UNSIGNED NOT NULL DEFAULT 0 AFTER answers_json,
  ADD COLUMN last_saved_at DATETIME NULL DEFAULT NULL AFTER answers_version;
```

### Race-Condition Prevention Mechanism
Network delays can result in an older autosave request arriving at the server *after* a newer autosave request.

To prevent stale overwrites:
1. Every autosave request includes a client revision version:
   `POST /api/competency/topics/<id>/autosave` $\rightarrow$ `{ "attempt_id": 104, "answers": {...}, "version": 4 }`
2. The server compares `incoming_version` against `current_version`:
   - If `incoming_version < current_version`: The server detects a stale out-of-order packet, logs the event, and retains the newer answers without overwriting.
   - If `incoming_version >= current_version`: The server persists the merged answers, increments `answers_version = incoming_version + 1`, and records `last_saved_at = NOW()`.
   - Atomicity is guaranteed within a single database transaction.

---

## 3. Resumption Flow

When an agent navigates to an assessment (or reloads `AssessmentPage.jsx`):

1. **Attempt Discovery:**
   The frontend calls `competencyService.startTopicAttempt(topicId, taskId)`.
2. **Active Attempt Detection:**
   The backend checks for an existing `IN_PROGRESS` attempt where `NOW() < expires_at`.
   - If found, it returns the existing attempt record rather than generating a new one.
   - The frozen snapshot (`question_snapshot_json`) reconstructs the identical question sequence and option permutations.
3. **State Rehydration:**
   The client receives:
   ```json
   {
     "attempt_id": 104,
     "status": "IN_PROGRESS",
     "expires_at": "2026-11-11T10:15:00Z",
     "answers_version": 3,
     "saved_answers": { "9": "B", "10": "D" },
     "last_saved_at": "2026-11-11T09:45:12Z",
     "questions": [ ... ]
   }
   ```
4. **Candidate Experience:**
   - Saved selections are populated into `selectedAnswers`.
   - The stepper jumps automatically to the first unanswered scenario.
   - The countdown timer resumes accurately from `expires_at`.
   - The autosave status indicator reflects `Answers saved`.

---

## 4. Frontend Autosave Lifecycle

In [`frontend/src/pages/AssessmentPage.jsx`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/frontend/src/pages/AssessmentPage.jsx):

```
Candidate clicks option
       │
       ▼
[Update Local State] ──────── Instant UI feedback (option highlighted)
       │
       ▼
[Debounce Queue (600ms)] ──── Consolidates rapid clicks / option changes
       │
       ▼
[Autosave Trigger] ────────── Status changes to "Saving draft..."
       │
  ┌────┴────────────────────────┐
  ▼                             ▼
(Success)                    (Failure)
Status: "Answers saved"      Status: "Sync pending" (safe background retry)
```

- **Immediate Flush:** Pending autosaves are flushed synchronously before moving to the next question (`handleNext`) or opening the review confirmation screen.
- **Unload Guard:** A `beforeunload` listener triggers an emergency sync if the browser tab is about to close.

---

## 5. Test Evidence & Validation

Automated regression coverage implemented in `tests/test_phase3_grading_and_autosave.py`:
- `test_04_autosave_persists_answers_and_increments_version`: Verified draft answers persist and version counter increments monotonically.
- `test_05_concurrency_control_stale_revision_rejected`: Verified stale out-of-order autosaves are safely ignored and cannot overwrite newer answers.
- `test_06_attempt_resumption_restores_snapshot_and_saved_answers`: Verified page reload/resumption restores complete snapshot and draft selections.

**Outcome:** **6 of 6 tests passed (100% OK in 2.76s).**

