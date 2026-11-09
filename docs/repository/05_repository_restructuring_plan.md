# VERIFYMESH — PHASE 0.5: REPOSITORY RESTRUCTURING & CLEANUP PLAN

**Date:** 2026-11-09  
**Repository:** VerifyMesh (`VerifyMesh-ML`)  
**Auditor:** Senior Software & ML Engineering Lead / Repository Maintainer  
**Status:** PHASE 0.5 COMPLETED — AWAITING REVIEW & APPROVAL  

---

## 1. TARGET REPOSITORY ARCHITECTURE

The restructuring plan aligns the repository with modern software engineering standards while respecting existing import paths, avoiding arbitrary file churn, and strictly honoring the **Updated Legacy Asset Retirement Policy**.

### Final Repository Layout

```text
VerifyMesh-ML/
│
├── .gitignore                                # Comprehensive production ignore rules with active model whitelist
├── .env.example                              # Verified environment variable template with safe placeholders
├── LICENSE                                   # Standard MIT License
├── README.md                                 # Master reproducible documentation & dual-layer architecture guide
├── requirements.txt                          # Python dependencies manifest
│
├── docs/                                     # Centralized system documentation
│   ├── architecture/
│   │   ├── VerifyMesh_End_to_End_Functional_Specification.md
│   │   └── PHASE_4_HANDOVER.md
│   ├── testing/
│   │   ├── test_plan.md
│   │   ├── test_results.md
│   │   ├── defect_report.md
│   │   ├── panel_demo_checklist.md
│   │   └── system_audit.md
│   └── repository/                           # Phase 0 forensic and hygiene deliverables
│       ├── 01_git_forensic_audit.md
│       ├── 02_file_inventory.md
│       ├── 03_dependency_and_legacy_audit.md
│       ├── 04_security_and_secrets_audit.md
│       └── 05_repository_restructuring_plan.md
│
├── frontend/                                 # Production React 19 + Vite + Tailwind CSS Single-Page Application
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── public/
│   └── src/
│       ├── components/                       # UI primitives, auth forms, dashboard modals
│       ├── pages/                            # AdminDashboard, AgentDashboard, CreateTaskPage, ProfilePage, SupervisorVerifyPage
│       ├── services/                         # adminService, authService, competencyService, workforceService, api.js
│       ├── context/                          # AuthContext.jsx
│       └── styles/                           # Core styles and Obsidian Dark theme
│
├── backend/                                  # Production Flask REST API & Deterministic Eligibility Engine
│   ├── app.py                                # Application factory & CORS configuration
│   ├── config.py                             # Secure environment loader with fail-safe checks
│   ├── db.py                                 # Authoritative DB data access layer & Stage 1 engine
│   ├── admin_routes.py                       # Workforce officer API endpoints
│   ├── auth_routes.py                        # Authentication, OTP, and supervisor loop endpoints
│   ├── competency_routes.py                  # Assessment attempt and retake transition endpoints
│   ├── email_service.py                      # HTML transactional email delivery
│   ├── init_db.py                            # Database bootstrapping & seed data script
│   ├── schema.sql                            # Canonical MySQL 8.0 DDL (including agent_topic_results)
│   └── migrations/                           # Ordered, idempotent migration chain
│       ├── 002_assessment_integrity.sql & .py
│       ├── 003_assessment_topics_framework.sql & .py
│       ├── 004_binary_eligibility_alignment.sql & .py
│       ├── 005_supervisor_reference_loop.sql & .py
│       └── 006_task_multi_certifications.sql & .py
│
├── src/                                      # Production ML Feature Engineering & Inference Engine
│   ├── stage2_feature_engineering.py         # Canonical 5-feature schema & domain weights
│   └── task_suitability_inference.py         # L2-Logistic Regression prediction engine
│
├── ml/                                       # Machine Learning Experiments, Models, and Thesis Evidence
│   ├── README.md                             # Stage 2 ML documentation
│   ├── metadata/
│   │   ├── verifymesh_stage2_metadata_v2.json # Active model hyperparameters & traceability
│   │   └── verifymesh_threshold_metadata.json # Advisory threshold configuration
│   ├── models/
│   │   └── verifymesh_stage2_suitability_pipeline_v2.joblib # Active trained pipeline artifact (2.6 KB)
│   ├── notebooks/
│   │   └── VerifyMesh_Task_Suitability_Experiment.ipynb    # Reproducible research experiment notebook
│   ├── experiments/
│   │   ├── task_specific_synthetic_data/     # Workforce simulation methodology, generator, and datasets
│   │   └── stage2_refinement/                # 3-phase cross-validation, benchmarks, and Scenario B data
│   └── outputs/
│       └── chapter5/                         # 19 academic thesis figures, ROC curves, and tables
│
└── tests/                                    # Automated PyUnit Regression & Verification Test Suite
    ├── test_assessment_integrity.py
    ├── test_assessment_topics_workflow.py
    ├── test_competency_consistency.py
    ├── test_create_task_restructuring.py
    ├── test_exam_pass_thresholds.py
    ├── test_panel_demonstration_readiness.py
    ├── test_security_remediation.py
    ├── test_supervisor_reference_loop.py
    ├── test_system_suite.py                  # Modernized for Stage 2 suitability engine
    ├── test_task_eligibility_enforcement.py
    └── test_task_management.py
```

---

## 2. RATIONALE FOR STRUCTURAL DESIGN CHOICES

1. **Retaining `src/` at the Root Level:**  
   In Python application design, a root-level `src/` directory is standard. `backend/admin_routes.py`, `backend/competency_routes.py`, `backend/db.py`, `tests/`, and `ml/experiments/` all import directly via `from src.stage2_feature_engineering import ...` and `from src.task_suitability_inference import ...`. Moving `src/` into `ml/` would require modifying dozens of working files and risks breaking package resolution. Keeping `src/` at root maintains 100% stability.
2. **Consolidating Documentation under `docs/`:**  
   Moving loose root specification files (`VerifyMesh_End_to_End_Functional_Specification.md`) into `docs/architecture/` produces a clean root while preserving all historical documentation.
3. **Preserving `ml/experiments/` and `ml/outputs/chapter5/`:**  
   All 52 experimental files and 19 thesis output assets remain organized under `ml/`. They prove the Design Science Research methodology, cross-validation, and empirical evaluation for the thesis.

---

## 3. FORMAL LEGACY ASSET RETIREMENT MANIFEST (FOR APPROVAL)

In compliance with the **Updated Legacy Asset Retirement Policy**, the following 13 assets are scheduled for permanent removal:

| # | Asset Path | Category | Reason for Permanent Deletion | Prerequisite Action |
|---|---|---|---|---|
| **1** | `backend/models/binary_eligibility_model.pkl` (3.45 MB) | Obsolete Model | Superseded by deterministic Stage 1 engine & Stage 2 suitability model. | None. |
| **2** | `src/inference.py` | Obsolete Engine | Legacy binary inference wrapper; superseded by `src/task_suitability_inference.py`. | **Modernize `tests/test_system_suite.py` first.** |
| **3** | `data/raw/VerifyMesh_Competency_Dataset_V2.csv` (116 KB) | Obsolete Data | 2,000-sample binary dataset superseded by Scenario B training data ($N=4,675$). | None. |
| **4** | `data/README.md` | Obsolete Docs | Documentation for deleted binary dataset. | Delete empty `data/` folder. |
| **5** | `ml/train.py` | Obsolete Script | Superseded by `train_and_serialize_stage2_v2.py`. | None. |
| **6** | `ml/evaluate.py` | Obsolete Script | Superseded by Phase 1/2 benchmark scripts. | None. |
| **7** | `ml/notebooks/Verify_Mesh.ipynb` | Obsolete Notebook | Superseded by `VerifyMesh_Task_Suitability_Experiment.ipynb`. | None. |
| **8** | `docs/PHASE_1_BINARY_ALIGNMENT_AUDIT.md` | Obsolete Audit | Superseded by Phase 4 handover documentation. | None. |
| **9** | `scratch/migrate_profile_schema.py` | Obsolete Scratch | Ephemeral script tracked in `b25c8da`; untrack via `git rm --cached`. | Preserve local copy. |
| **10** | `scratch/migrate_task_form_schema.py` | Obsolete Scratch | Ephemeral script tracked in `b25c8da`; untrack via `git rm --cached`. | Preserve local copy. |
| **11** | `scratch/test_admin_task_form.py` | Obsolete Scratch | Ephemeral script tracked in `b25c8da`; untrack via `git rm --cached`. | Preserve local copy. |
| **12** | `scratch/test_agent_dashboard_metrics.py` | Obsolete Scratch | Ephemeral script tracked in `b25c8da`; untrack via `git rm --cached`. | Preserve local copy. |
| **13** | `scratch/test_profile_workflow.py` | Obsolete Scratch | Ephemeral script tracked in `b25c8da`; untrack via `git rm --cached`. | Preserve local copy. |

---

## 4. PREREQUISITE ACTIONS BEFORE DELETION

Before the deletion manifest is executed in Phase 0.7, the following prerequisite fixes must be implemented and tested:

### Prerequisite 1: Modernize `tests/test_system_suite.py`
- **Issue:** Line 53 imports `from src.inference import inference_engine`, and lines 387–505 assert legacy binary predictions.
- **Fix:** Update lines 53 and 387–505 to import and assert `src.task_suitability_inference.task_suitability_engine`.
- **Verification:** Run `python -m unittest tests/test_system_suite.py` to confirm 100% pass rate.

### Prerequisite 2: Synchronize `backend/schema.sql`
- **Issue:** `schema.sql` is currently missing the `agent_topic_results` table DDL from Migration 003.
- **Fix:** Append the canonical `agent_topic_results` table definition to `backend/schema.sql`.
- **Verification:** Verify schema completeness against all route queries.

### Prerequisite 3: Update `.gitignore`
- **Issue:** Blanket `*.joblib` prevents tracking the active Stage 2 model (`verifymesh_stage2_suitability_pipeline_v2.joblib`).
- **Fix:** Add `!ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib`.
- **Verification:** Verify `git status` sees the active model as ready for tracking.

---

## 5. EXECUTION PHASING (REMAINING PHASES)

| Phase | Planned Operations | Safeguards Enforced |
|---|---|---|
| **Phase 0.6** | Implement `.gitignore` update, add `LICENSE`, synchronize `schema.sql`, and modernize `test_system_suite.py`. | Run test suites to verify zero regressions. |
| **Phase 0.7** | Execute the approved Legacy Asset Retirement Manifest: permanently delete approved files and run `git rm --cached` on scratch scripts. | Re-run automated tests; inspect `git diff`. |
| **Phase 0.8** | Reproducibility verification: Update root `README.md` with complete developer installation and startup guides. | Verify fresh clone setup instructions. |
| **Phase 0.9** | Final regression verification: Execute frontend build (`npm run build`) and backend/ML tests. | Confirm 0 build errors and 0 test failures. |
| **Phase 0.10** | Logical Git commit structuring and clean push to GitHub remote (`origin/main`). | Review staged files; scan for secrets; standard push (no force-push). |

---

*This concludes Phase 0.5. The plan is submitted for review and approval. No files will be moved, modified, or deleted until explicit approval is given.*

