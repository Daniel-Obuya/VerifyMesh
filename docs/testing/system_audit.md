# VerifyMesh: Comprehensive System Architecture & Environment Audit

**Project:** VerifyMesh: Enhancing Workforce Task Allocation Through Competency Assessment and Eligibility Prediction  
**Evaluation Role:** Senior QA Automation Engineer, Application Security Tester, Full-Stack Engineer, ML Evaluator  
**Audit Date:** October 2026  
**System Status:** Authoritative Binary Gatekeeper Architecture (15-Feature Pipeline, MySQL 8.0, Flask 3.0, React 19 / Vite)

---

## 1. Executive Summary

VerifyMesh is an automated workforce task allocation and competency verification platform. It operates a **dual-layer gatekeeper architecture** combining:
1. **Hard Eligibility Constraints (Layer 1):** Strict rule-based validation of mandatory prerequisites (certifications, minimum verified experience months, active account status).
2. **Predictive Competency Gatekeeper (Layer 2):** A machine learning pipeline executing a StandardScaler + RandomForestClassifier trained on 15 profile and assessment features to predict binary eligibility (`Eligible` [1] vs `Not Eligible` [0]).

The system has undergone a full end-to-end audit across its frontend, backend API, database schema, ML inference pipeline, RBAC security boundaries, and automated test suite.

---

## 2. System Architecture & Component Mapping

```
               +-------------------------------------------------------+
               |             React 19 + Vite Frontend SPA              |
               | (Tailwind CSS, Lucide Icons, React Router v7, Google) |
               +-------------------------------------------------------+
                                           |
                                   REST API / JSON (Bearer Token)
                                           v
               +-------------------------------------------------------+
               |            VerifyMesh Flask API Core (3.0)            |
               |                                                       |
               |  +--------------------+    +-----------------------+  |
               |  |  auth_routes.py    |    |   admin_routes.py     |  |
               |  |  (OTP, Login, JWT) |    |   (Tasks, Verifs, KPI)|  |
               |  +--------------------+    +-----------------------+  |
               |  +-------------------------------------------------+  |
               |  |             competency_routes.py                |  |
               |  |   (Exams, Dynamic Topics, Profile, Scoring)     |  |
               |  +-------------------------------------------------+  |
               +-------------------------------------------------------+
                           |                               |
                           v                               v
         +----------------------------------+   +----------------------+
         |     src/inference.py (ML)        |   |    MySQL 8.0 Engine  |
         |  binary_eligibility_model.pkl    |   |  (InnoDB, 27 Tables, |
         |  StandardScaler + RandomForest   |   |   Foreign Keys,      |
         |  15 Feature Vector Engineering   |   |   Audit Logs)        |
         +----------------------------------+   +----------------------+
```

### 2.1 Technology Stack Summary

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend SPA** | React, Vite, Tailwind CSS | React 19.2, Vite 8.3 | User interface, state management, role-based dashboards |
| **Icons & Design** | Lucide React | 1.48.0 | UI icon system |
| **Backend API** | Flask, Flask-CORS, PyMySQL | Flask 3.0+, PyMySQL 1.1+ | REST service, business rules, grading, authorization |
| **Database** | MySQL 8.0 Community | 8.0.x InnoDB | Persistent relational storage, transactions, audit logs |
| **Machine Learning**| scikit-learn, pandas, joblib | scikit-learn 1.4+, joblib 1.3+ | Feature engineering, binary eligibility classification |
| **Authentication** | HMAC-SHA256 Signed Tokens | Custom Cryptographic | Stateless Bearer token verification with database re-check |
| **Email Service** | Python smtplib / CSPRNG OTP | OS CSPRNG `secrets` | 6-digit email OTP generation and verification |

---

## 3. Discovered Routes and Endpoints (42 Endpoints)

### 3.1 Authentication Blueprint (`/api/auth`)
- `POST /api/auth/register`: Candidate registration (validates fields, creates pending signup, generates 6-digit CSPRNG OTP).
- `POST /api/auth/verify-email`: Validates OTP against MySQL `email_verifications`, creates active agent record.
- `POST /api/auth/resend-otp`: Resends fresh OTP with strict rate limiting (max 3 resends per 10 minutes).
- `POST /api/auth/login`: Authenticates agent or administrator, enforces brute-force rate limit (max 5 failed attempts per 15 min), issues signed Bearer token.
- `GET /api/auth/me`: Re-validates active session and DB role.
- `POST /api/auth/logout`: Invalidates client session.
- `POST /api/auth/forgot-password`: Generates reset token.
- `POST /api/auth/google`: Google OAuth token verification and account provisioning.

### 3.2 Competency & Agent Blueprint (`/api/competency`)
- `GET /api/competency/profile`: Retrieves authenticated agent's profile, verified metrics, and status.
- `PUT /api/competency/profile`: Updates editable personal details (bio, location); mass assignment of role/experience strictly blocked.
- `GET /api/competency/tasks`: Retrieves available tasks evaluated through the 8-step precedence rule.
- `GET /api/competency/tasks/<id>`: Retrieves detailed task specification, deliverables, and prerequisites.
- `POST /api/competency/tasks/<id>/apply`: Submits application if prerequisites and eligibility are met.
- `GET /api/competency/experiences`: Lists work history entries with verification statuses.
- `POST /api/competency/experiences`: Submits work experience for admin review (validates date ranges).
- `DELETE /api/competency/experiences/<id>`: Removes owned pending/rejected work experience.
- `GET /api/competency/certifications`: Lists agent certifications.
- `POST /api/competency/certifications`: Submits certification for admin verification.
- `DELETE /api/competency/certifications/<id>`: Deletes owned certification record.
- `GET /api/competency/exams/<id>/questions`: Retrieves sanitized exam questions (omits correct answers & weights).
- `POST /api/competency/exams/<id>/start-attempt`: Initiates an authoritative attempt, checking retake cooldown.
- `POST /api/competency/exams/<id>/submit`: Scores answers server-side, runs ML inference, saves `exam_results` and `ml_predictions`.
- `GET /api/competency/attempts/<id>`: Retrieves attempt score breakdown, enforcing strict agent ownership.
- `GET /api/competency/topics`: Lists active assessment topics.
- `GET /api/competency/topics/<id>`: Details of a specific assessment topic.
- `GET /api/competency/topics/<id>/questions`: Sanitized topic questions.
- `POST /api/competency/topics/<id>/start-attempt`: Starts dynamic topic assessment attempt.
- `POST /api/competency/topics/<id>/submit`: Graded topic submission.
- `POST /api/competency/evaluate`: Direct profile evaluation endpoint (strictly rejects client-supplied scores).
- `POST /api/competency/reset-assessment`: Non-destructive reset of assessment state for testing/rehearsal.
- `GET /api/competency/model-info`: Returns active model metadata and feature schema.
- `GET /api/competency/sample-inputs`: Returns benchmark feature sets.
- `GET /api/competency/activities`: Lists recent audit log activities for authenticated agent.
- `GET /api/competency/agent-status`: Summary of current assessment status and latest ML prediction.

### 3.3 Administration Blueprint (`/api/admin`)
- `GET /api/admin/overview`: Dashboard metrics (agent count, active tasks, pass rates, runtime model info).
- `GET /api/admin/agents`: Agent directory with search, filtering, and experience summaries.
- `GET /api/admin/tasks`: Task management list.
- `POST /api/admin/tasks`: Creates a new task and associated `task_requirements` transactionally.
- `GET /api/admin/tasks/<id>`: Retrieves complete task configuration.
- `PUT /api/admin/tasks/<id>`: Updates task parameters and requirements.
- `DELETE /api/admin/tasks/<id>`: Deactivates or removes a task.
- `PATCH /api/admin/tasks/<id>/status`: Toggles task status (`ACTIVE`, `INACTIVE`, `COMPLETED`).
- `GET /api/admin/tasks/metadata`: Retrieves categories, exams, and certifications for task builder dropdowns.
- `GET /api/admin/assessments`: Administrative overview of all assessment attempts and scores across candidates.
- `GET /api/admin/reviews`: Lists eligibility evaluations requiring administrative review.
- `GET /api/admin/reviews/<id>`: Detailed evidence behind an agent's eligibility prediction.
- `GET /api/admin/verifications`: Verification queue for pending experiences and certifications.
- `POST /api/admin/verifications/experiences/<id>/review`: Approves or rejects experience entry (with reason).
- `POST /api/admin/verifications/certifications/<id>/review`: Approves or rejects certification entry.

### 3.4 System Health Endpoint
- `GET /api/health`: Validates MySQL connectivity, engine mode, and ML model loaded status.

---

## 4. Database Schema & Integrity

The database `verifymesh_db` contains 27 tables and 1 view:
- **Core Entities:** `users`, `agents`, `categories`, `tasks`, `task_requirements`, `certifications`, `skills`.
- **Competency & Assessments:** `exams`, `exam_questions`, `assessment_attempts`, `exam_results`, `assessment_topics`, `task_assessment_topics`, `agent_topic_results`.
- **Machine Learning & Decisions:** `ml_models`, `ml_predictions`, `eligibility_evaluations`, `eligibility_checks`, `task_applications`, `task_recommendations`.
- **Verification & Security:** `email_verifications`, `agent_certifications`, `agent_experience`, `agent_skills`, `agent_categories`, `audit_logs`, `schema_migrations`.
- **View:** `v_eligibility_summary`.

### Key Relational Controls:
- All core tables utilize Foreign Keys with `ON DELETE CASCADE` or `RESTRICT` where appropriate.
- Unique constraints prevent duplicate accounts (`users.email`), duplicate active verifications, and redundant submissions.
- Multi-table modifications are wrapped in database transactions (`conn.commit()` / `conn.rollback()`).

---

## 5. Machine Learning Artifacts

- **Model Artifact:** `backend/models/binary_eligibility_model.pkl` (3.45 MB)
- **Architecture:** scikit-learn `Pipeline([('scaler', StandardScaler()), ('classifier', RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_split=5, random_state=42))])`
- **Feature Set:** Exact 15 features matching training:
  1. `previous_experience_months`
  2. `sales_experience_months`
  3. `customer_service_experience_months`
  4. `certification_count`
  5. `relevant_certification`
  6. `assessment_score`
  7. `communication_score`
  8. `product_knowledge_score`
  9. `sales_skill_score`
  10. `customer_service_score`
  11. `certified_leverage` (Engineered: count * (1 + relevant))
  12. `total_experience_months` (Engineered: sum of work months)
  13. `mean_score` (Engineered: mean of 5 subscores)
  14. `min_score` (Engineered: min of 5 subscores)
  15. `max_score` (Engineered: max of 5 subscores)
- **Output Classes:** `0`: Not Eligible, `1`: Eligible.
- **Evaluation Performance on 400 Holdout Test Samples:**
  - Accuracy: **90.75%**
  - ROC-AUC: **0.9639**
  - Macro F1: **0.9065**

---

## 6. Security Boundaries & Risk Assessment

1. **Authentication Token Security:** HMAC-SHA256 signature verification over base64 JSON payload. Tokens signed with an incorrect secret, modified payload, or expired timestamp are rejected (401).
2. **Server-Side Role Re-validation:** Role claims in tokens are never trusted blindly; `get_authenticated_admin()` and `get_authenticated_agent()` query MySQL `users` table on every request to confirm active status and current role.
3. **Question & Scoring Sanitization:** Correct answers and point weights are never delivered to the client. Assessment scoring and pass/fail calculations are performed strictly on the backend.
4. **Client-Supplied Score Rejection:** Any client request containing `assessment_score`, `score`, `passed`, or subscores is rejected with HTTP 400.
5. **Rate Limiting:** In-memory thread-safe rate limiters throttle login attempts (max 5 per 15 min) and OTP verification/resend requests.
6. **Cross-Origin Configuration:** CORS origins are restricted to configured localhost origins; wildcard `*` with credentials is explicitly forbidden.
7. **Environment Secrets:** Secrets are loaded from `.env` (gitignored). `.env.example` contains placeholder tokens.
