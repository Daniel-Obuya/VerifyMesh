# VerifyMesh: Comprehensive Quality Assurance & End-to-End Test Plan

**Project:** VerifyMesh: Enhancing Workforce Task Allocation Through Competency Assessment and Eligibility Prediction  
**Author:** QA Engineering & Academic Review Team  
**Scope:** Complete verification across Authentication, Agent Profile, Competency Assessments, Task Management, ML Binary Gatekeeper, RBAC, Database Integrity, and Panel Rehearsal  

---

## 1. Test Objectives & Strategy

The primary objective is to validate that the VerifyMesh system operates robustly and reliably under live examination conditions, strictly enforcing security controls, business rules, and predictive accuracy without relying on mocks, shortcuts, or hardcoded demonstration values.

### Core Testing Pillars:
1. **Zero-Mock Production Testing:** All tests execute against the genuine Flask 3.0 backend, real MySQL 8.0 database, and the active scikit-learn binary eligibility model (`binary_eligibility_model.pkl`).
2. **Authoritative Server-Side Governance:** Validate that all critical decisions (assessment scores, pass/fail thresholds, eligibility states, role assignments) are determined strictly by server logic and stored in MySQL.
3. **Safe Offline Execution:** External network dependencies (SMTP outbound email dispatch, Google remote token verification) are isolated using test fixtures or mocked transports so automated tests can run reliably offline.
4. **Data Isolation & Non-Destructive Operations:** Never delete or corrupt existing persistent records; use isolated test fixtures and transaction cleanups.

---

## 2. Test Environment & Prerequisites

| Environment Variable | Value / Configuration | Purpose |
| :--- | :--- | :--- |
| `FLASK_ENV` | `development` / `testing` | Application environment mode |
| `SECRET_KEY` | High-entropy 32-byte secret | HMAC-SHA256 signature generation and validation |
| `DB_HOST` | `localhost` | MySQL 8.0 Community server host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `verifymesh_db` | Main relational database |
| `ASSESSMENT_COOLDOWN_SECONDS` | `0` (Testing) / `300` (Production) | Retake cooldown window |
| `Python Runtime` | Python 3.13.3 (`.venv`) | Execution environment |
| `Node Runtime` | Node.js v20+ / Vite 8.3 | Frontend client bundler |

---

## 3. Test Fixtures & Accounts

| Account Role | Identifier / Email | Initial State | Purpose |
| :--- | :--- | :--- | :--- |
| **Verified Agent 1** | `alex.morgan@university.edu` | Verified, 40 mo exp, 1 cert | Validates eligible candidate journeys, passed evaluations, and task applications |
| **Entry Agent 2** | `daniel.nyabuto@strathmore.edu` | Verified, 0 mo exp, 0 certs | Validates prerequisite enforcement, ineligible ML predictions, and blocking reasons |
| **System Admin** | `admin@verifymesh.io` | Administrator role | Validates task builder, verification queues, overview KPIs, and review approvals |
| **Dynamic Test Candidate** | `panel_demo_<timestamp>@verifymesh.io` | Clean registration | Validates full registration, OTP verification, onboarding, and assessment attempt |

---

## 4. Test Categories & Scenarios

### Category 1: User Registration, OTP & Authentication (TC001 - TC004)
- **1.1 Valid Registration:** Registers a clean candidate; verifies that password hash is created (never plaintext) and 6-digit OTP is recorded in `email_verifications`.
- **1.2 Missing Required Fields:** Validates rejection of empty full name, phone number, or passwords.
- **1.3 Email Format Validation:** Rejects invalid syntaxes (missing `@`, missing domain, invalid characters).
- **1.4 Password Policy:** Rejects passwords under 8 characters or mismatched confirmation passwords.
- **1.5 OTP Lifecycle:** Validates matching 6-digit OTP, rejects invalid code (`000000`), rejects expired OTP (>10 min), and blocks reused OTP codes.
- **1.6 Rate Limiting:** Verifies that >5 failed OTP attempts or >5 failed login attempts trigger HTTP 429 with `Retry-After` header.
- **1.7 Valid Login & Role Routing:** Validates correct token issuance and dashboard URL assignment for Agent vs Administrator.
- **1.8 Token Tampering:** Rejects modified token payloads, altered signatures, expired tokens, or malformed strings with HTTP 401.

### Category 2: Agent Profile, Experience & Overlapping Interval Merging (TC005 - TC007)
- **2.1 Profile Retrieval & Update:** Validates retrieval of profile fields and safe update of personal bio and location.
- **2.2 Mass Assignment Prevention:** Confirms that sending `role`, `agent_id`, or `experience_months` in profile update payload is ignored.
- **2.3 Experience Date Validation:** Rejects invalid date formats (`not-a-date`) and reversed date ranges (`start_date > end_date`).
- **2.4 Interval Merging Algorithm:** Verifies that overlapping verified jobs within the same category are merged without double-counting months.
- **2.5 Unverified Experience Isolation:** Confirms that pending or rejected work experiences are excluded from verified tenure totals.
- **2.6 Cross-Agent Deletion:** Ensures an agent cannot delete or modify another agent's experience or certification records.

### Category 3: Competency Assessment Integrity & Server Scoring (TC008 - TC011)
- **3.1 Question Sanitization:** Confirms `/api/competency/exams/<id>/questions` omits `correct_answer` and point weights.
- **3.2 Authoritative Attempt Initiation:** Confirms starting an exam creates an `assessment_attempts` record with `IN_PROGRESS` status.
- **3.3 Server-Side Grading:** Calculates score strictly on backend by comparing answer keys to MySQL `exam_questions`.
- **3.4 Pass/Fail Determination:** Evaluates score against the exam's configured `passing_score` (e.g. 70.0% or 75.0%).
- **3.5 Client Score Injection Rejection:** Requests containing `score`, `assessment_score`, or `passed` are rejected with HTTP 400.
- **3.6 Result Persistence:** Confirms attempt status transitions to `SUBMITTED`, and results are saved to `exam_results` and `ml_predictions`.
- **3.7 Attempt Ownership Protection:** Rejects attempts by Agent A to view or submit an attempt started by Agent B (HTTP 403).

### Category 4: Task Management & 4-Tier Dual-Layer Eligibility (TC012 - TC016)
- **4.1 Task Creation Validation:** Rejects generic titles ("test", "task 1"), titles <5 chars, negative compensation, and missing deadlines.
- **4.2 Transactional Integrity:** Validates that creating a task and its `task_requirements` commits atomically or rolls back on error.
- **4.3 Precedence Rule (Hard Certifications):** If a task requires Certification 1 and candidate lacks it, state is `Certification Required`.
- **4.4 Precedence Rule (Hard Experience):** If candidate lacks minimum experience months, state is `Requires X Months Exp`.
- **4.5 Precedence Rule (Assessment):** If candidate hasn't completed required assessment, state is `Assessment Needed`.
- **4.6 Precedence Rule (Competency Gatekeeper):** If ML model predicts `Not Eligible`, state is `Ineligible`.
- **4.7 Approved Application:** When all hard prerequisites, assessment pass, and ML eligibility are met, state is `Ready to Apply`.

### Category 5: Machine Learning Verification & Inference Pipeline (TC017 - TC019)
- **5.1 Feature Contract:** Verifies the 15 features are constructed in the exact order expected by the StandardScaler.
- **5.2 Feature Engineering:** Validates mathematical derivation of `certified_leverage`, `total_experience_months`, and score aggregates (`mean`, `min`, `max`).
- **5.3 Deterministic Output:** Identical input vectors must produce identical predictions and class probabilities.
- **5.4 Holdout Test Evaluation:** Evaluates genuine `binary_eligibility_model.pkl` on 400 test samples to audit Accuracy, ROC-AUC, and F1.

### Category 6: Role-Based Access Control & API Security (TC020 - TC023)
- **6.1 Unauthenticated Protection:** All sensitive `/api/admin/*` and `/api/competency/*` endpoints return 401 when token is missing.
- **6.2 Agent Role Boundaries:** Agents attempting to access administrative endpoints return HTTP 403.
- **6.3 Admin Role Boundaries:** Administrators attempting to access agent-specific profile or assessment endpoints return HTTP 403.
- **6.4 Database Demotion Check:** If an agent creates a token claiming Admin, but MySQL records them as Agent, the request is rejected with 403.
- **6.5 CORS Security:** Verifies CORS headers exclude wildcard `*` when credentials are supported.

---

## 5. Automated Test Execution Commands

```bash
# 1. Run the authoritative 15-test Panel Demonstration Readiness suite:
.venv\Scripts\python -m unittest tests/test_panel_demonstration_readiness.py

# 2. Run the complete 97-test VerifyMesh verification suite:
.venv\Scripts\python -m unittest discover tests

# 3. Run the standalone Machine Learning evaluation:
.venv\Scripts\python ml/evaluate.py

# 4. Build and lint the frontend:
cd frontend && npm run lint && npm run build
```
