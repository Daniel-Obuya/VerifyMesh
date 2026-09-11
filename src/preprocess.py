import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ============================================================
# VERIFYMESH - STEP 1
# DATA PREPROCESSING AND STRATIFIED TRAIN/TEST SPLIT
# ============================================================


# ------------------------------------------------------------
# 1. Project paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "VerifyMesh_Initial_Competency_Dataset_V2.csv"
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# ------------------------------------------------------------
# 2. Expected dataset structure
# ------------------------------------------------------------

expected_columns = [
    "agent_id",
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
    "competency_level",
]

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


# ------------------------------------------------------------
# 3. Load Version 2 dataset
# ------------------------------------------------------------

if not RAW_DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found:\n{RAW_DATA_PATH}"
    )
try:
    df = pd.read_csv(RAW_DATA_PATH)
except (UnicodeDecodeError, pd.errors.ParserError):
    df = pd.read_excel(RAW_DATA_PATH)


print("=" * 65)
print("VERIFYMESH - STEP 1")
print("DATA PREPROCESSING AND TRAIN/TEST SPLIT")
print("=" * 65)


# ------------------------------------------------------------
# 4. Verify basic dataset structure
# ------------------------------------------------------------

print("\n[1] DATASET STRUCTURE")

print(f"Rows loaded:    {df.shape[0]}")
print(f"Columns loaded: {df.shape[1]}")


if df.shape != (2000, 12):
    raise ValueError(
        f"Unexpected dataset shape: {df.shape}. "
        "Expected (2000, 12)."
    )

if list(df.columns) != expected_columns:
    raise ValueError(
        "Dataset columns do not match the expected 12-column structure."
    )

print("✓ Dataset contains exactly 2,000 rows and 12 columns.")
print("✓ Column structure is correct.")


# ------------------------------------------------------------
# 5. Check missing values
# ------------------------------------------------------------

print("\n[2] MISSING VALUES")

missing_values = int(df.isna().sum().sum())

print(f"Total missing values: {missing_values}")

if missing_values != 0:
    raise ValueError("Missing values detected.")

print("✓ No missing values.")


# ------------------------------------------------------------
# 6. Check duplicate records
# ------------------------------------------------------------

print("\n[3] DUPLICATES")

duplicate_ids = int(df["agent_id"].duplicated().sum())
duplicate_rows = int(df.duplicated().sum())

print(f"Duplicate agent IDs:      {duplicate_ids}")
print(f"Duplicate complete rows:  {duplicate_rows}")

if duplicate_ids != 0:
    raise ValueError("Duplicate agent IDs detected.")

if duplicate_rows != 0:
    raise ValueError("Duplicate complete rows detected.")

print("✓ No duplicate agent IDs.")
print("✓ No duplicate complete rows.")


# ------------------------------------------------------------
# 7. Verify predictor and target columns
# ------------------------------------------------------------

print("\n[4] MODEL VARIABLES")

X = df[feature_columns].copy()
y = df[target_column].copy()

if "agent_id" in X.columns:
    raise ValueError(
        "agent_id must not be included in the model predictors."
    )

if target_column in X.columns:
    raise ValueError(
        "The target variable must not be included in X."
    )

print(f"Number of predictors: {X.shape[1]}")
print(f"Target variable:      {target_column}")

print("\nPredictors:")

for feature in feature_columns:
    print(f"  ✓ {feature}")

print("\n✓ agent_id excluded from predictors.")
print("✓ competency_level separated as target.")


# ------------------------------------------------------------
# 8. Verify target classes
# ------------------------------------------------------------

print("\n[5] TARGET CLASSES")

target_classes = sorted(y.unique())

print("Classes found:")

for class_name in y.unique():
    print(f"  - {class_name}")

if sorted(target_classes) != sorted(expected_classes):
    raise ValueError(
        "Target classes do not match the expected four competency levels."
    )

print("✓ Four expected competency classes detected.")


# ------------------------------------------------------------
# 9. Verify original class distribution
# ------------------------------------------------------------

print("\n[6] ORIGINAL CLASS DISTRIBUTION")

original_counts = (
    y.value_counts()
    .reindex(expected_classes)
)

expected_counts = pd.Series(
    [300, 600, 700, 400],
    index=expected_classes,
)

print(original_counts)

if not original_counts.equals(expected_counts):
    raise ValueError(
        "Original class distribution does not match "
        "the expected 300/600/700/400 distribution."
    )

print("\n✓ Original class distribution is correct.")


# ------------------------------------------------------------
# 10. Perform stratified 80/20 split
# ------------------------------------------------------------

print("\n[7] STRATIFIED 80/20 SPLIT")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42,
)


# ------------------------------------------------------------
# 11. Verify split sizes
# ------------------------------------------------------------

print(f"Training features: {X_train.shape}")
print(f"Testing features:  {X_test.shape}")
print(f"Training target:   {y_train.shape}")
print(f"Testing target:    {y_test.shape}")

if X_train.shape != (1600, 10):
    raise ValueError(
        f"Unexpected training feature shape: {X_train.shape}"
    )

if X_test.shape != (400, 10):
    raise ValueError(
        f"Unexpected testing feature shape: {X_test.shape}"
    )

if y_train.shape != (1600,):
    raise ValueError(
        f"Unexpected training target shape: {y_train.shape}"
    )

if y_test.shape != (400,):
    raise ValueError(
        f"Unexpected testing target shape: {y_test.shape}"
    )

print("✓ 80/20 split produced 1,600 training and 400 testing records.")


# ------------------------------------------------------------
# 12. Verify training class distribution
# ------------------------------------------------------------

print("\n[8] TRAINING CLASS DISTRIBUTION")

train_counts = (
    y_train.value_counts()
    .reindex(expected_classes)
)

print(train_counts)

expected_train_counts = pd.Series(
    [240, 480, 560, 320],
    index=expected_classes,
)

if not train_counts.equals(expected_train_counts):
    raise ValueError(
        "Training class distribution is incorrect."
    )

print("\n✓ Training distribution is correct.")


# ------------------------------------------------------------
# 13. Verify testing class distribution
# ------------------------------------------------------------

print("\n[9] TESTING CLASS DISTRIBUTION")

test_counts = (
    y_test.value_counts()
    .reindex(expected_classes)
)

print(test_counts)

expected_test_counts = pd.Series(
    [60, 120, 140, 80],
    index=expected_classes,
)

if not test_counts.equals(expected_test_counts):
    raise ValueError(
        "Testing class distribution is incorrect."
    )

print("\n✓ Testing distribution is correct.")


# ------------------------------------------------------------
# 14. Display class proportions
# ------------------------------------------------------------

print("\n[10] CLASS PROPORTIONS")

train_proportions = (
    y_train.value_counts(normalize=True)
    .reindex(expected_classes)
    * 100
)

test_proportions = (
    y_test.value_counts(normalize=True)
    .reindex(expected_classes)
    * 100
)

print("\nTraining:")
print(train_proportions.round(2))

print("\nTesting:")
print(test_proportions.round(2))


# ------------------------------------------------------------
# 15. Save processed datasets
# ------------------------------------------------------------

print("\n[11] SAVING PROCESSED DATA")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

X_train.to_csv(
    PROCESSED_DIR / "X_train.csv",
    index=False
)

X_test.to_csv(
    PROCESSED_DIR / "X_test.csv",
    index=False
)

y_train.to_csv(
    PROCESSED_DIR / "y_train.csv",
    index=False
)

y_test.to_csv(
    PROCESSED_DIR / "y_test.csv",
    index=False
)

print(f"Saved to: {PROCESSED_DIR}")

print("✓ X_train.csv")
print("✓ X_test.csv")
print("✓ y_train.csv")
print("✓ y_test.csv")


# ------------------------------------------------------------
# 16. Final verification
# ------------------------------------------------------------

print("\n" + "=" * 65)
print("STEP 1 COMPLETED SUCCESSFULLY")
print("=" * 65)

print("\nFinal dataset structure:")
print("  Original dataset : 2,000 records × 12 columns")
print("  Predictors       : 10")
print("  Target           : competency_level")
print("  Training set     : 1,600 records")
print("  Testing set      : 400 records")
print("  Split            : Stratified 80/20")
print("  Random state     : 42")

print("\nRandom Forest trained: NO")

print("\n✓ All preprocessing and split validation checks passed.")
print("=" * 65)