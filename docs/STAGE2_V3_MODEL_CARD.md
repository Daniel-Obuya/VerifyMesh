# Model Card: VerifyMesh Stage 2 Task Suitability Predictor (v3.0.0)

**Model Identifier**: `VerifyMesh_Stage2_Suitability_LR_v3`  
**Model Version**: `3.0.0`  
**Artifact File**: `ml/models/verifymesh_stage2_suitability_pipeline_v3.joblib`  
**Artifact SHA-256**: `2897f781217895e6d7b285769132022e943e4ed9925e50a4e92938febc30f745`  
**Metadata File**: `ml/metadata/verifymesh_stage2_metadata_v3.json`  
**Date**: November 10, 2026  
**License**: Academic Capstone Project / MIT License  

---

## 1. Model Details

### 1.1 Model Description
`VerifyMesh_Stage2_Suitability_LR_v3` is an L2-regularized Logistic Regression pipeline designed to provide advisory task suitability scores for workforce applicants who have already satisfied all mandatory Stage 1 deterministic eligibility rules (cryptographic credential verification, verified tenure minimums, and required competency assessment thresholds).

The v3 model resolves the statistical collinearity and double-penalty defect of the previous v2 model by replacing the mathematically redundant `weakest_link_deficit` ($r=1.000$ on negative margins) with `deficit_competencies_ratio`, decoupling the depth of the applicant's single weakest skill from the breadth of multi-competency failure.

### 1.2 Pipeline Architecture
- **Preprocessing Step**: `ColumnTransformer` with `StandardScaler` fitted strictly on grouped training partitions across the 5 canonical input features.
- **Classification Estimator**: `LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)`.
- **Primary Signal**: Continuous advisory probability $P(\text{task\_success} = 1) \in (0, 1)$.
- **Operational Decision Rule**: 
  - $P \ge 0.60 \implies$ **"Strong Fit"** (Suitable for direct allocation)
  - $0.48 \le P < 0.60 \implies$ **"Moderate Fit"** (Suitable with managerial support)
  - $P < 0.48 \implies$ **"Needs Review"** (Advisory recommendation against immediate unguided deployment)
  - Stage 1 Ineligible $\implies$ **Never evaluated by Stage 2**

---

## 2. Intended Use & Users

### 2.1 Intended Users
Workforce managers, project coordinators, and enterprise administrators within the VerifyMesh decentralized workforce management platform.

### 2.2 Intended Use Cases
- Ranking pre-qualified candidates who meet all mandatory credential and competency requirements for a specific task.
- Providing transparent, feature-level explanations (skill margin surplus, experience leverage, task difficulty offset) to support administrative review.
- Identifying candidates who may require targeted onboarding or peer mentoring on specific task-relevant skills.

### 2.3 Out-of-Scope and Prohibited Uses
- **Autonomous Employment Decisions**: The model must never make automated hiring, assignment, or rejection decisions without human oversight.
- **Gatekeeping / Elimination**: The model must never be used to disqualify applicants who fail Stage 1; Stage 1 deterministic verification owns all compliance gating.
- **High-Stakes Legal Evaluation**: The model is trained on synthetic workforce data and has not been validated against real-world human performance outcomes.

---

## 3. Training & Evaluation Data

### 3.1 Training Dataset
- **File**: `ml/experiments/stage2_refinement/scenario_b_data/task_suitability_training_v3.csv`
- **Source**: Scenario B ("Strict Bottleneck / High-Stakes") synthetic workforce simulation.
- **Total Eligible Records**: $N = 4,675$ applicant-task pairs derived from $1,924$ synthetic applicants and $30$ tasks across $5$ functional domains.
- **Class Balance**: $62.61\%$ positive ($N = 2,927$), $37.39\%$ negative ($N = 1,748$).
- **Data Hygiene**: Zero missing values; strictly isolated to task-specific assessment topics.

### 3.2 Evaluation Methodology
- **Validation Protocol**: 5 seeds ($42, 101, 202, 303, 404$) $\times$ 5-fold `StratifiedGroupKFold` ($25$ folds total) grouped strictly on `applicant_id`.
- **Zero Leakage**: All applicants appearing in validation folds are strictly disjoint from the corresponding training folds ($\text{train\_applicants} \cap \text{val\_applicants} = \emptyset$).
- **Preprocessing Isolation**: `StandardScaler` was fitted exclusively within each training split and applied to validation splits.

---

## 4. Input Features & Model Parameters

$$\text{logit}(P(\text{task\_success} = 1)) = \beta_0 + \sum_{j=1}^{5} \beta_j \left(\frac{x_j - \mu_j}{\sigma_j}\right)$$

where $\beta_0 = +0.5632$ and feature parameters are:

| Index | Feature Name | Description | Mean ($\mu_j$) | Scale ($\sigma_j$) | Coef ($\beta_j$) |
| :---: | :--- | :--- | :---: | :---: | :---: |
| 0 | `weighted_skill_margin` | Task-specific category-weighted competency surplus relative to task cutoffs ($\sum w_k = 1.0$). | $+11.8063$ | $6.5142$ | **$+0.1388$** |
| 1 | `min_skill_margin` | Smallest individual margin across task-required assessment topics ($\min (\text{score}_k - \text{min}_k)$), capturing deficit **depth**. | $+2.3297$ | $7.0637$ | **$+0.3568$** |
| 2 | `deficit_competencies_ratio` | Proportion of required competencies below passing cutoff ($\sum \mathbb{I}(\text{deficit} < 0) / K \in [0, 1]$), capturing deficit **breadth**. | $+0.1160$ | $0.1711$ | **$-0.0546$** |
| 3 | `exp_surplus_tanh` | Saturating verified relevant experience buffer ($\tanh(\text{surplus}/12.0) \in [-1, 1]$). | $+0.7286$ | $0.2979$ | **$+0.2420$** |
| 4 | `difficulty_tier` | Numeric task complexity tier ($1.0 = \text{Foundational}, 2.0 = \text{Standard}, 3.0 = \text{Advanced}$). | $+1.3067$ | $0.5175$ | **$-0.3104$** |

---

## 5. Performance Benchmarks

### 5.1 5-Seed Grouped-CV Performance (Mean ± SD across 25 Folds)

| Metric | Dummy Baseline | Baseline LR v2 (Collinear) | Corrected LR v3 (Hardened) | Random Forest v3 |
| :--- | :---: | :---: | :---: | :---: |
| **ROC-AUC** | $0.5000 \pm 0.0000$ | $0.6776 \pm 0.0184$ | $\mathbf{0.6767 \pm 0.0177}$ | $0.6720 \pm 0.0183$ |
| **PR-AUC** | $0.8130 \pm 0.0000$ | $0.7572 \pm 0.0174$ | $\mathbf{0.7562 \pm 0.0173}$ | $0.7500 \pm 0.0187$ |
| **Macro F1 ($\tau=0.60$)** | $0.3850 \pm 0.0000$ | $0.6293 \pm 0.0163$ | $\mathbf{0.6297 \pm 0.0159}$ | $0.6244 \pm 0.0166$ |
| **Precision ($\tau=0.60$)** | $0.6261 \pm 0.0000$ | $0.7199 \pm 0.0168$ | $\mathbf{0.7252 \pm 0.0168}$ | $0.7167 \pm 0.0174$ |
| **Recall ($\tau=0.60$)** | $1.0000 \pm 0.0000$ | $0.7377 \pm 0.0244$ | $\mathbf{0.7148 \pm 0.0248}$ | $0.7318 \pm 0.0239$ |
| **Balanced Acc ($\tau=0.60$)** | $0.5000 \pm 0.0000$ | $0.6285 \pm 0.0159$ | $\mathbf{0.6305 \pm 0.0153}$ | $0.6237 \pm 0.0162$ |
| **Brier Score** | $0.2341 \pm 0.0000$ | $0.2108 \pm 0.0040$ | $\mathbf{0.2115 \pm 0.0041}$ | $0.2130 \pm 0.0044$ |
| **10-Bin ECE** | $0.0006 \pm 0.0000$ | $0.0290 \pm 0.0116$ | $\mathbf{0.0317 \pm 0.0119}$ | $0.0349 \pm 0.0125$ |

### 5.2 Out-of-Fold Confusion Matrix ($\tau = 0.60$, $N = 4,675$)

```
                  Predicted Negative (0)    Predicted Positive (1)
Actual Failed (0)        TN = 952                  FP = 796
Actual Success (1)       FN = 843                  TP = 2,084
```
- **Precision**: $72.36\%$ (Minimizes risk of allocating unqualified candidates to critical tasks).
- **Recall**: $71.20\%$ (Captures nearly three-quarters of all truly successful matches).

---

## 6. Limitations, Ethical Considerations & Human Oversight

1. **Synthetic Data Disclaimer**: This model was trained on simulated data reflecting parametric assumptions (logistic noise, deterministic log-odds index). It has not been validated on empirical workplace performance. Scores must be interpreted as **model-estimated suitability indices**, not real-world ground-truth probabilities.
2. **Mandatory Human Oversight**: The platform policy dictates that the model serves exclusively as an advisory assistant to the human administrator. Final task assignment authority remains strictly with the human administrator.
3. **Auditing and Version Traceability**: Every prediction logged in the database stores `stage2_model_version = "3.0.0"` alongside the raw feature payload to allow retrospective auditability and continuous model monitoring.

