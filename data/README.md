# VerifyMesh Dataset: Workforce Competency & Assessment Battery (V2)

## 1. Dataset Overview

This directory contains the authoritative dataset used for training, cross-validating, and evaluating the **VerifyMesh Binary Gatekeeper Competency Model** (`backend/models/binary_eligibility_model.pkl`).

- **File:** [`data/raw/VerifyMesh_Competency_Dataset_V2.csv`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/data/raw/VerifyMesh_Competency_Dataset_V2.csv)
- **Observations:** 2,000 synthetic candidate records (`AGT00001` through `AGT02000`)
- **Features:** 10 raw candidate attributes + 1 unique ID + 1 target column
- **Missing Values:** None (0 nulls across all fields)
- **Data Privacy & Licensing:** Purely synthetic evaluation dataset generated for academic research and prototype evaluation. No Personally Identifiable Information (PII) is included.

---

## 2. Feature Schema & Column Definitions

| Column Name | Data Type | Value Range / Description | Role in Modeling |
| :--- | :--- | :--- | :--- |
| `agent_id` | String | `AGT00001` - `AGT02000` | Identifier (excluded from training) |
| `previous_experience_months` | Integer | 0 to 111 months (general domain tenure) | Raw predictor |
| `sales_experience_months` | Integer | 0 to 85 months (specialized sales tenure) | Raw predictor |
| `customer_service_experience_months` | Integer | 0 to 88 months (service & support tenure) | Raw predictor |
| `certification_count` | Integer | 0 to 5 certifications completed | Raw predictor |
| `relevant_certification` | Binary | `1` (has domain-relevant cert) or `0` (none) | Raw predictor |
| `assessment_score` | Integer | 0 to 100 (Overall core test score) | Raw predictor |
| `communication_score` | Integer | 0 to 100 (Verbal/written exam score) | Raw predictor |
| `product_knowledge_score` | Integer | 0 to 100 (Technical/product battery score) | Raw predictor |
| `sales_skill_score` | Integer | 0 to 100 (Negotiation/sales assessment) | Raw predictor |
| `customer_service_score` | Integer | 0 to 100 (Client interaction score) | Raw predictor |
| `competency_level` | Categorical | `Competent`, `Basic`, `Advanced`, `Needs Improvement` | Ground truth label |

---

## 3. Authoritative Binary Target Mapping

To establish a strict, binary gatekeeper decision boundary, the 4-tier competency labels are mapped into two authoritative classes:

$$\text{Eligible} = \{\text{Advanced},\ \text{Competent}\} \quad (1,100 \text{ records}, 55.0\%)$$
$$\text{Not Eligible} = \{\text{Basic},\ \text{Needs Improvement}\} \quad (900 \text{ records}, 45.0\%)$$

Numerical Encoding:
- `Not Eligible` $\to 0$
- `Eligible` $\to 1$

---

## 4. Engineered Feature Derivations

The training pipeline in [`ml/notebooks/Verify_Mesh.ipynb`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/ml/notebooks/Verify_Mesh.ipynb) and the production inference engine in [`src/inference.py`](file:///c:/Users/DANIEL/Desktop/Verify_Mesh/src/inference.py) derive 5 features before standard scaling:

1. `certified_leverage`:
   $$\text{certified\_leverage} = \text{certification\_count} \times (1 + \text{relevant\_certification})$$
2. `total_experience_months`:
   $$\text{total\_experience\_months} = \text{previous\_experience\_months} + \text{sales\_experience\_months} + \text{customer\_service\_experience\_months}$$
3. `mean_score`:
   $$\text{mean\_score} = \frac{1}{5} \sum (\text{assessment} + \text{communication} + \text{product\_knowledge} + \text{sales\_skill} + \text{customer\_service})$$
4. `min_score`: Minimum of the 5 individual score fields.
5. `max_score`: Maximum of the 5 individual score fields.

Total feature vector length: **15 numerical features**.
