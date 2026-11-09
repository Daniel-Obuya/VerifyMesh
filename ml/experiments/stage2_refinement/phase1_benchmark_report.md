# VerifyMesh — Phase 1 Reproducible Baseline & Benchmark Report

## 1. Experimental Protocol & Reproducibility Metadata

- **Evaluation Dataset**: `synthetic_applicant_task_pairs.csv` (`is_eligible == 1`, aligned 1-to-1 with `task_suitability_training.csv`)
  - **Total Eligible Pairs**: `1,183` rows (across `503` unique `applicant_id`s and `29` unique eligible `task_id`s out of 30 tasks)
  - **Class Balance**: `786` positive (`66.44%`) vs. `397` negative (`33.56%`)
  - **Supplementary Sensitivity Set**: `1,127` rows (`assessment_satisfied == 1`, `490` unique `applicant_id`s, `67.26%` positive)
- **Dataset SHA-256 Hashes**:
  - `synthetic_applicants.csv`: `0b34ab0111c4fb21bfaacd5c5a4024ee64b9d42ac01223d208d2a8689cc863ea`
  - `synthetic_tasks.csv`: `a37f5de469839b4a48b21d10ca4698c0fa1c465681ada65d9957a7b3d8feba8a`
  - `synthetic_applicant_task_pairs.csv`: `df833a37c4884116a8091ca773e57099925861621bc4085608373ece3fa05bee`
  - `task_suitability_training.csv`: `15e2cbbaf2be7f545081ddca63905d61ad7b9965a7686ac48a9a24e7005aec7f`
- **Cross-Validation Protocol**:
  - Outer CV: `StratifiedGroupKFold(n_splits=5, shuffle=True)` grouped strictly by `applicant_id`
  - Random Seeds: `[42, 123, 456, 789, 2026]` (`25` total outer evaluation folds per model)
  - Inner Threshold Selection CV: `StratifiedGroupKFold(n_splits=4, shuffle=True)` inside each outer training partition (`oof_train_probs`)
- **Software Environment**:
  - Python `3.13`, `scikit-learn 1.8.0`, `pandas 2.3.3`, `numpy 2.3.4`, `joblib 1.5.3`

---

## 2. Full Benchmark Comparison Table (1,183 Eligible Pairs — Mean ± SD across 25 Grouped Folds)

| Model / Baseline | Features | Threshold Policy | Selected $\tau$ (Mean ± SD) | ROC-AUC (Mean ± SD) | Brier Score (Mean ± SD) | Accuracy (Mean ± SD) | Balanced Acc. (Mean ± SD) | Precision (Class 1) | Recall (Class 1) | F1-Score (Class 1) | Failure Recall (Class 0) | Macro F1 (Mean ± SD) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline_Majority_Class** | 0 | `fixed_050` | 0.500 ± 0.000 | 0.5000 ± 0.0000 | 0.2230 ± 0.0005 | 0.6644 ± 0.0016 | 0.5000 ± 0.0000 | 0.6644 | 1.0000 | 0.7984 | 0.0000 | 0.3992 ± 0.0006 |
| **Oracle_Latent_Prob** *(Ceiling)* | 0 | `fixed_050` | 0.500 ± 0.000 | **0.6503 ± 0.0285** | **0.2095 ± 0.0061** | **0.6754 ± 0.0153** | 0.5563 ± 0.0185 | 0.6930 | 0.9186 | 0.7899 | 0.1940 | 0.5374 ± 0.0262 |
| **Oracle_Latent_Prob** *(Ceiling)* | 0 | `inner_macro_f1` | 0.643 ± 0.021 | **0.6503 ± 0.0285** | **0.2095 ± 0.0061** | 0.6242 ± 0.0332 | 0.5873 ± 0.0278 | 0.7259 | 0.6995 | 0.7105 | 0.4751 | **0.5839 ± 0.0283** |
| **Oracle_Latent_Prob** *(Ceiling)* | 0 | `inner_bal_acc` | 0.694 ± 0.026 | **0.6503 ± 0.0285** | **0.2095 ± 0.0061** | 0.5868 ± 0.0374 | **0.5935 ± 0.0303** | 0.7478 | 0.5732 | 0.6453 | 0.6139 | 0.5715 ± 0.0330 |
| **Compact_LR_4Feat** | 4 | `fixed_050` | 0.500 ± 0.000 | **0.6116 ± 0.0284** | **0.2151 ± 0.0042** | **0.6693 ± 0.0147** | 0.5329 ± 0.0161 | 0.6803 | 0.9479 | 0.7920 | 0.1180 | 0.4919 ± 0.0251 |
| **Compact_LR_4Feat** | 4 | `inner_macro_f1` | 0.631 ± 0.016 | **0.6116 ± 0.0284** | **0.2151 ± 0.0042** | 0.6210 ± 0.0280 | 0.5658 ± 0.0232 | 0.7073 | 0.7339 | 0.7190 | 0.3976 | **0.5646 ± 0.0248** |
| **Compact_LR_4Feat** | 4 | `inner_bal_acc` | 0.689 ± 0.036 | **0.6116 ± 0.0284** | **0.2151 ± 0.0042** | 0.5435 ± 0.0459 | 0.5648 ± 0.0275 | 0.7349 | 0.4999 | 0.5832 | 0.6298 | 0.5282 ± 0.0312 |
| **Compact_LR_4Feat_Balanced** | 4 | `fixed_050` | 0.500 ± 0.000 | 0.6115 ± 0.0282 | 0.2401 ± 0.0055 | 0.5855 ± 0.0288 | 0.5699 ± 0.0238 | 0.7191 | 0.6173 | 0.6633 | 0.5225 | 0.5606 ± 0.0248 |
| **Extended_LR_6Feat_WeakestLink** | 6 | `fixed_050` | 0.500 ± 0.000 | 0.6095 ± 0.0320 | 0.2154 ± 0.0049 | 0.6693 ± 0.0147 | 0.5357 ± 0.0181 | 0.6819 | 0.9420 | 0.7910 | 0.1295 | 0.4987 ± 0.0289 |
| **Extended_LR_6Feat_WeakestLink** | 6 | `inner_macro_f1` | 0.632 ± 0.015 | 0.6095 ± 0.0320 | 0.2154 ± 0.0049 | 0.6294 ± 0.0265 | **0.5717 ± 0.0258** | 0.7107 | 0.7473 | 0.7274 | 0.3962 | **0.5713 ± 0.0267** |
| **Extended_LR_10Feat_DomainGaps** | 10 | `fixed_050` | 0.500 ± 0.000 | 0.5960 ± 0.0313 | 0.2172 ± 0.0047 | 0.6670 ± 0.0157 | 0.5303 ± 0.0187 | 0.6791 | 0.9458 | 0.7905 | 0.1149 | 0.4886 ± 0.0286 |
| **Regularized_RF_28Feat** | 28 | `fixed_050` | 0.500 ± 0.000 | 0.5933 ± 0.0320 | 0.2173 ± 0.0033 | 0.6636 ± 0.0111 | 0.5153 ± 0.0123 | 0.6716 | 0.9661 | 0.7923 | 0.0645 | 0.4518 ± 0.0256 |
| **Regularized_RF_28Feat** | 28 | `inner_macro_f1` | 0.636 ± 0.016 | 0.5933 ± 0.0320 | 0.2173 ± 0.0033 | 0.6281 ± 0.0328 | 0.5612 ± 0.0277 | 0.7034 | 0.7647 | 0.7299 | 0.3577 | 0.5578 ± 0.0278 |
| **Current_RF_28Feat** *(Legacy)* | 28 | `fixed_050` | 0.500 ± 0.000 | 0.5878 ± 0.0297 | 0.2238 ± 0.0038 | 0.6605 ± 0.0198 | 0.5425 ± 0.0224 | 0.6862 | 0.9016 | 0.7791 | 0.1834 | 0.5216 ± 0.0303 |
| **Current_RF_28Feat** *(Legacy)* | 28 | `inner_macro_f1` | 0.563 ± 0.015 | 0.5878 ± 0.0297 | 0.2238 ± 0.0038 | 0.6146 ± 0.0315 | 0.5586 ± 0.0277 | 0.7037 | 0.7289 | 0.7132 | 0.3883 | 0.5553 ± 0.0266 |
| **Current_RF_28Feat** *(Legacy)* | 28 | `legacy_fixed_061` | 0.610 ± 0.000 | 0.5878 ± 0.0297 | 0.2238 ± 0.0038 | 0.5273 ± 0.0279 | 0.5514 ± 0.0260 | 0.7174 | 0.4781 | 0.5716 | 0.6247 | 0.5204 ± 0.0256 |
| **Regularized_GB_10Feat** | 10 | `fixed_050` | 0.500 ± 0.000 | 0.5815 ± 0.0348 | 0.2195 ± 0.0036 | 0.6610 ± 0.0077 | 0.5078 ± 0.0078 | 0.6680 | 0.9738 | 0.7924 | 0.0418 | 0.4342 ± 0.0136 |
| **Regularized_RF_10Feat** | 10 | `fixed_050` | 0.500 ± 0.000 | 0.5749 ± 0.0347 | 0.2203 ± 0.0039 | 0.6615 ± 0.0081 | 0.5063 ± 0.0100 | 0.6673 | 0.9784 | 0.7934 | 0.0343 | 0.4279 ± 0.0203 |
| **Regularized_HistGB_10Feat** | 10 | `fixed_050` | 0.500 ± 0.000 | 0.5698 ± 0.0345 | 0.2207 ± 0.0040 | 0.6605 ± 0.0085 | 0.5085 ± 0.0106 | 0.6684 | 0.9707 | 0.7916 | 0.0464 | 0.4371 ± 0.0209 |

---

## 3. Sensitivity Check on the 1,127-Row Subset (`assessment_satisfied == 1`)

| Model / Baseline | Features | ROC-AUC (1,183 Set) | ROC-AUC (1,127 Subset) | Brier Score (1,183 Set) | Brier Score (1,127 Subset) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Oracle_Latent_Prob** | 0 | 0.6503 ± 0.0285 | 0.6491 ± 0.0272 | 0.2095 | 0.2072 |
| **Compact_LR_4Feat** | 4 | **0.6116 ± 0.0284** | **0.6078 ± 0.0340** | **0.2151** | **0.2133** |
| **Extended_LR_6Feat_WeakestLink** | 6 | 0.6095 ± 0.0320 | 0.6036 ± 0.0362 | 0.2154 | 0.2136 |
| **Extended_LR_10Feat_DomainGaps** | 10 | 0.5960 ± 0.0313 | 0.5955 ± 0.0336 | 0.2172 | 0.2148 |
| **Regularized_RF_28Feat** | 28 | 0.5933 ± 0.0320 | 0.5903 ± 0.0264 | 0.2173 | 0.2154 |
| **Current_RF_28Feat** | 28 | 0.5878 ± 0.0297 | 0.5825 ± 0.0242 | 0.2238 | 0.2219 |
| **Regularized_GB_10Feat** | 10 | 0.5815 ± 0.0348 | 0.5746 ± 0.0329 | 0.2195 | 0.2175 |
| **Regularized_RF_10Feat** | 10 | 0.5749 ± 0.0347 | 0.5659 ± 0.0314 | 0.2203 | 0.2182 |
| **Regularized_HistGB_10Feat** | 10 | 0.5698 ± 0.0345 | 0.5628 ± 0.0340 | 0.2207 | 0.2190 |

---

## 4. Scientific & Methodological Interpretation

1. **Theoretical Ceiling (`Oracle_Latent_Prob`)**:
   - Even with exact knowledge of the true noiseless data-generating probability `latent_success_prob`, the maximum achievable ROC-AUC on `scenario_a` (`N = 1,183` eligible pairs) is **0.6503 ± 0.0285** and the maximum accuracy at $\tau = 0.50$ is **67.54%** (only +1.10% above the **66.44%** majority-class baseline).
   - This occurs for two fundamental reasons:
     1. **Range Restriction after Stage 1 Gatekeeping**: Stage 1 deterministically removes all clearly unqualified pairs (`4,817` of `6,000` pairs), truncating the lower tail of the feature space so that surviving candidates cluster within a narrow band of positive margins.
     2. **Irreducible Bernoulli + Gaussian Simulation Noise**: In `scenario_a`, latent log-odds include $\epsilon \sim \mathcal{N}(0, 0.45^2)$ followed by a Bernoulli draw $y \sim \text{Bernoulli}(p)$. When $p \in [0.55, 0.78]$, the Bayes error rate $\mathbb{E}[\min(p, 1-p)]$ is approximately $32.5\%$, capping theoretical accuracy at $\approx 67.5\%$.
2. **Why `Compact_LR_4Feat` Outperforms 28-Feature Tree Ensembles**:
   - `Compact_LR_4Feat` achieves **0.6116 ± 0.0284 ROC-AUC** (recovering **74.2% of the learnable signal** above random chance: $(0.6116 - 0.50) / (0.6503 - 0.50) = 74.2\%$) and the lowest (best) Brier score (**0.2151 ± 0.0042**).
   - By contrast, `Current_RF_28Feat` achieves **0.5878 ± 0.0297 ROC-AUC** (only **58.4%** of the learnable signal) and a Brier score of **0.2238** (worse than the uninformative majority-class baseline Brier score of **0.2230** due to cost-sensitive class weights `{0: 1.5, 1: 1.0}` distorting probability calibration).
   - Tree ensembles split axis-aligned rectangles across 28 collinear raw and gap columns; in a high-noise, range-restricted regime ($N \approx 946$ training rows per fold), axis-aligned splits fit the Gaussian noise $\epsilon$, whereas regularized linear log-odds directly match the underlying monotonic domain relationship.
3. **Why `Extended_LR_6Feat_WeakestLink` Matches `Compact_LR_4Feat` on `scenario_a`**:
   - On `scenario_a` (Compensatory), `Extended_LR_6Feat_WeakestLink` achieves **0.6095 ± 0.0320 ROC-AUC** ($\Delta \text{AUC} = -0.0021$, well within the $< 0.02$ experimental noise band) and achieves the highest Macro F1 (**0.5713**) and Balanced Accuracy (**0.5717**) under `inner_macro_f1` threshold selection.
   - Because `scenario_a` does not penalize the weakest skill (`min_skill_margin`) beyond its linear contribution to `weighted_skill_margin`, weakest-link features do not add extra ROC-AUC on `scenario_a`, whereas on `scenario_b` (Strict Bottleneck) they directly capture the bottleneck penalty.
4. **Threshold Selection Analysis (Training-Fold OOF vs. Post-Hoc Test Selection)**:
   - Under `fixed_050`, models with well-calibrated probabilities (`Compact_LR_4Feat`, `Extended_LR_6Feat_WeakestLink`) predict the positive class for most eligible pairs because the true base rate of eligible pairs is `66.44%`, yielding **66.93% accuracy** (+0.49% over majority baseline) but low failure recall (**11.8%–13.0%**).
   - When the operational goal is to flag borderline eligible candidates (`Needs Review` vs `Strong Fit`), selecting $\tau$ inside each training fold via `inner_macro_f1` (maximizing Macro F1 subject to Positive Precision $\ge 0.68$) yields a stable threshold of **$\tau \approx 0.631 \pm 0.016$** for `Compact_LR_4Feat` and `Extended_LR_6Feat_WeakestLink`, achieving **62.1%–62.9% accuracy**, **56.6%–57.2% balanced accuracy**, **70.7%–71.1% precision**, and **39.6%–39.8% failure recall**.
   - Critically, when `Current_RF_28Feat` is evaluated honestly across 25 grouped folds using its legacy post-hoc threshold `0.61` (`legacy_fixed_061`), its accuracy drops to **52.73% ± 2.79%** and balanced accuracy is **55.14% ± 2.60%** (compared to the optimistic **58.85% accuracy / 58.60% balanced accuracy** reported on the single un-grouped 226-row Colab holdout split where `0.61` was hand-picked).

