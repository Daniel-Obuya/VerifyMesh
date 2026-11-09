# VerifyMesh Task-Specific ML Dataset: Data Dictionary & Feature Specification

**Author:** Daniel Obuya & Research Engineering Team  
**Context:** VerifyMesh Workforce Platform (Task-Specific Performance Modeling Prototype)  
**Status:** Synthetic Research Dataset (Not Empirical Production Records)  
**Location:** `ml/experiments/task_specific_synthetic_data/`

---

## 1. Overview and Architecture

The VerifyMesh system decouples candidate readiness into two discrete architectural stages:

1. **Stage 1 (Mandatory Gatekeeper & Eligibility Rules):** Determines whether an applicant meets legal, compliance, certification, and baseline assessment prerequisites. Applicants failing these checks are ruled **Ineligible** and cannot be dispatched to tasks regardless of statistical model score.
2. **Stage 2 (Task-Specific Performance Modeling):** For candidates who pass Stage 1, this machine learning component evaluates the relational fit between applicant competencies and specific task demands, predicting the probability of simulated successful task execution ($Y \in \{0, 1\}$).

This data dictionary covers the four generated data tables:
- `synthetic_applicants.csv` (Applicant source table)
- `synthetic_tasks.csv` (Task specifications table)
- `synthetic_applicant_task_pairs.csv` (All paired combinations with gatekeeper audits and simulation diagnostics)
- `task_suitability_training.csv` (Sanitized training dataset containing only eligible observations and permitted predictive features)

---

## 2. Table: `synthetic_applicants.csv`

Each row represents a distinct synthetic candidate ($N = 800$).

| Column Name | Data Type | Units / Format | Allowed Values / Range | Description | Permitted Predictive Feature? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `applicant_id` | String | Identifier (`APP-XXXX`) | `APP-0001` to `APP-0800` | Unique applicant identifier. Used solely for joins and audit tracing. | ❌ Forbidden (Identifier) |
| `relevant_experience_months` | Integer | Months | $[0, 180]$ | Verified total prior tenure in relevant operational or technical domains. | ✅ Yes |
| `sales_experience_months` | Integer | Months | $[0, 120]$ | Verified prior tenure specifically in sales, account acquisition, or telemarketing. | ✅ Yes |
| `customer_service_experience_months` | Integer | Months | $[0, 120]$ | Verified prior tenure in customer support, ticketing, or client relations. | ✅ Yes |
| `total_experience_months` | Integer | Months | $[1, 180]$ | Internally consistent overall work tenure ($\ge \max(\text{sales}, \text{cs})$). | ✅ Yes |
| `certification_count` | Integer | Count | $[0, 5]$ | Total count of verified credentials and professional certificates held. | ✅ Yes |
| `has_sales_cert` | Binary | Indicator | $\{0, 1\}$ | Indicator flag: candidate holds a verified Sales Specialist credential. | ✅ Yes |
| `has_cs_cert` | Binary | Indicator | $\{0, 1\}$ | Indicator flag: candidate holds a verified Customer Success Professional credential. | ✅ Yes |
| `has_technical_cert` | Binary | Indicator | $\{0, 1\}$ | Indicator flag: candidate holds a Technical Support Architect credential. | ✅ Yes |
| `primary_certification` | String | Categorical | `None`, `Sales_Specialist`, `Customer_Success_Pro`, `Technical_Support_Architect` | Categorical classification of the candidate's primary certified specialty. | ✅ Yes |
| `assessment_score` | Float | Score (0–100) | $[15.0, 99.0]$ | Standardized composite score from the VerifyMesh general assessment battery. | ✅ Yes |
| `communication_score` | Float | Score (0–100) | $[15.0, 99.0]$ | Standardized score in verbal/written communication and stakeholder engagement. | ✅ Yes |
| `product_knowledge_score` | Float | Score (0–100) | $[15.0, 99.0]$ | Standardized score in technical software comprehension and systems navigation. | ✅ Yes |
| `sales_skill_score` | Float | Score (0–100) | $[15.0, 99.0]$ | Standardized score in objection handling, qualification, and closing techniques. | ✅ Yes |
| `customer_service_score` | Float | Score (0–100) | $[15.0, 99.0]$ | Standardized score in de-escalation, active listening, and issue resolution. | ✅ Yes |

---

## 3. Table: `synthetic_tasks.csv`

Each row represents an active operational task template ($N = 30$).

| Column Name | Data Type | Units / Format | Allowed Values / Range | Description | Permitted Predictive Feature? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `task_id` | String | Identifier (`TSK-XXX`) | `TSK-001` to `TSK-030` | Unique task identifier. Used solely for traceability and indexing. | ❌ Forbidden (Identifier) |
| `task_title` | String | Text | Descriptive string | Human-readable title of the task assignment. | ❌ Excluded (High Cardinality) |
| `task_category` | String | Categorical | 5 categories (see below) | High-level operational classification of the assignment. | ✅ Yes |
| `difficulty_level` | String | Categorical | `Low`, `Medium`, `High` | Qualitative complexity rating assigned by administrator. | ✅ Yes |
| `difficulty_tier` | Integer | Ordinal Tier | $\{1, 2, 3\}$ | Numeric difficulty rank ($1 = \text{Low}, 2 = \text{Medium}, 3 = \text{High}$). | ✅ Yes |
| `min_relevant_experience_months` | Integer | Months | $[3, 40]$ | Mandatory minimum relevant tenure required to be eligible for assignment. | ✅ Yes |
| `required_certification` | String | Categorical | `None`, `Sales_Specialist`, `Customer_Success_Pro`, `Technical_Support_Architect` | Mandatory credential required for dispatch. | ✅ Yes |
| `min_assessment_score` | Float | Cutoff (0–100) | $[50.0, 80.0]$ | Minimum composite assessment score required for assignment. | ✅ Yes |
| `min_communication_score` | Float | Cutoff (0–100) | $[60.0, 82.0]$ | Minimum communication competency threshold. | ✅ Yes |
| `min_product_knowledge_score` | Float | Cutoff (0–100) | $[45.0, 85.0]$ | Minimum technical / product knowledge score threshold. | ✅ Yes |
| `min_sales_skill_score` | Float | Cutoff (0–100) | $[30.0, 80.0]$ | Minimum sales negotiation competency threshold. | ✅ Yes |
| `min_customer_service_score` | Float | Cutoff (0–100) | $[40.0, 80.0]$ | Minimum customer support competency threshold. | ✅ Yes |

### Task Categories
1. `Enterprise Sales`
2. `Customer Support Escalations`
3. `Technical Product Onboarding`
4. `Quality Assurance & Compliance`
5. `Account Retention & Growth`

---

## 4. Table: `synthetic_applicant_task_pairs.csv`

Each row represents an evaluated applicant–task pairing ($N = 6,000$). Contains raw feature inputs, relational match calculations, rule-based gatekeeper results, and simulation diagnostic fields.

| Column Name | Data Type | Units / Format | Allowed Values / Range | Description | Feature Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `applicant_id` | String | Identifier | `APP-XXXX` | Applicant reference ID. | ❌ Forbidden (Identifier) |
| `task_id` | String | Identifier | `TSK-XXX` | Task reference ID. | ❌ Forbidden (Identifier) |
| `task_category` | String | Categorical | 5 Categories | Task functional category. | ✅ Permitted Feature |
| `difficulty_tier` | Integer | Ordinal | $\{1, 2, 3\}$ | Task difficulty tier. | ✅ Permitted Feature |
| `difficulty_level` | String | Categorical | `Low`, `Medium`, `High` | Task difficulty tier label. | ✅ Permitted Feature |
| `applicant_relevant_exp` | Integer | Months | $[0, 180]$ | Applicant general domain experience. | ✅ Permitted Feature |
| `applicant_sales_exp` | Integer | Months | $[0, 120]$ | Applicant sales experience. | ✅ Permitted Feature |
| `applicant_cs_exp` | Integer | Months | $[0, 120]$ | Applicant customer service experience. | ✅ Permitted Feature |
| `applicant_cert_count` | Integer | Count | $[0, 5]$ | Applicant total certifications. | ✅ Permitted Feature |
| `applicant_has_sales_cert` | Binary | Flag | $\{0, 1\}$ | Applicant has sales certificate. | ✅ Permitted Feature |
| `applicant_has_cs_cert` | Binary | Flag | $\{0, 1\}$ | Applicant has CS certificate. | ✅ Permitted Feature |
| `applicant_has_tech_cert` | Binary | Flag | $\{0, 1\}$ | Applicant has technical certificate. | ✅ Permitted Feature |
| `applicant_primary_cert` | String | Categorical | Category name | Applicant's main certification domain. | ✅ Permitted Feature |
| `applicant_assessment_score` | Float | Score | $[15.0, 99.0]$ | Applicant general battery score. | ✅ Permitted Feature |
| `applicant_comm_score` | Float | Score | $[15.0, 99.0]$ | Applicant communication score. | ✅ Permitted Feature |
| `applicant_prod_score` | Float | Score | $[15.0, 99.0]$ | Applicant product knowledge score. | ✅ Permitted Feature |
| `applicant_sales_score` | Float | Score | $[15.0, 99.0]$ | Applicant sales score. | ✅ Permitted Feature |
| `applicant_cs_score` | Float | Score | $[15.0, 99.0]$ | Applicant customer support score. | ✅ Permitted Feature |
| `task_min_exp` | Integer | Months | $[3, 40]$ | Task minimum tenure requirement. | ✅ Permitted Feature |
| `task_required_cert` | String | Categorical | Credential name | Task required certification. | ✅ Permitted Feature |
| `task_min_assessment` | Float | Score | $[50.0, 80.0]$ | Task minimum assessment cutoff. | ✅ Permitted Feature |
| `task_min_comm` | Float | Score | $[60.0, 82.0]$ | Task minimum communication cutoff. | ✅ Permitted Feature |
| `task_min_prod` | Float | Score | $[45.0, 85.0]$ | Task minimum product cutoff. | ✅ Permitted Feature |
| `task_min_sales` | Float | Score | $[30.0, 80.0]$ | Task minimum sales cutoff. | ✅ Permitted Feature |
| `task_min_cs` | Float | Score | $[40.0, 80.0]$ | Task minimum customer service cutoff. | ✅ Permitted Feature |
| `task_relevant_experience_months` | Float | Months | $[0.0, 180.0]$ | Task-mapped relevant experience (e.g. sales exp for sales tasks). | ✅ Permitted Feature |
| `experience_surplus_months` | Float | Months | $[-40.0, 150.0]$ | $\text{task\_relevant\_experience} - \text{task\_min\_exp}$. | ✅ Permitted Feature |
| `assessment_gap` | Float | Points | $[-65.0, 45.0]$ | $\text{applicant\_assessment} - \text{task\_min\_assessment}$. | ✅ Permitted Feature |
| `communication_gap` | Float | Points | $[-65.0, 39.0]$ | $\text{applicant\_comm} - \text{task\_min\_comm}$. | ✅ Permitted Feature |
| `product_knowledge_gap` | Float | Points | $[-65.0, 54.0]$ | $\text{applicant\_prod} - \text{task\_min\_prod}$. | ✅ Permitted Feature |
| `sales_skill_gap` | Float | Points | $[-65.0, 69.0]$ | $\text{applicant\_sales} - \text{task\_min\_sales}$. | ✅ Permitted Feature |
| `customer_service_gap` | Float | Points | $[-65.0, 59.0]$ | $\text{applicant\_cs} - \text{task\_min\_cs}$. | ✅ Permitted Feature |
| `min_skill_margin` | Float | Points | $[-65.0, 40.0]$ | Smallest margin across all evaluated skill dimensions. | ✅ Permitted Feature |
| `weighted_skill_margin` | Float | Points | $[-55.0, 45.0]$ | Category-specific weighted skill surplus/deficit. | ✅ Permitted Feature |
| `cert_satisfied` | Binary | Flag | $\{0, 1\}$ | $1$ if task certification requirement is met or none needed. | ✅ Permitted Feature |
| `assessment_satisfied` | Binary | Flag | $\{0, 1\}$ | $1$ if all mandatory assessment thresholds are satisfied. | ✅ Permitted Feature |
| `is_eligible` | Binary | Flag | $\{0, 1\}$ | $1$ if all mandatory gatekeeper prerequisites pass, else $0$. | ❌ Excluded (Gatekeeper Target) |
| `ineligibility_reasons` | String | Semicolon-delimited | Text / `Eligible` | Detailed diagnostic audit reasons if rejected at gatekeeper. | ❌ Excluded (Audit Meta) |
| `simulation_scenario` | String | Categorical | `scenario_a`, `scenario_b` | Name of parameter configuration used to generate row. | ❌ Excluded (Simulation Meta) |
| `latent_score` | Float | Log-odds index | $[-\infty, +\infty]$ | Continuous unobserved suitability latent $z$. | ❌ Forbidden (Target Leakage) |
| `latent_success_prob` | Float | Probability | $[0.03, 0.97]$ | True generative Bernoulli probability $\sigma(z)$. | ❌ Forbidden (Target Leakage) |
| `task_success` | Binary | Indicator | $\{0, 1\}$ | **Model Target Variable.** Simulated successful task completion. | 🎯 **Target Variable** |

---

## 5. Table: `task_suitability_training.csv`

The sanitized training set filtered to strictly eligible pairs ($\text{is\_eligible} == 1$). Contains **30 input features** (27 numeric/ordinal, 3 categorical) and **1 binary target variable**.

```text
Target:
└── task_success (Binary: 1 = Success, 0 = Unsuccessful)

Permitted Input Features:
├── Categorical & Ordinal Task Metadata (3)
│   ├── task_category
│   ├── difficulty_level
│   └── difficulty_tier
├── Task Minimum Prerequisites (7)
│   ├── task_min_exp
│   ├── task_required_cert
│   ├── task_min_assessment
│   ├── task_min_comm
│   ├── task_min_prod
│   ├── task_min_sales
│   └── task_min_cs
├── Applicant Raw Capabilities (12)
│   ├── applicant_relevant_exp
│   ├── applicant_sales_exp
│   ├── applicant_cs_exp
│   ├── applicant_cert_count
│   ├── applicant_has_sales_cert
│   ├── applicant_has_cs_cert
│   ├── applicant_has_tech_cert
│   ├── applicant_primary_cert
│   ├── applicant_assessment_score
│   ├── applicant_comm_score
│   ├── applicant_prod_score
│   ├── applicant_sales_score
│   └── applicant_cs_score
└── Relational Match Features (8)
    ├── task_relevant_experience_months
    ├── experience_surplus_months
    ├── assessment_gap
    ├── communication_gap
    ├── product_knowledge_gap
    ├── sales_skill_gap
    ├── customer_service_gap
    ├── min_skill_margin
    ├── weighted_skill_margin
    ├── cert_satisfied
    └── assessment_satisfied
```

---

## 6. Leakage & Integrity Boundary Rules

1. **No Post-Completion Data:** No post-task execution metrics (e.g. customer rating, task completion duration, error count) are present in the dataset. All inputs represent state known *prior* to task dispatch.
2. **No Latent Probability Leakage:** The latent continuous score `latent_score` and probability `latent_success_prob` were strictly utilized as parameters in the Bernoulli generator and are quarantined from the training dataset.
3. **Strict Gatekeeper Decoupling:** Non-eligible candidates are recorded in `synthetic_applicant_task_pairs.csv` with explicit failure logs to audit gatekeeper fidelity, but are strictly excluded from `task_suitability_training.csv` so the performance model cannot inadvertently recommend an applicant who breached mandatory compliance standards.
