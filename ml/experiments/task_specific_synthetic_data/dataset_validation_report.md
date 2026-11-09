# VerifyMesh Task-Specific ML Dataset: Validation & Audit Report

**Audit Date:** 2026-11-01  
**Lead Auditor:** Senior Machine Learning Engineer & Research Data Scientist  
**Experiment Directory:** `ml/experiments/task_specific_synthetic_data/`  
**Execution Config:** Random Seed: `42` | Simulation Scenario: `scenario_a` (Compensatory)

---

## 1. Executive Summary

This validation audit confirms that the task-specific synthetic dataset pipeline satisfies all structural, statistical, integrity, and anti-leakage requirements. The dataset has been compiled to enable prototyping of a secondary machine-learning layer for VerifyMesh that predicts task-specific performance conditioned upon passing rule-based eligibility checks.

All automated validation tests passed without exception.

```text
=============================================================================================
AUDIT SUMMARY: 10 CHECKS CONDUCTED | 10 PASSED | 0 WARNINGS | 0 FAILURES
STATUS: PRODUCTION-READY FOR EXPERIMENTAL BENCHMARKING
=============================================================================================
```

---

## 2. Table-by-Table Volume & Cardinality Audit

| Table File | Row Count | Column Count | Primary Key / Index | Missing Values | Duplicate Rows |
| :--- | :---: | :---: | :--- | :---: | :---: |
| `synthetic_applicants.csv` | 800 | 15 | `applicant_id` | 0 | 0 |
| `synthetic_tasks.csv` | 30 | 12 | `task_id` | 0 | 0 |
| `synthetic_applicant_task_pairs.csv` | 6,000 | 41 | `(applicant_id, task_id)` | 0 | 0 |
| `task_suitability_training.csv` | 1,183 | 32 | Filtered Eligible Subset | 0 | 0 |

---

## 3. Data Integrity & Boundary Audits

### 3.1 Uniqueness & Identifiers
- **Applicant IDs:** Exactly 800 unique alphanumeric identifiers (`APP-0001` to `APP-0800`). Zero collisions.
- **Task IDs:** Exactly 30 unique identifiers (`TSK-001` to `TSK-030`). Zero collisions.
- **Applicant–Task Combinations:** Exactly 6,000 distinct pairs evaluated across the 30 tasks (200 pairs per task template). Zero duplicate pairs detected.

### 3.2 Value Range & Constraint Verification
- **Assessment Scores:** All five score dimensions (`assessment_score`, `communication_score`, `product_knowledge_score`, `sales_skill_score`, `customer_service_score`) are strictly bounded in $[15.0, 99.0]$.
  - Global Minimum Observed: $21.1$
  - Global Maximum Observed: $99.0$
  - Mean Score across applicant pool: $66.2 \pm 9.4$
- **Workplace Tenure & Consistency:**
  - All experience tenures (`relevant_experience_months`, `sales_experience_months`, `customer_service_experience_months`) are strictly non-negative integers ($\ge 0$).
  - Internally consistent tenure hierarchy confirmed: $\forall i, \text{total\_experience}_i \ge \max(\text{sales\_exp}_i, \text{cs\_exp}_i)$.
  - Max observed career tenure: 173 months (~14.4 years).

---

## 4. Eligibility Gatekeeper Audit (Stage 1 Separation)

Of the 6,000 generated application pairings, the rule-based gatekeeper filtered candidates into two distinct cohorts:

```mermaid
pie title Applicant-Task Pair Eligibility Distribution
    "Ineligible (Rule Rejection)" : 4817
    "Eligible (Admitted to Training)" : 1183
```

- **Eligible Observations:** $1,183$ pairs ($19.7\%$).
- **Ineligible Observations:** $4,817$ pairs ($80.3\%$).

### Ineligibility Root-Cause Decomposition
Ineligible pairs were audited to verify that no non-compliant candidate was admitted to the performance model. Many candidates failed on multiple concurrent dimensions:

| Ineligibility Reason Category | Occurrences in Ineligible Pairs | % of Ineligible Cohort | Example Failure Description |
| :--- | :---: | :---: | :--- |
| **Skill/Competency Deficit** | 3,574 | 74.2% | `Communication deficit below minimum (62.4 < 70.0)` |
| **Assessment Below Cutoff** | 2,677 | 55.6% | `Overall assessment below cutoff (61.2 < 75.0)` |
| **Insufficient Tenure** | 2,600 | 54.0% | `Insufficient experience (has 8m, requires 24m)` |
| **Missing Required Credential** | 2,430 | 50.4% | `Lacks required certification: Technical_Support_Architect` |

> [!NOTE]
> All 4,817 ineligible pairs have explicit, non-empty audit reason strings in `synthetic_applicant_task_pairs.csv`. None were silently dropped.

---

## 5. Training Dataset Quality & Class Balance Audit

The performance modeling dataset `task_suitability_training.csv` was verified across all training categories and difficulty tiers.

### 5.1 Outcome Class Distribution
- **Positive Outcomes (`task_success = 1`):** $786$ ($66.4\%$)
- **Negative Outcomes (`task_success = 0`):** $397$ ($33.6\%$)
- **Positive-to-Negative Ratio:** $1.98 : 1$

#### Rationale for Non-50/50 Balance
In professional labor dispatch systems, conditioning on candidates who already passed strict mandatory prerequisites (tenure minimums, verified credentials, and battery tests) naturally produces a baseline success rate above $50\%$ (here, $\approx 66\%$). Forcing an artificial 50/50 balance would distort the natural conditional probability distribution of qualified workers.

### 5.2 Representation Across Task Categories

| Task Functional Category | Eligible Pairs | Simulated Successes | Simulated Failures | Success Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Quality Assurance & Compliance** | 370 | 249 | 121 | $67.3\%$ |
| **Technical Product Onboarding** | 247 | 162 | 85 | $65.6\%$ |
| **Customer Support Escalations** | 212 | 143 | 69 | $67.5\%$ |
| **Account Retention & Growth** | 180 | 121 | 59 | $67.2\%$ |
| **Enterprise Sales** | 174 | 111 | 63 | $63.8\%$ |
| **Total** | **1,183** | **786** | **397** | **$66.4\%$** |

All five functional domains have robust sample sizes ($\ge 174$ observations per category) and consistent baseline performance rates.

### 5.3 Stratification Across Complexity Tiers

| Difficulty Tier | Qualitative Level | Eligible Count | Successes | Failures | Empirical Pass Rate |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Tier 1** | Low | 841 | 592 | 249 | $70.4\%$ |
| **Tier 2** | Medium | 298 | 174 | 124 | $58.4\%$ |
| **Tier 3** | High | 44 | 20 | 24 | $45.5\%$ |

As theoretically mandated, task difficulty exerts a strong downward pressure on success probability: Low-tier tasks exhibit a $70.4\%$ success rate, whereas High-tier tasks drop to $45.5\%$ among qualified applicants.

---

## 6. Anti-Leakage & Feature Boundary Audit

A strict feature-isolation inspection was executed against `task_suitability_training.csv`:

| Forbidden Column Name | Reason for Exclusion | Status in Training Dataset |
| :--- | :--- | :---: |
| `applicant_id` | Direct candidate identifier | ❌ Blocked (Not Present) |
| `task_id` | Direct task identifier | ❌ Blocked (Not Present) |
| `latent_score` | Generative log-odds index (Direct leakage) | ❌ Blocked (Not Present) |
| `latent_success_prob` | Generative Bernoulli probability (Direct leakage) | ❌ Blocked (Not Present) |
| `simulation_scenario` | Generative metadata | ❌ Blocked (Not Present) |
| `is_eligible` | Constant gatekeeper flag ($= 1$) | ❌ Blocked (Not Present) |
| `ineligibility_reasons` | Gatekeeper audit text | ❌ Blocked (Not Present) |

**Result:** Zero prohibited or target-derived columns are present in `task_suitability_training.csv`.

---

## 7. Deterministic Reproducibility Audit

The data generation pipeline was audited for bitwise reproducibility across independent executions:

1. Two distinct generation cycles were executed using `--seed 42 --scenario scenario_a` to temporary disjoint directories.
2. The SHA-256 cryptographic checksums of the resulting `task_suitability_training.csv` artifacts were computed:
   - Run 1 Checksum: `15e2cbbaf2be7f545081ddca63905d61ad7b9965a7686ac48a9a24e7005aec7f`
   - Run 2 Checksum: `15e2cbbaf2be7f545081ddca63905d61ad7b9965a7686ac48a9a24e7005aec7f`
3. Result: **Bitwise Identical (100% Deterministic Reproducibility)**.

---

## 8. Summary Checklist of Automated Validations

- [x] Unique applicant IDs verified ($800 / 800$).
- [x] Unique task IDs verified ($30 / 30$).
- [x] Unique applicant–task combinations verified ($6,000 / 6,000$).
- [x] Feature bounds and numerical types validated ($0 \le \text{Score} \le 100$).
- [x] Internal tenure consistency confirmed ($\text{total} \ge \text{components}$).
- [x] Missing value audit completed ($0$ null values across all tables).
- [x] Strict isolation of eligible cohort in training set confirmed ($1,183 / 1,183$).
- [x] Ineligible cohort rejections fully documented ($4,817 / 4,817$ have failure logs).
- [x] Anti-leakage protocol verified (no identifiers, latent parameters, or gatekeeper labels).
- [x] Robust class and category representation confirmed ($66.4\%$ positive, 5 categories).
- [x] Cryptographic reproducibility confirmed via SHA-256 verification.
