
# VerifyMesh: AI-Assisted Workforce Competency & Task Eligibility Engine

VerifyMesh is an AI-assisted qualification verification and task-eligibility engine designed for decentralized workforce platforms and gig marketplaces.

In open labor platforms, matching workers to high-stakes tasks is often hindered by self-reported credential fraud and manual screening bottlenecks. VerifyMesh addresses this through a **dual-layer evaluation architecture**:

1. **Layer 1 — Machine Learning Inference:** A pre-trained **Three-Way Decision (3WD) Random Forest Classifier** analyzes an 11-dimensional feature vector grounded in verified work history, credentials, and standardized competency sub-scores. Rather than forcing a binary decision, the model classifies candidates as **Eligible**, **Ineligible**, or within a **Boundary Region requiring human review**.
2. **Layer 2 — Deterministic Rules Engine:** Cross-references the candidate's verified competency tier, domain tenure, and active certifications against task-specific requirements to determine task eligibility.

---

## System Architecture & Workflow

```text
Candidate Profile & Verified History (MySQL)
                 +
         Assessment Scores
                 |
                 v
+----------------------------------------------+
| Layer 1: Three-Way Decision Random Forest    |
|                  (Flask API)                 |
|                                              |
| Predicts:                                    |
| 0 = Ineligible                               |
| 1 = Boundary / Human Review                  |
| 2 = Eligible                                 |
+----------------------+-----------------------+
                       |
                       v
+----------------------------------------------+
| Layer 2: Competency Mapping & Rules Engine   |
|                                              |
| Checks:                                      |
| - Minimum Competency Tier                    |
| - Verified Domain Experience                 |
| - Required Certifications                    |
| - Assessment Requirements                    |
+----------------------+-----------------------+
                       |
                       v
             Task Eligibility Decision
                       |
                       v
     Ready to Apply | Assessment Needed
             | Locked | Assigned
```

### High-Level Workflow

1. **Agent Registration & Profile Setup:** Agents create accounts, complete their professional profiles, and submit work history and certifications.
2. **Credential Verification:** Platform administrators inspect supporting documents and approve credentials for storage in MySQL.
3. **Assessment Battery:** Agents complete standardized assessments evaluating domain knowledge, customer service, communication, and sales skills.
4. **Feature Assembly:** When `/api/competency/evaluate` is triggered, the backend derives experience from administrator-verified records using date-interval deduplication and calculates the `certified_leverage` feature.
5. **Model Inference & Competency Mapping:** The pre-loaded Random Forest model produces a three-way decision class and prediction probability. Application rules map the result to a competency tier.
6. **Task Matching & Application:** The task catalog computes eligibility for published tasks using task-specific requirements. Eligible agents can apply, while borderline cases can be routed for administrator review.

---

## Machine Learning Architecture

VerifyMesh separates **offline model training** from **runtime inference**.

### 1. Training & Hyperparameter Tuning

Model training is conducted externally in Google Colab, keeping model development separate from the web application.

- **Environment:** Google Colab
- **Model:** `RandomForestClassifier`
- **Configuration:** 300 estimators, maximum depth of 15, minimum samples per leaf of 2, and balanced class weights.
- **Feature Contract:** 11 numerical features consisting of 10 raw features and one derived feature.
- **Validation:** Stratified 80/20 train-test split.
- **Reported Metrics:** 95.2% accuracy and 0.941 Macro F1-score.
- **Model Artifact:** `threeway_decision_model.joblib`

> **Note:** Confirm that the reported accuracy and Macro F1-score match the final saved model and its evaluation results before publishing them.

### 2. Runtime Inference & Prediction

The Flask backend loads the trained model once during application startup through the inference module.

- **Singleton Loader:** `src/inference.py`
- **Inference:** In-memory predictions without retraining the model for each request.
- **Error Handling:** Returns descriptive HTTP 503 or 500 responses when the model or inference process is unavailable.

### 3. Model Classes vs. Application Competency Tiers

The model predicts one of three decision regions:

| Model Class | Decision Region | Competency Mapping |
|---|---|---|
| `0` | Negative region — Ineligible | Needs Improvement |
| `1` | Boundary region — Human review | Basic |
| `2` | Positive region — Eligible | Competent |

#### Advanced Tier Promotion Rule

Candidates assigned to Model Class `2` can be promoted to the **Advanced** competency tier when they meet both deterministic thresholds:

- Assessment score of at least 88%.
- At least 18 months of verified experience.

```text
assessment_score >= 88.0
AND
verified_experience_months >= 18.0
```

These thresholds are application-level rules, separate from the model's predicted class.

### 4. Input Features (11 Dimensions)

| Index | Feature Name | Source | Description |
|---:|---|---|---|
| 0 | `previous_experience_months` | MySQL `agent_experience` | Total deduplicated, verified work history across roles. |
| 1 | `sales_experience_months` | MySQL `agent_experience` | Deduplicated, verified months in sales roles. |
| 2 | `customer_service_experience_months` | MySQL `agent_experience` | Deduplicated, verified months in customer support roles. |
| 3 | `certification_count` | MySQL `agent_certifications` | Number of active, administrator-verified credentials. |
| 4 | `relevant_certification` | MySQL `agent_certifications` | Binary indicator for a relevant domain-specific credential. |
| 5 | `assessment_score` | MySQL `exam_results` | Composite competency assessment score, from 0 to 100. |
| 6 | `communication_score` | Assessment sub-score | Standardized verbal and written communication score. |
| 7 | `product_knowledge_score` | Assessment sub-score | Standardized product comprehension score. |
| 8 | `sales_skill_score` | Assessment sub-score | Standardized objection-handling and sales score. |
| 9 | `customer_service_score` | Assessment sub-score | Standardized de-escalation and customer service score. |
| 10 | `certified_leverage` | Derived feature | Calculated as `certification_count * (1.0 + relevant_certification)`. |

---

## Project Structure

```text
Verify_Mesh/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── auth_routes.py
│   ├── competency_routes.py
│   ├── admin_routes.py
│   ├── db.py
│   ├── email_service.py
│   ├── init_db.py
│   ├── schema.sql
│   └── models/
│       └── threeway_decision_model.joblib
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── services/
│   │   └── pages/
│   │       ├── LoginPage.jsx
│   │       ├── RegisterPage.jsx
│   │       ├── AgentDashboard.jsx
│   │       ├── ProfilePage.jsx
│   │       ├── AdminDashboard.jsx
│   │       └── CreateTaskPage.jsx
│   ├── package.json
│   └── vite.config.js
├── src/
│   └── inference.py
├── scratch/
│   ├── test_profile_workflow.py
│   ├── test_admin_task_form.py
│   └── test_agent_dashboard_metrics.py
├── requirements.txt
└── README.md
```

---

## Setup & Reproducibility Guide

Follow these steps to set up VerifyMesh in a local development environment.

### Prerequisites

- Python 3.10 or 3.11
- Node.js 18 or higher, including npm
- MySQL Server 8.0 or higher
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/Daniel-Obuya/VerifyMesh.git
cd VerifyMesh
```

### Step 2: Backend Setup

Create and activate a Python virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux or macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

### Step 3: MySQL Database Initialization

Ensure that MySQL is running locally on port `3306`.

Configure your database credentials in a root-level `.env` file or in `backend/config.py`, depending on how the application loads its configuration.

Example `.env` configuration:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=verifymesh_db
SECRET_KEY=your_development_secret_key
```

Replace the example password and secret key with your own development values. Do not commit real credentials to GitHub.

Initialize the database:

```bash
python backend/init_db.py
```

The initialization script is intended to create the database, apply the schema, and seed development accounts. Confirm these actions against the actual implementation before running it.

### Step 4: Place the Machine Learning Model

VerifyMesh expects the pre-trained model at:

```text
backend/models/threeway_decision_model.joblib
```

If the model file is excluded by `.gitignore`, copy the artifact into this directory before starting the backend.

Only load trusted `.joblib` files, because deserializing an untrusted model file can execute malicious code.

### Step 5: Frontend Setup

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
```

### Step 6: Run the Application

#### Start the Flask Backend

From the project root, with the virtual environment activated:

```bash
python backend/app.py
```

The API is expected to run at:

```text
http://127.0.0.1:5000
```

Check the health endpoint:

```text
http://127.0.0.1:5000/api/health
```

#### Start the React Frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

The Vite development server is expected to be available at:

```text
http://localhost:5173
```

---

## Seeded Development Accounts

The database initialization script may provision development accounts for testing. The following are example credentials from the development setup and should be verified against `backend/init_db.py`.

| Role | Email | Password | Description |
|---|---|---|---|
| Agent | `alex.morgan@university.edu` | `password123` | Test agent with sample profile information. |
| Administrator | `admin@verifymesh.io` | `password123` | Development administrator account. |

**Security note:** These are development-only credentials. Never use default passwords in a production deployment.

---

## API Endpoints Overview

The following table documents the intended API surface. Confirm each endpoint, HTTP method, and access rule against the current Flask route definitions.

| Blueprint | Method | Endpoint | Access | Description |
|---|---|---|---|---|
| System | GET | `/api/health` | Public | Reports system status, database connectivity, and model status. |
| Auth | POST | `/api/auth/register` | Public | Registers an agent and initiates email OTP verification. |
| Auth | POST | `/api/auth/verify-email` | Public | Verifies the email OTP and activates the account. |
| Auth | POST | `/api/auth/login` | Public | Authenticates a user and issues an authentication token. |
| Competency | GET | `/api/competency/profile` | Agent | Retrieves the agent profile and readiness information. |
| Competency | PUT | `/api/competency/profile` | Agent | Updates permitted profile information. |
| Competency | POST | `/api/competency/experiences` | Agent | Submits employment experience for verification. |
| Competency | POST | `/api/competency/certifications` | Agent | Submits certifications for verification. |
| Competency | POST | `/api/competency/evaluate` | Agent | Runs competency evaluation and saves the result. |
| Competency | GET | `/api/competency/tasks` | Agent | Retrieves published tasks and eligibility status. |
| Competency | POST | `/api/competency/tasks/:id/apply` | Agent | Submits an application for a task, subject to eligibility checks. |
| Admin | GET | `/api/admin/overview` | Admin | Retrieves system-wide metrics and recent activity. |
| Admin | GET | `/api/admin/agents` | Admin | Lists registered agents and their competency states. |
| Admin | GET | `/api/admin/tasks` | Admin | Lists tasks and configured eligibility requirements. |
| Admin | POST | `/api/admin/tasks` | Admin | Creates a task with eligibility prerequisites. |
| Admin | GET | `/api/admin/verifications` | Admin | Retrieves pending experience and certification verifications. |
| Admin | PUT | `/api/admin/verifications/certifications/:id` | Admin | Approves or rejects submitted certifications. |

---

## Running Automated Tests

VerifyMesh includes integration and acceptance test scripts in the `scratch/` directory.

Run each test from the project root with the Python virtual environment activated:

```bash
# Profile workflow, experience deduplication, and verifications
python scratch/test_profile_workflow.py

# Task builder, input validation, and access controls
python scratch/test_admin_task_form.py

# Dashboard metrics, task catalog, and state transitions
python scratch/test_agent_dashboard_metrics.py
```

Ensure that the database, environment variables, and required model artifact are configured before running integration tests.

---

## Technology Stack

- **Frontend:** React 18, Vite, React Router, Tailwind CSS, Lucide Icons, Axios
- **Backend:** Python, Flask, PyMySQL, Werkzeug Security, itsdangerous
- **Database:** MySQL 8.0, InnoDB
- **Machine Learning:** scikit-learn, joblib, pandas, NumPy
- **Authentication:** Signed bearer tokens, email OTP verification, role-based access controls
- **Testing:** Python-based integration and acceptance test scripts
- **Model Development:** Google Colab

---

## License & Academic Disclaimer

VerifyMesh was developed as an undergraduate Computer Science capstone project. It is intended for academic, research, and demonstration purposes.

Unless a separate license file is provided, no open-source license should be assumed.
