"""
VerifyMesh — Stage 2 Task-Specific ML Model Refinement
Phase 3: Final Model Selection, Calibration Evaluation, and Serialization

Performs:
1. Probability calibration evaluation (Uncalibrated LR vs. Sigmoid Platt Scaling vs.
   Isotonic Regression) under 5-seed x 5-fold StratifiedGroupKFold on both Scenario B
   (N=4,675) and Scenario A (N=1,183), reporting ROC-AUC, Brier Score, Log-Loss, and
   10-bin Expected Calibration Error (ECE).
2. Out-of-fold (OOF) threshold selection strictly on grouped training folds.
3. Final pipeline training and serialization to a NEW model filename:
     ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib
4. Comprehensive metadata serialization to a NEW metadata filename:
     ml/metadata/verifymesh_stage2_metadata_v2.json
   while preserving all existing model and metadata artifacts untouched.
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "ml" / "experiments" / "stage2_refinement"))

from src.stage2_feature_engineering import (
    STAGE2_V2_FEATURE_DESCRIPTIONS,
    STAGE2_V2_FEATURES,
    compute_stage2_features_dataframe,
)
from run_phase1_benchmark import (
    FORBIDDEN_LEAKAGE_COLS,
    N_INNER_SPLITS,
    N_OUTER_SPLITS,
    SEEDS,
    compute_sha256,
    select_thresholds_from_training_oof,
)

SCENARIO_B_DIR = REPO_ROOT / "ml" / "experiments" / "stage2_refinement" / "scenario_b_data"
SCENARIO_A_DIR = REPO_ROOT / "ml" / "experiments" / "task_specific_synthetic_data"
MODELS_DIR = REPO_ROOT / "ml" / "models"
METADATA_DIR = REPO_ROOT / "ml" / "metadata"
OUTPUT_DIR = Path(__file__).resolve().parent

NEW_MODEL_FILENAME = "verifymesh_stage2_suitability_pipeline_v2.joblib"
NEW_METADATA_FILENAME = "verifymesh_stage2_metadata_v2.json"


def compute_ece(y_true: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
    """
    Compute Expected Calibration Error (ECE) across uniform probability bins in [0, 1].
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (probs >= lo) & (probs <= hi)
        else:
            mask = (probs >= lo) & (probs < hi)
        if np.any(mask):
            bin_acc = float(y_true[mask].mean())
            bin_conf = float(probs[mask].mean())
            ece += (np.sum(mask) / n) * abs(bin_acc - bin_conf)
    return float(ece)


def build_base_lr_pipeline(seed: int = 42) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[("scaler", StandardScaler(), STAGE2_V2_FEATURES)],
        remainder="drop",
    )
    clf = LogisticRegression(
        C=0.5,
        solver="lbfgs",
        max_iter=1000,
        random_state=seed,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


def evaluate_calibration_variants(df: pd.DataFrame, dataset_name: str) -> list[dict[str, Any]]:
    """
    Compare Uncalibrated LR vs. Sigmoid-Calibrated LR vs. Isotonic-Calibrated LR
    across 5 seeds x 5-fold StratifiedGroupKFold.
    """
    X = df[STAGE2_V2_FEATURES]
    y = df["task_success"].to_numpy(dtype=int)
    groups = df["applicant_id"].to_numpy()

    variants = ["Uncalibrated_LR_6Feat", "Sigmoid_Calibrated_LR_6Feat", "Isotonic_Calibrated_LR_6Feat"]
    records: list[dict[str, Any]] = []

    for seed in SEEDS:
        outer_cv = StratifiedGroupKFold(n_splits=N_OUTER_SPLITS, shuffle=True, random_state=seed)
        for fold_idx, (tr_idx, val_idx) in enumerate(outer_cv.split(X, y, groups), start=1):
            assert set(groups[tr_idx]).isdisjoint(set(groups[val_idx]))
            X_tr, y_tr, g_tr = X.iloc[tr_idx], y[tr_idx], groups[tr_idx]
            X_val, y_val = X.iloc[val_idx], y[val_idx]

            base_pipe = build_base_lr_pipeline(seed)

            # 1. Uncalibrated LR
            m_uncal = clone(base_pipe)
            m_uncal.fit(X_tr, y_tr)
            p_uncal = m_uncal.predict_proba(X_val)[:, 1]

            # 2. Sigmoid (Platt) Calibrated LR using grouped inner splits
            inner_cv = list(
                StratifiedGroupKFold(n_splits=N_INNER_SPLITS, shuffle=True, random_state=seed).split(
                    X_tr, y_tr, g_tr
                )
            )
            m_sig = CalibratedClassifierCV(estimator=clone(base_pipe), method="sigmoid", cv=inner_cv)
            m_sig.fit(X_tr, y_tr)
            p_sig = m_sig.predict_proba(X_val)[:, 1]

            # 3. Isotonic Calibrated LR using grouped inner splits
            m_iso = CalibratedClassifierCV(estimator=clone(base_pipe), method="isotonic", cv=inner_cv)
            m_iso.fit(X_tr, y_tr)
            p_iso = m_iso.predict_proba(X_val)[:, 1]

            for v_name, probs in [
                ("Uncalibrated_LR_5Feat", p_uncal),
                ("Sigmoid_Calibrated_LR_5Feat", p_sig),
                ("Isotonic_Calibrated_LR_5Feat", p_iso),
            ]:
                records.append(
                    {
                        "dataset": dataset_name,
                        "variant": v_name,
                        "seed": seed,
                        "fold": fold_idx,
                        "roc_auc": float(roc_auc_score(y_val, probs)),
                        "brier_score": float(brier_score_loss(y_val, probs)),
                        "log_loss": float(log_loss(y_val, probs)),
                        "ece_10bin": compute_ece(y_val, probs, n_bins=10),
                    }
                )

    rec_df = pd.DataFrame(records)
    summary = []
    for (ds, var), grp in rec_df.groupby(["dataset", "variant"], sort=False):
        summary.append(
            {
                "dataset": ds,
                "variant": var,
                "roc_auc_mean": float(grp["roc_auc"].mean()),
                "roc_auc_std": float(grp["roc_auc"].std(ddof=1)),
                "brier_score_mean": float(grp["brier_score"].mean()),
                "brier_score_std": float(grp["brier_score"].std(ddof=1)),
                "log_loss_mean": float(grp["log_loss"].mean()),
                "log_loss_std": float(grp["log_loss"].std(ddof=1)),
                "ece_10bin_mean": float(grp["ece_10bin"].mean()),
                "ece_10bin_std": float(grp["ece_10bin"].std(ddof=1)),
            }
        )
    return summary


def main() -> None:
    print("=== VerifyMesh Phase 3: Final Model Selection, Calibration & Serialization ===")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    # Verify zero leakage in final feature list
    assert FORBIDDEN_LEAKAGE_COLS.isdisjoint(set(STAGE2_V2_FEATURES)), "Leakage detected!"

    # Load Scenario B (Primary) and Scenario A (Original) eligible datasets
    scen_b_pairs_path = SCENARIO_B_DIR / "synthetic_applicant_task_pairs.csv"
    scen_b_train_path = SCENARIO_B_DIR / "task_suitability_training.csv"
    scen_a_pairs_path = SCENARIO_A_DIR / "synthetic_applicant_task_pairs.csv"
    scen_a_train_path = SCENARIO_A_DIR / "task_suitability_training.csv"

    df_b_raw = pd.read_csv(scen_b_pairs_path, keep_default_na=False)
    df_b_elig = compute_stage2_features_dataframe(
        df_b_raw[df_b_raw["is_eligible"] == 1].reset_index(drop=True)
    )

    df_a_raw = pd.read_csv(scen_a_pairs_path, keep_default_na=False)
    df_a_elig = compute_stage2_features_dataframe(
        df_a_raw[df_a_raw["is_eligible"] == 1].reset_index(drop=True)
    )

    print("1. Evaluating probability calibration across 5 seeds x 5-fold StratifiedGroupKFold...")
    cal_summary_b = evaluate_calibration_variants(df_b_elig, "scenario_b_4675")
    cal_summary_a = evaluate_calibration_variants(df_a_elig, "scenario_a_1183")
    cal_summary_all = cal_summary_b + cal_summary_a
    cal_df = pd.DataFrame(cal_summary_all)
    cal_df.to_csv(OUTPUT_DIR / "phase3_calibration_comparison.csv", index=False)
    print(cal_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # 2. Compute 5-seed OOF threshold and out-of-fold reliability curve on Scenario B
    print("\n2. Computing 5-seed OOF threshold and fitting final Stage 2 v2 pipeline...")
    X_b = df_b_elig[STAGE2_V2_FEATURES]
    y_b = df_b_elig["task_success"].to_numpy(dtype=int)
    groups_b = df_b_elig["applicant_id"].to_numpy()

    oof_thresholds_macro_f1 = []
    oof_thresholds_bal_acc = []
    oof_probs_accum = np.zeros(len(df_b_elig), dtype=float)

    for seed in SEEDS:
        cv = StratifiedGroupKFold(n_splits=N_OUTER_SPLITS, shuffle=True, random_state=seed)
        seed_oof = np.zeros(len(df_b_elig), dtype=float)
        for tr_idx, val_idx in cv.split(X_b, y_b, groups_b):
            pipe = build_base_lr_pipeline(seed)
            pipe.fit(X_b.iloc[tr_idx], y_b[tr_idx])
            seed_oof[val_idx] = pipe.predict_proba(X_b.iloc[val_idx])[:, 1]

        t_dict = select_thresholds_from_training_oof(y_b, seed_oof)
        oof_thresholds_macro_f1.append(t_dict["inner_macro_f1"])
        oof_thresholds_bal_acc.append(t_dict["inner_bal_acc"])
        oof_probs_accum += seed_oof / len(SEEDS)

    selected_threshold = float(round(float(np.mean(oof_thresholds_macro_f1)), 2))
    bal_acc_threshold = float(round(float(np.mean(oof_thresholds_bal_acc)), 2))
    print(
        f"Selected Operational Decision Threshold (inner_macro_f1 OOF mean): {selected_threshold:.2f} "
        f"(inner_bal_acc OOF mean: {bal_acc_threshold:.2f})"
    )

    # Fit final pipeline on full Scenario B eligible dataset (4,675 rows)
    final_pipeline = build_base_lr_pipeline(seed=42)
    final_pipeline.fit(X_b, y_b)

    # Extract learned scaler and logistic regression parameters for transparent explainability
    scaler: StandardScaler = final_pipeline.named_steps["preprocessor"].named_transformers_["scaler"]
    clf: LogisticRegression = final_pipeline.named_steps["classifier"]

    feature_parameters = {}
    for idx, feat_name in enumerate(STAGE2_V2_FEATURES):
        feature_parameters[feat_name] = {
            "order_index": idx,
            "description": STAGE2_V2_FEATURE_DESCRIPTIONS[feat_name],
            "scaler_mean": float(round(scaler.mean_[idx], 6)),
            "scaler_scale": float(round(scaler.scale_[idx], 6)),
            "standardized_coefficient": float(round(clf.coef_[0][idx], 6)),
        }
    intercept_val = float(round(clf.intercept_[0], 6))

    # Serialize new model artifact (never overwriting verifymesh_final_optimized_pipeline.joblib)
    model_out_path = MODELS_DIR / NEW_MODEL_FILENAME
    joblib.dump(final_pipeline, model_out_path)
    model_sha256 = compute_sha256(model_out_path)
    print(f"Saved final pipeline to: {model_out_path} (SHA-256: {model_sha256})")

    # Verify clean unpickling and inference in current environment
    reloaded_pipeline = joblib.load(model_out_path)
    sample_probs = reloaded_pipeline.predict_proba(X_b.iloc[:5])[:, 1]
    assert np.all((sample_probs > 0.0) & (sample_probs < 1.0)), "Invalid probabilities!"
    print(f"Verified reload & predict_proba on 5 rows: {np.round(sample_probs, 4)}")

    # Pull grouped CV validation summaries from Phase 2 for metadata completeness
    p2_summary = pd.read_csv(OUTPUT_DIR / "phase2_scenario_comparison_summary.csv")
    lr6_scen_b = p2_summary[
        (p2_summary["dataset"] == "scenario_b_4675")
        & (p2_summary["model"] == "Extended_LR_6Feat_WeakestLink")
    ].to_dict(orient="records")
    lr6_scen_a = p2_summary[
        (p2_summary["dataset"] == "scenario_a_1183")
        & (p2_summary["model"] == "Extended_LR_6Feat_WeakestLink")
    ].to_dict(orient="records")
    ora_scen_b = p2_summary[
        (p2_summary["dataset"] == "scenario_b_4675")
        & (p2_summary["model"] == "Oracle_Latent_Prob")
    ].to_dict(orient="records")
    ora_scen_a = p2_summary[
        (p2_summary["dataset"] == "scenario_a_1183")
        & (p2_summary["model"] == "Oracle_Latent_Prob")
    ].to_dict(orient="records")

    metadata_v2 = {
        "model_name": "VerifyMesh_Stage2_Suitability_LR_v2",
        "model_version": "2.0.0",
        "model_file": NEW_MODEL_FILENAME,
        "model_sha256": model_sha256,
        "legacy_model_file_preserved": "verifymesh_final_optimized_pipeline.joblib",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "positive_class": 1,
        "negative_class": 0,
        "threshold": selected_threshold,
        "advisory_tiers": {
            "strong_fit_min_prob": selected_threshold,
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
                "Out-of-fold (OOF) inner StratifiedGroupKFold optimization maximizing Macro F1 "
                "subject to Positive Precision >= 0.68 exclusively on training partitions."
            ),
            "selected_threshold": selected_threshold,
            "alternative_thresholds": {
                "probability_calibration_natural_050": 0.50,
                "inner_oof_macro_f1_precision_constrained": selected_threshold,
                "inner_oof_balanced_accuracy_youden_j": bal_acc_threshold,
            },
        },
        "training_dataset": {
            "primary_dataset_file": "ml/experiments/stage2_refinement/scenario_b_data/task_suitability_training.csv",
            "primary_pairs_file": "ml/experiments/stage2_refinement/scenario_b_data/synthetic_applicant_task_pairs.csv",
            "primary_training_sha256": compute_sha256(scen_b_train_path),
            "primary_pairs_sha256": compute_sha256(scen_b_pairs_path),
            "simulation_scenario": "scenario_b (Strict Bottleneck / Weakest-Link)",
            "total_applicants": 3200,
            "total_tasks": 30,
            "total_applicant_task_pairs": 24000,
            "eligible_training_records": int(len(df_b_elig)),
            "unique_eligible_applicants": int(df_b_elig["applicant_id"].nunique()),
            "unique_eligible_tasks": int(df_b_elig["task_id"].nunique()),
            "positive_class_rate": float(round(df_b_elig["task_success"].mean(), 4)),
            "original_scenario_a_dataset": {
                "dataset_file": "ml/experiments/task_specific_synthetic_data/task_suitability_training.csv",
                "training_sha256": compute_sha256(scen_a_train_path),
                "pairs_sha256": compute_sha256(scen_a_pairs_path),
                "simulation_scenario": "scenario_a (Balanced Compensatory)",
                "eligible_training_records": int(len(df_a_elig)),
                "unique_eligible_applicants": int(df_a_elig["applicant_id"].nunique()),
                "positive_class_rate": float(round(df_a_elig["task_success"].mean(), 4)),
            },
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
            "num_features": len(STAGE2_V2_FEATURES),
            "ordered_features": STAGE2_V2_FEATURES,
            "intercept": intercept_val,
            "features_detail": feature_parameters,
        },
        "model_configuration": {
            "pipeline_steps": [
                {
                    "name": "preprocessor",
                    "type": "ColumnTransformer(StandardScaler)",
                    "columns": STAGE2_V2_FEATURES,
                },
                {
                    "name": "classifier",
                    "type": "LogisticRegression",
                    "params": {
                        "C": 0.5,
                        "penalty": "l2",
                        "solver": "lbfgs",
                        "max_iter": 1000,
                        "random_state": 42,
                    },
                },
            ]
        },
        "cross_validation_configuration": {
            "outer_cv": "StratifiedGroupKFold(n_splits=5, shuffle=True)",
            "inner_threshold_cv": "StratifiedGroupKFold(n_splits=4, shuffle=True)",
            "group_identifier": "applicant_id",
            "random_seeds": SEEDS,
            "total_evaluation_folds": len(SEEDS) * N_OUTER_SPLITS,
        },
        "validation_metrics": {
            "scenario_b_4675_grouped_cv": {
                "majority_class_baseline_accuracy": 0.6261,
                "oracle_ceiling_roc_auc": 0.7427,
                "oracle_ceiling_accuracy_at_050": 0.7076,
                "model_roc_auc_mean": 0.6772,
                "model_roc_auc_std": 0.0203,
                "model_brier_score_mean": 0.2110,
                "model_ece_10bin_mean": float(
                    round(
                        next(
                            r["ece_10bin_mean"]
                            for r in cal_summary_b
                            if r["variant"] == "Uncalibrated_LR_5Feat"
                        ),
                        4,
                    )
                ),
                "by_threshold_policy": lr6_scen_b,
                "oracle_by_threshold_policy": ora_scen_b,
            },
            "scenario_a_1183_grouped_cv": {
                "majority_class_baseline_accuracy": 0.6644,
                "oracle_ceiling_roc_auc": 0.6503,
                "oracle_ceiling_accuracy_at_050": 0.6754,
                "model_roc_auc_mean": 0.6095,
                "model_roc_auc_std": 0.0320,
                "model_brier_score_mean": 0.2154,
                "model_ece_10bin_mean": float(
                    round(
                        next(
                            r["ece_10bin_mean"]
                            for r in cal_summary_a
                            if r["variant"] == "Uncalibrated_LR_5Feat"
                        ),
                        4,
                    )
                ),
                "by_threshold_policy": lr6_scen_a,
                "oracle_by_threshold_policy": ora_scen_a,
            },
            "calibration_comparison": cal_summary_all,
        },
        "expected_schema": {
            "input": {
                "stage_1_prerequisite": "is_eligible == True (applicant must satisfy all mandatory Stage 1 rules before Stage 2 inference)",
                "features": {name: "float" for name in STAGE2_V2_FEATURES},
            },
            "output": {
                "is_eligible": "bool",
                "predicted_success_probability": "float in [0.0, 1.0] or None if ineligible",
                "suitability_percent": "float in [0.0, 100.0] or None if ineligible",
                "suitability_label": "str ('Suitable' | 'Needs Review' | 'Ineligible — Stage 1 Gate Failed')",
                "advisory_tier": "str ('Strong Fit' | 'Moderate Fit' | 'Needs Review' | 'Ineligible')",
                "applied_threshold": "float",
                "eligible_rank": "int (1-based rank among eligible candidates for the task) or None if ineligible",
                "key_contributing_factors": "list[dict] (human-readable domain explanations)",
                "model_version": "str ('2.0.0')",
                "advisory_disclaimer": "str",
            },
        },
        "limitations_and_disclaimers": [
            "SYNTHETIC SIMULATION TRAINING DATA: This model was trained on synthetic applicant-task pairs where task_success is a stochastic simulated outcome, not observed real-world employee performance.",
            "STAGE 1 GATEKEEPER AUTHORITY: This Stage 2 model is strictly subordinate to the deterministic Stage 1 Eligibility Gatekeeper. An applicant failing mandatory certification, experience, or assessment thresholds must never be scored as eligible or approved by Stage 2.",
            "ADVISORY RANKING ONLY: Predicted probabilities estimate relative task suitability among already-eligible candidates to assist administrator prioritization. Final task assignment authority rests exclusively with the human administrator.",
            "INHERENT STOCHASTIC CEILING: Due to Stage 1 range restriction and stochastic outcome variance, theoretical Oracle ROC-AUC is ~0.65 (Scenario A) to ~0.74 (Scenario B); probabilities should be interpreted as calibrated risk/fit estimates rather than deterministic guarantees.",
        ],
    }

    metadata_out_path = METADATA_DIR / NEW_METADATA_FILENAME
    with open(metadata_out_path, "w", encoding="utf-8") as f:
        json.dump(metadata_v2, f, indent=2)
    print(f"Saved comprehensive v2 metadata to: {metadata_out_path}")


if __name__ == "__main__":
    main()

