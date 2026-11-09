"""
VerifyMesh — Stage 2 Task-Specific ML Model Refinement
Phase 1: Reproducible Baseline and Benchmark Pipeline

Enforces all non-negotiable methodological rules:
1. Evaluates strictly on Stage 1 eligible applicant-task pairs (is_eligible == 1).
2. Restores true applicant_id and task_id from synthetic_applicant_task_pairs.csv for grouping.
3. Enforces zero target leakage in model inputs.
4. Uses 5-fold StratifiedGroupKFold grouped by applicant_id across 5 fixed random seeds.
5. Selects classification thresholds exclusively inside each training fold via inner
   StratifiedGroupKFold out-of-fold (OOF) probability predictions.
6. Reports ROC-AUC, Accuracy, Balanced Accuracy, Precision, Recall, F1, Failure-Class Recall,
   Brier Score, Majority-Class Baseline, and Oracle (latent_success_prob) Ceiling.
"""

from __future__ import annotations

import hashlib
import json
import os
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
from sklearn.ensemble import (
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# 1. Constants & Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "ml" / "experiments" / "task_specific_synthetic_data"
OUTPUT_DIR = Path(__file__).resolve().parent

PAIRS_CSV = DATA_DIR / "synthetic_applicant_task_pairs.csv"
TRAINING_CSV = DATA_DIR / "task_suitability_training.csv"
APPLICANTS_CSV = DATA_DIR / "synthetic_applicants.csv"
TASKS_CSV = DATA_DIR / "synthetic_tasks.csv"

SEEDS = [42, 123, 456, 789, 2026]
N_OUTER_SPLITS = 5
N_INNER_SPLITS = 4

FORBIDDEN_LEAKAGE_COLS = {
    "latent_score",
    "latent_success_prob",
    "simulation_scenario",
    "is_eligible",
    "ineligibility_reasons",
    "applicant_id",
    "task_id",
    "task_success",
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# 2. Dataset Loading, Alignment & Leakage Verification
# ---------------------------------------------------------------------------


def load_and_verify_eligible_dataset() -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Load synthetic_applicant_task_pairs.csv and task_suitability_training.csv,
    verify exact 1-to-1 alignment on the 1,183 eligible rows, and return the
    aligned DataFrame with engineered candidate features.
    """
    hashes = {
        "synthetic_applicants.csv": compute_sha256(APPLICANTS_CSV),
        "synthetic_tasks.csv": compute_sha256(TASKS_CSV),
        "synthetic_applicant_task_pairs.csv": compute_sha256(PAIRS_CSV),
        "task_suitability_training.csv": compute_sha256(TRAINING_CSV),
    }

    pairs_df = pd.read_csv(PAIRS_CSV, keep_default_na=False)
    train_df = pd.read_csv(TRAINING_CSV, keep_default_na=False)

    # Filter strictly to Stage 1 eligible rows
    elig_pairs = pairs_df[pairs_df["is_eligible"] == 1].reset_index(drop=True)

    # Verification 1: Row counts
    assert len(elig_pairs) == len(train_df) == 1183, (
        f"Expected 1,183 eligible rows, got {len(elig_pairs)} vs {len(train_df)}"
    )

    # Verification 2: Zero ineligible rows
    assert (elig_pairs["is_eligible"] == 1).all(), "Ineligible rows found in Stage 2 dataset!"
    assert (elig_pairs["cert_satisfied"] == 1).all(), "cert_satisfied != 1 found in eligible set!"
    assert (elig_pairs["experience_surplus_months"] >= 0).all(), (
        "Negative experience_surplus_months found in eligible set!"
    )
    assert (elig_pairs["assessment_gap"] >= 0).all(), (
        "Negative assessment_gap found in eligible set!"
    )

    # Verification 3: Exact 1-to-1 column and value correspondence across all 35 columns
    train_cols = list(train_df.columns)
    assert len(train_cols) == 35, f"Expected 35 columns in training CSV, got {len(train_cols)}"
    assert elig_pairs[train_cols].equals(train_df), (
        "Mismatch between pairs_df[is_eligible == 1] and task_suitability_training.csv!"
    )

    # Engineer candidate features deterministically (using only pre-outcome applicant & task inputs)
    df = elig_pairs.copy()

    # 3 engineered features from the legacy 28-feature RF pipeline
    df["exp_leverage_ratio"] = df["applicant_relevant_exp"] / (df["task_min_exp"] + 1.0)
    df["assessment_gap_sq"] = df["assessment_gap"] ** 2
    df["comm_gap_sq"] = df["communication_gap"] ** 2

    # Non-linear experience surplus saturation (diminishing returns beyond 12-24 months)
    df["exp_surplus_tanh"] = np.tanh(df["experience_surplus_months"] / 12.0)
    df["exp_surplus_log1p"] = np.log1p(np.maximum(0.0, df["experience_surplus_months"]))

    # Weakest-link / bottleneck features
    df["weakest_link_deficit"] = np.minimum(0.0, df["min_skill_margin"])
    df["has_skill_deficit"] = (df["min_skill_margin"] < 0.0).astype(float)

    # Exact certification match indicator (1 if task required a specific cert and applicant matched it)
    df[" voluntary_or_req_cert_bonus"] = (df["applicant_cert_count"] > 0).astype(float)

    return df, hashes


# ---------------------------------------------------------------------------
# 3. Feature Sets & Candidate Models
# ---------------------------------------------------------------------------

FEATURES_28_RF = [
    "difficulty_tier",
    "task_min_exp",
    "task_min_assessment",
    "task_min_comm",
    "task_min_prod",
    "task_min_sales",
    "task_min_cs",
    "applicant_relevant_exp",
    "applicant_sales_exp",
    "applicant_cs_exp",
    "applicant_cert_count",
    "applicant_has_sales_cert",
    "applicant_has_cs_cert",
    "applicant_has_tech_cert",
    "applicant_assessment_score",
    "applicant_comm_score",
    "applicant_prod_score",
    "applicant_sales_score",
    "applicant_cs_score",
    "experience_surplus_months",
    "assessment_gap",
    "communication_gap",
    "product_knowledge_gap",
    "sales_skill_gap",
    "customer_service_gap",
    "exp_leverage_ratio",
    "assessment_gap_sq",
    "comm_gap_sq",
]

FEATURES_4_COMPACT_LR = [
    "weighted_skill_margin",
    "exp_surplus_tanh",
    "difficulty_tier",
    "cert_satisfied",
]

FEATURES_6_WEAKEST_LINK_LR = [
    "weighted_skill_margin",
    "min_skill_margin",
    "weakest_link_deficit",
    "exp_surplus_tanh",
    "difficulty_tier",
    "cert_satisfied",
]

FEATURES_10_DOMAIN_RELATIONAL = [
    "weighted_skill_margin",
    "min_skill_margin",
    "exp_surplus_tanh",
    "difficulty_tier",
    "cert_satisfied",
    "assessment_gap",
    "communication_gap",
    "product_knowledge_gap",
    "sales_skill_gap",
    "customer_service_gap",
]


def verify_no_leakage(feature_cols: list[str], model_name: str) -> None:
    overlap = FORBIDDEN_LEAKAGE_COLS.intersection(set(feature_cols))
    if overlap:
        raise ValueError(f"Leakage columns detected in {model_name}: {overlap}")


def build_candidate_models(seed: int) -> dict[str, tuple[list[str], Pipeline]]:
    """
    Construct candidate scikit-learn Pipelines with their exact feature lists.
    """

    def make_scaled_pipeline(cols: list[str], estimator: Any) -> Pipeline:
        preprocessor = ColumnTransformer(
            transformers=[("scaler", StandardScaler(), cols)],
            remainder="drop",
        )
        return Pipeline([("preprocessor", preprocessor), ("classifier", estimator)])

    candidates: dict[str, tuple[list[str], Pipeline]] = {
        "Current_RF_28Feat": (
            FEATURES_28_RF,
            make_scaled_pipeline(
                FEATURES_28_RF,
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=5,
                    min_samples_split=10,
                    min_samples_leaf=1,
                    max_features="sqrt",
                    class_weight={0: 1.5, 1: 1.0},
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ),
        "Compact_LR_4Feat": (
            FEATURES_4_COMPACT_LR,
            make_scaled_pipeline(
                FEATURES_4_COMPACT_LR,
                LogisticRegression(
                    C=1.0,
                    l1_ratio=0.0,
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ),
        "Compact_LR_4Feat_Balanced": (
            FEATURES_4_COMPACT_LR,
            make_scaled_pipeline(
                FEATURES_4_COMPACT_LR,
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ),
        "Extended_LR_6Feat_WeakestLink": (
            FEATURES_6_WEAKEST_LINK_LR,
            make_scaled_pipeline(
                FEATURES_6_WEAKEST_LINK_LR,
                LogisticRegression(
                    C=0.5,
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ),
        "Extended_LR_10Feat_DomainGaps": (
            FEATURES_10_DOMAIN_RELATIONAL,
            make_scaled_pipeline(
                FEATURES_10_DOMAIN_RELATIONAL,
                LogisticRegression(
                    C=0.25,
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ),
        "Regularized_RF_10Feat": (
            FEATURES_10_DOMAIN_RELATIONAL,
            make_scaled_pipeline(
                FEATURES_10_DOMAIN_RELATIONAL,
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=4,
                    min_samples_split=25,
                    min_samples_leaf=18,
                    max_features="sqrt",
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ),
        "Regularized_RF_28Feat": (
            FEATURES_28_RF,
            make_scaled_pipeline(
                FEATURES_28_RF,
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=4,
                    min_samples_split=30,
                    min_samples_leaf=20,
                    max_features="sqrt",
                    random_state=seed,
                    n_jobs=1,
                ),
            ),
        ),
        "Regularized_GB_10Feat": (
            FEATURES_10_DOMAIN_RELATIONAL,
            make_scaled_pipeline(
                FEATURES_10_DOMAIN_RELATIONAL,
                GradientBoostingClassifier(
                    n_estimators=50,
                    learning_rate=0.04,
                    max_depth=2,
                    min_samples_leaf=25,
                    subsample=0.8,
                    random_state=seed,
                ),
            ),
        ),
        "Regularized_HistGB_10Feat": (
            FEATURES_10_DOMAIN_RELATIONAL,
            make_scaled_pipeline(
                FEATURES_10_DOMAIN_RELATIONAL,
                HistGradientBoostingClassifier(
                    max_iter=50,
                    learning_rate=0.04,
                    max_depth=3,
                    min_samples_leaf=30,
                    l2_regularization=2.5,
                    random_state=seed,
                ),
            ),
        ),
    }

    for name, (cols, _) in candidates.items():
        verify_no_leakage(cols, name)

    return candidates


# ---------------------------------------------------------------------------
# 4. Inner-Fold Threshold Selection & Metric Calculation
# ---------------------------------------------------------------------------


def compute_oof_training_probs(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    groups_train: np.ndarray,
    seed: int,
) -> np.ndarray:
    """
    Generate out-of-fold probability predictions strictly inside the training fold
    using an inner StratifiedGroupKFold.
    """
    inner_cv = StratifiedGroupKFold(
        n_splits=N_INNER_SPLITS, shuffle=True, random_state=seed
    )
    oof_probs = np.zeros(len(y_train), dtype=float)

    for inner_tr_idx, inner_val_idx in inner_cv.split(X_train, y_train, groups_train):
        # Verify zero applicant leakage in inner fold
        assert set(groups_train[inner_tr_idx]).isdisjoint(
            set(groups_train[inner_val_idx])
        ), "Applicant leakage detected in inner CV!"

        inner_model = clone(pipeline)
        inner_model.fit(X_train.iloc[inner_tr_idx], y_train[inner_tr_idx])
        oof_probs[inner_val_idx] = inner_model.predict_proba(
            X_train.iloc[inner_val_idx]
        )[:, 1]

    return oof_probs


def select_thresholds_from_training_oof(
    y_train: np.ndarray, oof_probs: np.ndarray
) -> dict[str, float]:
    """
    Select classification thresholds strictly using training OOF predictions.
    Returns three threshold policies:
      - fixed_050: standard 0.50 threshold
      - inner_bal_acc: threshold maximizing inner-OOF Balanced Accuracy
      - inner_macro_f1: threshold maximizing inner-OOF Macro F1 (subject to Precision >= 0.68)
    """
    grid = np.linspace(0.25, 0.75, 51)

    best_bal_t = 0.50
    best_bal_score = -1.0

    best_f1_t = 0.50
    best_f1_score = -1.0

    for t in grid:
        preds = (oof_probs >= t).astype(int)
        # Require at least minimal predictions in both classes to avoid degenerate all-0 or all-1 threshold
        if preds.sum() == 0 or preds.sum() == len(preds):
            continue

        bal = balanced_accuracy_score(y_train, preds)
        if bal > best_bal_score:
            best_bal_score = bal
            best_bal_t = float(round(t, 4))

        prec_1 = precision_score(y_train, preds, pos_label=1, zero_division=0)
        macro_f1 = f1_score(y_train, preds, average="macro", zero_division=0)
        if prec_1 >= 0.68 and macro_f1 > best_f1_score:
            best_f1_score = macro_f1
            best_f1_t = float(round(t, 4))

    return {
        "fixed_050": 0.50,
        "inner_bal_acc": best_bal_t,
        "inner_macro_f1": best_f1_t,
    }


def evaluate_predictions(
    y_true: np.ndarray,
    probs: np.ndarray,
    threshold: float,
) -> dict[str, float]:
    preds = (probs >= threshold).astype(int)
    # ROC-AUC requires non-constant probs; for constant majority baseline, ROC-AUC is 0.50
    if np.allclose(probs, probs[0]):
        auc_val = 0.50
    else:
        auc_val = float(roc_auc_score(y_true, probs))

    return {
        "threshold": float(threshold),
        "roc_auc": auc_val,
        "brier_score": float(brier_score_loss(y_true, probs)),
        "accuracy": float(accuracy_score(y_true, preds)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, preds)),
        "precision": float(precision_score(y_true, preds, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, preds, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_true, preds, pos_label=1, zero_division=0)),
        "failure_precision": float(
            precision_score(y_true, preds, pos_label=0, zero_division=0)
        ),
        "failure_recall": float(
            recall_score(y_true, preds, pos_label=0, zero_division=0)
        ),
        "failure_f1": float(f1_score(y_true, preds, pos_label=0, zero_division=0)),
        "macro_f1": float(f1_score(y_true, preds, average="macro", zero_division=0)),
    }


# ---------------------------------------------------------------------------
# 5. Main Benchmark Execution Loop
# ---------------------------------------------------------------------------


def run_benchmark_on_dataframe(
    df: pd.DataFrame, dataset_label: str = "eligible_1183"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Execute 5-seed x 5-fold StratifiedGroupKFold benchmark on df.
    Returns (fold_records_df, summary_df).
    """
    y = df["task_success"].to_numpy(dtype=int)
    groups = df["applicant_id"].to_numpy()
    oracle_probs = df["latent_success_prob"].to_numpy(dtype=float)

    fold_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        outer_cv = StratifiedGroupKFold(
            n_splits=N_OUTER_SPLITS, shuffle=True, random_state=seed
        )
        candidates = build_candidate_models(seed)

        for fold_idx, (train_idx, val_idx) in enumerate(
            outer_cv.split(df, y, groups), start=1
        ):
            # Enforce strict group disjointness
            train_apps = set(groups[train_idx])
            val_apps = set(groups[val_idx])
            assert train_apps.isdisjoint(val_apps), (
                f"Applicant overlap in seed={seed}, fold={fold_idx}!"
            )

            y_train, y_val = y[train_idx], y[val_idx]
            groups_train = groups[train_idx]

            # 1. Majority-Class Baseline
            train_pos_rate = float(y_train.mean())
            maj_probs = np.full(len(y_val), train_pos_rate, dtype=float)
            maj_metrics = evaluate_predictions(y_val, maj_probs, threshold=0.50)
            fold_rows.append(
                {
                    "dataset": dataset_label,
                    "seed": seed,
                    "fold": fold_idx,
                    "model": "Baseline_Majority_Class",
                    "num_features": 0,
                    "threshold_policy": "fixed_050",
                    **maj_metrics,
                }
            )

            # 2. Oracle Ceiling (using true latent_success_prob)
            oracle_val_probs = oracle_probs[val_idx]
            oracle_train_probs = oracle_probs[train_idx]
            oracle_thresholds = select_thresholds_from_training_oof(
                y_train, oracle_train_probs
            )
            for policy_name, thresh in oracle_thresholds.items():
                ora_metrics = evaluate_predictions(y_val, oracle_val_probs, threshold=thresh)
                fold_rows.append(
                    {
                        "dataset": dataset_label,
                        "seed": seed,
                        "fold": fold_idx,
                        "model": "Oracle_Latent_Prob",
                        "num_features": 0,
                        "threshold_policy": policy_name,
                        **ora_metrics,
                    }
                )

            # 3. Candidate ML Models
            for model_name, (feat_cols, pipeline) in candidates.items():
                X_train = df.iloc[train_idx][feat_cols]
                X_val = df.iloc[val_idx][feat_cols]

                # Inner-fold OOF threshold selection strictly on training partition
                oof_train_probs = compute_oof_training_probs(
                    pipeline, X_train, y_train, groups_train, seed=seed + fold_idx
                )
                thresholds = select_thresholds_from_training_oof(y_train, oof_train_probs)

                # For Current_RF_28Feat, also record the legacy fixed 0.61 threshold for diagnostic comparison
                if model_name == "Current_RF_28Feat":
                    thresholds["legacy_fixed_061"] = 0.61

                # Fit model on full outer training partition and predict on validation partition
                fitted_pipe = clone(pipeline)
                fitted_pipe.fit(X_train, y_train)
                val_probs = fitted_pipe.predict_proba(X_val)[:, 1]

                for policy_name, thresh in thresholds.items():
                    metrics = evaluate_predictions(y_val, val_probs, threshold=thresh)
                    fold_rows.append(
                        {
                            "dataset": dataset_label,
                            "seed": seed,
                            "fold": fold_idx,
                            "model": model_name,
                            "num_features": len(feat_cols),
                            "threshold_policy": policy_name,
                            **metrics,
                        }
                    )

    fold_df = pd.DataFrame(fold_rows)

    # Aggregate mean and std across all 25 folds (5 seeds x 5 folds)
    metric_cols = [
        "threshold",
        "roc_auc",
        "brier_score",
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "failure_precision",
        "failure_recall",
        "failure_f1",
        "macro_f1",
    ]

    summary_rows = []
    for (ds, model_name, n_feat, policy), grp in fold_df.groupby(
        ["dataset", "model", "num_features", "threshold_policy"], sort=False
    ):
        row: dict[str, Any] = {
            "dataset": ds,
            "model": model_name,
            "num_features": int(n_feat),
            "threshold_policy": policy,
            "n_folds_total": len(grp),
        }
        for m in metric_cols:
            row[f"{m}_mean"] = float(grp[m].mean())
            row[f"{m}_std"] = float(grp[m].std(ddof=1))
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    return fold_df, summary_df


def main() -> None:
    print("=== VerifyMesh Phase 1: Reproducible Baseline & Benchmark Pipeline ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_1183, hashes = load_and_verify_eligible_dataset()
    print(
        f"Loaded & verified 1,183 eligible pairs across {df_1183['applicant_id'].nunique()} unique applicants "
        f"and {df_1183['task_id'].nunique()} unique tasks."
    )

    # Primary benchmark on all 1,183 Stage 1 eligible records
    print("Running 5-seed x 5-fold StratifiedGroupKFold on all 1,183 eligible records...")
    fold_1183, summary_1183 = run_benchmark_on_dataframe(df_1183, "eligible_1183")

    # Supplementary sensitivity check on the 1,127 subset (where assessment_satisfied == 1)
    df_1127 = df_1183[df_1183["assessment_satisfied"] == 1].reset_index(drop=True)
    print(
        f"Running supplementary sensitivity check on 1,127 subset "
        f"({df_1127['applicant_id'].nunique()} unique applicants)..."
    )
    fold_1127, summary_1127 = run_benchmark_on_dataframe(
        df_1127, "eligible_1127_strict_subskills"
    )

    all_folds = pd.concat([fold_1183, fold_1127], ignore_index=True)
    all_summaries = pd.concat([summary_1183, summary_1127], ignore_index=True)

    # Save CSV artifacts
    fold_csv_path = OUTPUT_DIR / "phase1_fold_details.csv"
    summary_csv_path = OUTPUT_DIR / "phase1_benchmark_summary.csv"
    all_folds.to_csv(fold_csv_path, index=False)
    all_summaries.to_csv(summary_csv_path, index=False)

    # Save JSON artifact with full reproducibility metadata
    metadata_payload = {
        "phase": "Phase 1 — Reproducible Baseline and Benchmark Pipeline",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "scikit_learn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "joblib_version": joblib.__version__,
        },
        "dataset_audit": {
            "simulation_scenario": "scenario_a",
            "total_pairs_in_source": 6000,
            "total_applicants_in_source": 800,
            "total_tasks_in_source": 30,
            "eligible_pairs_1183": {
                "rows": int(len(df_1183)),
                "unique_applicants": int(df_1183["applicant_id"].nunique()),
                "unique_tasks": int(df_1183["task_id"].nunique()),
                "positive_count": int((df_1183["task_success"] == 1).sum()),
                "negative_count": int((df_1183["task_success"] == 0).sum()),
                "positive_rate": float(df_1183["task_success"].mean()),
            },
            "eligible_subset_1127": {
                "rows": int(len(df_1127)),
                "unique_applicants": int(df_1127["applicant_id"].nunique()),
                "unique_tasks": int(df_1127["task_id"].nunique()),
                "positive_count": int((df_1127["task_success"] == 1).sum()),
                "negative_count": int((df_1127["task_success"] == 0).sum()),
                "positive_rate": float(df_1127["task_success"].mean()),
            },
            "sha256_hashes": hashes,
        },
        "cv_configuration": {
            "splitter": "StratifiedGroupKFold",
            "group_column": "applicant_id",
            "n_outer_splits": N_OUTER_SPLITS,
            "n_inner_splits": N_INNER_SPLITS,
            "random_seeds": SEEDS,
            "total_outer_evaluations_per_model": len(SEEDS) * N_OUTER_SPLITS,
        },
        "feature_sets": {
            "FEATURES_28_RF": FEATURES_28_RF,
            "FEATURES_4_COMPACT_LR": FEATURES_4_COMPACT_LR,
            "FEATURES_6_WEAKEST_LINK_LR": FEATURES_6_WEAKEST_LINK_LR,
            "FEATURES_10_DOMAIN_RELATIONAL": FEATURES_10_DOMAIN_RELATIONAL,
        },
        "summary_results": all_summaries.to_dict(orient="records"),
    }

    json_path = OUTPUT_DIR / "phase1_benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)

    print(f"Saved: {summary_csv_path}")
    print(f"Saved: {fold_csv_path}")
    print(f"Saved: {json_path}")

    # Print concise console table for eligible_1183
    print("\n=== SUMMARY (1,183 Eligible Pairs — 5 Seeds x 5-Fold StratifiedGroupKFold) ===")
    cols_to_show = [
        "model",
        "num_features",
        "threshold_policy",
        "threshold_mean",
        "roc_auc_mean",
        "roc_auc_std",
        "accuracy_mean",
        "balanced_accuracy_mean",
        "precision_mean",
        "recall_mean",
        "f1_mean",
        "failure_recall_mean",
        "brier_score_mean",
    ]
    print(
        summary_1183[cols_to_show].to_string(
            index=False, float_format=lambda x: f"{x:.4f}"
        )
    )


if __name__ == "__main__":
    main()

