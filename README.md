# VerifyMesh Machine Learning Pipeline

## Project

VerifyMesh: Enhancing Workforce Task Allocation Through Competency Assessment and Eligibility Prediction.

## Current Stage

Step 1 - Data Preprocessing and Stratified Train/Test Split

## Dataset

The modelling dataset contains 2,000 simulated agents and 12 columns.

The target variable is:

- competency_level

The predictor variables are:

- previous_experience_months
- sales_experience_months
- customer_service_experience_months
- certification_count
- relevant_certification
- assessment_score
- communication_score
- product_knowledge_score
- sales_skill_score
- customer_service_score

`agent_id` is excluded from model training because it is an identifier rather than a predictive feature.

## Train/Test Split

An 80/20 stratified split is used:

- Training set: 1,600 records
- Test set: 400 records

Random state:

- 42

Stratification is used to preserve the competency-level distribution in both datasets.

## Current Status

No machine-learning model has been trained at this stage.

The Random Forest modelling stage will begin only after the preprocessing and split have been independently verified.