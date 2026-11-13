# VERIFYMESH — PHASE 0A: RANDOMISATION, ABANDONMENT, AUTOSAVE AND CONCURRENCY AUDIT

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-11  
**Scope:** Forensic Audit of Question Randomisation, Answer Persistence, Attempt Lifecycles, and Multi-Session Concurrency  
**System State:** Pre-Implementation Baseline Inspection (Zero Code/Data Modifications Applied)

---

## 1. Executive Summary

This audit assesses the resilience of VerifyMesh's assessment subsystem against candidate collusion, question predictability, network interruptions, session abandonment, and concurrent device usage.

### Primary Audit Conclusions:
1. **Total Absence of Question & Option Randomisation:** The current question retrieval queries explicitly enforce `ORDER BY question_order ASC`. Every candidate receives identical questions with identical option mappings (`A`, `B`, `C`, `D`).
2. **Volatile In-Memory Client State:** Selected answers are stored only in React memory (`useState({})`). No autosave mechanism exists. Any browser reload, unexpected tab closure, or device failure causes immediate and total loss of candidate progress.
3. **Passive Expiration Without Active Enforcement:** Attempts carry a 30-minute server expiration timestamp (`expires_at`), but status updates to `EXPIRED` only occur lazily when an agent subsequently attempts to interact with that attempt.
4. **Idempotency Breakdown on Network Loss:** If a submission commits on the backend but the HTTP response is dropped, a client retry triggers an unhandled `HTTP 409 Conflict`, locking the candidate out of their assessment outcome.
5. **Administrative Invisibility:** The Admin Dashboard exclusively queries finalized records from `exam_results`. In-progress, expired, and abandoned attempts are completely hidden from Workforce Officers.

---

## 2. Answers to the 16 Forensic Audit Questions

### 1. Does the system currently randomise questions?
**No.**  
In `backend/competency_routes.py` (lines 609 and 1479) and `backend/db.py` (line 578), questions are queried with explicit ordering:
```sql
SELECT question_id, topic_id, exam_id, question_text, question_type, points, options_json, question_order
FROM exam_questions
WHERE topic_id = %s
ORDER BY question_order ASC
```
Every candidate receives questions in the static sequence defined by `question_order`.

### 2. Does it randomise answer options?
**No.**  
In `backend/db.py` (`get_topic_questions` lines 581–598), options are deserialized from `options_json` in their exact stored array order and assigned option letters sequentially:
```python
OPTION_LETTERS = ["A", "B", "C", "D"]
for idx, opt in enumerate(raw_opts):
    opt_letter = OPTION_LETTERS[idx] if idx < len(OPTION_LETTERS) else str(idx + 1)
```
Option A is always the first item in the JSON array, Option B is always the second, etc.

### 3. Is randomisation performed on the frontend or backend?
**Neither.**  
Neither the backend SQL queries/services nor the frontend React components perform any shuffling or randomization.

### 4. Does the question order change after a page refresh?
**No.**  
Because question ordering is statically queried by `question_order ASC`, reloading the page produces the exact same question order.

### 5. Does the system generate a new question set each time an agent opens an assessment?
**No.**  
There is no pool selection or blueprint sampling. Currently, each topic has exactly 5 configured questions, and all 5 are loaded unconditionally.

### 6. Are question selections stored in the database?
**No.**  
`assessment_attempts` contains columns for `score`, `passed`, `answers_json`, and `subscores_json`, but **no column exists to record which question IDs were assigned, what order they appeared in, or how options were permuted**.

### 7. Can an agent close the browser and resume an assessment?
**No, practically.**  
While the backend attempt record in `assessment_attempts` remains in `status = 'IN_PROGRESS'` until `expires_at` (30 minutes), the frontend state is entirely lost upon browser closure. When the candidate returns to `/agent/assessment/:taskId`, the page reloads the introduction screen. If they click "Start Assessment", the backend returns the existing attempt ID, but all previously answered questions are blank, forcing the agent to answer everything again while the 30-minute timer continues running.

### 8. Are partially answered assessments persisted?
**No.**  
The system only accepts answers when the candidate reaches the final review screen and triggers `POST /api/competency/topics/:id/submit`. There is no incremental save endpoint.

### 9. Does an assessment remain in progress indefinitely?
**No.**  
When an attempt is created in `backend/db.py` (`create_assessment_attempt` lines 451–459), an expiration timestamp is computed:
```python
duration_min = getattr(Config, 'ASSESSMENT_ATTEMPT_DURATION_MINUTES', 30)
expires_at = now + timedelta(minutes=duration_min)
```
The attempt is bounded to a 30-minute window.

### 10. Is there a timeout mechanism?
**Yes, on the backend (lazy); No, on the frontend (active).**  
- **Backend:** During submission or attempt retrieval, if `now > expires_at`, the server updates `status = 'EXPIRED'` and rejects the action with `HTTP 400 Bad Request`.
- **Frontend:** `AssessmentPage.jsx` does not run an active countdown timer or automatic force-submit handler when the deadline passes.

### 11. Are abandoned attempts counted against attempt limits?
**No.**  
Because the system currently enforces **no maximum attempt limits** (only a 5-minute cooldown between submitted attempts), an abandoned or expired attempt does not restrict the candidate from creating new attempts indefinitely.

### 12. Can an agent have multiple active attempts for the same assessment?
**Partially protected by application logic; Vulnerable to database race conditions.**  
- In single-threaded execution, `create_assessment_attempt` searches for an existing `IN_PROGRESS` attempt where `expires_at > now` and reuses it.
- However, `assessment_attempts` has **no database-level unique constraint** on `(agent_id, exam_id, status)` or `(agent_id, topic_id, status)`. Two concurrent API requests (e.g., rapid double-clicks or two tabs) can bypass the read check and insert duplicate `IN_PROGRESS` rows.

### 13. Can the same attempt be opened in multiple tabs or devices?
**Yes.**  
If an agent opens the assessment in two browser tabs or two separate devices, both clients can query the same active attempt. Whichever tab submits first will succeed, while the second tab's submission will fail with `HTTP 409 Conflict`.

### 14. Can a late autosave request overwrite a more recent answer?
**Currently Not Applicable (No Autosave Exists).**  
However, if an autosave endpoint is implemented without concurrency versioning (such as monotonic question timestamps or answer revision counters), out-of-order network packets could cause older answer selections to overwrite newer ones.

### 15. What happens when submission succeeds on the server but the browser never receives the response?
**Candidate Experience Breakdown (409 Deadlock):**  
1. The server successfully grades the exam, updates `assessment_attempts` to `SUBMITTED`, writes to `agent_topic_results`, and commits.
2. A client-side network disruption prevents the HTTP 200 response from reaching the browser.
3. The browser displays an error: *"Error submitting assessment. Progress was preserved."*
4. The candidate clicks "Submit" again.
5. The server checks the attempt status, sees `status == 'SUBMITTED'`, and returns `HTTP 409 Conflict`: *"This assessment attempt has already been submitted and finalized."*
6. The candidate is trapped: they cannot see their score, cannot view their results screen, and believe the system has crashed.

### 16. Can administrators identify abandoned attempts?
**No.**  
In `backend/db.py`, `get_admin_assessments()` performs an inner join on `exam_results`:
```sql
SELECT ... FROM exam_results er
JOIN agents a ON er.agent_id = a.agent_id
...
```
Because rows are only inserted into `exam_results` upon successful submission, any attempt that was abandoned or expired in `assessment_attempts` is completely invisible to administrators.

---

## 3. Subsystem Component & Dependency Inventory

| Domain | File / Function | Responsibility | Identified Deficiency |
| :--- | :--- | :--- | :--- |
| **Question Retrieval** | `backend/db.py: get_topic_questions` | Formats questions for display. | Fixed `ORDER BY question_order ASC`. Zero randomization. |
| **Attempt Creation** | `backend/db.py: create_assessment_attempt` | Generates attempt row in MySQL. | Does not store question selection or option mapping snapshot. Lacks unique concurrency lock. |
| **Client Interaction** | `frontend/src/pages/AssessmentPage.jsx` | Renders questions and manages choices. | Answers stored only in component memory (`useState`). Lacks autosave and recovery. |
| **API Endpoints** | `backend/competency_routes.py: start_topic_attempt` | Dispatches attempt creation. | Does not seed or return randomized question snapshots. |
| **API Endpoints** | `backend/competency_routes.py: submit_topic_answers` | Evaluates and persists exam grades. | Returns 409 on re-submit instead of idempotent result recovery. |
| **Admin Reporting** | `backend/db.py: get_admin_assessments` | Surfaces candidate assessment records. | Queries `exam_results` only; ignores abandoned/expired attempts in `assessment_attempts`. |

---

## 4. Confirmed Defects & Architecture Risks

```
                                [ THREAT MATRIX ]
 ┌──────────────────────────────────────┬──────────────────────────────────────┐
 │ Risk Factor                          │ Impact & Exposure Level              │
 ├──────────────────────────────────────┼──────────────────────────────────────┤
 │ 1. Deterministic Question Sequence   │ HIGH: Collusion and answer harvesting│
 │ 2. In-Memory Answer Volatility       │ HIGH: Loss of candidate work         │
 │ 3. Submission Idempotency Breakdown  │ HIGH: False failure & candidate lock │
 │ 4. Unlimited Retake Cycling          │ MEDIUM: Brute-force answer guessing  │
 │ 5. Invisible Abandoned Attempts      │ MEDIUM: Audit blindness              │
 └──────────────────────────────────────┴──────────────────────────────────────┘
```

1. **Deterministic Question Sequence (Collusion Threat):**  
   Because questions and options are 100% static, candidates can document the sequence of correct letter choices (`A, B, A, B, A`) and distribute answer keys to unauthorized parties.
2. **In-Memory Answer Volatility (Reliability Threat):**  
   Candidates operating on unstable mobile connections or experiencing browser crashes lose all answers, creating frustration and administrative support overhead.
3. **Submission Idempotency Breakdown (Availability Threat):**  
   Any dropped network packet during the final submit call strands the candidate in a 409 deadlock state.
4. **Unlimited Retake Cycling (Integrity Threat):**  
   Without an upper limit on attempts, candidates can cycle attempts every 5 minutes until they achieve a passing mark.
5. **Invisible Abandoned Attempts (Governance Threat):**  
   Administrators cannot detect whether an agent struggled with questions and abandoned an attempt or encountered technical difficulty.

---

## 5. Architectural Recommendations for Phase 1A–3A

### A. Randomized Attempt Snapshot Engine (Backend)
- Store a question bank larger than the required test count (e.g., 10+ questions per topic).
- At attempt creation, sample a balanced subset using cryptographically secure random selection (`secrets` module).
- Permute the display order of answer options independently per attempt.
- Persist an immutable JSON snapshot in `assessment_attempts`:
  ```json
  {
    "question_ids": [15, 13, 17, 14, 16],
    "option_orders": {
      "15": ["C", "A", "D", "B"],
      "13": ["B", "D", "A", "C"]
    }
  }
  ```
- Resuming an attempt loads this exact persisted snapshot, ensuring question and option stability across page refreshes.

### B. Incremental Autosave Protocol
- Introduce `POST /api/competency/attempts/:id/save-answers`.
- Maintain a monotonic `client_version` integer per question to reject stale, out-of-order autosave requests.
- Store interim selections in `assessment_attempts.answers_json`.
- When an agent reopens an active attempt, hydrate `selectedAnswers` directly from the database record.

### C. Idempotent Submission Recovery
- In `submit_topic_answers`, if the attempt status is already `SUBMITTED`, retrieve the existing attempt details, score, and decision payload, and return `HTTP 200 OK` with the finalized result.
- This guarantees that repeated submissions due to network retry safely recover the result screen without throwing 409 errors.

### D. Enforce Configurable Attempt Quotas
- Introduce `max_attempts` (default: 3) on `assessment_topics`.
- If an agent reaches the maximum attempt count without passing, lock the topic and require Workforce Officer intervention.

### E. Comprehensive Admin Audit Visibility
- Update `backend/admin_routes.py` and `backend/db.py` to query from `assessment_attempts` left-joined with `exam_results`.
- Surface attempt status badges (`In Progress`, `Submitted`, `Expired`, `Closed`) on the Admin Dashboard so Workforce Officers can identify abandoned sessions.

---

## 6. Verification and Hold

This audit confirms that while the core grading rules are mathematically sound, the assessment subsystem requires hardening against question harvesting, network volatility, and state loss.

**Status:** Forensic Randomisation and Abandonment Audit Complete. Zero code or schema modifications applied.  
**Action Required:** STOP and present this audit for approval before proceeding to Phase 1 / Phase 1A.

