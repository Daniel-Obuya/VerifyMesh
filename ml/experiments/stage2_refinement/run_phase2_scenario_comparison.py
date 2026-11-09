"""
VerifyMesh — Stage 2 Task-Specific ML Model Refinement
Phase 2: Controlled Dataset / Simulation Refinement & Scenario Comparison

Compares:
1. Original Dataset (Scenario A: Balanced Compensatory, 800 applicants, 6,000 pairs, 1,183 eligible)
2. Controlled Refined Dataset (Scenario B: Strict Bottleneck / Weakest-Link, 3,200 applicants,
   24,000 pairs, saved in ml/experiments/stage2_refinement/scenario_b_data/)

All evaluations strictly follow the Phase 1 protocol:
- Eligible pairs only (is_eligible == 1)
- 5-fold StratifiedGroupKFold grouped by true applicant_id across 5 fixed seeds
- Threshold selection strictly inside each training fold via 4-fold inner StratifiedGroupKFold OOF
- Zero target leakage
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

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ml" / "experiments" / "task_specific_synthetic_data"))
sys.path.insert(0, str(REPO_ROOT / "ml" / "experiments" / "stage2_refinement"))

import generate_synthetic_dataset as gen
from run_phase1_benchmark import (
    FEATURES_4_COMPACT_LR,
    FEATURES_6_WEAKEST_LINK_LR,
    FEATURES_10_DOMAIN_RELATIONAL,
    FEATURES_28_RF,
    N_INNER_SPLITS,
    N_OUTER_SPLITS,
    SEEDS,
    compute_sha256,
    run_benchmark_on_dataframe,
)

OUTPUT_DIR = Path(__file__).resolve().parent
SCENARIO_B_DIR = OUTPUT_DIR / "scenario_b_data"
ORIG_DATA_DIR = REPO_ROOT / "ml" / "experiments" / "task_specific_synthetic_data"


def prepare_engineered_eligible_df(pairs_csv: Path, train_csv: Path) -> pd.DataFrame:
    pairs_df = pd.read_csv(pairs_csv, keep_default_na=False)
    train_df = pd.read_csv(train_csv, keep_default_na=False)

    elig_pairs = pairs_df[pairs_df["is_eligible"] == 1].reset_index(drop=True)
    assert len(elig_pairs) == len(train_df), (
        f"Row count mismatch: {len(elig_pairs)} vs {len(train_df)}"
    )
    assert (elig_pairs["is_eligible"] == 1).all()
    train_cols = list(train_df.columns)
    assert elig_pairs[train_cols].equals(train_df), "1-to-1 column match failed!"

    df = elig_pairs.copy()
    df["exp_leverage_ratio"] = df["applicant_relevant_exp"] / (df["task_min_exp"] + 1.0)
    df["assessment_gap_sq"] = df["assessment_gap"] ** 2
    df["comm_gap_sq"] = df["communication_gap"] ** 2
    df["exp_surplus_tanh"] = np.tanh(df["experience_surplus_months"] / 12.0)
    df["exp_surplus_log1p"] = np.log1p(np.maximum(0.0, df["experience_surplus_months"]))
    df["weakest_link_deficit"] = np.minimum(0.0, df["min_skill_margin"])
    df["has_skill_deficit"] = (df["min_skill_margin"] < 0.0).astype(float)

    return df


def main() -> None:
    print("=== VerifyMesh Phase 2: Scenario A vs. Scenario B Controlled Comparison ===")
    SCENARIO_B_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure Scenario B dataset exists in SCENARIO_B_DIR (without touching original files)
    scen_b_pairs = SCENARIO_B_DIR / "synthetic_applicant_task_pairs.csv"
    scen_b_train = SCENARIO_B_DIR / "task_suitability_training.csv"
    scen_b_apps = SCENARIO_B_DIR / "synthetic_applicants.csv"
    scen_b_tasks = SCENARIO_B_DIR / "synthetic_tasks.csv"

    if not (scen_b_pairs.exists() and scen_b_train.exists()):
        print("Generating Scenario B dataset (3,200 applicants, 30 tasks, 24,000 pairs)...")
        gen.generate_task_specific_dataset(
            num_applicants=3200,
            num_tasks=30,
            num_pairs=24000,
            scenario="scenario_b",
            seed=42,
            output_dir=SCENARIO_B_DIR,
        )

    # Load Scenario A (from Phase 1 summary if already computed, plus dataset stats)
    df_scen_a = prepare_engineered_eligible_df(
        ORIG_DATA_DIR / "synthetic_applicant_task_pairs.csv",
        ORIG_DATA_DIR / "task_suitability_training.csv",
    )
    df_scen_b = prepare_engineered_eligible_df(scen_b_pairs, scen_b_train)

    print(
        f"Scenario A Eligible: {len(df_scen_a)} rows ({df_scen_a['applicant_id'].nunique()} applicants, "
        f"pos_rate={df_scen_a['task_success'].mean():.4f})"
    )
    print(
        f"Scenario B Eligible: {len(df_scen_b)} rows ({df_scen_b['applicant_id'].nunique()} applicants, "
        f"pos_rate={df_scen_b['task_success'].mean():.4f})"
    )

    # Load Scenario A benchmark summary from Phase 1
    p1_summary_csv = OUTPUT_DIR / "phase1_benchmark_summary.csv"
    p1_fold_csv = OUTPUT_DIR / "phase1_fold_details.csv"
    assert p1_summary_csv.exists(), "Phase 1 summary CSV missing!"

    summary_a = pd.read_csv(p1_summary_csv)
    summary_a = summary_a[summary_a["dataset"] == "eligible_1183"].copy()
    summary_a["dataset"] = "scenario_a_1183"

    fold_a = pd.read_csv(p1_fold_csv)
    fold_a = fold_a[fold_a["dataset"] == "eligible_1183"].copy()
    fold_a["dataset"] = "scenario_a_1183"

    # Run identical 5-seed x 5-fold StratifiedGroupKFold benchmark on Scenario B
    print(
        f"Running 5-seed x 5-fold StratifiedGroupKFold benchmark on Scenario B ({len(df_scen_b)} eligible rows)..."
    )
    fold_b, summary_b = run_benchmark_on_dataframe(
        df_scen_b, dataset_label=f"scenario_b_{len(df_scen_b)}"
    )

    combined_summary = pd.concat([summary_a, summary_b], ignore_index=True)
    combined_folds = pd.concat([fold_a, fold_b], ignore_index=True)

    p2_summary_path = OUTPUT_DIR / "phase2_scenario_comparison_summary.csv"
    p2_folds_path = OUTPUT_DIR / "phase2_scenario_comparison_folds.csv"
    combined_summary.to_csv(p2_summary_path, index=False)
    combined_folds.to_csv(p2_folds_path, index=False)

    scen_b_hashes = {
        "synthetic_applicants.csv": compute_sha256(scen_b_apps),
        "synthetic_tasks.csv": compute_sha256(scen_b_tasks),
        "synthetic_applicant_task_pairs.csv": compute_sha256(scen_b_pairs),
        "task_suitability_training.csv": compute_sha256(scen_b_train),
    }

    p2_json = {
        "phase": "Phase 2 — Controlled Dataset / Simulation Refinement",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "scikit_learn_version": sklearn.__version__,
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "joblib_version": joblib.__version__,
        },
        "datasets": {
            "scenario_a": {
                "scenario": "scenario_a (Balanced Compensatory)",
                "seed": 42,
                "total_applicants": 800,
                "total_tasks": 30,
                "total_pairs": 6000,
                "eligible_pairs": int(len(df_scen_a)),
                "unique_eligible_applicants": int(df_scen_a["applicant_id"].nunique()),
                "unique_eligible_tasks": int(df_scen_a["task_id"].nunique()),
                "positive_rate": float(df_scen_a["task_success"].mean()),
                "mean_latent_prob": float(df_scen_a["latent_success_prob"].mean()),
                "std_latent_prob": float(df_scen_a["latent_success_prob"].std()),
            },
            "scenario_b": {
                "scenario": "scenario_b (Strict Bottleneck / Weakest-Link)",
                "seed": 42,
                "total_applicants": 3200,
                "total_tasks": 30,
                "total_pairs": 24000,
                "eligible_pairs": int(len(df_scen_b)),
                "unique_eligible_applicants": int(df_scen_b["applicant_id"].nunique()),
                "unique_eligible_tasks": int(df_scen_b["task_id"].nunique()),
                "positive_rate": float(df_scen_b["task_success"].mean()),
                "mean_latent_prob": float(df_scen_b["latent_success_prob"].mean()),
                "std_latent_prob": float(df_scen_b["latent_success_prob"].std()),
                "sha256_hashes": scen_b_hashes,
            },
        },
        "summary_results": combined_summary.to_dict(orient="records"),
    }

    p2_json_path = OUTPUT_DIR / "phase2_scenario_comparison_results.json"
    with open(p2_json_path, "w", encoding="utf-8") as f:
        json.dump(p2_json, f, indent=2)

    print(f"Saved: {p2_summary_path}")
    print(f"Saved: {p2_folds_path}")
    print(f"Saved: {p2_json_path}")

    cols = [
        "dataset",
        "model",
        "num_features",
        "threshold_policy",
        "threshold_mean",
        "roc_auc_mean",
        "roc_auc_std",
        "brier_score_mean",
        "accuracy_mean",
        "balanced_accuracy_mean",
        "precision_mean",
        "recall_mean",
        "f1_mean",
        "failure_recall_mean",
    ]
    print("\n=== SCENARIO B BENCHMARK SUMMARY ===")
    print(
        summary_b[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}")
    )


if __name__ == "__main__":
    main()

