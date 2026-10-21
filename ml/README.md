# VerifyMesh Machine Learning Pipeline

This directory contains the authoritative machine learning code, training notebook, evaluation tools, and reproducibility documentation for the **VerifyMesh Workforce Competency Gatekeeper**.

---

## 1. Machine Learning Overview

VerifyMesh utilizes a **Binary Random Forest Classifier** to evaluate candidate readiness for task dispatch. The model functions as a statistical gatekeeper, predicting whether an agent is **`Eligible`** or **`Not Eligible`** based on verified domain experience, certifications, and core assessment test scores.

| Parameter | Specification |
| :--- | :--- |
| **Model Type** | Scikit-Learn `Pipeline` (`StandardScaler` + `RandomForestClassifier`) |
| **Number of Estimators** | 150 trees |
| **Max Depth** | 10 levels |
| **Min Samples Split** | 5 |
| **Random State** | `42` (Fixed for full reproducibility) |
| **Decision Boundary** | $\tau = 0.50$ ($P(\text{Eligible}) \ge 0.50 \implies \text{Eligible}$) |
| **Active Artifact** | [`backend/models/binary_eligibility_model.pkl`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/backend/models/binary_eligibility_model.pkl) (3.45 MB) |

---

## 2. Directory Structure

```text
ml/
├── notebooks/
│   └── Verify_Mesh.ipynb    # Google Colab / Jupyter interactive research notebook
├── train.py                 # Standalone training script (trains, cross-validates, and saves artifact)
├── evaluate.py              # Standalone evaluation & threshold sensitivity audit script
└── README.md                # ML architecture & reproducibility guide (this file)
```

---

## 3. Feature Contract & Engineering Specification

The model expects exactly **15 numerical features** in the precise order specified below:

| Index | Feature Name | Source / Derivation Formula |
| :---: | :--- | :--- |
| 0 | `previous_experience_months` | Raw: Candidate's verified prior domain tenure (months) |
| 1 | `sales_experience_months` | Raw: Specific sales experience tenure (months) |
| 2 | `customer_service_experience_months` | Raw: Specific customer service tenure (months) |
| 3 | `certification_count` | Raw: Total number of verified certifications (0 - 5) |
| 4 | `relevant_certification` | Raw: Flag (`1` or `0`) indicating domain-specific certification |
| 5 | `assessment_score` | Raw: Overall core assessment battery score (0 - 100) |
| 6 | `communication_score` | Raw: Communication competency exam score (0 - 100) |
| 7 | `product_knowledge_score` | Raw: Technical product exam score (0 - 100) |
| 8 | `sales_skill_score` | Raw: Sales negotiation exam score (0 - 100) |
| 9 | `customer_service_score` | Raw: Customer support exam score (0 - 100) |
| 10 | `certified_leverage` | Engineered: $\text{certification\_count} \times (1 + \text{relevant\_certification})$ |
| 11 | `total_experience_months` | Engineered: $\sum(\text{previous} + \text{sales} + \text{customer\_service})$ |
| 12 | `mean_score` | Engineered: $\text{mean}(\text{all 5 exam scores})$ |
| 13 | `min_score` | Engineered: $\text{min}(\text{all 5 exam scores})$ |
| 14 | `max_score` | Engineered: $\text{max}(\text{all 5 exam scores})$ |

---

## 4. How to Reproduce the ML Workflow

Ensure your virtual environment is active before running commands:
```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### Option A: Evaluate the Pre-Trained Model (No Re-Training Required)
To evaluate the active model artifact on the 400-sample stratified holdout test set without modifying anything:

```powershell
python ml/evaluate.py
```

Expected Output:
- Model Loading Confirmation
- Hold-out Accuracy, ROC-AUC, and Confusion Matrix
- Precision and Recall across classes (`Eligible` vs `Not Eligible`)
- Decision Threshold Sensitivity Table ($\tau \in [0.40, 0.60]$)

---

### Option B: Retrain the Model from Scratch
To re-run the complete training pipeline (including 5-fold cross-validation and holdout evaluation):

```powershell
# Run training and overwrite active model artifact
python ml/train.py

# Or test training without modifying the saved model artifact:
python ml/train.py --no-save
```

---

### Option C: Interactive Exploration in Jupyter or Google Colab
The original training notebook is preserved in:
[`ml/notebooks/Verify_Mesh.ipynb`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/notebooks/Verify_Mesh.ipynb)

To run locally with Jupyter:
```powershell
pip install jupyter
jupyter notebook ml/notebooks/Verify_Mesh.ipynb
```
Or upload the notebook to [Google Colab](https://colab.research.google.com/) and load the dataset from `data/raw/VerifyMesh_Competency_Dataset_V2.csv`.

---

## 5. Architectural Decoupling Invariant

> [!IMPORTANT]
> The ML model's prediction (`Eligible` or `Not Eligible`) functions strictly as a **gatekeeper recommendation**. In VerifyMesh, task eligibility is decoupled: an agent predicted as `Eligible` must still independently satisfy deterministic task-specific rules (mandatory certifications, minimum experience months, and passing topic-specific exams) before they are permitted to apply for a task.
