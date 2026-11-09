# VerifyMesh — Phase 3 Final Model Selection, Calibration & Serialization Report

## 1. Probability Calibration Audit (`5 Seeds × 5-Fold StratifiedGroupKFold`)

Because Stage 2 predicted probabilities are used both for **candidate ranking** and **Admin UI display**, we evaluated whether post-hoc probability calibration (`CalibratedClassifierCV` with Sigmoid/Platt scaling or Isotonic regression) improves upon uncalibrated L2-regularized Logistic Regression (`Extended_LR_6Feat_WeakestLink`).

| Dataset | Calibration Variant | ROC-AUC (Mean ± SD) | Brier Score (Mean ± SD) | Log-Loss (Mean ± SD) | 10-Bin ECE (Mean ± SD) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`scenario_b` (`N=4,675`)** | **Uncalibrated `Extended_LR_6Feat_WeakestLink`** | **0.6772 ± 0.0203** | **0.2110 ± 0.0042** | **0.6110 ± 0.0098** | **0.0298 ± 0.0117** |
| **`scenario_b` (`N=4,675`)** | Sigmoid (Platt) Calibrated LR | 0.6773 ± 0.0203 | 0.2110 ± 0.0041 | 0.6110 ± 0.0096 | 0.0300 ± 0.0120 |
| **`scenario_b` (`N=4,675`)** | Isotonic Calibrated LR | 0.6768 ± 0.0201 | 0.2119 ± 0.0048 | 0.6266 ± 0.0393 | 0.0356 ± 0.0132 |
| **`scenario_a` (`N=1,183`)** | **Uncalibrated `Extended_LR_6Feat_WeakestLink`** | **0.6095 ± 0.0320** | 0.2154 ± 0.0049 | 0.6213 ± 0.0110 | 0.0413 ± 0.0184 |
| **`scenario_a` (`N=1,183`)** | Sigmoid (Platt) Calibrated LR | 0.6089 ± 0.0318 | **0.2153 ± 0.0043** | **0.6211 ± 0.0095** | **0.0405 ± 0.0170** |
| **`scenario_a` (`N=1,183`)** | Isotonic Calibrated LR | 0.6085 ± 0.0324 | 0.2169 ± 0.0057 | 0.6425 ± 0.0624 | 0.0562 ± 0.0241 |

### Calibration Conclusion
- **Uncalibrated L2 Logistic Regression (`C=0.5`, unweighted) is already intrinsically well-calibrated** because Logistic Regression directly minimizes cross-entropy (proper scoring rule) under the canonical logistic link function without artificial class-weight distortion.
- Its 10-bin Expected Calibration Error (ECE) on `scenario_b` is **2.98% (`0.0298`)** and Brier score is **0.2110**, matching Sigmoid calibration to 4 decimal places while avoiding nested `CalibratedClassifierCV` wrapper complexity and preserving direct coefficient interpretability.

---

## 2. Final Stage 2 Model Specification (`VerifyMesh_Stage2_Suitability_LR_v2`)

- **Serialized Pipeline Path**: `ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib`
  - **SHA-256**: `70dc562ed5a80c68b791432785e044a2c21cc3f9a7eb16c696dec9f10378862a`
- **Serialized Metadata Path**: `ml/metadata/verifymesh_stage2_metadata_v2.json`
- **Legacy Artifacts Preserved Untouched**:
  - `ml/models/verifymesh_final_optimized_pipeline.joblib`
  - `ml/metadata/verifymesh_threshold_metadata.json`

### Learned Parameters (Standardized Log-Odds Equation)

$$\text{logit}(P(\text{task\_success} = 1)) = \beta_0 + \sum_{j=1}^{6} \beta_j \left(\frac{x_j - \mu_j}{\sigma_j}\right)$$

where $\beta_0 = +0.552574$ and:

| Order | Feature Name | Scaler Mean ($\mu_j$) | Scaler Scale ($\sigma_j$) | Standardized Coefficient ($\beta_j$) | Domain Interpretation |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 0 | `weighted_skill_margin` | `11.8063` | `6.5142` | **`+0.1886`** | Higher category-weighted competency surplus increases predicted task success probability. |
| 1 | `min_skill_margin` | `2.3297` | `7.0637` | **`+0.1861`** | Higher weakest-skill margin across all 5 dimensions increases predicted success probability. |
| 2 | `weakest_link_deficit` | `-1.6129` | `3.4743` | **`+0.2231`** | Non-positive bottleneck term ($\le 0$); any sub-skill deficit below task target reduces predicted probability. |
| 3 | `exp_surplus_tanh` | `0.7286` | `0.2979` | **`+0.2368`** | Diminishing-returns relevant experience buffer ($\tanh(\text{surplus}/12)$) increases predicted probability. |
| 4 | `difficulty_tier` | `1.3067` | `0.5175` | **`-0.3208`** | Higher task complexity (`Tier 1 -> Tier 2 -> Tier 3`) lowers baseline success probability. |
| 5 | `cert_satisfied` | `1.0000` | `1.0000` | **`0.0000`** | Constant `1.0` across all Stage 1 eligible records; zeroed by L2 regularization. |

---

## 3. Operational Decision Threshold & Advisory Tiers

- **Primary Ranking Signal**: Continuous `predicted_success_probability` $\in (0, 1)$, used to rank Stage 1 eligible applicants in descending order (`eligible_rank = 1, 2, ...`).
- **Selected Binary Advisory Threshold**: **$\tau = 0.60$** (selected strictly via 5-seed inner-OOF `StratifiedGroupKFold` Macro F1 optimization subject to Positive Precision $\ge 0.68$).
  - Candidates with $P \ge 0.60$: `suitability_label = "Suitable"` (`advisory_tier = "Strong Fit"`).
  - Candidates with $0.48 \le P < 0.60$: `suitability_label = "Needs Review"` (`advisory_tier = "Moderate Fit"`).
  - Candidates with $P < 0.48$: `suitability_label = "Needs Review"` (`advisory_tier = "Needs Review"`).
  - Candidates failing Stage 1 (`is_eligible == False`): **Never scored by Stage 2** (`predicted_success_probability = None`, `suitability_label = "Ineligible — Stage 1 Gate Failed"`, `eligible_rank = None`).

