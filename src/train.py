import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for generating figures
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ============================================================
# VERIFYMESH - STEP 2
# BASELINE RANDOM FOREST CLASSIFIER
# ============================================================

# ------------------------------------------------------------
# 1. Project Paths
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 2. Expected Structure and Schema
# ------------------------------------------------------------
feature_columns = [
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
]

target_column = "competency_level"

expected_classes = [
    "Needs Improvement",
    "Basic",
    "Competent",
    "Advanced",
]

print("=" * 65)
print("VERIFYMESH - STEP 2: BASELINE RANDOM FOREST")
print("=" * 65)

# ------------------------------------------------------------
# 3. Load Processed Datasets
# ------------------------------------------------------------
print("\n[1] LOADING PROCESSED DATASETS")

train_features_path = PROCESSED_DATA_DIR / "X_train.csv"
test_features_path = PROCESSED_DATA_DIR / "X_test.csv"
train_target_path = PROCESSED_DATA_DIR / "y_train.csv"
test_target_path = PROCESSED_DATA_DIR / "y_test.csv"

for p in [train_features_path, test_features_path, train_target_path, test_target_path]:
    if not p.exists():
        raise FileNotFoundError(f"Required data file missing: {p}")

X_train = pd.read_csv(train_features_path)
X_test = pd.read_csv(test_features_path)
y_train = pd.read_csv(train_target_path)[target_column]
y_test = pd.read_csv(test_target_path)[target_column]

print(f"Loaded X_train from : {train_features_path.name}")
print(f"Loaded X_test from  : {test_features_path.name}")
print(f"Loaded y_train from : {train_target_path.name}")
print(f"Loaded y_test from  : {test_target_path.name}")

# ------------------------------------------------------------
# 4. Verify Dimensions and Features
# ------------------------------------------------------------
print("\n[2] VERIFYING DIMENSIONS AND COLUMNS")

print(f"X_train shape : {X_train.shape} (Expected: 1600, 10)")
print(f"X_test shape  : {X_test.shape}  (Expected: 400, 10)")
print(f"y_train shape : {y_train.shape}  (Expected: 1600,)")
print(f"y_test shape  : {y_test.shape}   (Expected: 400,)")

if X_train.shape != (1600, 10):
    raise ValueError(f"Unexpected X_train shape: {X_train.shape}")
if X_test.shape != (400, 10):
    raise ValueError(f"Unexpected X_test shape: {X_test.shape}")
if y_train.shape != (1600,):
    raise ValueError(f"Unexpected y_train shape: {y_train.shape}")
if y_test.shape != (400,):
    raise ValueError(f"Unexpected y_test shape: {y_test.shape}")

if list(X_train.columns) != feature_columns:
    raise ValueError("X_train columns do not match expected feature list.")
if list(X_test.columns) != feature_columns:
    raise ValueError("X_test columns do not match expected feature list.")

if "agent_id" in X_train.columns or "agent_id" in X_test.columns:
    raise ValueError("Leakage alert: 'agent_id' must NOT be in feature set!")

print("✓ All shapes and feature columns verified.")
print("✓ Verified that agent_id is strictly excluded.")

# ------------------------------------------------------------
# 5. Initialize Baseline Model
# ------------------------------------------------------------
print("\n[3] INITIALIZING BASELINE RANDOM FOREST")

rf = RandomForestClassifier(
    n_estimators=100,  #100 decision trees will be built
    random_state=42 #42 is the seed for reproducibility
)

print("Configuration:")
print(f"  - n_estimators : 100")
print(f"  - random_state : 42")
print(f"  - max_depth    : None (standard default, unpruned)")
print(f"  - criterion    : 'gini' (standard default)")

# ------------------------------------------------------------
# 6. Train the Baseline Model (Training Set Only)
# ------------------------------------------------------------
print("\n[4] TRAINING MODEL ON TRAINING DATA ONLY")
rf.fit(X_train, y_train)
print("✓ Training completed successfully.")

# ------------------------------------------------------------
# 7. Generate Predictions on Test Set
# ------------------------------------------------------------
print("\n[5] GENERATING PREDICTIONS ON UNSEEN TEST SET")
y_pred = rf.predict(X_test)
print("✓ Generated predictions for 400 test records.")

# ------------------------------------------------------------
# 8. Compute Baseline Metrics
# ------------------------------------------------------------
print("\n[6] BASELINE EVALUATION METRICS")

accuracy = accuracy_score(y_test, y_pred)
precision_macro = precision_score(y_test, y_pred, average="macro")
precision_weighted = precision_score(y_test, y_pred, average="weighted")
recall_macro = recall_score(y_test, y_pred, average="macro")
recall_weighted = recall_score(y_test, y_pred, average="weighted")
f1_macro = f1_score(y_test, y_pred, average="macro")
f1_weighted = f1_score(y_test, y_pred, average="weighted")

print(f"Overall Accuracy   : {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Macro Precision    : {precision_macro:.4f}")
print(f"Weighted Precision : {precision_weighted:.4f}")
print(f"Macro Recall       : {recall_macro:.4f}")
print(f"Weighted Recall    : {recall_weighted:.4f}")
print(f"Macro F1-Score     : {f1_macro:.4f}")
print(f"Weighted F1-Score  : {f1_weighted:.4f}")

print("\nDetailed Classification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        labels=expected_classes,
        target_names=expected_classes,
        digits=4,
    )
)

# ------------------------------------------------------------
# 9. Confusion Matrix & Visualization
# ------------------------------------------------------------
print("[7] GENERATING CONFUSION MATRIX")

cm = confusion_matrix(y_test, y_pred, labels=expected_classes)
cm_df = pd.DataFrame(cm, index=expected_classes, columns=expected_classes)

print("\nConfusion Matrix (Rows: Actual, Columns: Predicted):")
print(cm_df)

plt.figure(figsize=(8, 6))
sns.heatmap(
    cm_df,
    annot=True,
    fmt="d",
    cmap="Blues",
    cbar=True,
    annot_kws={"size": 12},
)
plt.title("VerifyMesh - Baseline Random Forest Confusion Matrix", fontsize=13, pad=12)
plt.xlabel("Predicted Competency Level", fontsize=11)
plt.ylabel("Actual Competency Level", fontsize=11)
plt.tight_layout()

cm_fig_path = RESULTS_DIR / "baseline_confusion_matrix.png"
plt.savefig(cm_fig_path, dpi=300)
plt.close()

print(f"✓ Confusion matrix figure saved to: {cm_fig_path}")

# ------------------------------------------------------------
# 10. Feature Importance & Visualization
# ------------------------------------------------------------
print("\n[8] CALCULATING FEATURE IMPORTANCE")

importances = rf.feature_importances_
feature_imp_df = pd.DataFrame(
    {"Feature": feature_columns, "Importance": importances}
).sort_values("Importance", ascending=False)

print("\nRanked Feature Importances:")
for rank, row in enumerate(feature_imp_df.itertuples(), start=1):
    print(f"  {rank:2d}. {row.Feature:<38} : {row.Importance:.4f} ({row.Importance * 100:.2f}%)")

plt.figure(figsize=(10, 6))
sns.barplot(
    data=feature_imp_df,
    x="Importance",
    y="Feature",
    hue="Feature",
    palette="viridis",
    legend=False,
)
plt.title("VerifyMesh - Baseline Random Forest Feature Importance", fontsize=13, pad=12)
plt.xlabel("Gini Importance (Mean Decrease in Impurity)", fontsize=11)
plt.ylabel("Predictor Variable", fontsize=11)
plt.tight_layout()

fi_fig_path = RESULTS_DIR / "baseline_feature_importance.png"
plt.savefig(fi_fig_path, dpi=300)
plt.close()

print(f"✓ Feature importance figure saved to: {fi_fig_path}")

# ------------------------------------------------------------
# 11. Save the Model Artifact
# ------------------------------------------------------------
print("\n[9] SAVING TRAINED MODEL")

model_save_path = MODELS_DIR / "baseline_random_forest.joblib"
joblib.dump(rf, model_save_path)
print(f"✓ Trained model saved to: {model_save_path}")

# ------------------------------------------------------------
# 12. Final Summary
# ------------------------------------------------------------
print("\n" + "=" * 65)
print("BASELINE RANDOM FOREST EXECUTION COMPLETED")
print("=" * 65)
print("Summary of Generated Artifacts:")
print(f"  1. Model File          : {model_save_path}")
print(f"  2. Confusion Matrix    : {cm_fig_path}")
print(f"  3. Feature Importance  : {fi_fig_path}")
print("=" * 65)
