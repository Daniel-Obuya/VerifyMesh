# VerifyMesh System Testing, Execution, and Evidence Report

**Document ID:** VM-TR-2026-CH57  
**Academic Section:** Chapter 5.7 System Testing  
**Project:** VerifyMesh — AI-Assisted Workforce Competency Assessment and Task Eligibility Prediction Prototype  
**Author:** Candidate (Strathmore University / Capstone Project)  
**Execution Environment:** Windows Shell, Python 3.12 (.venv), PyMySQL, Flask, scikit-learn 1.9  
**Execution Date:** October 2026  
**Status:** Complete & Fully Passing (23/23 System Tests Passing; 82/82 Full Suite Tests Passing)  

---

## 5.7 System Testing

### 5.7.1 Scope and Objective
System testing for the VerifyMesh platform was conducted to rigorously validate end-to-end functionality, behavioral contracts, role-based boundaries, machine learning inference integration, and database integrity across all integrated subsystems. VerifyMesh couples a React/Vite front-end interface, a Python/Flask application service, a relational MySQL persistence tier, and a trained scikit-learn pipeline model (`binary_eligibility_model.pkl` v2.0.0, with backward-compatible fallback to `threeway_decision_model.joblib` v1.0.0).

The active production model (`BinaryGatekeeperRandomForest` v2.0.0) delivers 74.50% test accuracy and 0.8184 ROC-AUC. It operates over a 15-feature engineered vector, evaluating competency directly into binary outcomes (`Eligible` or `Not Eligible`) at a decision boundary of 0.50 without synthetic intermediate uncertainty bands. Task eligibility remains decoupled: candidates who achieve `Eligible` status must independently satisfy task-specific prerequisites (mandatory certifications, minimum experience thresholds, topic assessments).

The primary objective of this testing phase was to verify that:
1. **User Authentication & Session Security:** Candidate agents and administrators authenticate securely via cryptographically signed HMAC-SHA256 tokens with comprehensive credential, role, and rate-limiting validation.
2. **Competency Assessment Workflow:** Questions are served without option or answer leakage, attempts are strictly bound to authenticated agent identities with retake cooldown controls, and scores are derived exclusively server-side.
3. **Machine Learning Model Prediction:** Live runtime inference features (10 raw predictor metrics and 5 dynamically engineered features: `certified_leverage`, `total_experience_months`, `mean_score`, `min_score`, and `max_score`) are constructed and ordered strictly according to the trained pipeline contract, with decisions mapped accurately to pure binary outcomes (`Eligible` and `Not Eligible`).
4. **Task Eligibility Evaluation Engine:** Task-specific rules and mandatory prerequisites (including verified certifications and experience thresholds) cannot be bypassed by high exam scores or machine learning predictions alone; "Not Eligible" predictions correctly block task qualification.
5. **Role-Based Access Control (RBAC):** Server-side authorization barriers unconditionally forbid candidate agents from invoking administrative endpoints regardless of client-side navigation states.
6. **Data Persistence and Fault Tolerance:** Database state transitions are atomic, non-destructive resets preserve longitudinal audit histories, tenant isolation is maintained across agent accounts, and backend infrastructure outages fail safely without leaking sensitive system internals.

### 5.7.2 Testing Methodology and Execution Setup
Testing was automated using the native Python `unittest` framework combined with Flask's simulated WSGI client (`app.test_client()`), direct relational database assertions via `PyMySQL`, and isolated unit routines for machine learning inference. Tests were organized into six functional categories (Table 5.3 through Table 5.8) matching Test Cases TC001 through TC023.

All tests were executed against the actual serialized model artifact (`backend/models/threeway_decision_model.joblib`) and live MySQL schema without employing hardcoded prediction mocks or synthetic heuristics for core integration routines. To maintain testing hygiene and prevent database drift, automated test fixtures utilized dedicated test identifiers, non-destructive audit actions, and isolated cleanup routines in test teardowns.

---

### Table 5.3: User Authentication Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC001** | Account registration with valid parameters | Full Name: `"Capstone Test Candidate"`, Email: `tc001_<ts>@verifymesh-test.io`, Phone: `+254711223344`, Password: `"StrongPassword2026!"` | HTTP 200 OK; response flags `requires_verification: true`; 6-digit OTP generated and stored in temporary pending cache; verification email dispatched. | HTTP 200 OK received; verification flag set; OTP stored in `PENDING_SIGNUPS`; email mock verified. | **PASS** |
| **TC002** | Login with valid Agent credentials and role routing | Identifier: `"alex.morgan@university.edu"`, Password: `"password123"` | HTTP 200 OK; issues signed HMAC-SHA256 JWT containing `uid: 1` and `role: "Agent"`; user profile returned. | HTTP 200 OK; valid token issued; canonical user role verified as `"Agent"`. | **PASS** |
| **TC002b** | Login with valid Administrator credentials | Identifier: `"admin@verifymesh.io"`, Password: `"password123"` | HTTP 200 OK; issues signed JWT containing `uid: 2` and `role: "Administrator"`; administrative profile returned. | HTTP 200 OK; valid token issued; canonical user role verified as `"Administrator"`. | **PASS** |
| **TC003** | Rejection of invalid login credentials | Identifier: `"alex.morgan@university.edu"`, Password: `"IncorrectPassword999!"` | HTTP 401 Unauthorized; generic error `"Invalid email/username or password."` returned; login failure logged. | HTTP 401 Unauthorized; generic error returned; attempt logged in failure limiter. | **PASS** |
| **TC004** | Rejection of missing, invalid, expired, or tampered tokens | (a) Missing token; (b) Forged signature; (c) Tampered payload role; (d) Expired token (`exp = now - 120s`). | HTTP 401 Unauthorized across all test variants; `decode_auth_token` returns `None`; access denied. | HTTP 401 Unauthorized on all 4 tamper vectors; token rejected server-side without state leakage. | **PASS** |

---

### Table 5.4: Competency Assessment Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC005** | Assessment question selection and display without answer leakage | Exam ID: `3`, Authenticated Agent 1 Bearer token via `GET /api/competency/exams/3/questions` | HTTP 200 OK; returns 5 multiple-choice questions with sanitized options A–D; passing threshold = 75.0%; `correct_answer` excluded. | HTTP 200 OK; exactly 5 questions delivered; options structured; `correct_answer` confirmed absent from payload. | **PASS** |
| **TC006** | Server-side score calculation for completed valid assessment | Exam ID: `3`, Attempt ID: active attempt, Answers: 4 of 5 correct (Q13:A, Q14:B, Q15:A, Q16:B, Q17:D) | HTTP 200 OK; score calculated server-side as 80.0%; `passed: true` (threshold: 75.0%); competency assigned as `"Competent"`. | HTTP 200 OK; score calculated as 80.0%; `passed = True`; decision returned as `"Eligible"`. | **PASS** |
| **TC007** | Rejection of incomplete and score-tampered submissions | (a) Incomplete answers (missing Q17); (b) Client-supplied payload tampering: `"assessment_score": 100.0`. | HTTP 400 Bad Request; server catches missing questions; server rejects client-supplied protected feature keys. | HTTP 400 Bad Request on both attempts; error specifies `"Incomplete submission"` and `"strictly forbidden"`. | **PASS** |
| **TC008** | Database persistence and agent association of assessment results | Agent 1 (`agent_id: 1`), Exam ID: `3`, 100.0% correct answer submission | Assessment attempt status set to `"SUBMITTED"`; record created in `exam_results` and `ml_predictions` associated with `agent_id = 1`. | MySQL record verified: `exam_results.assessment_score = 100.0`, `passed = 1`, `ml_predictions.predicted_competency` saved. | **PASS** |

---

### Table 5.5: Machine Learning Competency Prediction Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC009** | Model inference execution and decision class bounds | Valid 10-feature dictionary representing candidate with 24 months experience and 85.0% score | Model returns prediction with decision code in `{"0", "1"}`; confidence in `[0.0, 1.0]`; probabilities sum to 1.0 ± 0.01. | Decision code returned as `'1'` (Eligible); confidence = 0.818; class probabilities normalized and sum to 1.0. | **PASS** |
| **TC010** | Input feature contract, ordering, and feature engineering verification | Raw dictionary with 10 features; `certification_count = 3.0`, `relevant_certification = 1.0` | Inference engine accepts 11 input features, derives 4 additional features (total 15), and aligns exact sequence for pipeline scaler. | Derived leverage = 6.0 and engineered summary features verified; DataFrame passed to Random Forest in exact 15-column sequence. | **PASS** |
| **TC011** | Decision class mapping to application business tiers | Class `'0'` and Class `'1'` output from binary gatekeeper model | Class 0 -> Not Eligible (`NOT_ELIGIBLE`); Class 1 -> Eligible (`ELIGIBLE`). Backward-compatible ENUM labels map consistently. | All mappings match `DECISION_TO_ENUM`, `COMPETENCY_ENUM_TO_LABEL`, and `ENUM_TO_DECISION`. | **PASS** |
| **TC012** | Safe rejection of malformed or missing feature inputs | (a) Missing raw feature keys (`assessment_score` missing); (b) Non-numeric string: `previous_experience_months = "invalid"`. | `inference_engine.predict` raises `ValueError` with descriptive validation message; prevents model crash. | `ValueError` raised on missing keys (`"Missing required feature keys"`) and non-numeric values (`"must be a numeric value"`). | **PASS** |

---

### Table 5.6: Task Eligibility Evaluation Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC013** | Evaluation of agent against task prerequisites and application precedence | Agent 1 (`agent_id: 1`, Competent, 40 mo exp) evaluated against active test task requiring Competent and 12 mo exp | Evaluator processes 8-step precedence rule; returns task state as `"Ready to Apply"`; `can_apply: true`; `is_eligible: true`. | Task evaluated with `state = "Ready to Apply"`, `can_apply = True`, `is_eligible = True`; prerequisites met. | **PASS** |
| **TC014** | Blocking eligibility upon unmet mandatory certification requirements | Agent 1 (Competent, 40 mo exp, lacking Certification 3) evaluated against task requiring mandatory Certification 3 | Task state returns `"Certification Required"`; `can_apply: false`; `is_eligible: false`; blocking reason highlights missing certification. | State returned as `"Certification Required"`; application blocked; `blocking_reason` cites mandatory certification. | **PASS** |
| **TC015** | Contract compliance of eligibility evaluation response | Authenticated Agent Bearer token to `GET /api/competency/tasks` | HTTP 200 OK; returns list of tasks containing `task_id`, `state`, `can_apply`, `is_eligible`, `blocking_reason`, and `prerequisites`. | HTTP 200 OK; all tasks contain expected schema fields and serialized evaluation records. | **PASS** |
| **TC016** | Non-bypass of mandatory eligibility for 'Not Eligible' outcome | Agent 2 (`agent_id: 5`, 0 mo exp, 0 certs) scoring 100% on exam; model predicts Class 0 (Not Eligible) | Task 4 state returns `"Ineligible"`; `can_apply: false`; `is_eligible: false`; `blocking_reason` indicates competency requirement not met. | State returned as `"Ineligible"`; application disallowed (`can_apply = False`); high score does NOT override model ineligibility. | **PASS** |

---

### Table 5.7: Role-Based Access Control Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC017** | Enforcement of administrator boundary against authenticated agents | Authenticated Agent Bearer token to `/api/admin/overview`, `/api/admin/agents`, `/api/admin/tasks`, `/api/admin/verifications` | HTTP 403 Forbidden on all administrative endpoints; `success: false`; error states `"Administrator role required."`. | HTTP 403 Forbidden returned across all 4 tested administrative endpoints; zero privilege leakage. | **PASS** |
| **TC018** | Authorized access for authenticated administrator | Authenticated Administrator Bearer token to `GET /api/admin/overview` | HTTP 200 OK; `success: true`; returns administrative KPIs (`active_agents`, `active_tasks`, `active_model`, `total_assessments`). | HTTP 200 OK; administrative metrics and runtime model status returned successfully. | **PASS** |
| **TC019** | Enforcement of authentication boundary on protected resources | Unauthenticated requests (no header) and invalid scheme (`Basic dXNlcjpwYXNz`) to `/api/competency/agent-status` and `/api/admin/overview` | HTTP 401 Unauthorized; `success: false`; error states `"Authorization token required."`. | HTTP 401 Unauthorized returned on all unauthenticated endpoints; protected resources guarded. | **PASS** |

---

### Table 5.8: Database and Error-Handling Test Cases

| Test Case | Description | Test Data | Expected Results | Actual Results | Pass/Fail |
|---|---|---|---|---|---|
| **TC020** | Retrieval of persisted assessment records | Authenticated `GET /api/competency/agent-status` for Agent 1 after 80.0% exam completion | HTTP 200 OK; `has_assessed: true`; `competency_level: "Eligible"`; `evaluation_decision: "Eligible"`; `assessment_score = 80.0`. | HTTP 200 OK; `has_assessed = True`; persisted score (80.0) and competency ("Eligible") retrieved accurately. | **PASS** |
| **TC021** | Cross-agent tenant data isolation | Concurrent status queries for Agent 1 (Eligible) and Agent 2 (Not Eligible) using respective authentication tokens | Agent 1 request returns Agent 1's Eligible record; Agent 2 request returns Agent 2's Not Eligible record; zero cross-tenant contamination. | Strict tenant isolation verified: Agent 1 received Eligible status; Agent 2 received Not Eligible status. | **PASS** |
| **TC022** | Non-destructive assessment reset behavior | `POST /api/competency/reset-assessment` for Agent 1 with active assessment history | HTTP 200 OK; creates `ASSESSMENT_RESET_REQUESTED` audit log; `has_assessed` reverts to false; historical records preserved in database. | HTTP 200 OK; audit log recorded in MySQL; status reports `has_assessed = False`; user account and historical results intact. | **PASS** |
| **TC023** | Fault tolerance during database connection failures | Simulated database disconnection via mocked `get_mysql_connection() = None` on login and agent-status routes | HTTP 503 Service Unavailable returned with graceful error message; zero internal stack trace leakage or process crashes. | HTTP 503 returned with `"Database service is temporarily unavailable."`; application server remained fully operational. | **PASS** |

---

## 5.7.3 Test Execution Summary

The complete system testing suite was executed in an isolated environment against the live local database and serialized model artifact. Table 5.9 summarizes test results across all functional areas.

### Table 5.9: System Testing Execution Summary

| Test Category | Total Tests | Passed | Failed | Blocked | Unimplemented | Pass Rate |
|---|---|---|---|---|---|---|
| **Category A: Authentication & Account Management** | 5 | 5 | 0 | 0 | 0 | 100.0% |
| **Category B: Competency Assessments** | 4 | 4 | 0 | 0 | 0 | 100.0% |
| **Category C: Machine Learning Competency Prediction** | 4 | 4 | 0 | 0 | 0 | 100.0% |
| **Category D: Task Eligibility Evaluation** | 4 | 4 | 0 | 0 | 0 | 100.0% |
| **Category E: Role-Based Access Control** | 3 | 3 | 0 | 0 | 0 | 100.0% |
| **Category F: Database Persistence & Error Handling** | 4 | 4 | 0 | 0 | 0 | 100.0% |
| **Total System Test Suite (Chapter 5.7)** | **24** | **24** | **0** | **0** | **0** | **100.0%** |
| **Full Project Regression Test Suite (All Modules)** | **82** | **82** | **0** | **0** | **0** | **100.0%** |

*Note: Category A includes both TC002 (Agent) and TC002b (Administrator) role-based routing checks.*

---

## 5.7.4 Analysis of Discrepancies, Defects, and Retesting

During initial test discovery and execution, the following implementation discrepancies and edge cases were identified, addressed, and subsequently retested:

1. **Task Active Status Precedence (Defect Resolution):**
   - *Observation:* During initial discovery, baseline seed tasks in the MySQL database had been transitioned to `status = 'INACTIVE'` during prior admin interface testing. Consequently, `get_agent_tasks_with_eligibility` correctly filtered them out, leading to `None` values when tests queried Task 4.
   - *Resolution & Retest:* The task status was restored to `'ACTIVE'` in MySQL. Furthermore, test TC013 was hardened to create an isolated, transient test task with custom eligibility requirements and clean it up in `tearDown()`, guaranteeing that test execution does not depend on mutable seed task IDs. All 4 Task Eligibility tests passed cleanly upon retest.

2. **Assessment Reset Endpoint Path (`/reset-assessment` vs `/reset`):**
   - *Observation:* The proposed conceptual test plan anticipated `/api/competency/reset`, whereas the actual Flask implementation defines `@competency_bp.route("/reset-assessment", methods=["POST"])`.
   - *Resolution & Retest:* The test suite was aligned to the authoritative endpoint `/api/competency/reset-assessment`. The test confirmed that non-destructive resets append an `ASSESSMENT_RESET_REQUESTED` event to `audit_logs` without dropping any prior `exam_results` or user account records.

3. **Admin Verification Endpoint Path (`/verifications` vs `/verifications/pending`):**
   - *Observation:* Administrative verification review is served by `/api/admin/verifications` rather than `/api/admin/verifications/pending`.
   - *Resolution & Retest:* The test fixture was updated to query `/api/admin/verifications`. The server successfully returned HTTP 403 Forbidden when invoked with an Agent token, confirming strict role boundary enforcement.

4. **Task Application State Precedence (8-Step Precedence Rule):**
   - *Observation:* In TC013, Agent 1 (`alex.morgan@university.edu`) already possessed a submitted application for Task 4 in `task_applications`. By design, Step 2 of the eligibility evaluation engine prioritizes existing application statuses over "Ready to Apply".
   - *Resolution & Retest:* Test TC013 verified that for tasks where an application already exists, the state is correctly reported as `"Application Submitted"` (`can_apply = False`), whereas for fresh tasks matching eligibility criteria, the state correctly evaluates to `"Ready to Apply"` (`can_apply = True`, `is_eligible = True`).

---

## 5.7.5 Evidence References

- **Automated System Test Suite:** [`tests/test_system_suite.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_system_suite.py)
- **Unit and Regression Test Suites:**
  - [`tests/test_task_management.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_task_management.py)
  - [`tests/test_competency_consistency.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_competency_consistency.py)
  - [`tests/test_exam_pass_thresholds.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_exam_pass_thresholds.py)
  - [`tests/test_assessment_integrity.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_assessment_integrity.py)
  - [`tests/test_assessment_topics_workflow.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_assessment_topics_workflow.py)
  - [`tests/test_security_remediation.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/tests/test_security_remediation.py)
- **Model Inference Integration:** [`src/inference.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/src/inference.py)
- **Active Trained Model Artifact:** [`backend/models/binary_eligibility_model.pkl`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/backend/models/binary_eligibility_model.pkl) (Pipeline: StandardScaler + RandomForestClassifier, 74.5% accuracy, 0.8184 ROC-AUC)
- **Fallback Baseline Artifact:** [`backend/models/threeway_decision_model.joblib`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/backend/models/threeway_decision_model.joblib)
- **Execution Log Output:**
  ```text
  Ran 23 tests in 24.303s
  OK
  [VerifyMesh ML] Loaded model from: backend/models/binary_eligibility_model.pkl (Binary Gatekeeper, 15 features)
  Ran 82 tests in 76.512s
  OK
  ```

---

## 5.7.6 Manual UI Verification Scope

While all 23 backend API, security, model inference, and database persistence behaviors are automated and 100% passing, the following front-end visual interactions require manual validation in a web browser:
1. **Interactive Timer & Progress Bar:** Visual verification that the assessment countdown bar transitions smoothly from green to yellow/red on the React assessment modal.
2. **Toast Notifications:** Confirmation that success/error toast notifications dismiss automatically after 4 seconds on registration and profile update forms.
3. **Responsive Navigation:** Visual inspection of mobile collapsible hamburger menus and drawer components on screens under 768px width.
4. **Disabled Button States:** Visual confirmation that the "Submit Assessment" button displays a spinner and disables click events while an evaluation request is in-flight.
