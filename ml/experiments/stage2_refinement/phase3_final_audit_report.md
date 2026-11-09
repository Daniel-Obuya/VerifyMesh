# VerifyMesh — Phase 3 Final Audit Before Integration

**Audit Date (UTC):** `2026-11-02T10:12:49Z`  
**Audit Script:** [`ml/experiments/stage2_refinement/run_phase3_final_audit.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/experiments/stage2_refinement/run_phase3_final_audit.py)  
**Audit Results JSON:** [`ml/experiments/stage2_refinement/phase3_final_audit_results.json`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/experiments/stage2_refinement/phase3_final_audit_results.json)  
**5-Feature vs. 6-Feature CV Summary CSV:** [`ml/experiments/stage2_refinement/phase3_final_audit_5v6_summary.csv`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/experiments/stage2_refinement/phase3_final_audit_5v6_summary.csv)

---

## 1. Feature Schema Audit

### 1.1 Exact Features Expected by the Serialized Pipeline (`verifymesh_stage2_suitability_pipeline_v2.joblib`)
Loading [`verifymesh_stage2_suitability_pipeline_v2.joblib`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib) in a fresh Python process confirms `pipeline.feature_names_in_` expects the exact ordered 6-feature list:
1. `weighted_skill_margin`
2. `min_skill_margin`
3. `weakest_link_deficit`
4. `exp_surplus_tanh`
5. `difficulty_tier`
6. `cert_satisfied`

### 1.2 Constancy of `cert_satisfied` Across Stage 1-Eligible Records
Because Stage 1 deterministically enforces mandatory certification possession (`cert_satisfied == 1`) before any candidate reaches Stage 2:
- **Scenario B (`N = 4,675` eligible rows, `1,924` unique applicants):** `min = 1.0`, `max = 1.0`, `std = 0.0`, `unique_values = [1.0]` (`is_constant_one = True`).
- **Scenario A (`N = 1,183` eligible rows, `503` unique applicants):** `min = 1.0`, `max = 1.0`, `std = 0.0`, `unique_values = [1.0]` (`is_constant_one = True`).

In the 6-feature pipeline (`StandardScaler` + L2 `LogisticRegression`), `StandardScaler` maps `cert_satisfied` to `(1.0 - 1.0) / 1.0 = 0.0` for every eligible candidate, and L2 regularization assigns it a standardized weight of exactly `0.000000`.

### 1.3 Five-Feature vs. Six-Feature Applicant-Grouped Cross-Validation Comparison
Using the identical `5 Seeds × 5-Fold StratifiedGroupKFold` (`25` outer folds grouped by `applicant_id`, seeds `[42, 123, 456, 789, 2026]`), we evaluated `LR_5Feat_NoCert` (`weighted_skill_margin`, `min_skill_margin`, `weakest_link_deficit`, `exp_surplus_tanh`, `difficulty_tier`) against `LR_6Feat_WithCert`:

| Dataset | Model | Features | Threshold Policy | Threshold ($\tau$) | ROC-AUC | Brier Score | Log-Loss | 10-Bin ECE | Accuracy | Balanced Acc | Pos Precision | Pos Recall | Pos F1 | Failure Recall | Macro F1 |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`scenario_b`** (`N=4,675`) | `LR_6Feat_WithCert` | 6 | `fixed_050` | `0.5000` | `0.6772 ± 0.0203` | `0.2110 ± 0.0042` | `0.6110 ± 0.0098` | `0.0298 ± 0.0117` | `67.23%` | `59.97%` | `68.36%` | `88.74%` | `0.7722` | `31.20%` | `0.5939` |
| **`scenario_b`** (`N=4,675`) | **`LR_5Feat_NoCert`** | **5** | `fixed_050` | `0.5000` | **`0.6772 ± 0.0203`** | **`0.2110 ± 0.0042`** | **`0.6110 ± 0.0098`** | **`0.0298 ± 0.0117`** | **`67.23%`** | **`59.97%`** | **`68.36%`** | **`88.74%`** | **`0.7722`** | **`31.20%`** | **`0.5939`** |
| **`scenario_b`** (`N=4,675`) | `LR_6Feat_WithCert` | 6 | `inner_bal_acc` | `0.6220` | `0.6772 ± 0.0203` | `0.2110 ± 0.0042` | `0.6110 ± 0.0098` | `0.0298 ± 0.0117` | `64.23%` | `62.93%` | `73.00%` | `68.09%` | `0.7039` | `57.76%` | `0.6252` |
| **`scenario_b`** (`N=4,675`) | **`LR_5Feat_NoCert`** | **5** | `inner_bal_acc` | `0.6220` | **`0.6772 ± 0.0203`** | **`0.2110 ± 0.0042`** | **`0.6110 ± 0.0098`** | **`0.0298 ± 0.0117`** | **`64.23%`** | **`62.93%`** | **`73.00%`** | **`68.09%`** | **`0.7039`** | **`57.76%`** | **`0.6252`** |
| **`scenario_b`** (`N=4,675`) | `LR_6Feat_WithCert` | 6 | `inner_macro_f1` | `0.6012` | `0.6772 ± 0.0203` | `0.2110 ± 0.0042` | `0.6110 ± 0.0098` | `0.0298 ± 0.0117` | `65.27%` | `62.61%` | `71.92%` | `73.15%` | `0.7247` | `52.06%` | `0.6262` |
| **`scenario_b`** (`N=4,675`) | **`LR_5Feat_NoCert`** | **5** | `inner_macro_f1` | `0.6012` | **`0.6772 ± 0.0203`** | **`0.2110 ± 0.0042`** | **`0.6110 ± 0.0098`** | **`0.0298 ± 0.0117`** | **`65.27%`** | **`62.61%`** | **`71.92%`** | **`73.15%`** | **`0.7247`** | **`52.06%`** | **`0.6262`** |
| **`scenario_b`** (`N=4,675`) | `LR_6Feat_WithCert` | 6 | `selected_fixed_060` | `0.6000` | `0.6772 ± 0.0203` | `0.2110 ± 0.0042` | `0.6110 ± 0.0098` | `0.0298 ± 0.0117` | `65.54%` | `62.79%` | `71.96%` | `73.71%` | `0.7281` | `51.87%` | `0.6287` |
| **`scenario_b`** (`N=4,675`) | **`LR_5Feat_NoCert`** | **5** | `selected_fixed_060` | `0.6000` | **`0.6772 ± 0.0203`** | **`0.2110 ± 0.0042`** | **`0.6110 ± 0.0098`** | **`0.0298 ± 0.0117`** | **`65.54%`** | **`62.79%`** | **`71.96%`** | **`73.71%`** | **`0.7281`** | **`51.87%`** | **`0.6287`** |
| **`scenario_a`** (`N=1,183`) | `LR_6Feat_WithCert` | 6 | `selected_fixed_060` | `0.6000` | `0.6095 ± 0.0320` | `0.2154 ± 0.0049` | `0.6213 ± 0.0110` | `0.0413 ± 0.0184` | `65.53%` | `56.89%` | `70.37%` | `83.18%` | `0.7621` | `30.59%` | `0.5670` |
| **`scenario_a`** (`N=1,183`) | **`LR_5Feat_NoCert`** | **5** | `selected_fixed_060` | `0.6000` | **`0.6095 ± 0.0320`** | **`0.2154 ± 0.0049`** | **`0.6213 ± 0.0110`** | **`0.0413 ± 0.0184`** | **`65.53%`** | **`56.89%`** | **`70.37%`** | **`83.18%`** | **`0.7621`** | **`30.59%`** | **`0.5670`** |

- **Maximum absolute predicted probability difference across all 25 Scenario B outer folds (`23,375` out-of-fold evaluations):** `3.331e-16` (machine epsilon).
- **Maximum absolute predicted probability difference across all 25 Scenario A outer folds (`5,915` out-of-fold evaluations):** `4.441e-16` (machine epsilon).
- **Maximum absolute predicted probability difference on the full 4,675-row fit:** `2.220e-16`.
- **Learned Parameters Comparison (`LR_5Feat_NoCert` vs. `LR_6Feat_WithCert`):**
  - Intercept: `+0.552574` (identical to 6 decimal places)
  - `weighted_skill_margin`: $\beta = +0.188595$ (identical)
  - `min_skill_margin`: $\beta = +0.186129$ (identical)
  - `weakest_link_deficit`: $\beta = +0.223144$ (identical)
  - `exp_surplus_tanh`: $\beta = +0.236757$ (identical)
  - `difficulty_tier`: $\beta = -0.320832$ (identical)
- **Recommendation:** **Retain the simpler 5-feature model (`LR_5Feat_NoCert`)** once approved, as removing the zero-variance `cert_satisfied` column eliminates a redundant input feature while preserving 100% mathematical and empirical equivalence.

### 1.4 Consistency of `weakest_link_deficit = min(0.0, min_skill_margin)` in Training and Inference
In [`src/stage2_feature_engineering.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/src/stage2_feature_engineering.py):
- **Batch Training Mode (`compute_stage2_features_dataframe`):** Computes `np.minimum(0.0, min_skill_margin)`. Verified across all `4,675` Scenario B rows (`1,716` rows with negative `min_skill_margin`, `2,959` rows with non-negative `min_skill_margin`) and all `1,183` Scenario A rows (`448` negative, `735` non-negative) with `max_abs_diff = 0.0`.
- **Single-Pair Inference Mode (`build_complete_stage2_feature_dict`):** Computes `min(0.0, min_skill_margin)`. Verified against batch DataFrame output across 150 sampled rows per dataset with `max_abs_diff = 0.0`.

---

## 2. Threshold Evaluation at Selected Threshold ($\tau = 0.60$)

### 2.1 Held-Out Grouped-CV Metrics at $\tau = 0.60$ (`LR_5Feat_NoCert` / `LR_6Feat_WithCert`)
Evaluated on outer held-out applicant-grouped folds (`5 Seeds × 5 Folds = 25 Folds`):

| Metric | Scenario B (`N = 4,675`, `1,924` Applicants) | Scenario A (`N = 1,183`, `503` Applicants) |
| :--- | :---: | :---: |
| **ROC-AUC (Threshold-Free)** | **`0.6772 ± 0.0203`** | `0.6095 ± 0.0320` |
| **Brier Score** | **`0.2110 ± 0.0042`** | `0.2154 ± 0.0049` |
| **Log-Loss** | **`0.6110 ± 0.0098`** | `0.6213 ± 0.0110` |
| **10-Bin ECE** | **`0.0298 ± 0.0117`** | `0.0413 ± 0.0184` |
| **Positive Precision (`task_success = 1`)** | **`71.96% ± 1.08%`** | `70.37% ± 1.47%` |
| **Positive Recall (`task_success = 1`)** | **`73.71% ± 1.99%`** | `83.18% ± 3.26%` |
| **Positive F1-Score** | **`0.7281 ± 0.0116`** | `0.7621 ± 0.0174` |
| **Macro F1-Score** | **`0.6287 ± 0.0138`** | `0.5670 ± 0.0263` |
| **Balanced Accuracy** | **`62.79% ± 1.38%`** | `56.89% ± 2.34%` |
| **Failure Recall (`task_success = 0`)** | **`51.87% ± 2.83%`** | `30.59% ± 4.88%` |
| **Failure Precision (`task_success = 0`)** | **`54.12% ± 1.88%`** | `48.05% ± 4.55%` |
| **Overall Accuracy** | **`65.54% ± 1.29%`** | `65.53% ± 2.16%` |

### 2.2 Candidate Distribution Across Advisory Tiers (Held-Out Grouped-CV Predictions)
Across the `4,675` Stage 1-eligible candidate-task pairs in Scenario B (`23,375` total out-of-fold evaluations across 5 seeds):

| Advisory Tier | Probability Range | Mean Candidates per Seed (`N = 4,675`) | % of Eligible Candidates | Empirical Simulated Task Success Rate | Operational Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Strong Fit** | $P \ge 0.60$ | **`2,998.6`** | **`64.14%`** | **`71.95%`** | Exceeds $\tau = 0.60$; strong positive competency margin and low bottleneck risk. |
| **Moderate Fit** | $0.48 \le P < 0.60$ | **`915.2`** | **`19.58%`** | **`54.63%`** | Meets Stage 1 rules; borderline margin or high task difficulty requiring administrator comparison. |
| **Needs Review** | $P < 0.48$ | **`761.2`** | **`16.28%`** | **`35.42%`** | Meets Stage 1 overall rules, but exhibits sub-skill bottleneck deficits (`weakest_link_deficit < 0`) warranting targeted review. |

*(Identical tier counts and percentages hold for both `LR_5Feat_NoCert` and `LR_6Feat_WithCert`.)*

### 2.3 Verification of Inner-Fold Precision Constraint ($\text{Precision}_{\text{pos}} \ge 0.68$)
- In every one of the 25 outer folds (`5 seeds × 5 folds`), threshold selection was performed **exclusively on inner 3-fold `StratifiedGroupKFold` out-of-fold predictions** computed within the outer training split, without consulting outer validation outcomes.
- Across all 25 outer folds on Scenario B:
  - **100% of inner folds (`25/25`) satisfied $\text{Precision}_{\text{inner}} \ge 0.68$** (`all_inner_folds_satisfied_precision_ge_068 = True`).
  - Inner out-of-fold positive precision ranged from **`0.7109` to `0.7332`** (mean = **`0.7213`**).
  - Inner selected thresholds ranged tightly between **`0.58` and `0.62`** with mean **`0.6012 ± 0.0097`**.
  - When those inner-selected thresholds were applied to the held-out outer validation folds, outer positive precision averaged **`0.7192 ± 0.0150`**.

---

## 3. Serialization Verification

### 3.1 Fresh-Process Pipeline Load & Prediction Parity
We verified [`ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib) and [`ml/metadata/verifymesh_stage2_metadata_v2.json`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/metadata/verifymesh_stage2_metadata_v2.json):
- **Expected Feature Order Match:** `list(loaded_pipeline.feature_names_in_) == metadata["feature_schema"]["ordered_features"]` (`True`).
- **In-Memory vs. Loaded Pipeline Parity:** Comparing `loaded_pipeline.predict_proba(X_full)[:, 1]` against a freshly fitted in-memory pipeline over all `4,675` records yields `max_abs_diff = 0.0`.
- **Finite & Bounded Probabilities:**
  - `all_probabilities_finite = True` (`np.all(np.isfinite(p))`)
  - `all_probabilities_within_0_1 = True` (`min = 0.010269`, `max = 0.911036`, `mean = 0.626127`)
- **SHA-256 Integrity Check:**
  - Recalculated SHA-256 of `.joblib`: `70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a`
  - Recorded SHA-256 in metadata JSON: `70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a`
  - Exact match: **`True`**
- **Recorded Runtime Environment:**
  - Python: `3.13.3 (tags/v3.13.3:6280bb5, Apr 8 2025, 14:47:33) [MSC v.1943 64 bit (AMD64)]`
  - `scikit-learn`: `1.8.0`
  - `numpy`: `2.3.4`
  - `pandas`: `2.3.3`
  - `joblib`: `1.5.3`
- **Metadata Completeness:** Confirmed that [`verifymesh_stage2_metadata_v2.json`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/metadata/verifymesh_stage2_metadata_v2.json) accurately records the model SHA-256, training dataset SHA-256 hashes (`synthetic_applicant_task_pairs.csv`: `19f4736c456eb00e3d97c46f6b473ab9a0cb3160f0b61a7bf85d40299c00e55d`, `task_suitability_training.csv`: `d8968158d91746b2aa1e976a9d63f1e569b4e1192647e185b8324bf42912b513`), feature formulas, scaler means/scales, standardized coefficients, inner-CV threshold policy, advisory tier thresholds, and held-out grouped-CV metrics.

---

## 4. Final Safety and Architecture Checks

1. **Stage 1 Remains Authoritative:** Confirmed (`stage1_gatekeeper_authoritative = True`). Stage 1 deterministic rules (mandatory certification, minimum experience, minimum assessment score, and category competency rules) act as an authoritative gatekeeper.
2. **Ineligible Applicants Never Passed to Stage 2:** Confirmed (`ineligible_excluded_from_stage2_training_and_cv = True`). All Phase 1–3 training and cross-validation experiments filtered strictly on `stage1_eligible == 1`, and Phase 4 integration will enforce `if meets_all:` before calling `task_suitability_engine.predict(...)` in [`backend/db.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/backend/db.py).
3. **Advisory Ranking Signals Only:** Confirmed (`predictions_strictly_advisory_ranking_signals = True`). Predicted probabilities represent estimated probabilities of simulated task success (`Strong Fit`, `Moderate Fit`, `Needs Review`) to support administrator comparison, never automated hiring or task allocation.
4. **Legacy & Existing Serialized Artifacts Untouched:** Confirmed:
   - [`ml/models/verifymesh_final_optimized_pipeline.joblib`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/models/verifymesh_final_optimized_pipeline.joblib): Untouched (`SHA-256: 8bc737a96a3b73e20d19327ee07a7f501c5c80eb951006e2b68ae0c0c4b33572`)
   - [`ml/metadata/verifymesh_threshold_metadata.json`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/metadata/verifymesh_threshold_metadata.json): Untouched (`SHA-256: 81a261e4831e33c8fe0077392598f8ffd106f7d404e55f6244ff29cac45c82ab`)
   - [`backend/models/binary_eligibility_model.pkl`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/backend/models/binary_eligibility_model.pkl): Untouched (`SHA-256: 4f0ff4421ff7ffc61e948e0ef25f77729235480d271ee60b71b5762d415c82bf`)
   - [`ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib): Unmodified during this audit (`SHA-256: 70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a`), awaiting approval to finalize the 5-feature version.

