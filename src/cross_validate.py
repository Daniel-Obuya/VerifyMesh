import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ============================================================
# VERIFYMESH - STEP 3
# STRATIFIED 5-FOLD CROSS-VALIDATION (BASELINE STABILITY)
# ============================================================

# ------------------------------------------------------------
# 1. Project Paths
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
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
print("VERIFYMESH - STEP 3: STRATIFIED 5-FOLD CROSS-VALIDATION")
print("=" * 65)

# ------------------------------------------------------------
# 3. Load Training Data ONLY (Strictly No Test Set Leakage)
# ------------------------------------------------------------
print("\n[1] LOADING TRAINING DATASET ONLY")

train_features_path = PROCESSED_DATA_DIR / "X_train.csv"
train_target_path = PROCESSED_DATA_DIR / "y_train.csv"

if not train_features_path.exists() or not train_target_path.exists():
    raise FileNotFoundError("Processed training files not found!")

X_train = pd.read_csv(train_features_path)
y_train = pd.read_csv(train_target_path)[target_column]

print(f"Loaded X_train from : {train_features_path.name} {X_train.shape}")
print(f"Loaded y_train from : {train_target_path.name} {y_train.shape}")
print("✓ Verified: Test set (X_test, y_test) remains strictly isolated in the vault.")

# ------------------------------------------------------------
# 4. Verify Dimensions and Features
# ------------------------------------------------------------
print("\n[2] VERIFYING DIMENSIONS AND COLUMNS")

if X_train.shape != (1600, 10):
    raise ValueError(f"Unexpected X_train shape: {X_train.shape}. Expected (1600, 10).")
if y_train.shape != (1600,):
    raise ValueError(f"Unexpected y_train shape: {y_train.shape}. Expected (1600,).")
if list(X_train.columns) != feature_columns:
    raise ValueError("Features do not match expected 10 predictor columns.")
if "agent_id" in X_train.columns:
    raise ValueError("Leakage alert: agent_id detected in features!")

print("✓ All 1,600 training samples and 10 predictors validated.")

# ------------------------------------------------------------
# 5. Configure Stratified 5-Fold Cross-Validation
# ------------------------------------------------------------
print("\n[3] CONFIGURING STRATIFIED 5-FOLD SPLITS")

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("Configuration:")
print(f"  - Number of folds : 5")
print(f"  - Split ratio     : 80% train / 20% validation per fold (1,280 / 320 agents)")
print(f"  - Stratified      : Yes (preserves class ratios in every fold)")
print(f"  - Random seed     : 42")

# ------------------------------------------------------------
# 6. Execute 5-Fold Cross-Validation Loop
# ------------------------------------------------------------
print("\n[4] EXECUTING 5-FOLD CROSS-VALIDATION")

fold_records = []

for fold_num, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train), start=1):
    X_fold_train, X_fold_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
    y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
    
    # Train fresh baseline Random Forest for this fold
    rf_fold = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_fold.fit(X_fold_train, y_fold_train)
    
    # Predict on validation fold
    y_fold_pred = rf_fold.predict(X_fold_val)
    
    # Metrics
    acc = accuracy_score(y_fold_val, y_fold_pred)
    f1_macro = f1_score(y_fold_val, y_fold_pred, average="macro")
    f1_weighted = f1_score(y_fold_val, y_fold_pred, average="weighted")
    
    fold_records.append({
        "Fold": f"Fold {fold_num}",
        "Accuracy": acc,
        "Macro F1": f1_macro,
        "Weighted F1": f1_weighted,
    })
    
    print(f"  Fold {fold_num}: Accuracy = {acc:.4f} ({acc*100:.2f}%) | Macro F1 = {f1_macro:.4f} | Weighted F1 = {f1_weighted:.4f}")

# ------------------------------------------------------------
# 7. Aggregate and Summarize Results
# ------------------------------------------------------------
cv_results_df = pd.DataFrame(fold_records)

print("\n[5] CROSS-VALIDATION SUMMARY STATISTICS")
print("-" * 60)
print(cv_results_df.to_string(index=False))
print("-" * 60)

mean_acc = cv_results_df["Accuracy"].mean()
std_acc = cv_results_df["Accuracy"].std()
mean_macro_f1 = cv_results_df["Macro F1"].mean()
std_macro_f1 = cv_results_df["Macro F1"].std()
mean_weighted_f1 = cv_results_df["Weighted F1"].mean()
std_weighted_f1 = cv_results_df["Weighted F1"].std()

print(f"Mean Accuracy     : {mean_acc:.4f} ± {std_acc:.4f} ({mean_acc*100:.2f}% ± {std_acc*100:.2f}%)")
print(f"Mean Macro F1     : {mean_macro_f1:.4f} ± {std_macro_f1:.4f}")
print(f"Mean Weighted F1  : {mean_weighted_f1:.4f} ± {std_weighted_f1:.4f}")

# ------------------------------------------------------------
# 8. Visualization: Fold Performance and Stability
# ------------------------------------------------------------
print("\n[6] GENERATING CROSS-VALIDATION STABILITY PLOT")

fig, ax = plt.subplots(figsize=(8, 5))
x_positions = np.arange(len(cv_results_df))
width = 0.25

rects1 = ax.bar(x_positions - width, cv_results_df["Accuracy"], width, label="Accuracy", color="#2b5c8f")
rects2 = ax.bar(x_positions, cv_results_df["Macro F1"], width, label="Macro F1", color="#4ba3e3")
rects3 = ax.bar(x_positions + width, cv_results_df["Weighted F1"], width, label="Weighted F1", color="#9ecae1")

ax.axhline(mean_acc, color="#d95f02", linestyle="--", linewidth=1.5, label=f"Mean Accuracy ({mean_acc:.4f})")

ax.set_title("VerifyMesh - Baseline 5-Fold Stratified Cross-Validation Stability", fontsize=12, pad=12)
ax.set_ylabel("Metric Score", fontsize=11)
ax.set_xticks(x_positions)
ax.set_xticklabels(cv_results_df["Fold"], fontsize=10)
ax.set_ylim(0.35, 0.60)
ax.legend(loc="lower right", frameon=True)
ax.grid(axis="y", linestyle=":", alpha=0.6)

plt.tight_layout()
cv_plot_path = RESULTS_DIR / "baseline_cross_validation.png"
plt.savefig(cv_plot_path, dpi=300)
plt.close()

print(f"✓ Cross-validation stability figure saved to: {cv_plot_path}")

# ------------------------------------------------------------
# 9. Conclusion & Comparison with Isolated Test Set
# ------------------------------------------------------------
print("\n" + "=" * 65)
print("CROSS-VALIDATION ANALYSIS & BENCHMARK COMPARISON")
print("=" * 65)
print(f"5-Fold CV Accuracy    : {mean_acc*100:.2f}% (Range: {cv_results_df['Accuracy'].min()*100:.2f}% - {cv_results_df['Accuracy'].max()*100:.2f}%)")
print(f"Step 2 Test Accuracy  : 49.25%")
if cv_results_df["Accuracy"].min() <= 0.4925 <= cv_results_df["Accuracy"].max():
    print("✓ Consistency Check PASSED: The Step 2 test set accuracy (49.25%) falls right")
    print("  inside the 5-fold cross-validation range. This confirms that the test split")
    print("  is representative and not an anomaly.")
else:
    print("Notice: Step 2 test set accuracy is slightly outside the CV fold range.")
print("=" * 65)
