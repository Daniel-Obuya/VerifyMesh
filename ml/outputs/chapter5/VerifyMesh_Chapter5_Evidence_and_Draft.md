# CHAPTER 5: SYSTEM IMPLEMENTATION — MACHINE LEARNING DATASET, MODEL TRAINING, AND EVALUATION
*(Academic Evidence Blueprint and Sample Chapter 5 Text for the VerifyMesh Capstone Report)*

> **Document Purpose and Scope:**  
> This document provides a complete, publication-ready academic guide and sample text for **Chapter 5 (Sections 5.1 and 5.2)** of the VerifyMesh final-year Computer Science capstone report. Every statistic, parameter, and evaluation metric reported in this document is derived directly from the completed Phase 0–3 repository artifacts (`ml/experiments/`, `ml/models/`, `ml/metadata/`, `src/stage2_feature_engineering.py`, and `ml/outputs/chapter5/`). Sections 5.3–5.5 at the end of this document provide the **Figure and Table Recommendation Checklist**, the **Draft Discrepancy Reconciliation Table**, and the **Artifact Traceability & Missing Export Audit**.

---

## 5.1 Dataset Description

### 5.1.1 Purpose of the Dataset and Rationale for Controlled Synthetic Data Generation

The machine learning component of VerifyMesh is designed to address a specific operational challenge in workforce credential verification and task allocation: distinguishing between candidates who merely satisfy minimum mandatory qualifications and candidates who possess the competency profile required to execute a specific task successfully. In the VerifyMesh two-stage architecture, **Stage 1** acts as an authoritative, deterministic gatekeeper that verifies hard requirements—such as mandatory certifications, minimum relevant work experience, and baseline competency thresholds. However, among candidates who pass Stage 1, substantial variation remains in domain-specific skill surpluses, secondary skill bottlenecks, and task complexity. **Stage 2** therefore introduces an advisory machine learning model that estimates the probability of simulated task execution success for Stage 1-eligible applicant–task pairs.

Developing and benchmarking a task-specific suitability model requires granular records linking individual applicant competency assessments, verified certifications, and domain tenure to task-level requirement specifications and post-allocation execution outcomes. In real-world enterprise environments, such longitudinal workforce performance records are proprietary, subject to strict employment data protection regulations, and unavailable as public benchmark datasets for academic distribution. Furthermore, early exploratory work in the project revealed that predicting a single global "general eligibility" label independent of the target task conflated deterministic rule checking with performance forecasting. Consequently, a controlled parametric synthetic dataset generator (`ml/experiments/task_specific_synthetic_data/generate_synthetic_dataset.py`) was engineered to simulate realistic applicant profiles, multi-category enterprise tasks, deterministic Stage 1 gatekeeping, and noisy Bernoulli task execution outcomes (`task_success`). Using a controlled synthetic data-generating process enables rigorous evaluation of model generalisation, probability calibration, and feature parsimony against a known theoretical performance ceiling (`Oracle_Latent_Prob`), while ensuring full reproducibility via fixed pseudorandom seeds (`seed = 42`). Throughout this chapter, all target outcomes (`task_success`) are explicitly interpreted as **simulated task execution outcomes** rather than empirical real-world workforce measurements.

### 5.1.2 Dataset Generation Methodology and Multi-Entity Structure

The synthetic data pipeline models workforce allocation as a relational interaction between two primary entities—**applicants** and **tasks**—which are paired and evaluated through a two-stage simulation pipeline. Rather than generating independent, unstructured feature rows, the generator first constructs a population of synthetic applicants (`synthetic_applicants.csv`) and a catalog of operational tasks (`synthetic_tasks.csv`), and then samples multiple candidate–task assignments per applicant (`synthetic_applicant_task_pairs.csv`).

#### Applicant Dataset (`synthetic_applicants.csv`)
Each applicant record represents a candidate whose credentials and competency assessments have been captured on the VerifyMesh platform. An applicant profile comprises fifteen attributes covering three dimensions:
1. **Work Experience Tenure:** Total work experience (`total_experience_months`) and domain-relevant experience (`relevant_experience_months`, `sales_experience_months`, and `customer_service_experience_months`), generated from right-skewed distributions reflecting realistic workforce tenure.
2. **Verified Certifications:** Binary indicators for domain certifications (`has_sales_cert`, `has_cs_cert`, `has_technical_cert`), total certification count (`certification_count`), and the candidate's primary held credential (`primary_certification`, taking values `"Sales_Specialist"`, `"Customer_Success_Pro"`, `"Technical_Support_Architect"`, or `"None"`).
3. **Competency Assessment Scores:** Five continuous assessment scores bounded on the $[0, 100]$ scale: overall assessment (`assessment_score`), communication (`communication_score`), product knowledge (`product_knowledge_score`), sales skill (`sales_skill_score`), and customer service skill (`customer_service_score`). To reflect realistic human skill profiles, applicant competencies are generated around a latent general ability factor combined with domain-specific variations rather than independent uniform noise.

Table 5.1A illustrates five representative applicant profiles extracted directly from the Scenario B applicant dataset (`ml/outputs/chapter5/table_5_1a_sample_applicants.csv`), omitting internal database identifiers (`applicant_id`) for clarity.

**Table 5.1A: Sample Synthetic Applicant Records (`synthetic_applicants.csv`, Scenario B)**  
*(Source: `ml/outputs/chapter5/table_5_1a_sample_applicants.csv`)*

| Relevant Exp (Months) | Total Exp (Months) | Cert Count | Primary Certification | Assessment Score | Communication | Product Knowledge | Sales Skill | Customer Service |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 13 | 15 | 0 | `None` | 65.1 | 80.9 | 60.0 | 67.1 | 44.9 |
| 32 | 36 | 0 | `None` | 75.9 | 87.3 | 74.6 | 67.1 | 74.5 |
| 47 | 55 | 0 | `None` | 71.9 | 60.4 | 56.6 | 47.3 | 59.5 |
| 26 | 33 | 0 | `None` | 79.8 | 81.9 | 63.0 | 60.1 | 77.3 |
| 15 | 17 | 1 | `Technical_Support_Architect` | 68.4 | 70.2 | 72.1 | 72.5 | 54.9 |

The distribution of competency scores across all $3,200$ synthetic applicants in Scenario B is visualised in **Figure 5.1** (`ml/outputs/chapter5/figure_5_1_applicant_dataset.png`). As shown in the violin distributions, applicant scores across all five competency dimensions are centred between $66$ and $72$ points with standard deviations of approximately $11\text{–}13$ points, providing realistic spread across foundational, intermediate, and specialist skill levels.

#### Task Dataset (`synthetic_tasks.csv`)
The platform task catalog consists of $30$ distinct operational tasks distributed evenly across five workforce categories ($6$ tasks per category): *Enterprise Sales*, *Customer Support Escalations*, *Technical Product Onboarding*, *Quality Assurance & Compliance*, and *Account Retention & Growth*. Each task specifies twelve attributes defining its operational domain, complexity (`difficulty_level` $\in \{\text{Low}, \text{Medium}, \text{High}\}$, mapped to ordinal `difficulty_tier` $\in \{1, 2, 3\}$), minimum required relevant experience (`min_relevant_experience_months`), mandatory certification (`required_certification`), and minimum required scores across all five competency dimensions. Furthermore, each task category is governed by a domain-specific competency weight vector $(w_{\text{comm}}, w_{\text{prod}}, w_{\text{sales}}, w_{\text{cs}})$ summing to $1.0$ in `CATEGORY_DOMAINS` (for example, *Enterprise Sales* weights sales skill at $0.50$ and communication at $0.25$, whereas *Technical Product Onboarding* weights product knowledge at $0.50$). Table 5.1B displays five representative task definitions—one from each category—extracted from `synthetic_tasks.csv`.

**Table 5.1B: Sample Synthetic Task Records Across the Five Operational Categories (`synthetic_tasks.csv`)**  
*(Source: `ml/outputs/chapter5/table_5_1b_sample_tasks.csv`)*

| Task Title | Task Category | Difficulty Level | Difficulty Tier | Min Exp (Months) | Required Certification | Min Assessment | Min Comm | Min Product | Min Sales | Min CS |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| B2B SaaS Mid-Market Pipeline Prospecting | Enterprise Sales | Medium | 2 | 12 | `Sales_Specialist` | 65.0 | 70.0 | 60.0 | 70.0 | 50.0 |
| Tier-1 Multi-Channel Helpdesk Support | Customer Support Escalations | Low | 1 | 3 | `None` | 50.0 | 65.0 | 45.0 | 40.0 | 65.0 |
| Developer API & Webhook Integration Guidance | Technical Product Onboarding | High | 3 | 30 | `Technical_Support_Architect` | 78.0 | 70.0 | 82.0 | 40.0 | 50.0 |
| Call Recording QA & Scorecard Auditing | Quality Assurance & Compliance | Low | 1 | 6 | `None` | 60.0 | 65.0 | 55.0 | 40.0 | 60.0 |
| At-Risk Client Churn Intervention & Save | Account Retention & Growth | High | 3 | 24 | `Customer_Success_Pro` | 72.0 | 80.0 | 65.0 | 70.0 | 75.0 |

#### Applicant–Task Pair Dataset (`synthetic_applicant_task_pairs.csv`)
To simulate candidate evaluation across multiple tasks, each applicant is paired with a random subset of tasks (averaging $7.5$ tasks per applicant), producing the full evaluation dataset (`synthetic_applicant_task_pairs.csv`, containing $42$ columns). For every pair, the generator computes the raw skill gaps ($\text{applicant\_score}_k - \text{task\_min\_score}_k$), experience surplus (`experience_surplus_months`), Stage 1 eligibility status (`is_eligible`), diagnostic ineligibility reasons (`ineligibility_reasons`), unobserved simulation logits (`latent_score` and `latent_success_prob`), and the binary simulated execution outcome (`task_success`). Table 5.1C presents five representative applicant–task evaluation records, showing three Stage 1-eligible pairs and two Stage 1-ineligible pairs alongside their engineered interaction features.

**Table 5.1C: Sample Applicant–Task Evaluation Records (`synthetic_applicant_task_pairs.csv`, Scenario B)**  
*(Source: `ml/outputs/chapter5/table_5_1c_sample_applicant_task_pairs.csv`)*

| Task Category | Difficulty | Difficulty Tier | Cert Satisfied | Exp Surplus (Mo) | `exp_surplus_tanh` | `weighted_skill_margin` | `min_skill_margin` | `weakest_link_deficit` | Stage 1 Eligibility | Simulated Outcome |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Enterprise Sales | Medium | 2 | 1 | 40.0 | 0.997 | 8.77 | -4.4 | -4.4 | Eligible (Pass) | Successful (1) |
| Enterprise Sales | Medium | 2 | 1 | 4.0 | 0.322 | 6.67 | -0.6 | -0.6 | Eligible (Pass) | Successful (1) |
| Enterprise Sales | Medium | 2 | 1 | 4.0 | 0.322 | 1.37 | -3.8 | -3.8 | Eligible (Pass) | Unsuccessful (0) |
| Enterprise Sales | Medium | 2 | 0 | -8.0 | -0.583 | 1.02 | -5.1 | -5.1 | Ineligible (Fail) | Unsuccessful (0) |
| Enterprise Sales | Medium | 2 | 0 | -3.0 | -0.245 | -10.02 | -13.8 | -13.8 | Ineligible (Fail) | Unsuccessful (0) |

### 5.1.3 Simulation Regimes: Scenario A versus Scenario B

To evaluate how model families respond to sample scale and competency bottleneck dynamics, `generate_synthetic_dataset.py` supports two distinct parametric simulation regimes:

1. **Scenario A — Balanced Compensatory Regime (`ml/experiments/task_specific_synthetic_data/`):**  
   Generated with $800$ applicants and $30$ tasks ($6,000$ total pairs, yielding $N = 1,183$ Stage 1-eligible records across $503$ unique applicants and $29$ of $30$ tasks). In Scenario A, task suitability follows a predominantly linear compensatory structure where high scores in one competency can largely offset moderate deficits in another. Because Stage 1 already filters out gross mismatches and Gaussian logistic noise ($\sigma = 0.45$) is added before Bernoulli sampling, the latent success probabilities in Scenario A are tightly compressed around the mean of $0.6644$ (interquartile range $\text{IQR} = 0.172$), resulting in a low theoretical Oracle ROC-AUC ceiling of $0.6503 \pm 0.0285$. Furthermore, one extreme-requirement task (`T0026`) had zero eligible candidates in Scenario A.
2. **Scenario B — Strict Bottleneck / Weakest-Link Regime (`ml/experiments/stage2_refinement/scenario_b_data/`):**  
   Generated using the same generator script with `--scenario scenario_b --num-applicants 3200 --pairs-per-applicant 8 --seed 42` ($3,200$ applicants, $30$ tasks, $24,000$ total pairs, yielding $N = 4,675$ Stage 1-eligible records across $1,924$ unique applicants and all $30 / 30$ tasks). Scenario B introduces a realistic **non-compensatory weakest-link penalty**: when an eligible candidate exhibits a negative sub-skill margin ($g_{\min} = \text{min\_skill\_margin} < 0$), a steep deficit penalty ($-0.18 \cdot |g_{\min}|$, plus an additional $-0.85$ step penalty if $g_{\min} < -2.0$) is applied to the latent logit, and $50\%$ of the positive weighted-margin bonus is suppressed so excess strength in secondary skills cannot mask a deficiency in a required competency. Task difficulty also exerts a steeper non-linear penalty ($-0.22 \cdot (\text{difficulty\_tier} - 1)^{1.3}$).

**Methodological Note on Scenario B:** Because Scenario B modifies both the sample size ($4,675$ vs. $1,183$ eligible records) and the underlying data-generating formula (widening the latent probability $\text{IQR}$ from $0.172$ to $0.312$ and raising the theoretical Oracle ROC-AUC ceiling from $0.6503$ to $0.7427$), higher discrimination metrics observed on Scenario B reflect a stronger synthetic signal-to-noise ratio and reduced estimation variance, rather than an intrinsic change in real-world predictive accuracy.

### 5.1.4 Deterministic Stage 1 Eligibility Filtering and Target Variable Formulation

Before any record reaches Stage 2, it must pass the deterministic Stage 1 gatekeeper implemented in `generate_synthetic_dataset.py` (lines 345–355). A candidate–task pair is marked eligible (`is_eligible == 1`) if and only if all five mandatory conditions hold simultaneously:
1. **Certification Compliance:** `cert_satisfied == 1` (the applicant holds the task's required certification, or the task requires `"None"`).
2. **Minimum Relevant Experience:** `experience_surplus_months >= 0` ($\text{task\_relevant\_experience\_months} \ge \text{task\_min\_exp}$).
3. **Overall Assessment Floor:** `assessment_gap >= 0` ($\text{applicant\_assessment\_score} \ge \text{task\_min\_assessment}$).
4. **Foundational Competency Floors:** `communication_gap >= -5.0` and `product_knowledge_gap >= -5.0`.
5. **Domain-Specific Competency Floors:** `sales_skill_gap >= -3.0` for *Enterprise Sales* tasks, and `customer_service_gap >= -3.0` for *Customer Support Escalations* tasks.

As shown in **Figure 5.2** (`figure_5_2_task_distribution.png`) and **Figure 5.3** (`figure_5_3_eligibility_distribution.png`), Stage 1 rejects $80.28\%$ ($4,817 / 6,000$) of initial pairs in Scenario A and $80.52\%$ ($19,325 / 24,000$) of initial pairs in Scenario B, primarily due to missing specialist certifications ($\sim 54.8\%$ of all pairs) and insufficient assessment or competency scores. Only pairs satisfying `is_eligible == 1` are exported to `task_suitability_training.csv` ($35$ columns: $34$ observable candidate, task, and interaction attributes plus the binary target variable `task_success` $\in \{0, 1\}$). Unobserved simulation variables (`applicant_id`, `task_id`, `latent_score`, `latent_success_prob`, `is_eligible`, `ineligibility_reasons`, and `simulation_scenario`) are stripped from `task_suitability_training.csv` so they can never be used as model predictors.

Within the final Scenario B Stage 2 modelling cohort ($N = 4,675$), the binary target variable `task_success` comprises $2,927$ successful task executions ($62.61\%$) and $1,748$ unsuccessful executions ($37.39\%$), as depicted in **Figure 5.4** (`figure_5_4_task_success_distribution.png`). Table 5.1 summarises the complete structural statistics of both Scenario A and Scenario B calculated directly from the repository CSV files (`ml/outputs/chapter5/table_5_1_scenario_a_vs_b_statistics.csv`).

**Table 5.1: Dataset Characteristics and Summary Statistics — Scenario A versus Scenario B**  
*(Source: `ml/outputs/chapter5/table_5_1_scenario_a_vs_b_statistics.csv`)*

| Dataset Metric | Scenario A (`Balanced Compensatory`) | Scenario B (`Strict Bottleneck` — Final Dataset) |
| :--- | :---: | :---: |
| **Number of applicants (`synthetic_applicants.csv`)** | $800$ | $3,200$ |
| **Number of tasks (`synthetic_tasks.csv`)** | $30$ | $30$ |
| **Number of task categories** | $5$ | $5$ |
| **Number of difficulty tiers (`Low=1, Medium=2, High=3`)** | $3$ | $3$ |
| **Number of initial applicant–task pairs (`synthetic_applicant_task_pairs.csv`)** | $6,000$ | $24,000$ |
| **Number of eligible applicant–task pairs (`is_eligible == 1`, Stage 2 cohort)** | $1,183$ ($19.72\%$) | $4,675$ ($19.48\%$) |
| **Number of ineligible pairs (`is_eligible == 0`, rejected at Stage 1)** | $4,817$ ($80.28\%$) | $19,325$ ($80.52\%$) |
| **Number of unique eligible applicants** | $503 / 800$ ($62.88\%$) | $1,924 / 3,200$ ($60.12\%$) |
| **Number of eligible tasks represented** | $29 / 30$ ($96.7\%$, `T0026` missing) | $30 / 30$ ($100.0\%$) |
| **Number of successful outcomes (`task_success == 1`, Eligible Cohort)** | $786$ | $2,927$ |
| **Number of unsuccessful outcomes (`task_success == 0`, Eligible Cohort)** | $397$ | $1,748$ |
| **Positive class percentage (`task_success == 1`, Eligible Cohort)** | $66.44\%$ | $62.61\%$ |
| **Negative class percentage (`task_success == 0`, Eligible Cohort)** | $33.56\%$ | $37.39\%$ |
| **Theoretical Oracle ROC-AUC Ceiling (`5 seeds × 5 folds`)** | $0.6503 \pm 0.0285$ | $0.7427 \pm 0.0137$ |

### 5.1.5 Domain-Grounded Feature Engineering (`src/stage2_feature_engineering.py`)

A central finding of the Phase 0–1 investigation was that feeding all $28$ raw applicant, task, and gap columns into high-capacity tree ensembles caused severe overfitting to collinear sub-features while obscuring domain relationships. Because task suitability depends on how an applicant's competencies align with a specific task's requirements rather than raw isolated scores, a shared feature engineering module (`src/stage2_feature_engineering.py`) was implemented to transform raw candidate–task attributes into five compact, domain-grounded features used identically during training and live inference. Table 5.2 defines the final five input features, their exact mathematical formulation in `src/stage2_feature_engineering.py`, and their operational relevance.

**Table 5.2: Description and Mathematical Formulation of the Final Five Stage 2 Input Features**  
*(Source: `src/stage2_feature_engineering.py` and `ml/experiments/stage2_refinement/phase3_final_audit_results.json`)*

| Feature Name | Mathematical Definition / Calculation | Scenario B Mean $\pm$ SD | Operational Interpretation | Relevance to Task Suitability |
| :--- | :--- | :---: | :--- | :--- |
| **`weighted_skill_margin`** | $\sum_{k \in \{\text{comm, prod, sales, cs}\}} w_{c,k} \cdot (\text{app\_score}_k - \text{task\_min}_k)$ | $11.81 \pm 6.51$ | Category-weighted competency surplus above task minimums using `CATEGORY_WEIGHTS` for task category $c$. | Captures overall alignment with the specific competency priorities of the task domain. |
| **`min_skill_margin`** | $\min_{k \in \{\text{comm, prod, sales, cs, assess}\}} (\text{app\_score}_k - \text{task\_min}_k)$ | $2.33 \pm 7.06$ | Smallest individual margin across all five competency dimensions ($g_{\min}$). | Identifies the candidate's weakest required competency dimension relative to the task. |
| **`weakest_link_deficit`** | $\min(0.0,\; \text{min\_skill\_margin})$ | $-1.61 \pm 3.47$ | Non-positive bottleneck hinge ($\le 0$); equals $0.0$ when all skills meet or exceed task targets, and equals the negative deficit otherwise. | Enables a linear model to apply a steeper piecewise risk penalty when a candidate falls below a sub-skill target ($1,716$ of $4,675$ eligible pairs have $g_{\min} < 0$). |
| **`exp_surplus_tanh`** | $\tanh\!\left(\frac{\text{task\_relevant\_exp} - \text{task\_min\_exp}}{12.0}\right)$ | $0.73 \pm 0.30$ | Hyperbolic tangent transformation of relevant experience surplus (scaled by $12$ months). | Captures diminishing marginal returns of excess tenure beyond $18\text{–}24$ months above the minimum requirement. |
| **`difficulty_tier`** | $\text{Low} \mapsto 1.0,\; \text{Medium} \mapsto 2.0,\; \text{High} \mapsto 3.0$ | $1.31 \pm 0.52$ | Ordinal encoding of intrinsic task complexity. | Accounts for the higher baseline execution difficulty and lower empirical success rate of complex tasks. |

#### Audit and Removal of the Constant `cert_satisfied` Feature
In the initial Phase 1–3 extended feature set (`STAGE2_V2_FEATURES`), a sixth feature—`cert_satisfied`—was included alongside the five features in Table 5.2. However, the Phase 3 Final Audit (`ml/experiments/stage2_refinement/run_phase3_final_audit.py`) verified that because Stage 1 deterministically rejects any candidate with `cert_satisfied == 0`, the column `cert_satisfied` is **strictly constant at $1.0$** ($\min = 1.0$, $\max = 1.0$, $\text{std} = 0.0$) across all $1,183$ Stage 1-eligible records in Scenario A and all $4,675$ Stage 1-eligible records in Scenario B. When passed through `StandardScaler`, a constant column is centred to $0.0$ for every observation, and L2 regularisation assigns it a standardized coefficient of exactly **$0.000000$**. Removing `cert_satisfied` to form the five-feature specification (`LR_5Feat_NoCert`) produces identical out-of-fold ROC-AUC ($0.677223$), Brier score ($0.210984$), log-loss ($0.610981$), and Expected Calibration Error ($0.029760$), with a maximum absolute probability difference across all $23,375$ out-of-fold evaluations of $3.33 \times 10^{-16}$ (IEEE-754 floating-point machine epsilon).

---

## 5.2 Model Training and Evaluation

### 5.2.1 Model Components

#### Problem Formulation and Two-Stage Decision Boundary
Within VerifyMesh, candidate evaluation is formulated as a sequential two-stage architecture rather than a single monolithic classifier:
1. **Stage 1 (Deterministic Gatekeeper):** Evaluates hard eligibility constraints $G(\mathbf{x}_{\text{raw}}) \in \{0, 1\}$. If $G(\mathbf{x}_{\text{raw}}) = 0$, the candidate is deterministically classified as *Ineligible* and blocked from Stage 2 scoring.
2. **Stage 2 (Probabilistic Task-Suitability Estimator):** Conditioned strictly on $G(\mathbf{x}_{\text{raw}}) = 1$, Stage 2 estimates the conditional probability $P(Y = 1 \mid \mathbf{x}, G=1)$, where $Y = \text{task\_success} \in \{0, 1\}$ denotes simulated task execution success and $\mathbf{x} \in \mathbb{R}^5$ denotes the five engineered suitability features defined in Table 5.2. Crucially, Stage 2 outputs an **advisory probability and suitability tier** to assist human administrators in ranking eligible candidates; the administrator retains final authority over task allocation.

#### Applicant-Grouped Cross-Validation Protocol
Because individual applicants are evaluated against multiple tasks in the dataset (averaging $2.35$ eligible tasks per applicant in Scenario A and $2.43$ eligible tasks per applicant in Scenario B), standard row-level random splitting (`train_test_split` or ungrouped `StratifiedKFold`) leaks applicant-specific attributes across training and test partitions. During the Phase 0 audit of the preliminary Google Colab notebook, it was discovered that because `task_suitability_training.csv` excludes `applicant_id`, the preliminary notebook had synthesized sequential per-row identifiers (`applicant_0 .. applicant_1126`), which caused `GroupShuffleSplit` to degenerate into an ungrouped $80:20$ row split and leaked the same real applicants across training and test sets.

To eliminate applicant leakage, Phases 1–3 enforced **repeated applicant-grouped stratified cross-validation**:
- **Outer Evaluation Protocol:** Five-fold `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)` grouped strictly by the true `applicant_id` from `synthetic_applicant_task_pairs.csv`, repeated across **five independent random seeds** (`[42, 123, 456, 789, 2026]`), yielding **$25$ outer evaluation folds** ($23,375$ held-out evaluations on Scenario B; $5,915$ on Scenario A). Programmatic verification confirmed **zero `applicant_id` overlap** ($\max |\text{Train}_{\text{app}} \cap \text{Val}_{\text{app}}| = 0$) across all $25$ outer splits.
- **Nested Inner Cross-Validation for Threshold Selection:** Within each outer training fold, a nested `StratifiedGroupKFold` grouped by `applicant_id` generated out-of-fold training predictions to select classification thresholds and evaluate post-hoc calibration wrappers without ever consulting outer test labels.

#### Candidate Algorithm Comparison (Phases 1 and 2)
Across Phases 1 and 2 (`run_phase1_benchmark.py` and `run_phase2_scenario_comparison.py`), ten model configurations were benchmarked across both Scenario A ($N = 1,183$) and Scenario B ($N = 4,675$):
- **Non-Learned Reference Bounds:** `Baseline_Majority_Class` (predicts the majority positive class; $\text{ROC-AUC} = 0.5000$) and `Oracle_Latent_Prob` (evaluates the unobserved true simulation probability `latent_success_prob`; non-deployable theoretical upper bound).
- **Domain-Engineered Linear Models:** `Compact_LR_4Feat` ($4$ features), `Compact_LR_4Feat_Balanced` (`class_weight='balanced'`), `Extended_LR_6Feat_WeakestLink` ($5$ active features + constant `cert_satisfied`, mathematically identical to `LR_5Feat_NoCert`), and `Extended_LR_10Feat_DomainGaps` ($10$ features).
- **Regularised and Historical Tree Ensembles:** `Regularized_RF_10Feat`, `Regularized_GB_10Feat`, `Regularized_HistGB_10Feat`, `Regularized_RF_28Feat`, and the historical `Current_RF_28Feat` ($28$ features, `n_estimators=200, max_depth=8, min_samples_leaf=10`).

Table 5.3A and Table 5.3B present the complete 25-fold cross-validation results from Phase 1 (`phase1_benchmark_summary.csv`) and Phase 2 (`phase2_scenario_comparison_summary.csv`).

**Table 5.3A: Phase 1 Candidate Model Benchmark on Scenario A (`N = 1,183`, 5 Seeds $\times$ 5 Outer Applicant-Grouped Folds)**  
*(Source: `ml/experiments/stage2_refinement/phase1_benchmark_summary.csv`, `threshold_policy = inner_macro_f1` unless noted)*

| Model / Reference | Active Features | Mean Threshold | ROC-AUC (Mean $\pm$ SD) | Brier Score (Mean $\pm$ SD) | Accuracy (Mean $\pm$ SD) | Balanced Acc (Mean $\pm$ SD) | Positive Precision | Positive Recall | Failure Recall (Class 0) | Macro F1 (Mean $\pm$ SD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| *`Oracle_Latent_Prob` (Theoretical Ceiling)* | *Latent* | $0.643$ | $0.6503 \pm 0.0285$ | $0.2095 \pm 0.0061$ | $62.42\% \pm 3.32\%$ | $58.73\% \pm 2.78\%$ | $72.59\%$ | $69.95\%$ | $47.51\%$ | $0.5839 \pm 0.0283$ |
| **`Compact_LR_4Feat`** | **4** | $0.631$ | **$0.6116 \pm 0.0284$** | **$0.2151 \pm 0.0042$** | $62.10\% \pm 2.80\%$ | $56.58\% \pm 2.32\%$ | $70.73\%$ | $73.39\%$ | $39.76\%$ | $0.5646 \pm 0.0248$ |
| **`Extended_LR_6Feat_WeakestLink` (`LR_5Feat`)** | **5** *(+1 const)* | $0.632$ | **$0.6095 \pm 0.0320$** | **$0.2154 \pm 0.0049$** | **$62.94\% \pm 2.65\%$** | **$57.17\% \pm 2.58\%$** | **$71.07\%$** | **$74.73\%$** | **$39.62\%$** | **$0.5713 \pm 0.0267$** |
| `Extended_LR_10Feat_DomainGaps` | 10 | $0.629$ | $0.5960 \pm 0.0313$ | $0.2172 \pm 0.0047$ | $61.13\% \pm 3.37\%$ | $55.26\% \pm 2.31\%$ | $69.83\%$ | $73.13\%$ | $37.39\%$ | $0.5507 \pm 0.0240$ |
| `Regularized_RF_28Feat` | 28 | $0.636$ | $0.5933 \pm 0.0320$ | $0.2173 \pm 0.0033$ | $62.81\% \pm 3.28\%$ | $56.12\% \pm 2.77\%$ | $70.34\%$ | $76.47\%$ | $35.77\%$ | $0.5578 \pm 0.0278$ |
| `Current_RF_28Feat` (Historical RF, inner CV) | 28 | $0.563$ | $0.5878 \pm 0.0297$ | $0.2238 \pm 0.0038$ | $61.46\% \pm 3.15\%$ | $55.86\% \pm 2.77\%$ | $70.37\%$ | $72.89\%$ | $38.83\%$ | $0.5553 \pm 0.0266$ |
| `Current_RF_28Feat` (Historical RF @ fixed $0.61$) | 28 | $0.610$ | $0.5878 \pm 0.0297$ | $0.2238 \pm 0.0038$ | $52.73\% \pm 2.79\%$ | $55.14\% \pm 2.60\%$ | $71.74\%$ | $47.81\%$ | $62.47\%$ | $0.5204 \pm 0.0256$ |
| `Regularized_GB_10Feat` | 10 | $0.640$ | $0.5815 \pm 0.0348$ | $0.2195 \pm 0.0036$ | $61.60\% \pm 3.23\%$ | $55.59\% \pm 2.87\%$ | $70.12\%$ | $73.89\%$ | $37.29\%$ | $0.5531 \pm 0.0273$ |
| `Regularized_RF_10Feat` | 10 | $0.637$ | $0.5749 \pm 0.0347$ | $0.2203 \pm 0.0039$ | $60.69\% \pm 3.19\%$ | $54.45\% \pm 2.96\%$ | $69.29\%$ | $73.46\%$ | $35.44\%$ | $0.5429 \pm 0.0302$ |
| `Regularized_HistGB_10Feat` | 10 | $0.640$ | $0.5698 \pm 0.0345$ | $0.2207 \pm 0.0040$ | $59.21\% \pm 4.33\%$ | $53.65\% \pm 2.60\%$ | $69.14\%$ | $70.57\%$ | $36.73\%$ | $0.5284 \pm 0.0250$ |
| *`Baseline_Majority_Class` (@ fixed $0.50$)* | *0* | $0.500$ | $0.5000 \pm 0.0000$ | $0.2230 \pm 0.0005$ | $66.44\% \pm 0.16\%$ | $50.00\% \pm 0.00\%$ | $66.44\%$ | $100.00\%$ | $0.00\%$ | $0.3992 \pm 0.0006$ |

**Table 5.3B: Phase 2 Scenario A ($N = 1,183$) versus Scenario B ($N = 4,675$) Model Comparison (25 Outer Folds)**  
*(Source: `ml/experiments/stage2_refinement/phase2_scenario_comparison_summary.csv`, `threshold_policy = inner_macro_f1`)*

| Model / Reference | Active Features | Scenario A ROC-AUC | Scenario B ROC-AUC | $\Delta$ ROC-AUC ($\text{B} - \text{A}$) | Scenario A Brier | Scenario B Brier | Scenario A Bal Acc | Scenario B Bal Acc | Scenario B Macro F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| *`Oracle_Latent_Prob` (Non-Deployable Ceiling)* | *Latent* | $0.6503 \pm 0.0285$ | $0.7427 \pm 0.0137$ | $+0.0924$ | $0.2095$ | $0.1927$ | $58.73\%$ | $66.83\%$ | $0.6682 \pm 0.0141$ |
| `Extended_LR_10Feat_DomainGaps` | 9 *(+1 const)* | $0.5960 \pm 0.0313$ | $0.6782 \pm 0.0187$ | $+0.0822$ | $0.2172$ | $0.2111$ | $55.26\%$ | $62.66\%$ | $0.6250 \pm 0.0151$ |
| **`Extended_LR_6Feat_WeakestLink` (`LR_5Feat`)** | **5** *(+1 const)* | **$0.6095 \pm 0.0320$** | **$0.6772 \pm 0.0203$** | **$+0.0678$** | **$0.2154$** | **$0.2110$** | **$57.17\%$** | **$62.61\%$** | **$0.6262 \pm 0.0170$** |
| `Regularized_RF_10Feat` | 10 | $0.5749 \pm 0.0347$ | $0.6724 \pm 0.0181$ | $+0.0974$ | $0.2203$ | $0.2135$ | $54.45\%$ | $62.33\%$ | $0.6236 \pm 0.0144$ |
| `Regularized_GB_10Feat` | 10 | $0.5815 \pm 0.0348$ | $0.6717 \pm 0.0197$ | $+0.0902$ | $0.2195$ | $0.2143$ | $55.59\%$ | $62.54\%$ | $0.6252 \pm 0.0125$ |
| `Regularized_HistGB_10Feat` | 10 | $0.5698 \pm 0.0345$ | $0.6695 \pm 0.0194$ | $+0.0997$ | $0.2207$ | $0.2143$ | $53.65\%$ | $62.35\%$ | $0.6238 \pm 0.0141$ |
| `Compact_LR_4Feat` | 4 | $0.6116 \pm 0.0284$ | $0.6656 \pm 0.0205$ | $+0.0540$ | $0.2151$ | $0.2145$ | $56.58\%$ | $61.98\%$ | $0.6212 \pm 0.0187$ |
| `Current_RF_28Feat` (Historical 28-Feat RF) | 28 | $0.5878 \pm 0.0297$ | $0.6645 \pm 0.0191$ | $+0.0768$ | $0.2238$ | $0.2224$ | $55.86\%$ | $62.23\%$ | $0.6229 \pm 0.0174$ |
| `Regularized_RF_28Feat` | 28 | $0.5933 \pm 0.0320$ | $0.6641 \pm 0.0192$ | $+0.0709$ | $0.2173$ | $0.2159$ | $56.12\%$ | $61.95\%$ | $0.6202 \pm 0.0165$ |
| *`Baseline_Majority_Class` (@ fixed $0.50$)* | *0* | $0.5000 \pm 0.0000$ | $0.5000 \pm 0.0000$ | $0.0000$ | $0.2230$ | $0.2341$ | $50.00\%$ | $50.00\%$ | $0.3850 \pm 0.0003$ |

Three pivotal conclusions emerge from Tables 5.3A and 5.3B:
1. **Superior Generalisation of Compact Linear Models over 28-Feature Tree Ensembles:** On Scenario A, the historical 28-feature Random Forest (`Current_RF_28Feat`) exhibited a severe train–validation ROC-AUC overfitting gap of $+0.1939$ (`phase1_benchmark_results.json`) and achieved an out-of-fold ROC-AUC of only $0.5878 \pm 0.0297$. In contrast, `Extended_LR_6Feat_WeakestLink` (`LR_5Feat_NoCert`) reduced the train–validation gap to $+0.0063$ on Scenario A and $+0.0020$ on Scenario B, outperforming `Current_RF_28Feat` by **$+2.17$ ROC-AUC points on Scenario A** ($0.6095$ vs. $0.5878$) and **$+1.27$ ROC-AUC points on Scenario B** ($0.6772$ vs. $0.6645$), while also achieving the lowest Brier score ($0.2110$ vs. $0.2224$).
2. **Value of the Piecewise Bottleneck Hinge (`weakest_link_deficit`):** On Scenario B, adding `weakest_link_deficit = min(0.0, min_skill_margin)` to the four base features (`Compact_LR_4Feat`) increased out-of-fold ROC-AUC from $0.6656$ to **$0.6772$** ($+1.16$ points) and reduced Brier error from $0.2145$ to $0.2110$, confirming that the piecewise hinge captures non-compensatory bottleneck risk effectively.
3. **Feature Parsimony (`5` Features vs. `10` Features):** Adding four extra category-specific raw gap columns in `Extended_LR_10Feat_DomainGaps` degraded Scenario A ROC-AUC by $-1.35$ points ($0.5960$ vs. $0.6095$) and yielded a negligible $+0.0010$ difference on Scenario B ($0.6782$ vs. $0.6772$) with lower Macro F1 ($0.6250$ vs. $0.6262$). Consequently, the five-feature specification was selected as the optimal parsimonious architecture, capturing **$91.2\%$ of the theoretical noiseless Oracle ROC-AUC ceiling** ($0.6772 / 0.7427$) on Scenario B.

#### Mathematical Formulation of StandardScaler and L2-Regularised Logistic Regression
In the selected pipeline (`VerifyMesh_Stage2_Suitability_LR_v2`), each active input feature $x_j$ ($j \in \{1, \dots, 5\}$) is first standardised to zero mean and unit variance using `StandardScaler` fitted strictly on the training partition:
$$z_j = \frac{x_j - \mu_j}{\sigma_j}$$
where $\mu_j$ and $\sigma_j$ denote the training sample mean and standard deviation of feature $j$. Standardization ensures that features measured on different numerical scales—such as competency margins in points ($\sigma \approx 6.5\text{–}7.1$) and bounded hyperbolic tangent experience surplus ($\sigma \approx 0.30$)—receive equitable penalisation under L2 regularisation.

The standardised feature vector $\mathbf{z} \in \mathbb{R}^5$ is then mapped to the conditional probability of simulated task success via the logistic sigmoid function $\sigma(\eta)$:
$$P(Y = 1 \mid \mathbf{z}) = \sigma(\eta) = \frac{1}{1 + \exp(-\eta)}, \qquad \text{where} \quad \eta = \beta_0 + \sum_{j=1}^{5} \beta_j z_j$$
Model parameters $(\beta_0, \boldsymbol{\beta})$ are estimated using the L-BFGS quasi-Newton optimiser (`solver='lbfgs'`) by minimising the L2-penalised binary cross-entropy (negative log-likelihood) objective across $N_{\text{train}}$ training pairs:
$$\mathcal{L}(\beta_0, \boldsymbol{\beta}) = -\sum_{i=1}^{N_{\text{train}}} \Big[ y_i \ln \hat{p}_i + (1 - y_i) \ln(1 - \hat{p}_i) \Big] + \frac{1}{2C} \sum_{j=1}^{5} \beta_j^2$$
where $C = 0.5$ is the inverse regularisation strength ($\lambda = \frac{1}{C} = 2.0$), shrinking collinear weights between `min_skill_margin` and `weakest_link_deficit` to prevent variance inflation. Table 5.4 documents the exact configuration and metadata of the final selected model (`ml/metadata/verifymesh_stage2_metadata_v2.json` and `ml/experiments/stage2_refinement/phase3_final_audit_results.json`).

**Table 5.4: Final Stage 2 Logistic Regression Model Configuration and Serialization Metadata**  
*(Source: `ml/metadata/verifymesh_stage2_metadata_v2.json` and `ml/experiments/stage2_refinement/phase3_final_audit_results.json`)*

| Configuration / Metadata Attribute | Authoritative Value |
| :--- | :--- |
| **Model Identifier & Version** | `VerifyMesh_Stage2_Suitability_LR_v2` (`v2.0.0`) |
| **Pipeline Architecture** | `Pipeline([("preprocessor", ColumnTransformer(StandardScaler)), ("classifier", LogisticRegression)])` |
| **Classifier Hyperparameters** | `penalty='l2'`, `C=0.5`, `solver='lbfgs'`, `max_iter=1000`, `random_state=42`, `class_weight=None` |
| **Probability Calibration Wrapper** | `None` (Uncalibrated native L2 Logistic Regression retained following Phase 3 calibration audit) |
| **Approved Final Active Feature Schema (5 Features)** | `['weighted_skill_margin', 'min_skill_margin', 'weakest_link_deficit', 'exp_surplus_tanh', 'difficulty_tier']` |
| **Pre-Update Serialized `.joblib` Schema Note** | On-disk artifact (`verifymesh_stage2_suitability_pipeline_v2.joblib`) retains 6th constant column `cert_satisfied = 1.0` (`standardized_coefficient = 0.000000`, `max_abs_diff = 2.22e-16` vs. 5-feature fit) |
| **Primary Training Dataset** | Scenario B (`ml/experiments/stage2_refinement/scenario_b_data/task_suitability_training.csv`, $N = 4,675$ eligible records, $1,924$ unique applicants, $30$ tasks) |
| **Training Dataset SHA-256** | `5492d2070cfbd6a5a393e50d7eca646ac94bd1c984c050de6e2e97e85280dc65` |
| **Serialized Model Artifact Path & SHA-256** | `ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib` (`70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a`) |
| **Validation Protocol** | $5$ random seeds (`[42, 123, 456, 789, 2026]`) $\times$ $5$-fold outer `StratifiedGroupKFold` grouped by `applicant_id` ($25$ outer folds) |
| **Selected Advisory Decision Threshold** | $\tau = 0.60$ (selected via inner-fold `StratifiedGroupKFold` maximising Macro F1 subject to $\text{Precision} \ge 0.68$) |
| **Advisory Tier Threshold Boundaries** | **Strong Fit:** $\hat{p} \ge 0.60$ $\mid$ **Moderate Fit:** $0.48 \le \hat{p} < 0.60$ $\mid$ **Needs Review:** $\hat{p} < 0.48$ |
| **Software Environment** | `Python 3.13.3`, `scikit-learn 1.8.0`, `pandas 2.3.3`, `numpy 2.3.4`, `joblib 1.5.3` |

---

### 5.2.2 Model Evaluation Metrics and Experimental Results

To evaluate `VerifyMesh_Stage2_Suitability_LR_v2` rigorously across both ranking discrimination, probability reliability, and threshold-specific classification utility, ten complementary metrics were computed across the $25$ applicant-grouped outer folds.

#### Mathematical Definitions of Evaluation Metrics in the VerifyMesh Context
Let $TP$, $FP$, $TN$, and $FN$ denote the counts of True Positives (actual successful pairs predicted $\hat{p} \ge \tau$), False Positives (actual unsuccessful pairs predicted $\hat{p} \ge \tau$), True Negatives (actual unsuccessful pairs predicted $\hat{p} < \tau$), and False Negatives (actual successful pairs predicted $\hat{p} < \tau$) at advisory threshold $\tau$:

1. **Overall Classification Accuracy:** Measures the overall proportion of Stage 1-eligible pairs assigned to the correct outcome category:
   $$\text{Accuracy} = \frac{TP + TN}{TP + FP + TN + FN}$$
2. **Positive-Class Precision ($\text{Precision}_1$):** Measures the empirical task success rate among candidates recommended in the *Strong Fit* category ($\hat{p} \ge \tau$):
   $$\text{Precision}_1 = \frac{TP}{TP + FP}$$
3. **Positive-Class Recall ($\text{Recall}_1$ / Sensitivity):** Measures the proportion of genuinely successful candidates who are captured in the *Strong Fit* tier:
   $$\text{Recall}_1 = \frac{TP}{TP + FN}$$
4. **Failure Recall ($\text{Recall}_0$ / Specificity):** Measures the proportion of simulated task failures (`task_success == 0`) that the model successfully flags below $\tau$ ($\hat{p} < \tau$) for administrator caution:
   $$\text{Failure Recall} = \frac{TN}{TN + FP}$$
5. **Balanced Accuracy:** Computes the unweighted arithmetic mean of positive recall and failure recall, preventing majority-class inflation (`62.61%` positive base rate):
   $$\text{Balanced Accuracy} = \frac{1}{2}\left(\text{Recall}_1 + \text{Failure Recall}\right)$$
6. **Positive F1-Score ($\text{F1}_1$) and Macro F1-Score:** $\text{F1}_1$ is the harmonic mean of $\text{Precision}_1$ and $\text{Recall}_1$, while $\text{Macro F1}$ averages the F1-scores of both the successful and unsuccessful classes equally:
   $$\text{F1}_1 = \frac{2 \cdot \text{Precision}_1 \cdot \text{Recall}_1}{\text{Precision}_1 + \text{Recall}_1}, \qquad \text{Macro F1} = \frac{1}{2}\left(\text{F1}_1 + \text{F1}_0\right)$$
7. **Area Under the ROC Curve ($\text{ROC-AUC}$):** Measures threshold-independent ranking discrimination—specifically, the probability that a randomly chosen successful candidate–task pair receives a higher suitability score than a randomly chosen unsuccessful pair.
8. **Brier Score:** Measures the mean squared error between predicted probabilities $\hat{p}_i$ and binary outcomes $y_i \in \{0, 1\}$, capturing both refinement and calibration (lower is better):
   $$\text{Brier Score} = \frac{1}{N}\sum_{i=1}^{N} (\hat{p}_i - y_i)^2$$
9. **Binary Log-Loss (Cross-Entropy):** Penalises confident probabilistic misclassifications logarithmically (lower is better):
   $$\text{Log-Loss} = -\frac{1}{N}\sum_{i=1}^{N} \Big[y_i \ln \hat{p}_i + (1 - y_i)\ln(1 - \hat{p}_i)\Big]$$
10. **10-Bin Expected Calibration Error ($\text{ECE}$):** Partitions predictions into $M = 10$ uniform probability bins $B_m$ on $[0, 1]$ and computes the weighted average absolute difference between empirical bin accuracy $\text{acc}(B_m)$ and mean predicted probability $\text{conf}(B_m)$:
    $$\text{ECE} = \sum_{m=1}^{10} \frac{|B_m|}{N} \left|\text{acc}(B_m) - \text{conf}(B_m)\right|$$

#### Authoritative Final Model Evaluation Results (Table 5.5)
Table 5.5 reports the comprehensive evaluation results for the final five-feature Logistic Regression model (`LR_5Feat_NoCert` / `VerifyMesh_Stage2_Suitability_LR_v2`), clearly distinguishing **25-fold cross-validation mean $\pm$ SD** on Scenario B ($N = 4,675$), **pooled out-of-fold metrics** on Scenario B (Seed 42, $N = 4,675$), and **25-fold cross-validation mean $\pm$ SD** on Scenario A ($N = 1,183$).

**Table 5.5: Final Five-Feature Logistic Regression Evaluation Metrics Across Evaluation Protocols ($\tau = 0.60$)**  
*(Source: `ml/experiments/stage2_refinement/phase3_final_audit_5v6_summary.csv` and `ml/outputs/chapter5/table_5_4b_confusion_matrix_details.csv`)*

| Evaluation Metric | Scenario B: 25-Fold Grouped CV (Mean $\pm$ SD, Authoritative) | Scenario B: Pooled Out-of-Fold (Seed 42, $N = 4,675$) | Scenario A: 25-Fold Grouped CV (Mean $\pm$ SD, $N = 1,183$) |
| :--- | :---: | :---: | :---: |
| **ROC-AUC (Threshold-Independent)** | **$0.6772 \pm 0.0203$** | $0.6766$ | $0.6095 \pm 0.0320$ |
| **Brier Score (Lower is Better)** | **$0.2110 \pm 0.0042$** | $0.2110$ | $0.2154 \pm 0.0049$ |
| **Binary Log-Loss (Lower is Better)** | **$0.6110 \pm 0.0098$** | $0.6110$ | $0.6213 \pm 0.0110$ |
| **10-Bin Expected Calibration Error ($\text{ECE}$)** | **$0.0298 \pm 0.0117$** | $0.0219$ | $0.0413 \pm 0.0184$ |
| **Classification Accuracy (@ $\tau = 0.60$)** | **$65.54\% \pm 1.29\%$** | $65.41\%$ | $65.53\% \pm 2.16\%$ |
| **Balanced Accuracy (@ $\tau = 0.60$)** | **$62.79\% \pm 1.38\%$** | $62.60\%$ | $56.89\% \pm 2.34\%$ |
| **Positive-Class Precision ($\text{Precision}_1$ @ $\tau = 0.60$)** | **$71.96\% \pm 1.08\%$** | $71.78\%$ | $70.37\% \pm 1.47\%$ |
| **Positive-Class Recall ($\text{Recall}_1$ @ $\tau = 0.60$)** | **$73.71\% \pm 1.99\%$** | $73.76\%$ | $83.18\% \pm 3.26\%$ |
| **Positive-Class F1-Score ($\text{F1}_1$ @ $\tau = 0.60$)** | **$0.7281 \pm 0.0116$** | $0.7276$ | $0.7621 \pm 0.0174$ |
| **Failure Precision ($\text{Precision}_0$ @ $\tau = 0.60$)** | **$54.12\% \pm 1.88\%$** | $53.93\%$ | $48.05\% \pm 4.55\%$ |
| **Failure Recall / Specificity ($\text{Recall}_0$ @ $\tau = 0.60$)** | **$51.87\% \pm 2.83\%$** | $51.43\%$ | $30.59\% \pm 4.88\%$ |
| **Failure F1-Score ($\text{F1}_0$ @ $\tau = 0.60$)** | **$0.5294 \pm 0.0199$** | $0.5265$ | $0.3719 \pm 0.0435$ |
| **Macro F1-Score (@ $\tau = 0.60$)** | **$0.6287 \pm 0.0138$** | $0.6270$ | $0.5670 \pm 0.0263$ |

#### Classification Threshold Selection and Policy Comparison (Table 5.6)
Because $62.61\%$ of Stage 1-eligible candidates in Scenario B succeed on their assigned task, operating at the default $\tau = 0.50$ probability cutoff causes the classifier to predict success for nearly $89\%$ of eligible pairs (`Recall = 88.74%`), resulting in poor failure detection (`Failure Recall = 31.20%`). To establish an operational advisory cutoff without consulting outer test folds, nested inner-fold `StratifiedGroupKFold` cross-validation swept candidate thresholds $\tau \in [0.35, 0.80]$ on inner training out-of-fold predictions, maximising **Macro F1** subject to the operational safety constraint **`Positive Precision >= 0.68`**. Across all $25$ outer training splits, inner-fold optimization satisfied the $\ge 0.68$ precision constraint in **$25 / 25$ folds** (`inner_oof_precision_mean = 71.95%`), converging to a mean inner-selected threshold of **$0.6012 \pm 0.0097$** (range $[0.59, 0.63]$), which rounds cleanly to the operational advisory threshold **$\tau = 0.60$**. Table 5.6 compares performance across threshold policies.

**Table 5.6: Classification Performance of the Final Five-Feature Logistic Regression Model Across Threshold Policies (Scenario B, 25 Outer Folds)**  
*(Source: `ml/experiments/stage2_refinement/phase3_final_audit_5v6_summary.csv`, `model = LR_5Feat_NoCert`)*

| Threshold Policy | Threshold ($\text{Mean} \pm \text{SD}$) | Accuracy | Balanced Accuracy | Positive Precision ($\text{Prec}_1$) | Positive Recall ($\text{Rec}_1$) | Failure Recall ($\text{Rec}_0$) | Macro F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Natural Probability Cutoff (`fixed_050`)** | $0.5000 \pm 0.0000$ | $67.23\% \pm 0.87\%$ | $59.97\% \pm 0.99\%$ | $68.36\% \pm 0.61\%$ | $88.74\% \pm 1.31\%$ | $31.20\% \pm 2.17\%$ | $0.5939 \pm 0.0122$ |
| **Selected Operational Advisory Cutoff (`selected_fixed_060`)** | **$0.6000 \pm 0.0000$** | **$65.54\% \pm 1.29\%$** | **$62.79\% \pm 1.38\%$** | **$71.96\% \pm 1.08\%$** | **$73.71\% \pm 1.99\%$** | **$51.87\% \pm 2.83\%$** | **$0.6287 \pm 0.0138$** |
| **Inner-CV Macro F1 (`inner_macro_f1`, $\text{Prec}_1 \ge 0.68$)** | $0.6012 \pm 0.0097$ | $65.27\% \pm 1.63\%$ | $62.61\% \pm 1.73\%$ | $71.92\% \pm 1.50\%$ | $73.15\% \pm 3.48\%$ | $52.06\% \pm 4.68\%$ | $0.6262 \pm 0.0170$ |
| **Inner-CV Balanced Accuracy (`inner_bal_acc`)** | $0.6220 \pm 0.0161$ | $64.23\% \pm 1.94\%$ | $62.93\% \pm 1.70\%$ | $73.00\% \pm 1.45\%$ | $68.09\% \pm 4.16\%$ | $57.76\% \pm 4.19\%$ | $0.6252 \pm 0.0175$ |

#### Confusion Matrix, ROC, Precision–Recall, and Probability Separation Analysis
As shown in **Figure 5.8** (`ml/outputs/chapter5/figure_5_8_final_confusion_matrix.png`) and Table 5.4B (`ml/outputs/chapter5/table_5_4b_confusion_matrix_details.csv`), evaluating the pooled out-of-fold predictions on Scenario B (Seed 42, $N = 4,675$) at $\tau = 0.60$ yields **$2,159$ True Positives** ($73.76\%$ of the $2,927$ successful pairs), **$899$ True Negatives** ($51.43\%$ of the $1,748$ unsuccessful pairs), **$849$ False Positives**, and **$768$ False Negatives** ($5$-seed mean counts: $\text{TP} = 2,157.4$, $\text{TN} = 906.8$, $\text{FP} = 841.2$, $\text{FN} = 769.6$). Compared to the $\tau = 0.50$ threshold, raising the advisory threshold to $\tau = 0.60$ increases failure detection by **$+20.67$ percentage points** ($31.20\% \rightarrow 51.87\%$), enabling administrators to identify more than half of the latent task failures that passed Stage 1.

The threshold-independent **ROC curve (Figure 5.9)** and **Precision–Recall curve (Figure 5.10)** further demonstrate consistent ranking separation across the entire operating range, achieving an out-of-fold $\text{ROC-AUC}$ of $0.6772 \pm 0.0203$ (compared to $0.7427$ for the noiseless Oracle reference) and elevating positive precision from the $62.61\%$ base rate to $71.96\%$ at $\tau = 0.60$. Similarly, **Figure 5.11** (predicted probability distributions stratified by actual outcome) confirms that actual successful outcomes are concentrated at higher predicted probabilities ($\text{median} \approx 0.68$) than actual unsuccessful outcomes ($\text{median} \approx 0.59$).

#### Probability Calibration Evaluation (Table 5.6B and Figure 5.12)
Because Stage 2 outputs numerical probabilities directly to administrators, probability calibration was audited in Phase 3 (`ml/experiments/stage2_refinement/phase3_calibration_comparison.csv`) by comparing the uncalibrated L2 Logistic Regression pipeline against post-hoc Platt scaling (`CalibratedClassifierCV(method='sigmoid')`) and isotonic regression (`CalibratedClassifierCV(method='isotonic')`) fitted via nested inner cross-validation. Table 5.6B reports the resulting 25-fold calibration metrics.

**Table 5.6B: Out-of-Fold Probability Calibration Comparison (Phase 3, 25 Outer Applicant-Grouped Folds)**  
*(Source: `ml/experiments/stage2_refinement/phase3_calibration_comparison.csv`)*

| Dataset | Calibration Variant | ROC-AUC (Mean $\pm$ SD) | Brier Score (Mean $\pm$ SD) | Log-Loss (Mean $\pm$ SD) | 10-Bin ECE (Mean $\pm$ SD) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Scenario B ($N = 4,675$)** | **`Uncalibrated_LR` (Selected)** | **$0.6772 \pm 0.0203$** | **$0.2110 \pm 0.0042$** | **$0.6110 \pm 0.0098$** | **$0.0298 \pm 0.0117$** |
| **Scenario B ($N = 4,675$)** | `Sigmoid_Calibrated_LR` (Platt) | $0.6773 \pm 0.0203$ | $0.2110 \pm 0.0041$ | $0.6110 \pm 0.0096$ | $0.0300 \pm 0.0120$ |
| **Scenario B ($N = 4,675$)** | `Isotonic_Calibrated_LR` | $0.6768 \pm 0.0201$ | $0.2119 \pm 0.0048$ | $0.6266 \pm 0.0393$ | $0.0356 \pm 0.0132$ |
| **Scenario A ($N = 1,183$)** | **`Uncalibrated_LR`** | **$0.6095 \pm 0.0320$** | $0.2154 \pm 0.0049$ | $0.6213 \pm 0.0110$ | $0.0413 \pm 0.0184$ |
| **Scenario A ($N = 1,183$)** | `Sigmoid_Calibrated_LR` (Platt) | $0.6089 \pm 0.0318$ | **$0.2153 \pm 0.0043$** | **$0.6211 \pm 0.0095$** | **$0.0405 \pm 0.0170$** |
| **Scenario A ($N = 1,183$)** | `Isotonic_Calibrated_LR` | $0.6085 \pm 0.0324$ | $0.2169 \pm 0.0057$ | $0.6425 \pm 0.0624$ | $0.0562 \pm 0.0241$ |

Although Logistic Regression is not guaranteed to be well-calibrated under model misspecification, empirically auditing the five-feature L2 Logistic Regression pipeline on Scenario B confirms that it achieves a low out-of-fold 10-bin Expected Calibration Error of **$0.0298 \pm 0.0117$** and Brier score of **$0.2110 \pm 0.0042$**. Non-parametric isotonic calibration overfits step boundaries on inner folds—degrading Brier score ($0.2119$), log-loss ($0.6266$), and ECE ($0.0356$)—while Platt sigmoid rescaling yields virtually identical Brier and log-loss values with slightly higher ECE ($0.0300$). Consequently, the uncalibrated L2 Logistic Regression model was retained on grounds of empirical calibration accuracy and architectural simplicity.

#### Fitted Logistic Regression Coefficient Analysis (Table 5.7 and Figure 5.13)
Unlike black-box tree ensembles that rely on impurity-based feature importance scores, Logistic Regression provides directly interpretable log-odds coefficients ($\beta_j$) and odds ratios ($\exp(\beta_j)$) per one-standard-deviation ($+1\text{ SD}$) change in each standardised input feature, holding the remaining four features constant. Table 5.7 reports the exact fitted parameters of the final model on Scenario B ($N = 4,675$, intercept $\beta_0 = +0.552574$). Note that these coefficients represent predictive associations within the synthetic simulation model rather than causal effects in real-world employment.

**Table 5.7: Fitted Standardized L2 Logistic Regression Coefficients (`VerifyMesh_Stage2_Suitability_LR_v2`, Scenario B, $N = 4,675$)**  
*(Source: `ml/experiments/stage2_refinement/phase3_final_audit_results.json`, Intercept $\beta_0 = +0.552574$)*

| Input Feature | `StandardScaler` Mean ($\mu_j$) | `StandardScaler` SD ($\sigma_j$) | Standardized Coefficient ($\beta_j$) | Odds Ratio per $+1\text{ SD}$ ($\exp(\beta_j)$) | Direction of Association | Domain Interpretation (Holding Other Features Constant) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`exp_surplus_tanh`** | $+0.7286$ | $0.2979$ | **$+0.236757$** | $1.267$ | Positive ($+$) | A $+1\text{ SD}$ increase in saturating relevant experience surplus increases the odds of simulated task success by $+26.7\%$. |
| **`weakest_link_deficit`** | $-1.6129$ | $3.4743$ | **$+0.223144$** | $1.250$ | Positive ($+$) | Because `weakest_link_deficit` $\le 0$, moving $+1\text{ SD}$ closer to zero deficit ($0.0$) increases success odds by $+25.0\%$ (conversely, deeper negative deficits sharply reduce predicted suitability). |
| **`weighted_skill_margin`** | $+11.8063$ | $6.5142$ | **$+0.188595$** | $1.208$ | Positive ($+$) | A $+1\text{ SD}$ ($+6.51$ point) increase in category-weighted competency surplus increases simulated success odds by $+20.8\%$. |
| **`min_skill_margin`** | $+2.3297$ | $7.0637$ | **$+0.186129$** | $1.205$ | Positive ($+$) | A $+1\text{ SD}$ ($+7.06$ point) increase in the candidate's lowest skill margin increases simulated success odds by $+20.5\%$. |
| **`difficulty_tier`** | $+1.3067$ | $0.5175$ | **$-0.320832$** | $0.726$ | Negative ($-$) | A $+1\text{ SD}$ increase in task difficulty tier reduces the odds of simulated task success by $-27.4\%$, reflecting the higher failure risk of complex tasks. |
| *(Pre-update 6th col)* `cert_satisfied` | $+1.0000$ | $1.0000$ | `$0.000000$` | $1.000$ | Zero ($0$) | Constant $1.0$ across all Stage 1-eligible records; contributes zero log-odds weight (`excluded in 5-feature specification`). |

#### Advisory Suitability Tiers and Administrator Decision Support (Table 5.8 and Figure 5.14)
To translate continuous out-of-fold probabilities into structured decision support for human administrators, Stage 2 maps each eligible candidate–task pair into one of three advisory tiers (`Strong Fit` $\hat{p} \ge 0.60$, `Moderate Fit` $0.48 \le \hat{p} < 0.60$, and `Needs Review` $\hat{p} < 0.48$). Table 5.8 reports the candidate distribution and empirical simulated success rate across the three advisory tiers from the 25-fold cross-validation audit on Scenario B (`phase3_final_audit_results.json`).

**Table 5.8: Candidate Distribution and Empirical Simulated Success Rate Across Stage 2 Advisory Suitability Tiers (Scenario B, $N = 4,675$)**  
*(Source: `ml/experiments/stage2_refinement/phase3_final_audit_results.json`, Section `2_threshold_evaluation.scenario_b_diagnostics.tier_distributions.LR_5Feat_NoCert`)*

| Advisory Suitability Tier | Predicted Probability Interval | Mean Candidate–Task Pairs per Seed ($N = 4,675$) | Percentage of Eligible Candidates | Empirical Simulated Task Success Rate Within Tier | Recommended Administrator Action |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Strong Fit** | $\hat{p} \ge 0.60$ | $2,998.4$ | **$64.14\%$** | **$71.95\%$** | Priority shortlist for task allocation; candidate exceeds domain competency and tenure benchmarks. |
| **Moderate Fit** | $0.48 \le \hat{p} < 0.60$ | $915.4$ | **$19.58\%$** | **$54.63\%$** | Secondary comparison pool; inspect factor breakdown for minor sub-skill trade-offs before assignment. |
| **Needs Review** | $\hat{p} < 0.48$ | $761.2$ | **$16.28\%$** | **$35.42\%$** | Caution flag; candidate passed Stage 1 minimums but exhibits a sub-skill bottleneck or high task difficulty risk. |
| **Total Eligible Cohort** | $\hat{p} \in [0.00, 1.00]$ | **$4,675.0$** | **$100.00\%$** | **$62.61\%$ (Base Rate)** | Human administrator retains final allocation authority across all tiers. |

As Table 5.8 and **Figure 5.14** demonstrate, the advisory tiers establish monotonic risk stratification across the eligible candidate pool: candidates placed in **Strong Fit** succeed at **$71.95\%$** (more than double the **$35.42\%$** empirical success rate of candidates flagged in **Needs Review**), providing clear operational value while preserving human-in-the-loop governance.

#### Serialization Verification Audit (Table 5.9)
Finally, Table 5.9 records the fresh-process serialization and parity checks executed in `run_phase3_final_audit.py` (`phase3_final_audit_results.json`, Section `3_serialization_verification`), confirming that the saved `.joblib` artifact loads cleanly in an isolated Python subprocess and produces finite, bounded probabilities in $[0, 1]$ matching in-memory pipelines to machine precision.

**Table 5.9: Serialization Integrity and Subprocess Parity Verification Results**  
*(Source: `ml/experiments/stage2_refinement/phase3_final_audit_results.json`, Section `3_serialization_verification`)*

| Verification Check | Observed Result | Status |
| :--- | :--- | :---: |
| **Fresh Python Subprocess Load (`verifymesh_stage2_suitability_pipeline_v2.joblib`)** | Loaded cleanly (`exit_code = 0`) in isolated subprocess | **PASS** |
| **Cryptographic Checksum Match (`SHA-256`)** | `70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a` (Exact match with metadata JSON) | **PASS** |
| **Loaded Artifact vs. Fresh In-Memory 6-Feature Pipeline Parity ($N = 4,675$)** | $\max |\hat{p}_{\text{loaded,6}} - \hat{p}_{\text{inmem,6}}| = 0.00 \times 10^{0}$ | **PASS** |
| **Loaded 6-Feature Artifact vs. Fresh 5-Feature (`LR_5Feat_NoCert`) Parity ($N = 4,675$)** | $\max |\hat{p}_{\text{loaded,6}} - \hat{p}_{\text{inmem,5}}| = 2.22 \times 10^{-16}$ | **PASS** |
| **Probability Validity & Boundedness ($\hat{p} \in [0, 1]$, No `NaN`/`Inf`)** | All $4,675$ predictions finite; range $[0.1610, 0.8759]$ (mean $= 0.6261$) | **PASS** |

---

## 5.3 Recommended Chapter 5 Figure and Table Checklist

To keep Chapter 5 focused, readable, and academically rigorous, **do not include every exploratory plot from the notebook in the main report body**. Below is the prioritized recommendation of **Essential (Core Chapter 5 Body)** versus **Optional (Appendix or Supporting)** figures, distinguishing conceptual workflow diagrams from empirical data/evaluation plots, and indicating which PNG files already exist in `ml/outputs/chapter5/` versus which remain to be exported from the notebook.

| Proposed Fig # | Figure Title / Caption | Visualisation Type (Conceptual vs. Empirical) | Exact Source Dataset / Artifact | What the Figure Demonstrates | Target Subsection | Priority | Current Status in `ml/outputs/chapter5/` |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Figure 5.1** | Distribution of Applicant Competency Scores Across Five Assessment Dimensions ($N = 3,200$) | Empirical Violin + Quartile Plot | `scenario_b_data/synthetic_applicants.csv` | Shows realistic bounded distribution ($66\text{–}72$ mean) and spread across all 5 applicant competency scores. | `5.1.2` | **Essential** | **Exists** (`figure_5_1_applicant_dataset.png`) |
| **Figure 5.2** | Task Distribution Across Operational Categories (Catalog vs. Stage 1-Eligible Pairs) | Empirical Two-Panel Horizontal Bar Chart | `scenario_b_data/synthetic_tasks.csv` & `synthetic_applicant_task_pairs.csv` | Contrasts uniform task catalog ($6$ per category) with post-Stage 1 eligible pair volume across categories. | `5.1.2` | **Essential** | **Exists** (`figure_5_2_task_distribution.png`) |
| **Figure 5.3** | Stage 1 Deterministic Eligibility Gate Outcome Distribution ($N = 24,000$ Pairs) | Empirical Bar + Stacked Category Pass-Rate Chart | `scenario_b_data/synthetic_applicant_task_pairs.csv` | Demonstrates that Stage 1 filters out $80.52\%$ of unqualified pairs, passing only $19.48\%$ ($4,675$) to Stage 2. | `5.1.4` | **Essential** | **Exists** (`figure_5_3_eligibility_distribution.png`) |
| **Figure 5.4** | Distribution of Simulated Task Execution Outcomes in the Stage 2 Cohort ($N = 4,675$) | Empirical Bar + Stacked Difficulty Outcome Chart | `scenario_b_data/synthetic_applicant_task_pairs.csv` | Shows the $62.61\%$ vs. $37.39\%$ class balance and rising failure rates on higher-difficulty tasks. | `5.1.4` | **Essential** | **Exists** (`figure_5_4_task_success_distribution.png`) |
| *Fig 5.4C–H (Optional)* | Supporting Distributions (Difficulty, Experience, Surplus `tanh`, Margins, Latent Oracle, Scenario A vs. B Class Balance) | Empirical Histograms / KDEs / Boxplots | `scenario_b_data/*.csv` & `task_specific_synthetic_data/*.csv` | Supports feature transformation choices (`exp_surplus_tanh`, `min_skill_margin`, Scenario B IQR expansion). | `5.1.3` / Appendix | *Optional (Select 1–2 or Appendix)* | `5.4c` & `5.4d` **Exist**; `5.4e–h` code provided above |
| **Figure 5.5** | Two-Stage VerifyMesh Eligibility and Task-Suitability Prediction Architecture | **Conceptual System Workflow Diagram** | Architectural specification (`Stage 1 Gate -> 5-Feat Engineering -> StandardScaler -> L2 LR -> Advisory Tiers -> Admin`) | Illustrates the end-to-end two-stage pipeline and human-in-the-loop boundary (replacing the old Random Forest diagram). | `5.2.1` | **Essential** | **Needs Export** (Mermaid / Matplotlib diagram) |
| **Figure 5.6** | Candidate Model Out-of-Fold ROC-AUC and Brier Score Comparison (Scenario A vs. Scenario B) | Empirical Grouped Bar Chart with Error Bars ($\pm 1\text{ SD}$) | `phase2_scenario_comparison_summary.csv` | Demonstrates that `VerifyMesh_Stage2_Suitability_LR_v2` outperforms 28-feature Random Forest and reaches $91.2\%$ of the Oracle ceiling. | `5.2.1` | **Essential** |Rendered inside notebook (`sec12_code`); **Needs standalone PNG export** (`figure_5_5_model_auc_comparison.png` / `figure_5_6_brier.png`) |
| **Figure 5.7** | Feature Correlation Heatmap and Piecewise Bottleneck Hinge (`weakest_link_deficit`) | Empirical Heatmap + Scatter Plot | `scenario_b_data/task_suitability_training.csv` + `stage2_feature_engineering.py` | Shows low multi-collinearity across the 5 engineered features and the kinked slope of `weakest_link_deficit = min(0, min_skill_margin)`. | `5.1.5` / `5.2.1` | *Recommended* | Rendered inside notebook (`sec9_code`); **Needs standalone PNG export** |
| **Figure 5.8** | Out-of-Fold Confusion Matrix for the Final Five-Feature Logistic Regression Model ($\tau = 0.60$, $N = 4,675$) | Empirical 2x2 Heatmap (Counts & Row Recall %) | Held-out OOF predictions (`Seed 42, N = 4,675`) on `scenario_b_data` | Demonstrates $51.43\%$ failure recall ($899/1,748$) and $73.76\%$ positive recall ($2,159/2,927$) at $\tau = 0.60$. | `5.2.2` | **Essential** | **Exists** (`figure_5_8_final_confusion_matrix.png`) |
| **Figure 5.9** | Out-of-Fold Receiver Operating Characteristic (ROC) Curve (`VerifyMesh_Stage2_Suitability_LR_v2`) | Empirical ROC Curve vs. Oracle Ceiling & Random Baseline | Held-out OOF predictions (`scenario_b_data`, $N = 4,675$) | Shows threshold-independent discrimination ($\text{AUC} = 0.6772 \pm 0.0203$ vs. $0.7427$ Oracle ceiling). | `5.2.2` | **Essential** | Rendered in `sec15_code` subplot; **Needs standalone PNG export** (`figure_5_9_roc_curve.png`) |
| **Figure 5.10** | Out-of-Fold Precision–Recall Curve (`VerifyMesh_Stage2_Suitability_LR_v2`) | Empirical PR Curve with $\tau = 0.60$ Operating Point Marked | Held-out OOF predictions (`scenario_b_data`, $N = 4,675$) | Demonstrates precision–recall trade-off and marks the $\tau = 0.60$ operating point ($\text{Precision} = 71.96\%$, $\text{Recall} = 73.71\%$). | `5.2.2` | **Essential** | Rendered in `sec15_code` subplot; **Needs standalone PNG export** (`figure_5_10_precision_recall_curve.png`) |
| **Figure 5.11** | Predicted Task-Success Probability Distribution by Actual Simulated Outcome | Empirical Violin / Box / KDE Plot with $\tau = 0.60$ and $0.48$ Tier Lines | Held-out OOF predictions (`scenario_b_data`, $N = 4,675$) | Shows separation in predicted probability distributions between actual successful (`1`) and unsuccessful (`0`) tasks. | `5.2.2` | *Recommended* | Rendered in `sec15_code` subplot; **Needs standalone PNG export** (`figure_5_11_probability_distribution.png`) |
| **Figure 5.12** | Reliability Diagram (Calibration Curve) Across Calibration Methods (`Uncalibrated` vs. `Sigmoid` vs. `Isotonic`) | Empirical 10-Bin Calibration Curve + Probability Histogram | Held-out OOF predictions & `phase3_calibration_comparison.csv` | Demonstrates that uncalibrated L2 Logistic Regression closely tracks the $y = x$ diagonal ($\text{ECE} = 0.0298$, $\text{Brier} = 0.2110$). | `5.2.2` | **Essential** | Rendered in `sec13_code` & `sec15_code`; **Needs standalone PNG export** (`figure_5_12_calibration_curve.png`) |
| **Figure 5.13** | Standardized L2 Logistic Regression Coefficients for the Five Final Input Features | Empirical Horizontal Bar Chart ($\beta_j$ per $+1\text{ SD}$) | `phase3_final_audit_results.json` (`five_feature_learned_parameters`) | Replaces the historical Random Forest feature-importance chart with exact signed log-odds weights ($+0.237$ to $-0.321$). | `5.2.2` | **Essential** | Rendered in `sec15_code` subplot; **Needs standalone PNG export** (`figure_5_13_logistic_regression_coefficients.png`) |
| **Figure 5.14** | Candidate Distribution and Empirical Task Success Rate Across Advisory Suitability Tiers | Empirical Two-Panel Bar Chart (`% of Eligible` & `Empirical Success Rate %`) | `phase3_final_audit_results.json` (`tier_distributions.LR_5Feat_NoCert`) | Demonstrates clear monotonic success stratification across Strong Fit ($71.95\%$), Moderate Fit ($54.63\%$), and Needs Review ($35.42\%$). | `5.2.2` | **Essential** | Rendered in `sec16_code`; **Needs standalone PNG export** (`figure_5_14_advisory_tier_distribution.png`) |

---

## 5.4 Discrepancy Report: Earlier Chapter 5 Draft vs. Completed Phase 0–3 Experiments

Table 5.10 systematically maps every outdated statement in the earlier Chapter 5 draft (which was based on the preliminary Google Colab notebook) against the verified Phase 0–3 repository findings and provides the exact correction required for the final report.

**Table 5.10: Reconciliation of Earlier Chapter 5 Draft Statements Against Authoritative Phase 0–3 Results**

| Existing Chapter 5 Draft Statement | Actual Phase 0–3 Experimental Position (Authoritative) | Recommended Correction for Final Chapter 5 Report |
| :--- | :--- | :--- |
| **1. "The modelling dataset contains $1,127$ eligible records."** | Scenario A actually contains **$1,183$** Stage 1-eligible records (`is_eligible == 1`), and Scenario B (the final modelling dataset) contains **$4,675$** Stage 1-eligible records out of $24,000$ initial pairs. The $1,127$ figure resulted from filtering on `(cert_satisfied == 1) & (assessment_satisfied == 1)`, which unintentionally dropped $56$ valid Stage 1-eligible records where secondary non-domain skills were between $-8.0$ and $-10.0$. | Report **$N = 4,675$ Stage 1-eligible pairs** (from $24,000$ initial pairs, $3,200$ applicants, $30$ tasks in Scenario B) as the primary modelling dataset, and **$N = 1,183$** ($6,000$ initial pairs, $800$ applicants in Scenario A) as the initial benchmark regime. Document the $1,127$ subset briefly as a corrected historical filter. |
| **2. "The dataset was evaluated using an $80:20$ train–test split (`GroupShuffleSplit`)."** | In Cell 19 of the preliminary Colab notebook, sequential per-row fake IDs (`applicant_0 .. applicant_1126`) were synthesized because `applicant_id` had been removed from `task_suitability_training.csv`. This caused `GroupShuffleSplit` to degenerate into an ungrouped single $80:20$ row split ($901$ train / $226$ test) that leaked the same real applicants across train and test sets. | Replace the single $80:20$ split description with the **5-seed $\times$ 5-fold applicant-grouped `StratifiedGroupKFold` protocol ($25$ outer folds)** using the true `applicant_id` from `synthetic_applicant_task_pairs.csv` ($\max |\text{Train}_{\text{app}} \cap \text{Val}_{\text{app}}| = 0$). |
| **3. "The model uses $28$ input features (`task_suitability_training.csv`)."** | Feeding $28$ raw applicant, task, and gap features into tree ensembles caused severe overfitting (`train-val ROC-AUC gap = +0.1939` on Scenario A) and inferior out-of-fold generalisation. Furthermore, `task_suitability_training.csv` actually contains $34$ feature columns + $1$ target column ($35$ total). | Present the **five domain-engineered features** (`weighted_skill_margin`, `min_skill_margin`, `weakest_link_deficit`, `exp_surplus_tanh`, `difficulty_tier`) implemented in `src/stage2_feature_engineering.py` as the final feature schema, and explain why `cert_satisfied = 1.0` was removed as a zero-variance Stage 1 constant. |
| **4. "Random Forest (`verifymesh_final_optimized_pipeline.joblib`) was selected as the final Stage 2 model."** | Across both Scenario A and Scenario B, L2-regularised Logistic Regression (`StandardScaler` + `LogisticRegression(C=0.5)`) outperformed the 28-feature Random Forest in ROC-AUC ($0.6095$ vs. $0.5878$ on Scenario A; **$0.6772$ vs. $0.6645$ on Scenario B**) and Brier calibration ($0.2110$ vs. $0.2224$). | Discuss the 28-feature Random Forest (`Current_RF_28Feat`) strictly as a **candidate baseline model in Section 5.2.1** that was outperformed by the compact L2-regularised Logistic Regression pipeline (`VerifyMesh_Stage2_Suitability_LR_v2`). |
| **5. "A classification threshold of $0.61$ was selected, achieving $58.85\%$ accuracy and $58.60\%$ balanced accuracy."** | The $0.610$ threshold in the preliminary Colab notebook (Cell 67) was tuned **post-hoc directly on the 226-row outer test set** (`test_probs`). When evaluated without leakage across 25 applicant-grouped folds in Phase 1, `Current_RF_28Feat` at $0.61$ achieved only $52.73\% \pm 2.79\%$ accuracy and $55.14\% \pm 2.60\%$ balanced accuracy. | Report the **$\tau = 0.60$ advisory threshold** for `VerifyMesh_Stage2_Suitability_LR_v2`, selected strictly via nested inner-fold `StratifiedGroupKFold` (`Positive Precision >= 0.68`, inner mean $= 0.6012 \pm 0.0097$), achieving **$65.54\% \pm 1.29\%$ accuracy**, **$62.79\% \pm 1.38\%$ balanced accuracy**, **$71.96\%$ positive precision**, and **$51.87\%$ failure recall** on Scenario B. |
| **6. "Random Forest Confusion Matrix and Gini Feature Importance Chart presented as final model evidence."** | Impurity-based Random Forest feature importances and the 226-row RF confusion matrix do not apply to the final Logistic Regression model. | Replace the RF confusion matrix with **Figure 5.8** (held-out out-of-fold Logistic Regression confusion matrix across $N = 4,675$ pairs at $\tau = 0.60$) and replace the RF feature-importance chart with **Figure 5.13** and **Table 5.7** (standardized L2 Logistic Regression log-odds coefficients $\beta_j$). |
| **7. "Serialized model artifact schema assumption (`5` vs. `6` features)."** | While the Phase 3 Final Audit proved that removing constant `cert_satisfied = 1.0` (`LR_5Feat_NoCert`) produces identical metrics and probabilities ($\max |\Delta \hat{p}| \le 4.44 \times 10^{-16}$), the `.joblib` file currently on disk (`verifymesh_stage2_suitability_pipeline_v2.joblib`, `SHA-256: 70dc562e...`) was not overwritten during the audit and still expects the 6-column schema where `cert_satisfied` has weight $0.000000$. | Explicitly state in Section 5.1.5 and Section 5.2.1 that the five-feature model is the approved specification and note transparently that the pre-update `.joblib` artifact retains the zero-weight constant `cert_satisfied = 1.0` column with exact mathematical equivalence. |

---

## 5.5 Artifact Traceability and Missing Export Checklist

### 5.5.1 Complete Source File Traceability Matrix
Every numerical claim and table in this document is directly traceable to the following unedited repository files:
1. **Scenario A Dataset Files:** `ml/experiments/task_specific_synthetic_data/synthetic_applicants.csv`, `synthetic_tasks.csv`, `synthetic_applicant_task_pairs.csv`, `task_suitability_training.csv`, and `generate_synthetic_dataset.py`.
2. **Scenario B Dataset Files:** `ml/experiments/stage2_refinement/scenario_b_data/synthetic_applicants.csv`, `synthetic_tasks.csv`, `synthetic_applicant_task_pairs.csv`, and `task_suitability_training.csv`.
3. **Feature Engineering Implementation:** `src/stage2_feature_engineering.py` (`compute_stage2_features_dataframe`, `build_complete_stage2_feature_dict`, `explain_stage2_prediction`).
4. **Phase 1 Benchmark Artifacts:** `ml/experiments/stage2_refinement/run_phase1_benchmark.py`, `phase1_benchmark_summary.csv`, `phase1_fold_details.csv`, `phase1_benchmark_results.json`, and `phase1_benchmark_report.md`.
5. **Phase 2 Scenario Comparison Artifacts:** `ml/experiments/stage2_refinement/run_phase2_scenario_comparison.py`, `phase2_scenario_comparison_summary.csv`, `phase2_scenario_comparison_folds.csv`, `phase2_scenario_comparison_results.json`, and `phase2_scenario_comparison_report.md`.
6. **Phase 3 Calibration & Serialization Artifacts:** `ml/experiments/stage2_refinement/run_phase3_calibration_and_serialization.py`, `phase3_calibration_comparison.csv`, `phase3_final_model_results.json`, `phase3_final_model_report.md`, `ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib`, and `ml/metadata/verifymesh_stage2_metadata_v2.json`.
7. **Phase 3 Final Audit Artifacts:** `ml/experiments/stage2_refinement/run_phase3_final_audit.py`, `phase3_final_audit_5v6_summary.csv`, `phase3_final_audit_results.json`, and `phase3_final_audit_report.md`.

### 5.5.2 Inventory of Files Currently Exported in `ml/outputs/chapter5/` vs. Remaining Standalone Exports
1. **Already Exported in `ml/outputs/chapter5/` (13 Files Verified on Disk):**
   - **Figures (300 DPI PNGs):**
     - `figure_5_1_applicant_dataset.png`
     - `figure_5_2_task_distribution.png`
     - `figure_5_3_eligibility_distribution.png`
     - `figure_5_4_task_success_distribution.png`
     - `figure_5_4c_task_difficulty_distribution.png`
     - `figure_5_4d_applicant_experience_distribution.png`
     - `figure_5_8_final_confusion_matrix.png`
   - **Tables (CSVs):**
     - `table_5_1a_sample_applicants.csv`
     - `table_5_1b_sample_tasks.csv`
     - `table_5_1c_sample_applicant_task_pairs.csv`
     - `table_5_1_dataset_summary_scenario_b.csv`
     - `table_5_1_scenario_a_vs_b_statistics.csv`
     - `table_5_4b_confusion_matrix_details.csv`
2. **Visualisations Already Rendered Inline in `ml/notebooks/VerifyMesh_Task_Suitability_Experiment.ipynb` That Can Be Exported as Standalone 300 DPI PNGs into `ml/outputs/chapter5/` When Needed:**
   - Because the Phase 1–3 experiment scripts save aggregated fold metrics (CSVs/JSONs) rather than persisting a 23,375-row raw out-of-fold probability array to disk, plots that require observation-level out-of-fold probabilities (**ROC curve `Figure 5.9`**, **Precision–Recall curve `Figure 5.10`**, **Predicted Probability Distribution by Outcome `Figure 5.11`**, and **Reliability Diagram `Figure 5.12`**) are computed reproducibly inside the notebook (`sec13_code` and `sec15_code`) using the exact `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)` split on `scenario_b_data`.
   - Similarly, the **Candidate Model Comparison chart (`Figure 5.6`)**, **Logistic Regression Coefficient horizontal bar chart (`Figure 5.13`)**, and **Advisory Suitability Tier Distribution chart (`Figure 5.14`)** are already rendered inline in `sec12_code`, `sec15_code`, and `sec16_code` of `VerifyMesh_Task_Suitability_Experiment.ipynb`, and only need `fig.savefig(OUT_DIR / "figure_5_X_....png", dpi=300)` calls if you wish to insert them as standalone PNG files into Word/LaTeX.

