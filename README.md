# VerifyMesh Machine Learning Architecture

## Project Overview
VerifyMesh is an AI-assisted platform that assesses workers' skills and determines whether they qualify for specific tasks on online work platforms.
In online marketplaces, it can be difficult to verify workers' qualifications and screen large numbers of applicants manually. VerifyMesh aims to make this process easier by combining competency assessments, verified credentials, and machine learning.
First, an agent completes assessments and provides their credentials. The Flask backend uses verified information, such as work experience and certifications, to create 11 input features for a pre-trained Random Forest model. The model classifies candidates into three groups: Eligible, Ineligible, or requiring human review when the result is uncertain.
Second, a rules engine checks whether the agent meets the specific requirements of a task, including relevant work experience, valid certifications, and assessment scores.
The project is currently in Sprint II. The React frontend, Flask backend, MySQL database, and machine-learning model are integrated. The system also includes role-based access controls and audit logs to help protect information and track important activities.


## Machine Learning Responsibilities

### 1. Google Colab (Training & Tuning Only)
**Google Colab is the exclusive environment responsible for:**
- Training dataset ingestion & exploration
- Data preprocessing & stratified train/test split
- Feature engineering experiments
- Random Forest model training
- Hyperparameter tuning (`RandomizedSearchCV` / `GridSearchCV`)
- Cross-validation (`StratifiedKFold`) & evaluation metrics (accuracy, macro F1, confusion matrices)
- Exporting the final trained model: `tuned_random_forest.joblib` or `final_random_forest.joblib`

### 2. VerifyMesh Application (Inference & Prediction Only)
**The VerifyMesh Flask backend is responsible for:**
- Loading the pre-trained `.joblib` model **once at startup** via `src/inference.py`
- Validating agent competency inputs (10 raw predictor features)
- Applying necessary feature transformations (e.g. `certified_leverage` via `src/features.py`)
- Generating real-time competency predictions & confidence scores
- Returning predictions to the React frontend

> [!NOTE]
> The VerifyMesh application does NOT train, tune, or retrain the Random Forest model.

## Model Classes

The Random Forest model predicts one of four competency tiers:
1. **Needs Improvement** (Level 1)
2. **Basic** (Level 2)
3. **Competent** (Level 3)
4. **Advanced** (Level 4)

## VerifyMesh Workflow

```
Agent
↓
Login
↓
Complete Assessment
↓
Assessment Scores & Profile
↓
VerifyMesh Flask Backend
↓
Preloaded Colab Random Forest Model
↓
Competency Prediction (Level 1 - 4)
↓
Certification Check & Task Requirements (Rules Engine)
↓
Eligibility Decision (Eligible / Not Eligible)
↓
Task Recommendation & Human Review
```

## Running the Application

### 1. Backend (Flask API)
```powershell
.\.venv\Scripts\python.exe backend/app.py
```
*API runs on `http://127.0.0.1:5000` with endpoints:*
- `POST /api/auth/login`
- `GET /api/health`
- `POST /api/competency/predict`
- `GET /api/competency/model-info`
- `GET /api/competency/sample-inputs`

### 2. Frontend (React + Vite)
```powershell
cd frontend
npm run dev
```
*Web client runs on `http://localhost:5173`.*
