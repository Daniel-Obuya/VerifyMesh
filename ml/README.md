# VerifyMesh — Machine Learning Experiments, Models & Metadata (`ml/`)

This directory contains the synthetic datasets, experimental benchmarks (Phases 0–3), reproducible Jupyter notebook, serialized machine learning pipelines, and model metadata for **VerifyMesh Stage 2 (Task-Specific Suitability Prediction)**.

---

## 1. Two-Stage VerifyMesh Decision Architecture

VerifyMesh strictly separates deterministic eligibility verification from advisory machine learning ranking:

1. **Stage 1 — Deterministic Eligibility Gatekeeper (Authoritative):**
   - Evaluates mandatory task requirements: required certification (`cert_satisfied == 1`), minimum relevant experience (`experience_surplus_months >= 0`), overall assessment threshold (`assessment_gap >= 0`), communication/product competency floors (`communication_gap >= -5.0`, `product_knowledge_gap >= -5.0`), and domain-specific skill floors (`sales_skill_gap >= -3.0` for *Enterprise Sales*; `customer_service_gap >= -3.0` for *Customer Support Escalations*).
   - Candidates who fail Stage 1 (`is_eligible == 0`) are **never** passed to Stage 2, ranked as eligible, or overridden by ML predictions.
2. **Stage 2 — Task-Specific Suitability Prediction (Advisory):**
   - Scores **only** Stage 1-eligible candidate–task pairs (`is_eligible == 1`).
   - Predicts the calibrated probability $P(\text{task\_success} = 1 \mid \mathbf{x})$ of simulated task execution success and assigns an advisory tier (`Strong Fit` $\ge 0.60$, `Moderate Fit` $[0.48, 0.60)$, `Needs Review` $< 0.48$) alongside transparent factor-level explanations to support human administrators.

---

## 2. Directory Structure

```text
ml/
├── README.md                                                     # This documentation file
├── notebooks/
│   ├── VerifyMesh_Task_Suitability_Experiment.ipynb              # Reconstructed & executed Phases 0–3 notebook
│   └── VerifyMesh_Task_Suitability_Experiment_legacy_colab_backup.ipynb  # Backup of original Colab notebook
├── models/
│   ├── verifymesh_stage2_suitability_pipeline_v2.joblib          # Final Phase 3 Stage 2 LR pipeline
│   └── verifymesh_final_optimized_pipeline.joblib                # Preserved legacy 28-feature RF pipeline
├── metadata/
│   ├── verifymesh_stage2_metadata_v2.json                        # Final Phase 3 Stage 2 metadata & schema
│   └── verifymesh_threshold_metadata.json                        # Preserved legacy threshold metadata (0.61)
└── experiments/
    ├── task_specific_synthetic_data/                             # Scenario A (Original Balanced Compensatory)
    │   ├── generate_synthetic_dataset.py                         # Synthetic dataset generator (Scenario A & B)
    │   ├── synthetic_applicants.csv                              # 800 applicants
    │   ├── synthetic_tasks.csv                                   # 30 tasks across 5 categories
    │   ├── synthetic_applicant_task_pairs.csv                    # 6,000 evaluated pairs (42 columns)
    │   ├── task_suitability_training.csv                         # 1,183 Stage 1-eligible pairs (35 columns)
    │   ├── data_dictionary.md                                    # Column definitions
    │   ├── simulation_methodology.md                             # Mathematical specification of generator
    │   └── dataset_validation_report.md                          # Initial dataset validation report
    └── stage2_refinement/                                        # Phases 1–3 Controlled Refinement Benchmarks
        ├── scenario_b_data/                                      # Scenario B (Strict Bottleneck / Weakest-Link)
        │   ├── synthetic_applicants.csv                          # 3,200 applicants
        │   ├── synthetic_tasks.csv                               # 30 tasks across 5 categories
        │   ├── synthetic_applicant_task_pairs.csv                # 24,000 evaluated pairs (42 columns)
        │   └── task_suitability_training.csv                     # 4,675 Stage 1-eligible pairs (35 columns)
        ├── run_phase1_benchmark.py                               # Phase 1: Applicant-grouped CV model benchmark
        ├── phase1_benchmark_summary.csv                          # Phase 1 aggregated 25-fold metrics
        ├── phase1_fold_details.csv                               # Phase 1 per-fold metrics
        ├── phase1_benchmark_results.json                         # Phase 1 full diagnostic results
        ├── phase1_benchmark_report.md                            # Phase 1 technical report
        ├── run_phase2_scenario_comparison.py                     # Phase 2: Scenario A vs. Scenario B comparison
        ├── phase2_scenario_comparison_summary.csv                # Phase 2 aggregated 25-fold metrics
        ├── phase2_scenario_comparison_folds.csv                  # Phase 2 per-fold metrics
        ├── phase2_scenario_comparison_results.json               # Phase 2 full diagnostic results
        ├── phase2_scenario_comparison_report.md                  # Phase 2 technical report
        ├── run_phase3_calibration_and_serialization.py           # Phase 3: Calibration audit & serialization
        ├── phase3_calibration_comparison.csv                     # Phase 3 calibration variant metrics
        ├── phase3_threshold_analysis.csv                         # Phase 3 threshold sweep & inner-CV diagnostics
        ├── phase3_final_model_results.json                       # Phase 3 full evaluation & parameters
        ├── phase3_final_model_report.md                          # Phase 3 technical report
        ├── run_phase3_final_audit.py                             # Phase 3 Final Audit: 5 vs. 6 features & parity
        ├── phase3_final_audit_5v6_summary.csv                    # 5-feature vs. 6-feature comparison table
        ├── phase3_final_audit_results.json                       # Phase 3 Final Audit JSON
        └── phase3_final_audit_report.md                          # Phase 3 Final Audit Markdown report
```

Shared feature engineering and inference utilities live in the repository's `src/` package:
- `src/stage2_feature_engineering.py`: Shared training and inference feature computation (`compute_stage2_features_dataframe`, `build_complete_stage2_feature_dict`, `explain_stage2_prediction`).
- `src/task_suitability_inference.py`: Stage 2 model loading and inference service.

---

## 3. Final Selected Stage 2 Model Summary (`VerifyMesh_Stage2_Suitability_LR_v2`)

- **Algorithm:** Uncalibrated L2-regularized Logistic Regression (`StandardScaler` + `LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)`).
- **Training Dataset:** Scenario B (`ml/experiments/stage2_refinement/scenario_b_data/task_suitability_training.csv`, $N = 4,675$ Stage 1-eligible pairs across $1,924$ unique applicants and $30$ tasks).
- **Engineered Features:**
  1. `weighted_skill_margin`: Category-weighted competency surplus across communication, product knowledge, sales, and customer support.
  2. `min_skill_margin`: Minimum individual competency margin across all 5 skill dimensions.
  3. `weakest_link_deficit`: $\min(0.0, \text{min\_skill\_margin})$ (isolates sub-threshold competency deficits).
  4. `exp_surplus_tanh`: $\tanh(\text{experience\_surplus\_months} / 12.0)$ (diminishing returns on excess experience).
  5. `difficulty_tier`: Ordinal task difficulty ($1.0=$ Low, $2.0=$ Medium, $3.0=$ High).
  - *Note on 6th Feature (`cert_satisfied`):* The pre-update `.joblib` artifact currently on disk (`SHA-256: 70dc562e...`) includes `cert_satisfied` as a 6th column. Because Stage 1 enforces `cert_satisfied == 1.0` for 100% of eligible pairs, its standardized weight is `0.000000`, making the 6-feature artifact and 5-feature `LR_5Feat_NoCert` pipeline mathematically identical (`max_abs_diff <= 4.44e-16`).
- **Held-Out Applicant-Grouped Cross-Validation Performance (`5 Seeds × 5 Folds = 25 Outer Folds` on Scenario B):**
  - **ROC-AUC:** `0.6772 ± 0.0203` (`91.2%` of the `0.7427` noiseless Oracle ceiling)
  - **Brier Score:** `0.2110 ± 0.0042`
  - **Log-Loss:** `0.6110 ± 0.0098`
  - **10-Bin ECE:** `0.0298 ± 0.0117`
  - **Operational Advisory Threshold ($\tau = 0.60$, selected via inner-fold CV with `Positive Precision >= 0.68`):**
    - **Accuracy:** `65.54% ± 1.29%` (`67.23% ± 1.07%` at $\tau = 0.50$)
    - **Balanced Accuracy:** `62.79% ± 1.38%`
    - **Positive Precision / Recall / F1:** `71.96%` / `73.71%` / `0.7280`
    - **Failure Recall (Class 0):** `51.87% ± 2.83%`
    - **Macro F1:** `0.6287 ± 0.0138`

---

## 4. Reproducing the Notebook and Experiments

### Dependencies

Install the required Python packages (tested with Python `3.13.7` and `scikit-learn 1.8.0`):

```bash
pip install numpy pandas scikit-learn joblib matplotlib seaborn jupyter
```

### Running the Experiment Notebook

From the repository root (`Verify_Mesh/`):

```bash
jupyter notebook ml/notebooks/VerifyMesh_Task_Suitability_Experiment.ipynb
```

All paths inside `VerifyMesh_Task_Suitability_Experiment.ipynb` resolve dynamically relative to the repository root, so the notebook runs cleanly whether launched from `Verify_Mesh/` or `Verify_Mesh/ml/notebooks/`.

### Running the Phase 1–3 Benchmark Scripts Directly

From the repository root (`Verify_Mesh/`):

```bash
python ml/experiments/stage2_refinement/run_phase1_benchmark.py
python ml/experiments/stage2_refinement/run_phase2_scenario_comparison.py
python ml/experiments/stage2_refinement/run_phase3_calibration_and_serialization.py
python ml/experiments/stage2_refinement/run_phase3_final_audit.py
```

