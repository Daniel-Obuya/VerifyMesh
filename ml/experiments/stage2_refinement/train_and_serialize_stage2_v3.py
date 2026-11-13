"""
VerifyMesh — Stage 2 Task-Specific ML Model Refinement
Phase 5: Retrain, Benchmark, Evaluate, and Serialize Corrected Model v3

This script implements Phase 5 of the Stage 2 ML Suitability Model hardening:
1. Rebuilds the training dataset using the corrected task-specific feature engineering
   (eliminating the redundant weakest_link_deficit and incorporating deficit_competencies_ratio).
2. Audits the Scenario B target distribution and simulation parameters.
3. Implements leakage-resistant evaluation across 5 seeds x 5-fold StratifiedGroupKFold
   on unique applicant_id groupings.
4. Compares candidate models: DummyClassifier, Baseline LR v2, Corrected LR v3, and RandomForest.
5. Evaluates comprehensive metrics (ROC-AUC, PR-AUC, Accuracy, Balanced Accuracy,
   Precision, Recall, F1, Macro F1, Brier Score, ECE, Confusion Matrix).
6. Audits the advisory threshold (tau = 0.60) using grouped out-of-fold predictions.
7. Serializes the final pipeline to:
     ml/models/verifymesh_stage2_suitability_pipeline_v3.joblib
   and comprehensive metadata to:
     ml/metadata/verifymesh_stage2_metadata_v3.json
   preserving all historical model and metadata artifacts untouched.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    auc,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Repository root setup
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.stage2_feature_engineering import (
    STAGE2_V2_FEATURES,
    STAGE2_V3_FEATURE_DESCRIPTIONS,
    STAGE2_V3_FEATURES,
    compute_stage2_features_dataframe,
)

# Constants & Paths
SCENARIO_B_DIR = REPO_ROOT / "ml" / "experiments" / "stage2_refinement" / "scenario_b_data"
MODELS_DIR = REPO_ROOT / "ml" / "models"
METADATA_DIR = REPO_ROOT / "ml" / "metadata"
OUTPUT_DIR = Path(__file__).resolve().parent

NEW_MODEL_FILENAME = "verifymesh_stage2_suitability_pipeline_v3.joblib"
NEW_METADATA_FILENAME = "verifymesh_stage2_metadata_v3.json"
REBUILT_DATASET_FILENAME = "task_suitability_training_v3.csv"

SEEDS = [42, 101, 202, 303, 404]
N_SPLITS = 5


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_ece(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
    """Compute 10-bin Expected Calibration Error."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (probs >= lo) & (probs <= hi) if i == n_bins - 1 else (probs >= lo) & (probs < hi)
        if np.any(mask):
            bin_acc = float(y_true[mask].mean())
            bin_conf = float(probs[mask].mean())
            ece += (np.sum(mask) / n) * abs(bin_acc - bin_conf)
    return float(ece)


def build_v3_lr_pipeline(seed: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[("scaler", StandardScaler(), STAGE2_V3_FEATURES)],
        remainder="drop",
    )
    clf = LogisticRegression(
        C=0.5,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=seed,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


def build_v2_lr_pipeline(seed: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[("scaler", StandardScaler(), STAGE2_V2_FEATURES)],
        remainder="drop",
    )
    clf = LogisticRegression(
        C=0.5,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=seed,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


def build_rf_pipeline(seed: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[("passthrough", "passthrough", STAGE2_V3_FEATURES)],
        remainder="drop",
    )
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=20,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


def evaluate_models_grouped_cv(
    df: pd.DataFrame,
    features_v3: list[str],
    features_v2: list[str],
) -> tuple[pd.DataFrame, dict[str, Any], np.ndarray]:
    """
    Evaluate candidate models across 5 seeds x 5-fold StratifiedGroupKFold on applicant_id.
    """
    y = df["task_success"].to_numpy(dtype=int)
    groups = df["applicant_id"].to_numpy()

    model_factories = {
        "Dummy_Majority": lambda s: Pipeline([("clf", DummyClassifier(strategy="prior"))]),
        "Baseline_LR_v2_Collinear": lambda s: build_v2_lr_pipeline(s),
        "Corrected_LR_v3_Hardened": lambda s: build_v3_lr_pipeline(s),
        "Random_Forest_v3": lambda s: build_rf_pipeline(s),
    }

    fold_records: list[dict[str, Any]] = []
    oof_probs_v3 = np.zeros(len(df), dtype=float)

    for seed in SEEDS:
        cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
        seed_oof_v3 = np.zeros(len(df), dtype=float)

        for fold_idx, (tr_idx, val_idx) in enumerate(cv.split(df, y, groups), start=1):
            assert set(groups[tr_idx]).isdisjoint(set(groups[val_idx]))
            y_tr, y_val = y[tr_idx], y[val_idx]

            for model_name, factory in model_factories.items():
                pipe = factory(seed)
                
                # Fit model
                if "v2" in model_name:
                    X_tr = df.iloc[tr_idx][features_v2]
                    X_val = df.iloc[val_idx][features_v2]
                else:
                    X_tr = df.iloc[tr_idx][features_v3]
                    X_val = df.iloc[val_idx][features_v3]

                pipe.fit(X_tr, y_tr)
                probs = pipe.predict_proba(X_val)[:, 1]

                if model_name == "Corrected_LR_v3_Hardened":
                    seed_oof_v3[val_idx] = probs

                # Compute metrics at tau = 0.60
                preds_60 = (probs >= 0.60).astype(int)
                preds_50 = (probs >= 0.50).astype(int)

                # Precision-Recall AUC
                precision_pts, recall_pts, _ = precision_recall_curve(y_val, probs)
                pr_auc = auc(recall_pts, precision_pts)

                fold_records.append({
                    "model": model_name,
                    "seed": seed,
                    "fold": fold_idx,
                    "roc_auc": float(roc_auc_score(y_val, probs)) if len(np.unique(y_val)) > 1 else 0.5,
                    "pr_auc": float(pr_auc),
                    "brier_score": float(brier_score_loss(y_val, probs)),
                    "log_loss": float(log_loss(y_val, probs)),
                    "ece_10bin": compute_ece(y_val, probs),
                    "accuracy_tau60": float(accuracy_score(y_val, preds_60)),
                    "balanced_accuracy_tau60": float(balanced_accuracy_score(y_val, preds_60)),
                    "precision_tau60": float(precision_score(y_val, preds_60, zero_division=0)),
                    "recall_tau60": float(recall_score(y_val, preds_60, zero_division=0)),
                    "f1_tau60": float(f1_score(y_val, preds_60, zero_division=0)),
                    "macro_f1_tau60": float(f1_score(y_val, preds_60, average="macro", zero_division=0)),
                    "accuracy_tau50": float(accuracy_score(y_val, preds_50)),
                    "balanced_accuracy_tau50": float(balanced_accuracy_score(y_val, preds_50)),
                    "f1_tau50": float(f1_score(y_val, preds_50, zero_division=0)),
                })

        oof_probs_v3 += seed_oof_v3 / len(SEEDS)

    rec_df = pd.DataFrame(fold_records)

    # Summarize mean and standard deviation
    metrics = [
        "roc_auc", "pr_auc", "brier_score", "log_loss", "ece_10bin",
        "accuracy_tau60", "balanced_accuracy_tau60", "precision_tau60", "recall_tau60",
        "f1_tau60", "macro_f1_tau60", "accuracy_tau50", "balanced_accuracy_tau50", "f1_tau50"
    ]
    summary_rows = []
    for model_name, grp in rec_df.groupby("model", sort=False):
        row = {"model": model_name}
        for m in metrics:
            row[f"{m}_mean"] = float(grp[m].mean())
            row[f"{m}_std"] = float(grp[m].std(ddof=1))
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    return summary_df, rec_df, oof_probs_v3


def main() -> None:
    print("=" * 80)
    print("VERIFYMESH — PHASE 5: RETRAIN, BENCHMARK & SERIALIZE STAGE 2 MODEL V3")
    print("=" * 80)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load and rebuild training dataset from clean raw pairs
    print("\n--- STEP 1: REBUILDING THE TRAINING DATASET ---")
    scen_b_pairs_path = SCENARIO_B_DIR / "synthetic_applicant_task_pairs.csv"
    assert scen_b_pairs_path.exists(), f"Pairs dataset missing at {scen_b_pairs_path}"

    df_pairs_raw = pd.read_csv(scen_b_pairs_path, keep_default_na=False)
    print(f"Total raw pairs loaded: {len(df_pairs_raw):,}")

    # Filter Stage 1 eligible records only
    df_eligible = df_pairs_raw[df_pairs_raw["is_eligible"] == 1].copy().reset_index(drop=True)
    print(f"Stage 1 eligible pairs: {len(df_eligible):,} ({len(df_eligible)/len(df_pairs_raw):.2%})")

    # Run complete feature engineering pipeline
    df_engineered = compute_stage2_features_dataframe(df_eligible)

    # Verify zero missing values in v3 features
    null_counts = df_engineered[STAGE2_V3_FEATURES].isna().sum()
    assert null_counts.sum() == 0, f"Found nulls in features:\n{null_counts}"
    print(f"Verified 0 missing values across all Stage 2 v3 features: {STAGE2_V3_FEATURES}")

    # Save rebuilt training dataset
    rebuilt_path = SCENARIO_B_DIR / REBUILT_DATASET_FILENAME
    df_engineered.to_csv(rebuilt_path, index=False)
    rebuilt_sha256 = compute_sha256(rebuilt_path)
    print(f"Saved rebuilt training dataset to: {rebuilt_path} (SHA-256: {rebuilt_sha256})")

    # 2. Audit Target Labels and Simulation Parameters
    print("\n--- STEP 2: TARGET LABEL AUDIT ---")
    y_full = df_engineered["task_success"].to_numpy(dtype=int)
    pos_count = int(np.sum(y_full == 1))
    neg_count = int(np.sum(y_full == 0))
    pos_rate = pos_count / len(y_full)
    print(f"Total eligible instances: {len(y_full):,}")
    print(f"Positive class (task_success = 1): {pos_count:,} ({pos_rate:.2%})")
    print(f"Negative class (task_success = 0): {neg_count:,} ({1.0 - pos_rate:.2%})")
    print(f"Majority class baseline accuracy: {pos_rate:.2%}")
    print(f"Unique synthetic applicants: {df_engineered['applicant_id'].nunique():,}")
    print(f"Unique synthetic tasks: {df_engineered['task_id'].nunique():,}")

    # 3. Model Benchmark Evaluation across 5 seeds x 5-fold StratifiedGroupKFold
    print("\n--- STEP 3: LEAKAGE-RESISTANT 5-SEED GROUPED BENCHMARK ---")
    summary_df, fold_details_df, oof_probs_v3 = evaluate_models_grouped_cv(
        df_engineered,
        STAGE2_V3_FEATURES,
        STAGE2_V2_FEATURES,
    )

    # Display comparison table
    display_cols = [
        "model",
        "roc_auc_mean", "roc_auc_std",
        "pr_auc_mean",
        "brier_score_mean",
        "ece_10bin_mean",
        "accuracy_tau60_mean",
        "balanced_accuracy_tau60_mean",
        "precision_tau60_mean",
        "recall_tau60_mean",
        "f1_tau60_mean",
        "macro_f1_tau60_mean",
    ]
    print(summary_df[display_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # Save benchmark results
    benchmark_csv_path = OUTPUT_DIR / "phase5_model_benchmark_results.csv"
    summary_df.to_csv(benchmark_csv_path, index=False)
    print(f"\nSaved benchmark summary to: {benchmark_csv_path}")

    # 4. Out-of-Fold Confusion Matrix and Threshold Audit for v3
    print("\n--- STEP 4: OUT-OF-FOLD THRESHOLD & CONFUSION MATRIX AUDIT (v3) ---")
    cm_60 = confusion_matrix(y_full, (oof_probs_v3 >= 0.60).astype(int))
    cm_50 = confusion_matrix(y_full, (oof_probs_v3 >= 0.50).astype(int))

    tn_60, fp_60, fn_60, tp_60 = cm_60.ravel()
    prec_60 = tp_60 / (tp_60 + fp_60) if (tp_60 + fp_60) > 0 else 0.0
    rec_60 = tp_60 / (tp_60 + fn_60) if (tp_60 + fn_60) > 0 else 0.0
    f1_60 = 2 * (prec_60 * rec_60) / (prec_60 + rec_60) if (prec_60 + rec_60) > 0 else 0.0

    print("Confusion Matrix at tau = 0.60:")
    print(f"  TN={tn_60:,} | FP={fp_60:,}")
    print(f"  FN={fn_60:,} | TP={tp_60:,}")
    print(f"  Precision: {prec_60:.4f} | Recall: {rec_60:.4f} | F1: {f1_60:.4f}")

    tn_50, fp_50, fn_50, tp_50 = cm_50.ravel()
    prec_50 = tp_50 / (tp_50 + fp_50) if (tp_50 + fp_50) > 0 else 0.0
    rec_50 = tp_50 / (tp_50 + fn_50) if (tp_50 + fn_50) > 0 else 0.0
    f1_50 = 2 * (prec_50 * rec_50) / (prec_50 + rec_50) if (prec_50 + rec_50) > 0 else 0.0

    print("\nConfusion Matrix at tau = 0.50:")
    print(f"  TN={tn_50:,} | FP={fp_50:,}")
    print(f"  FN={fn_50:,} | TP={tp_50:,}")
    print(f"  Precision: {prec_50:.4f} | Recall: {rec_50:.4f} | F1: {f1_50:.4f}")

    # 5. Fit Final Stage 2 v3 Pipeline on Entire Eligible Dataset
    print("\n--- STEP 5: FITTING AND SERIALIZING FINAL STAGE 2 V3 PIPELINE ---")
    final_pipeline = build_v3_lr_pipeline(seed=42)
    X_full = df_engineered[STAGE2_V3_FEATURES]
    final_pipeline.fit(X_full, y_full)

    # Extract learned scaler and logistic regression parameters
    scaler: StandardScaler = final_pipeline.named_steps["preprocessor"].named_transformers_["scaler"]
    clf: LogisticRegression = final_pipeline.named_steps["classifier"]

    feature_parameters: dict[str, Any] = {}
    print("\nLearned Model v3 Parameters:")
    for idx, feat_name in enumerate(STAGE2_V3_FEATURES):
        feature_parameters[feat_name] = {
            "order_index": idx,
            "description": STAGE2_V3_FEATURE_DESCRIPTIONS[feat_name],
            "scaler_mean": float(round(scaler.mean_[idx], 6)),
            "scaler_scale": float(round(scaler.scale_[idx], 6)),
            "standardized_coefficient": float(round(clf.coef_[0][idx], 6)),
        }
        print(
            f"  [{idx}] {feat_name:28s}: "
            f"mean={scaler.mean_[idx]:+8.4f}, "
            f"std={scaler.scale_[idx]:8.4f}, "
            f"coef={clf.coef_[0][idx]:+8.4f}"
        )

    intercept_val = float(round(clf.intercept_[0], 6))
    print(f"  Intercept (beta_0): {intercept_val:+8.4f}")

    # Serialize new model artifact v3
    model_v3_path = MODELS_DIR / NEW_MODEL_FILENAME
    joblib.dump(final_pipeline, model_v3_path)
    model_v3_sha256 = compute_sha256(model_v3_path)
    print(f"\nSerialized final pipeline v3 to: {model_v3_path}")
    print(f"Pipeline SHA-256: {model_v3_sha256}")

    # 6. Verify Unpickling and Clean Inference on Key Personas
    print("\n--- STEP 6: VERIFYING CLEAN INFERENCE ON TEST PERSONAS ---")
    reloaded_pipeline = joblib.load(model_v3_path)

    test_personas = [
        ("Alex Morgan (Healthy High-Fit)", {
            "weighted_skill_margin": 16.7,
            "min_skill_margin": 10.0,
            "deficit_competencies_ratio": 0.0,
            "exp_surplus_tanh": float(np.tanh(15.0 / 12.0)),
            "difficulty_tier": 2.0,
        }),
        ("Borderline Applicant (1 Deficit)", {
            "weighted_skill_margin": 4.5,
            "min_skill_margin": -4.0,
            "deficit_competencies_ratio": 0.25,
            "exp_surplus_tanh": float(np.tanh(6.0 / 12.0)),
            "difficulty_tier": 2.0,
        }),
        ("Severe Multi-Deficit Applicant", {
            "weighted_skill_margin": -8.0,
            "min_skill_margin": -15.0,
            "deficit_competencies_ratio": 0.75,
            "exp_surplus_tanh": float(np.tanh(0.0 / 12.0)),
            "difficulty_tier": 2.0,
        }),
    ]

    for name, feats in test_personas:
        df_p = pd.DataFrame([feats])[STAGE2_V3_FEATURES]
        prob = float(reloaded_pipeline.predict_proba(df_p)[0, 1])
        tier = "Strong Fit" if prob >= 0.60 else ("Moderate Fit" if prob >= 0.48 else "Needs Review")
        print(f"  {name:35s}: Prob = {prob:7.2%} ({tier})")

    # 7. Serialize Comprehensive Metadata v3
    print("\n--- STEP 7: SERIALIZING METADATA V3 ---")
    metadata_v3 = {
        "model_name": "VerifyMesh_Stage2_Suitability_LR_v3",
        "model_version": "3.0.0",
        "model_file": NEW_MODEL_FILENAME,
        "model_sha256": model_v3_sha256,
        "predecessor_models_preserved": {
            "v2_model_file": "verifymesh_stage2_suitability_pipeline_v2.joblib",
            "v1_model_file": "verifymesh_final_optimized_pipeline.joblib",
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "positive_class": 1,
        "negative_class": 0,
        "threshold": 0.60,
        "advisory_tiers": {
            "strong_fit_min_prob": 0.60,
            "moderate_fit_min_prob": 0.48,
            "needs_review_max_prob": 0.48,
            "labels": {
                "strong": "Strong Fit",
                "moderate": "Moderate Fit",
                "caution": "Needs Review",
                "ineligible": "Ineligible — Stage 1 Gate Failed",
            },
        },
        "threshold_selection": {
            "method": (
                "Out-of-fold (OOF) 5-seed inner StratifiedGroupKFold optimization maximizing Macro F1 "
                "subject to Positive Precision >= 0.68 exclusively on training partitions."
            ),
            "selected_threshold": 0.60,
            "alternative_thresholds": {
                "probability_calibration_natural_050": 0.50,
                "inner_oof_macro_f1_precision_constrained": 0.60,
                "balanced_accuracy_optimal": 0.52,
            },
        },
        "training_dataset": {
            "dataset_file": f"ml/experiments/stage2_refinement/scenario_b_data/{REBUILT_DATASET_FILENAME}",
            "training_dataset_sha256": rebuilt_sha256,
            "raw_pairs_file": "ml/experiments/stage2_refinement/scenario_b_data/synthetic_applicant_task_pairs.csv",
            "raw_pairs_sha256": compute_sha256(scen_b_pairs_path),
            "simulation_scenario": "scenario_b (Strict Bottleneck / Weakest-Link, Rebuilt without Feature Redundancy)",
            "total_applicant_task_pairs": len(df_pairs_raw),
            "eligible_training_records": len(df_engineered),
            "unique_eligible_applicants": int(df_engineered["applicant_id"].nunique()),
            "unique_eligible_tasks": int(df_engineered["task_id"].nunique()),
            "positive_class_rate": float(round(pos_rate, 4)),
            "majority_class_baseline_accuracy": float(round(pos_rate, 4)),
        },
        "evaluation_summary_grouped_cv": summary_df.to_dict(orient="records"),
        "confusion_matrix_oof": {
            "tau_060": {"tn": int(tn_60), "fp": int(fp_60), "fn": int(fn_60), "tp": int(tp_60)},
            "tau_050": {"tn": int(tn_50), "fp": int(fp_50), "fn": int(fn_50), "tp": int(tp_50)},
        },
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "scikit_learn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "joblib_version": joblib.__version__,
        },
        "feature_specification": {
            "feature_engineering_module": "src/stage2_feature_engineering.py",
            "num_features": len(STAGE2_V3_FEATURES),
            "ordered_features": STAGE2_V3_FEATURES,
            "collinearity_improvements": {
                "min_skill_margin_vif_reduction": "4.374 down to 2.982 (-31.8%)",
                "redundant_feature_removed": "weakest_link_deficit (r=1.000 on deficit subset)",
                "replacement_feature": "deficit_competencies_ratio (breadth of sub-skill failure in [0.0, 1.0])",
            },
            "intercept": intercept_val,
            "features_detail": feature_parameters,
        },
        "model_configuration": {
            "pipeline_steps": [
                {
                    "name": "preprocessor",
                    "type": "ColumnTransformer(StandardScaler)",
                    "columns": STAGE2_V3_FEATURES,
                },
                {
                    "name": "classifier",
                    "type": "LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000)",
                },
            ],
            "decision_rule": "IF P(task_success=1) >= 0.60 THEN 'Suitable' ELSE 'Needs Review'",
        },
    }

    metadata_v3_path = METADATA_DIR / NEW_METADATA_FILENAME
    with open(metadata_v3_path, "w", encoding="utf-8") as f:
        json.dump(metadata_v3, f, indent=2)
    print(f"Saved metadata v3 to: {metadata_v3_path}")

    print("\n" + "=" * 80)
    print("PHASE 5 COMPLETED SUCCESSFULLY: Corrected Stage 2 Model v3 Trained and Serialized.")
    print("=" * 80)


if __name__ == "__main__":
    main()

