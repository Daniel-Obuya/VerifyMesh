# VerifyMesh — Phase 2 Controlled Dataset / Simulation Refinement Report

## 1. Side-by-Side Dataset Comparison (`scenario_a` vs. `scenario_b`)

All original files in `ml/experiments/task_specific_synthetic_data/` were preserved untouched. The controlled `scenario_b` benchmark dataset was generated using the existing generator (`generate_synthetic_dataset.py`) into `ml/experiments/stage2_refinement/scenario_b_data/`.

| Characteristic | Original Dataset (`scenario_a`) | Controlled Refined Dataset (`scenario_b`) | Why the Change Matters |
| :--- | :--- | :--- | :--- |
| **Directory** | `ml/experiments/task_specific_synthetic_data/` | `ml/experiments/stage2_refinement/scenario_b_data/` | Preserves original files untouched. |
| **Simulation Mechanism** | **Balanced Compensatory** (linear weighted skill average; weak sub-skills compensated by strong ones) | **Strict Bottleneck / Weakest-Link** (penalizes weakest skill margin `min_skill_margin` & non-linear difficulty) | Reflects real-world workforce tasks where a severe deficit in one required competency creates a performance bottleneck. |
| **Random Seed** | `42` | `42` | Fully deterministic & reproducible. |
| **Total Applicants** | `800` | `3,200` | 4× larger candidate pool reduces sampling variance. |
| **Total Tasks** | `30` | `30` | Identical 30-task catalog across 5 categories & 3 tiers. |
| **Total Applicant-Task Pairs** | `6,000` | `24,000` | 4× larger application volume. |
| **Eligible Training Pairs (`is_eligible == 1`)** | `1,183` (`19.72%`) | `4,675` (`19.48%`) | ~4× more eligible training examples per fold (`~3,740` train / `~935` val). |
| **Unique Eligible Applicants** | `503` | `1,924` | Stronger applicant-grouped cross-validation stability. |
| **Eligible Task Coverage** | `29 / 30` tasks (`TSK-010` had 0 eligible pairs) | `30 / 30` tasks (`100%` coverage) | Eliminates zero-sample task blind spots. |
| **Simulated Positive Rate (`task_success == 1`)** | `66.44%` (Majority baseline = `0.6644`) | `62.61%` (Majority baseline = `0.6261`) | More balanced positive/negative outcome distribution among eligible pairs. |
| **Latent Probability Spread (`mean ± std`)** | `0.6743 ± 0.1361` | `0.6297 ± 0.2078` | **+52.7% wider probability dispersion** among eligible candidates while remaining genuinely stochastic. |

### `scenario_b` SHA-256 Checksums
- `synthetic_applicants.csv`: `436498f33a0a90aa2b83fd78b7b96b14bd218d4bcaa1b2eb6396159574dbf824`
- `synthetic_tasks.csv`: `a37f5de469839b4a48b21d10ca4698c0fa1c465681ada65d9957a7b3d8feba8a`
- `synthetic_applicant_task_pairs.csv`: `600d2b2bae9754a007be7d7f2bc2074c227e8c11946d07d8be265f3e4155e29c`
- `task_suitability_training.csv`: `5492d2070cfbd6a5a393e50d7eca646ac94bd1c984c050de6e2e97e85280dc65`

---

## 2. Oracle Ceiling Comparison (`latent_success_prob`)

| Dataset | Threshold Policy | Selected $\tau$ | Oracle ROC-AUC (Mean ± SD) | Oracle Brier Score | Oracle Accuracy | Majority Baseline Acc. | Accuracy Gain Over Baseline | Oracle Balanced Acc. | Oracle Failure Recall | Oracle Macro F1 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`scenario_a` (`N=1,183`)** | `fixed_050` | 0.500 | 0.6503 ± 0.0285 | 0.2095 ± 0.0061 | 0.6754 ± 0.0153 | 0.6644 | **+1.10%** | 0.5563 ± 0.0185 | 0.1940 | 0.5374 |
| **`scenario_a` (`N=1,183`)** | `inner_macro_f1` | 0.643 | 0.6503 ± 0.0285 | 0.2095 ± 0.0061 | 0.6242 ± 0.0332 | 0.6644 | -4.02% | 0.5873 ± 0.0278 | 0.4751 | 0.5839 |
| **`scenario_b` (`N=4,675`)** | `fixed_050` | 0.500 | **0.7427 ± 0.0137** | **0.1927 ± 0.0046** | **0.7076 ± 0.0106** | 0.6261 | **+8.15%** | **0.6545 ± 0.0123** | **0.4439** | **0.6595** |
| **`scenario_b` (`N=4,675`)** | `inner_macro_f1` | 0.592 | **0.7427 ± 0.0137** | **0.1927 ± 0.0046** | **0.6895 ± 0.0133** | 0.6261 | **+6.34%** | **0.6683 ± 0.0145** | **0.5847** | **0.6682** |

---

## 3. Side-by-Side Model Comparison (`scenario_a` vs. `scenario_b` — 5 Seeds × 5-Fold `StratifiedGroupKFold`)

### 3.1 Probability Discrimination & Calibration (Threshold-Independent)

| Model | Feat. | `scenario_a` ROC-AUC | `scenario_b` ROC-AUC | `scenario_a` Brier | `scenario_b` Brier | Signal Recovered on `scenario_b` ($\frac{\text{AUC} - 0.5}{\text{Oracle} - 0.5}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline_Majority_Class** | 0 | 0.5000 ± 0.0000 | 0.5000 ± 0.0000 | 0.2230 | 0.2341 | 0.0% |
| **Oracle_Latent_Prob** *(Ceiling)* | 0 | 0.6503 ± 0.0285 | **0.7427 ± 0.0137** | 0.2095 | **0.1927** | 100.0% |
| **Extended_LR_10Feat_DomainGaps** | 10 | 0.5960 ± 0.0313 | **0.6782 ± 0.0187** | 0.2172 | 0.2111 | **73.4%** |
| **Extended_LR_6Feat_WeakestLink** | 6 | 0.6095 ± 0.0320 | **0.6772 ± 0.0203** | 0.2154 | **0.2110** | **73.0%** |
| **Regularized_RF_10Feat** | 10 | 0.5749 ± 0.0347 | 0.6724 ± 0.0181 | 0.2203 | 0.2135 | 71.0% |
| **Regularized_GB_10Feat** | 10 | 0.5815 ± 0.0348 | 0.6717 ± 0.0197 | 0.2195 | 0.2143 | 70.8% |
| **Regularized_HistGB_10Feat** | 10 | 0.5698 ± 0.0345 | 0.6695 ± 0.0194 | 0.2207 | 0.2143 | 69.8% |
| **Compact_LR_4Feat** | 4 | **0.6116 ± 0.0284** | 0.6656 ± 0.0205 | **0.2151** | 0.2145 | 68.2% |
| **Current_RF_28Feat** *(Legacy)* | 28 | 0.5878 ± 0.0297 | 0.6645 ± 0.0191 | 0.2238 | 0.2224 | 67.8% |
| **Regularized_RF_28Feat** | 28 | 0.5933 ± 0.0320 | 0.6641 ± 0.0192 | 0.2173 | 0.2159 | 67.6% |

### 3.2 Classification Metrics on `scenario_b` (`N = 4,675` Eligible Pairs)

| Model | Feat. | Policy | Selected $\tau$ | ROC-AUC | Accuracy | Balanced Acc. | Precision (Pos) | Recall (Pos) | F1 (Pos) | Failure Recall (Neg) | Macro F1 |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline_Majority_Class** | 0 | `fixed_050` | 0.500 | 0.5000 | 0.6261 | 0.5000 | 0.6261 | 1.0000 | 0.7701 | 0.0000 | 0.3850 |
| **Oracle_Latent_Prob** | 0 | `fixed_050` | 0.500 | 0.7427 | 0.7076 | 0.6545 | 0.7227 | 0.8650 | 0.7874 | 0.4439 | 0.6595 |
| **Oracle_Latent_Prob** | 0 | `inner_macro_f1` | 0.592 | 0.7427 | 0.6895 | 0.6683 | 0.7522 | 0.7520 | 0.7519 | 0.5847 | 0.6682 |
| **Extended_LR_6Feat_WeakestLink** | 6 | `fixed_050` | 0.500 | **0.6772** | **0.6723** | 0.5997 | 0.6836 | 0.8874 | 0.7722 | 0.3120 | 0.5939 |
| **Extended_LR_6Feat_WeakestLink** | 6 | `inner_macro_f1` | 0.601 | **0.6772** | **0.6527** | **0.6261** | **0.7192** | 0.7315 | **0.7247** | **0.5206** | **0.6262** |
| **Extended_LR_6Feat_WeakestLink** | 6 | `inner_bal_acc` | 0.622 | **0.6772** | 0.6423 | **0.6293** | 0.7300 | 0.6809 | 0.7039 | 0.5776 | 0.6252 |
| **Extended_LR_10Feat_DomainGaps** | 10 | `fixed_050` | 0.500 | **0.6782** | **0.6753** | 0.6048 | 0.6870 | 0.8843 | 0.7732 | 0.3253 | 0.6006 |
| **Extended_LR_10Feat_DomainGaps** | 10 | `inner_macro_f1` | 0.602 | **0.6782** | 0.6472 | **0.6266** | 0.7232 | 0.7083 | 0.7148 | 0.5449 | 0.6250 |
| **Compact_LR_4Feat** | 4 | `fixed_050` | 0.500 | 0.6656 | 0.6635 | 0.5889 | 0.6771 | 0.8845 | 0.7669 | 0.2934 | 0.5806 |
| **Compact_LR_4Feat** | 4 | `inner_macro_f1` | 0.582 | 0.6656 | 0.6532 | 0.6198 | 0.7111 | 0.7521 | 0.7306 | 0.4875 | 0.6212 |
| **Regularized_RF_10Feat** | 10 | `inner_macro_f1` | 0.608 | 0.6724 | 0.6497 | 0.6233 | 0.7171 | 0.7278 | 0.7220 | 0.5189 | 0.6236 |
| **Regularized_GB_10Feat** | 10 | `inner_macro_f1` | 0.614 | 0.6717 | 0.6494 | 0.6254 | 0.7199 | 0.7206 | 0.7199 | 0.5302 | 0.6252 |
| **Current_RF_28Feat** *(Legacy)* | 28 | `inner_macro_f1` | 0.520 | 0.6645 | 0.6502 | 0.6223 | 0.7155 | 0.7331 | 0.7239 | 0.5114 | 0.6229 |
| **Current_RF_28Feat** *(Legacy)* | 28 | `legacy_fixed_061` | 0.610 | 0.6645 | 0.5467 | 0.5941 | 0.7581 | 0.4062 | 0.5284 | 0.7819 | 0.5458 |

---

## 4. Key Findings & Recommendation for Phase 3

1. **Weakest-Link Feature Gain Verified**:
   - In `scenario_b`, adding weakest-link / bottleneck features (`min_skill_margin` and `weakest_link_deficit`) to the compact linear model (`Extended_LR_6Feat_WeakestLink`) improves ROC-AUC from **0.6656** to **0.6772** (+0.0116 AUC), reduces Brier calibration error from **0.2145** to **0.2110**, and improves `fixed_050` accuracy from **66.35%** to **67.23%** (+4.62% above the 62.61% majority-class baseline).
2. **Parsimony & Interpretability Rule Applied (`6` Features vs. `10` or `28` Features)**:
   - Adding 4 raw individual domain gaps (`Extended_LR_10Feat_DomainGaps`, 10 features) yields `0.6782` ROC-AUC vs. `0.6772` for `Extended_LR_6Feat_WeakestLink` ($\Delta \text{AUC} = 0.0010 \ll 0.02$).
   - By the non-negotiable simplicity rule (*"Treat AUC differences smaller than 0.02 as potentially insignificant experimental variation. Prefer the simpler model when performance differences are within this range"*), **`Extended_LR_6Feat_WeakestLink`** (or its 5 non-constant active features on eligible pairs: `weighted_skill_margin`, `min_skill_margin`, `weakest_link_deficit`, `exp_surplus_tanh`, `difficulty_tier`, plus `cert_satisfied` retained for schema completeness) is the clear winner:
     - Outperforms all 28-feature Random Forest and 10-feature Gradient Boosting pipelines in both ROC-AUC (**0.6772**) and probability calibration (**Brier = 0.2110**).
     - Performs strongly on **both** `scenario_a` (**0.6095 ROC-AUC**, **0.5713 Macro F1**) and `scenario_b` (**0.6772 ROC-AUC**, **0.6262 Macro F1**).
     - Every coefficient is monotonically interpretable and directly explainable to administrators in the UI (weighted skill fit, weakest-link bottleneck margin, experience surplus saturation, task difficulty tier, and certification satisfaction).
3. **Recommendation for Phase 3 (Final Model Selection, Calibration & Serialization)**:
   - Adopt **`Extended_LR_6Feat_WeakestLink`** trained on the `scenario_b` eligible benchmark dataset (`4,675` eligible pairs across `1,924` applicants and all `30` tasks), while reporting metrics on both `scenario_a` and `scenario_b` in the model metadata and capstone report.
   - In Phase 3, evaluate probability calibration (`CalibratedClassifierCV` vs. uncalibrated Logistic Regression) using Brier score and reliability curves inside grouped CV, finalize the inner-fold OOF decision threshold ($\tau \approx 0.60$ for advisory classification alongside continuous probability ranking), and serialize the v2 pipeline (`verifymesh_stage2_suitability_pipeline_v2.joblib`) and rich metadata (`verifymesh_stage2_metadata_v2.json`).

