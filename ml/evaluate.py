"""
VerifyMesh - Standalone Model Evaluation & Audit Script
======================================================
Evaluates the pre-trained binary eligibility model on the holdout dataset:
  - Verifies model loading and feature compatibility
  - Computes hold-out Accuracy, ROC-AUC, and F1-Scores
  - Generates confusion matrix and decision threshold sensitivity audit

Author: Daniel Obuya (VerifyMesh Capstone)
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "binary_eligibility_model.pkl"
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "VerifyMesh_Competency_Dataset_V2.csv"

EXPECTED_FEATURES = [
    "previous_experience_months",
    "sales_experience_months",
    "customer_service_experience_months",
    "certification_count",
    "relevant_certification",
    "assessment_score",
    "communication_score",
    "product_knowledge_score",
    "sales_skill_score",
    "customer_service_score",
    "certified_leverage",
    "total_experience_months",
    "mean_score",
    "min_score",
    "max_score"
]

TARGET_MAP = {
    "Advanced": "Eligible",
    "Competent": "Eligible",
    "Basic": "Not Eligible",
    "Needs Improvement": "Not Eligible"
}

NUMERIC_LABEL_MAP = {
    "Not Eligible": 0,
    "Eligible": 1
}


def evaluate_model(model_path: Path, data_path: Path):
    """Load pre-trained model and audit performance against the test holdout."""
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found at: {model_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {data_path}")

    # Load model
    model = joblib.load(model_path)
    print(f"[Model] Successfully loaded pre-trained model from:\n  {model_path}")

    # Load data and apply feature engineering
    df = pd.read_csv(data_path)
    df["binary_target"] = df["competency_level"].map(TARGET_MAP)
    df["target_numeric"] = df["binary_target"].map(NUMERIC_LABEL_MAP)

    df["certified_leverage"] = df["certification_count"] * (1 + df["relevant_certification"])
    df["total_experience_months"] = (
        df["previous_experience_months"]
        + df["sales_experience_months"]
        + df["customer_service_experience_months"]
    )
    score_cols = [
        "assessment_score",
        "communication_score",
        "product_knowledge_score",
        "sales_skill_score",
        "customer_service_score"
    ]
    df["mean_score"] = df[score_cols].mean(axis=1)
    df["min_score"] = df[score_cols].min(axis=1)
    df["max_score"] = df[score_cols].max(axis=1)

    X = df[EXPECTED_FEATURES]
    y = df["target_numeric"]

    # Stratified test holdout (identical seed 42)
    _X_train, X_test, _y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    conf = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 65)
    print("VERIFYMESH BINARY GATEKEEPER - MODEL AUDIT REPORT")
    print("=" * 65)
    print(f"Evaluated Test Samples : {len(y_test)} (Stratified Holdout)")
    print(f"Accuracy               : {acc:.4f} ({acc * 100:.2f}%)")
    print(f"ROC-AUC Score          : {auc:.4f}")
    print("\nConfusion Matrix:")
    print(f"  True Negatives (TN)  : {conf[0, 0]:3d}  |  False Positives (FP) : {conf[0, 1]:3d}")
    print(f"  False Negatives (FN) : {conf[1, 0]:3d}  |  True Positives (TP)  : {conf[1, 1]:3d}")

    print("\nDetailed Classification Metrics:")
    print(classification_report(y_test, y_pred, target_names=["Not Eligible", "Eligible"], digits=4))

    print("-" * 65)
    print("DECISION THRESHOLD SENSITIVITY AUDIT (P(Eligible))")
    print("-" * 65)
    print(f"{'Threshold':<12} {'Accuracy':<12} {'Precision (Eligible)':<22} {'Recall (Eligible)':<18}")
    for t in [0.40, 0.45, 0.50, 0.55, 0.60]:
        t_pred = (y_proba >= t).astype(int)
        t_acc = accuracy_score(y_test, t_pred)
        t_prec = precision_score(y_test, t_pred, zero_division=0)
        t_rec = recall_score(y_test, t_pred, zero_division=0)
        marker = " <-- [Active System Threshold]" if t == 0.50 else ""
        print(f"{t:<12.2f} {t_acc:<12.4f} {t_prec:<22.4f} {t_rec:<18.4f}{marker}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and evaluate pre-trained VerifyMesh model")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="Path to binary_eligibility_model.pkl")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to raw dataset CSV")
    args = parser.parse_args()

    evaluate_model(args.model, args.data)
