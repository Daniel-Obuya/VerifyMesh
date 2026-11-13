# VERIFYMESH — PHASE 0: FORENSIC AUDIT OF THE EXISTING ASSESSMENT SUBSYSTEM

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-11  
**Auditor:** Senior Software Architect, Backend Security Engineer & Assessment Systems Specialist  
**System State:** Pre-Implementation Baseline Inspection (Zero Code/Data Modifications Applied)

---

## 1. Executive Summary

VerifyMesh utilizes a dual-path workforce verification architecture where deterministic rules govern qualification and eligibility, while machine learning models provide advisory suitability predictions for already-qualified applicants. 

A comprehensive forensic audit of the assessment subsystem was conducted across the frontend React codebase, backend Flask routes and business logic in `backend/db.py`, and the underlying MySQL schema. 

### Key Findings at a Glance:
- **Server-Side Scoring Integrity:** Scoring is computed entirely on the backend against authoritative database answer keys (`user_ans == correct_answer`). Client-supplied scores, pass/fail decisions, and protected features are strictly rejected.
- **Answer Key Security:** Correct answers (`correct_answer`) are omitted from all question retrieval endpoints (`/api/competency/exams/<id>/questions` and `/api/competency/topics/<id>/questions`).
- **Authorization & Isolation:** Attempt details (`/api/competency/attempts/<id>`) enforce strict ownership checks (`attempt["agent_id"] == authenticated_agent_id`), returning HTTP 403 upon tampering.
- **Legacy Architectural Vestiges:** The system operates two parallel assessment pathways:
  1. *Legacy single-exam pathway:* `/api/competency/exams/<exam_id>/...` and `tasks.exam_id`.
  2. *Topic-based multi-competency pathway:* `/api/competency/topics/<topic_id>/...` and `task_assessment_topics`.
- **Reset Security Defect:** The `/api/competency/reset-assessment` endpoint allows authenticated agents to self-issue an `ASSESSMENT_RESET_REQUESTED` audit event without administrator approval.
- **Absence of Autosave & State Persistence:** Active attempts only persist answers upon final submission. Browser refresh or navigation wipes in-memory responses.
- **Absence of Question/Blueprint Randomization:** All candidates receive the identical 5 questions in static `question_order ASC` with static option keys `A, B, C, D`.
- **Administrative Blind Spots:** Administrators only have visibility into completed exam results (`exam_results`). Active `IN_PROGRESS`, `EXPIRED`, or `CLOSED` attempts in `assessment_attempts` cannot be viewed or audited from the Admin Dashboard.

---

## 2. Existing Architecture & Subsystem Mapping

```
                                 [ AGENT USER ]
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
     [ AgentDashboard.jsx ]                         [ AssessmentPage.jsx ]
     • Task eligibility display                     • Instruction presentation
     • Action button dispatch                       • Step-by-step question view
     • Required topic progress                      • In-memory answer state
                │                                             │
                │ GET /api/competency/tasks                   │ POST /api/competency/topics/:id/start-attempt
                │ GET /api/competency/agent-status            │ GET  /api/competency/topics/:id/questions
                │                                             │ POST /api/competency/topics/:id/submit
                ▼                                             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                       FLASK API (competency_routes.py)                     │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ • JWT Authentication (Bearer Token)                                         │
 │ • Attempt Verification & Status Locking (409 on re-submit, 400 on expired) │
 │ • Server-side Scoring & Threshold Comparison                                │
 │ • Deterministic Qualification Evaluation                                    │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         DATABASE LAYER (MySQL)                              │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ • Configuration: exams, assessment_topics, task_assessment_topics           │
 │ • Question Bank: exam_questions (points, options_json, correct_answer)      │
 │ • Attempts & Results: assessment_attempts, agent_topic_results, exam_results │
 │ • Audit & Governance: audit_logs (ASSESSMENT_COMPLETED, RESET events)        │
 └─────────────────────────────────────────────────────────────────────────────┘
```

### Component Inventory

| Component Type | File / Resource | Operational Role & Current Behavior |
| :--- | :--- | :--- |
| **Frontend Page** | `frontend/src/pages/AssessmentPage.jsx` | Renders assessment instructions, loads topic questions, stores candidate selections in local state (`useState`), and submits finalized answers. |
| **Frontend Page** | `frontend/src/pages/AgentDashboard.jsx` | Surfaces task cards with server-evaluated eligibility badges (`Assessment Needed`, `Ready to Apply`), qualification progress (`X/Y Passed`), and routes agents to `AssessmentPage`. |
| **Frontend Page** | `frontend/src/pages/AdminDashboard.jsx` | Administrative interface. Displays completed candidate assessment attempts and ML advisory predictions; lacks question bank management. |
| **Frontend Service** | `frontend/src/services/competencyService.js` | Axios HTTP client handling `/api/competency` endpoints. |
| **Backend Router** | `backend/competency_routes.py` | Routes for exams, topics, attempts, submissions, eligibility, and applications. |
| **Backend Router** | `backend/admin_routes.py` | Routes for administrative KPI retrieval and viewing candidate assessments. |
| **Backend Core** | `backend/db.py` | Authoritative database functions for query execution, attempt creation, grading, and eligibility state machines. |

---

## 3. Database Relationships & Schema Analysis

The MySQL schema contains 8 core tables governing the assessment subsystem:

```
[ tasks ] 
   │
   ├─► 1:N ── [ task_assessment_topics ] ── N:1 ──► [ assessment_topics ]
   │                 (task_id, topic_id)                     │
   │                                                         ├─► 1:N ── [ agent_topic_results ]
   └─► 1:1 (legacy) ── [ exams ]                             │                ▲
                           │                                 │                │ (attempt_id)
                           ├─► 1:N ── [ exam_questions ] ────┘                │
                           │               (topic_id, options_json,           │
                           │                correct_answer)                   │
                           │                                                  │
                           └─► 1:N ── [ assessment_attempts ] ────────────────┘
                                           (attempt_uuid, status,
                                            score, passed, expires_at)
```

### Detailed Schema Evaluation

1. **`exams`**:
   - Primary key: `exam_id` (int unsigned).
   - Fields: `category_id`, `exam_name`, `passing_score` (decimal 5,2), `status` (ACTIVE, INACTIVE, DRAFT).
   - Role: Legacy umbrella entity representing a complete exam package.

2. **`assessment_topics`**:
   - Primary key: `topic_id` (int unsigned).
   - Fields: `topic_name`, `passing_score` (decimal 5,2), `estimated_minutes`, `status` (ACTIVE, INACTIVE).
   - Role: Authoritative competency dimension (e.g., Product Knowledge, Customer Communication).

3. **`task_assessment_topics`**:
   - Composite Primary Key: `(task_id, topic_id)`.
   - Fields: `is_mandatory` (tinyint 1).
   - Role: Authoritative mapping defining which competencies are required for a specific task.

4. **`exam_questions`**:
   - Primary Key: `question_id` (int unsigned).
   - Foreign Keys: `exam_id -> exams.exam_id`, `topic_id -> assessment_topics.topic_id`.
   - Fields: `question_text`, `question_type` (MULTIPLE_CHOICE, TRUE_FALSE), `points`, `correct_answer`, `options_json`, `question_order`.
   - Role: Master question bank. Stores choices in `options_json` and authoritative letter (`A`, `B`, `C`, `D`) in `correct_answer`.

5. **`assessment_attempts`**:
   - Primary Key: `attempt_id` (int unsigned). Unique key: `attempt_uuid`.
   - Foreign Keys: `agent_id`, `exam_id`, `topic_id`, `task_id`, `exam_result_id`, `prediction_id`.
   - Fields: `attempt_number`, `status` (IN_PROGRESS, SUBMITTED, EXPIRED, CLOSED), `started_at`, `expires_at`, `submitted_at`, `score`, `passed`, `answers_json`, `subscores_json`.
   - Role: Authoritative lifecycle tracker for individual attempts.

6. **`agent_topic_results`**:
   - Primary Key: `result_id` (int unsigned).
   - Foreign Keys: `agent_id`, `topic_id`, `attempt_id`.
   - Fields: `score`, `passed`, `answers_json`, `completed_at`.
   - Role: Granular competency achievement ledger used by the deterministic Eligibility Engine.

7. **`exam_results`**:
   - Primary Key: `exam_result_id` (int unsigned).
   - Fields: `attempt_id`, `exam_id`, `agent_id`, `assessment_score`, `passed`, `attempt_number`, `completed_at`.
   - Role: Legacy exam-level result ledger.

8. **`audit_logs`**:
   - Primary Key: `log_id` (bigint unsigned).
   - Fields: `user_id`, `action`, `entity_type`, `entity_id`, `description`, `created_at`.
   - Role: Compliance audit log capturing `ASSESSMENT_COMPLETED` and `ASSESSMENT_RESET_REQUESTED` events.

---

## 4. Investigation of Actual Business Behavior

### 1. Can an agent start an assessment without being eligible for the associated task?
**Yes.**  
Currently, `start_topic_attempt(topic_id)` and `create_assessment_attempt(...)` validate:
- Agent account is active (not suspended).
- If `task_id` is passed, `topic_id` must belong to the task's required topics.
However, it does **not** check whether the agent satisfies other non-assessment prerequisites (such as verified work experience or mandatory certifications). For example, Daniel Obuya (0 months verified experience) can start an assessment for Task 2 (which requires 24 months experience). While this allows agents to demonstrate skill ahead of credential verification, it can cause confusion if the agent expects passing the exam to immediately grant task eligibility.

### 2. Can an agent submit an assessment multiple times?
**No for the same attempt; Yes via new attempts.**  
Once an attempt reaches `status = 'SUBMITTED'`, `/submit` returns `HTTP 409 Conflict` ("This assessment attempt has already been submitted and finalized").  
However, an agent can initiate a new attempt after the 5-minute cooldown (`ASSESSMENT_COOLDOWN_SECONDS = 300`) expires. There is currently **no limit on the maximum number of attempts permitted**.

### 3. Can an agent modify answers after submission?
**No.**  
Final grading and state persistence execute inside the `/submit` endpoint. Once committed, the attempt status becomes `SUBMITTED`, locking the row from further mutations.

### 4. Can an agent manipulate their score through browser requests?
**No.**  
The backend checks `FORBIDDEN_PROTECTED_FEATURES` and rejects any payload containing client-computed scores, percentages, or decisions with `HTTP 400 Bad Request`. Scores are computed exclusively on the server by matching submitted option keys against the database `correct_answer`.

### 5. Are correct answers included in API responses?
**No.**  
- `get_exam_questions` and `get_topic_questions` explicitly omit `correct_answer` from SQL `SELECT` projections.
- Post-grading feedback returned by `/submit` includes `is_correct` (boolean), `points_earned`, and `max_points`, but never the correct option identifier or text.

### 6. Can an agent retrieve another agent's results?
**No.**  
`get_attempt_details` in `backend/competency_routes.py` (lines 1804–1806) executes an explicit authorization check:
```python
if attempt["agent_id"] != agent_id:
    return jsonify({"success": False, "error": "Unauthorized: attempt belongs to another agent."}), 403
```
Cross-agent record retrieval is strictly prevented.

### 7. Can an agent apply for a task after failing a mandatory assessment?
**No.**  
`apply_for_task` in `backend/db.py` (lines 1426–1430) executes independent server-side prerequisite re-verification:
```python
prereqs = target.get("prerequisites", {})
if target.get("exam_required") and not prereqs.get("assessment_met"):
    raise ValueError("Cannot apply: Mandatory task assessment has not been passed with the required score.")
```
Any attempt to submit an application via API with an unpassed or failed assessment is rejected with `HTTP 400 Bad Request`.

### 8. Can an assessment result be reset?
**Yes.**  
An assessment can be reset via `POST /api/competency/reset-assessment`.

### 9. Does resetting preserve historical information?
**Yes.**  
`reset_agent_assessment` does not execute destructive `DELETE` statements. It writes an `ASSESSMENT_RESET_REQUESTED` event into `audit_logs` and marks active `IN_PROGRESS` attempts as `CLOSED`. Historical rows in `exam_results`, `agent_topic_results`, `ml_predictions`, and `assessment_attempts` remain intact.  
Subsequent queries in `get_agent_assessment` and `get_agent_tasks_with_eligibility` ignore records timestamped prior to the latest reset event.

### 10. Are assessment results correctly associated with the relevant task and competency?
**Partially.**  
- `agent_topic_results` accurately links `agent_id`, `topic_id`, and `attempt_id`.
- `assessment_attempts` accurately records `task_id` when the assessment was launched from a specific task context.
- *Defect:* If launched from the general profile menu (`/agent/assessment/general`), `task_id` is `NULL`. While the resulting topic scores populate `agent_topic_results` and qualify the agent across tasks sharing that topic, legacy fallbacks in `submit_exam_answers` rely on hardcoded mappings (`topic_mapping = {1: [2], 2: [1], 3: [3], 4: [4]}`).

### 11. Can an administrator change an assessment after agents have completed it?
**Potentially, without version safeguards.**  
Neither `exams` nor `exam_questions` have versioning columns or immutable snapshots. If a question's `correct_answer`, `options_json`, or `points` are modified in the database, historical attempts reference the modified question ID. Although previous scores stored in `assessment_attempts.score` do not retroactively recalculate, reproducing the grading logic against historical answer selections would yield inconsistencies.

### 12. Are assessment scores used correctly by the Eligibility Engine?
**Yes.**  
The deterministic Eligibility Engine in `backend/db.py` (`get_agent_tasks_with_eligibility`) evaluates every mandatory topic configured in `task_assessment_topics`. For each topic, it compares the applicant's latest score from `agent_topic_results` against `assessment_topics.passing_score`. If any mandatory topic is unassessed or below passing threshold, `can_apply` is set to `False` and `assessment_met` is set to `False`.

---

## 5. Special Investigation: Historical Task Card Inconsistency

### Investigated Phenomenon:
In an earlier session, a task card for Task 5 displayed:
- Top-Right Badge: `Application Submitted`
- Required Qualification Assessment: `Failed (74%)`
- Legacy Field: `Required Competency: Eligible`

### Root Cause Analysis:
1. **Source of the Application Record:**  
   During automated test execution (`test_C_sales_task_retrieves_sales_results_only` in `tests/test_phase2_db_assessment_mapping.py`), the test harness inserted a row directly into `task_applications` (`agent_id = 1`, `task_id = 5`, `status = 'Application Submitted'`) without cleaning it up in a `finally` block or `tearDown`.
2. **Server State Precedence Evaluation:**  
   In `backend/db.py` (`get_agent_tasks_with_eligibility` lines 1307–1308):
   ```python
   if app_status == "Assigned":
       state = "Assigned"
   elif app_status in ("Application Submitted", "Under Review", "Shortlisted", "Rejected", "Withdrawn"):
       state = app_status
   ```
   The engine prioritizes existing application records above prerequisite evaluation. Because a row was present in `task_applications`, the task's primary state was set to `Application Submitted`.
3. **Coexistence with Qualification Status:**  
   Simultaneously, `task_assessment_topics` required Topic 2 (*Sales Techniques*). Alex Morgan's latest score was 74%, which was below the configured passing threshold of 75%, correctly producing the qualification status `Failed (74%)`.
4. **Source of `Required Competency: Eligible`:**  
   In `AgentDashboard.jsx` (legacy line 1283):
   ```jsx
   {task.requiredCompetency || task.required_competency || 'Eligible'}
   ```
   The frontend component attempted to read a non-existent property `requiredCompetency` from the task object, falling back to the hardcoded string `'Eligible'`. This conflated a deterministic eligibility concept with a competency requirement.

### Conclusion & Fix Status:
- This was **not** a failure of the application submission gatekeeper (which properly rejects applications when assessments are failed).
- It occurred because a raw database record bypassed the API layer during testing, combined with frontend fallback labeling.
- The test harness cleanup was resolved, the orphaned database row was deleted, and the misleading `Required Competency: Eligible` label was replaced with dynamic `Min. Experience` and `Certification` fields.

---

## 6. Identified Vulnerabilities & Confirmed Defects

### Defect 1: Unauthorized Agent-Initiated Reset (Security Defect)
- **File:** `backend/competency_routes.py` line 279
- **Vulnerability:** `/api/competency/reset-assessment` allows any authenticated candidate to reset their assessment state at will.
- **Impact:** An agent who fails an assessment can reset their profile to bypass retake cooldowns or clear failed assessment indicators without workforce officer oversight.
- **Recommended Fix:** Restrict reset authority strictly to Administrators (`ROLE_ADMIN` / `Workforce Officer`) via `backend/admin_routes.py`, requiring an administrative reason and logging the action.

### Defect 2: Absence of Answer Autosave & In-Progress Recovery
- **File:** `frontend/src/pages/AssessmentPage.jsx`
- **Defect:** Candidate answers exist exclusively in client React state (`useState({})`).
- **Impact:** If an agent's browser tab crashes, the device reboots, or network disconnects during a 30-minute exam, all selections are permanently lost. Upon returning, the candidate must restart all questions while the server expiry timer continues to tick down.
- **Recommended Fix:** Implement an autosave API (`POST /api/competency/attempts/:id/save-answers`) that updates `assessment_attempts.answers_json` in real time with monotonic versioning to prevent race conditions.

### Defect 3: Static Question Order & Predictable Question Bank
- **File:** `backend/competency_routes.py` lines 609, 1479; `backend/db.py` line 578
- **Defect:** SQL queries explicitly retrieve questions with `ORDER BY question_order ASC`.
- **Impact:** Every candidate receives identical questions in identical sequence. Option ordering (`A, B, C, D`) is static. Candidates can collude or memorize answer keys.
- **Recommended Fix:** Introduce a server-side randomized attempt blueprint that selects questions and shuffles options upon attempt creation, persisting an immutable snapshot of question and option order per attempt.

### Defect 4: Single-Attempt Submission Race & Lost Response Blind Spot
- **File:** `backend/competency_routes.py` line 1443
- **Defect:** Retrying `/submit` after a successful server commit returns `HTTP 409 Conflict`.
- **Impact:** If the network drops after the server commits the grade but before the client receives the response, the agent's browser shows an unhandled submission failure. When the agent clicks "Submit" again, they receive a 409 error without access to their results screen.
- **Recommended Fix:** Implement idempotent submission handling: if an attempt is already `SUBMITTED`, return the previously computed result object with `HTTP 200 OK` rather than throwing a blocking 409 conflict.

### Defect 5: Legacy Single-Exam Column Inconsistency
- **File:** `tasks.exam_id` vs `task_assessment_topics`
- **Defect:** Tasks requiring multiple topics (such as Task 2 requiring Topics 1, 3, and 4) have a single foreign key `tasks.exam_id = 3` (Customer Support Diagnostic Assessment).
- **Impact:** Any component or query relying on `task.exam_id` ignores 2 of the 3 required topics, causing divergence between legacy exam endpoints and modern topic endpoints.
- **Recommended Fix:** Deprecate `tasks.exam_id` in favor of `task_assessment_topics` as the single authoritative source of truth.

### Defect 6: Lack of Attempt Limits
- **File:** `backend/db.py` line 435
- **Defect:** The system enforces a 5-minute cooldown between attempts but places no upper limit on the total number of attempts an agent can make.
- **Impact:** Candidates can repeatedly guess questions every 5 minutes indefinitely.
- **Recommended Fix:** Introduce configurable `max_attempts` (default: 3) per topic/task. Once exhausted, further attempts require administrative review.

---

## 7. Files Identified for Modification

1. `backend/competency_routes.py`:
   - Deprecate agent-accessible `/reset-assessment`.
   - Add autosave route (`/attempts/<id>/save`).
   - Implement idempotent submission recovery.
2. `backend/admin_routes.py`:
   - Add administrator-authorized reset endpoint (`/agents/<id>/reset-assessment`).
   - Add comprehensive attempt inspection endpoint covering `IN_PROGRESS` and `EXPIRED` attempts.
3. `backend/db.py`:
   - Add attempt snapshot persistence (randomized question order and option mapping).
   - Implement autosave answer persistence.
   - Enforce attempt limits.
4. `frontend/src/pages/AssessmentPage.jsx`:
   - Integrate real-time autosave with status indicator ("Saving...", "Saved", "Save Failed").
   - Restore in-progress answers on component mount.
   - Implement client-side countdown timer synchronized with server `expires_at`.
5. `frontend/src/services/competencyService.js`:
   - Add API client methods for autosave and active attempt restoration.

---

## 8. Verification and Hold

This baseline forensic audit concludes that the core scoring, grading, and authorization layers are secure against client tampering, but lack resilience against session disruption, attempt abuse, and question predictability.

**Status:** Forensic Audit Complete. Zero code or schema modifications applied.  
**Action Required:** STOP and wait for approval before proceeding to Phase 1.

