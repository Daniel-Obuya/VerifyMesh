"""
VerifyMesh - Standalone Model Training Pipeline (Binary Gatekeeper)
==================================================================
Reproduces the Random Forest binary eligibility classifier from:
  ml/notebooks/Verify_Mesh.ipynb
Dataset:
  data/raw/VerifyMesh_Competency_Dataset_V2.csv
Output Artifact:
  backend/models/binary_eligibility_model.pkl

Author: Daniel Obuya (VerifyMesh Capstone)
"""

import os
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, confusion_matrix

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "VerifyMesh_Competency_Dataset_V2.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "backend" / "models" / "binary_eligibility_model.pkl"

# Exact authoritative feature ordering expected by inference
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


def load_and_preprocess_data(data_path: Path):
    """Load raw dataset and perform identical feature engineering as Colab notebook."""
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found at: {data_path}")

    df = pd.read_csv(data_path)
    print(f"[Data] Loaded dataset with shape {df.shape} from: {data_path}")

    # Map target competency levels to binary classes
    df["binary_target"] = df["competency_level"].map(TARGET_MAP)
    df["target_numeric"] = df["binary_target"].map(NUMERIC_LABEL_MAP)

    # 1. Feature Engineering: Certified leverage
    df["certified_leverage"] = df["certification_count"] * (1 + df["relevant_certification"])

    # 2. Feature Engineering: Total tenure
    df["total_experience_months"] = (
        df["previous_experience_months"]
        + df["sales_experience_months"]
        + df["customer_service_experience_months"]
    )

    # 3. Feature Engineering: Aggregate scores
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

    return X, y, df


def build_pipeline():
    """Build the standard production pipeline (StandardScaler + RandomForestClassifier)."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=150,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        ))
    ])


def train_and_evaluate(data_path: Path, output_path: Path, save_model: bool = True):
    """Execute stratified split, 5-fold cross-validation, test evaluation, and model export."""
    X, y, df = load_and_preprocess_data(data_path)

    print("\n--- Target Class Distribution ---")
    dist = df["binary_target"].value_counts()
    pct = df["binary_target"].value_counts(normalize=True) * 100
    for label in dist.index:
        print(f"  {label}: {dist[label]} ({pct[label]:.2f}%)")

    # Stratified 80/20 train/test split with fixed random seed
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[Split] Train Set: {X_train.shape[0]} samples | Test Holdout: {X_test.shape[0]} samples")

    # 5-Fold Stratified Cross-Validation
    print("\n[Cross-Validation] Running 5-Fold Stratified Cross-Validation on Train Set...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pipeline = build_pipeline()
    cv_scores = cross_validate(pipeline, X_train, y_train, cv=skf, scoring=["accuracy", "f1_macro", "roc_auc"])

    print(f"  CV Mean Accuracy : {cv_scores['test_accuracy'].mean():.4f} (±{cv_scores['test_accuracy'].std():.4f})")
    print(f"  CV Mean Macro F1 : {cv_scores['test_f1_macro'].mean():.4f} (±{cv_scores['test_f1_macro'].std():.4f})")
    print(f"  CV Mean ROC-AUC  : {cv_scores['test_roc_auc'].mean():.4f} (±{cv_scores['test_roc_auc'].std():.4f})")

    # Train final model on training set
    print("\n[Training] Fitting pipeline on 1,600 training samples...")
    pipeline.fit(X_train, y_train)

    # Holdout Test Evaluation
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    test_acc = accuracy_score(y_test, y_pred)
    test_roc_auc = roc_auc_score(y_test, y_proba)
    conf = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 60)
    print("HOLD-OUT TEST EVALUATION REPORT (400 Samples)")
    print("=" * 60)
    print(f"Test Accuracy : {test_acc:.4f} ({test_acc * 100:.2f}%)")
    print(f"Test ROC-AUC  : {test_roc_auc:.4f}")
    print("\nConfusion Matrix:")
    print(f"  True Not Eligible (TN): {conf[0, 0]} | False Eligible (FP): {conf[0, 1]}")
    print(f"  False Not Eligible (FN): {conf[1, 0]} | True Eligible (TP): {conf[1, 1]}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Not Eligible", "Eligible"], digits=4))

    # Save artifact
    if save_model:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, output_path)
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n[Artifact] Model successfully serialized to:\n  {output_path} ({file_size_mb:.2f} MB)")

    return pipeline, test_acc, test_roc_auc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VerifyMesh Binary Gatekeeper Model Training")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to raw dataset CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output path for .pkl model artifact")
    parser.add_argument("--no-save", action="store_true", help="Run evaluation without overwriting existing model artifact")
    args = parser.parse_args()

    train_and_evaluate(args.data, args.output, save_model=not args.no_save)
