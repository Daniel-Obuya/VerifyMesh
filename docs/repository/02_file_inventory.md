# VERIFYMESH — PHASE 0.2: COMPLETE FILE INVENTORY & CLASSIFICATION

**Date:** 2026-11-09  
**Repository:** VerifyMesh (`VerifyMesh-ML`)  
**Auditor:** Senior Software & ML Engineering Lead / Repository Maintainer  
**Status:** PHASE 0.2 COMPLETED — AWAITING REVIEW & APPROVAL  

---

## 1. EXECUTIVE SUMMARY & INVENTORY METRICS

A comprehensive, recursive audit of all tracked, untracked, deleted, and ignored files in the `VerifyMesh` repository was conducted. Every file has been evaluated for operational necessity, academic/research provenance, security posture, and version-control status.

### Inventory Summary by Category

| Category Code | Category Name | File Count | Primary Action |
|---|---|---|---|
| **Category A** | Essential Application Source | 47 | KEEP (Version-control active code) |
| **Category B** | Essential Database Files | 14 | KEEP (Version-control schema & migrations) |
| **Category C** | Essential ML Implementation | 4 | KEEP AND ORGANISE (Active Stage 2 model & inference) |
| **Category D** | Research & Experimental Evidence | 52 | KEEP AND ORGANISE (Retain thesis Chapter 5 evidence & synthetic benchmarks) |
| **Category E** | Obsolete & Legacy Implementation | 14 | ARCHIVE / REMOVE AFTER APPROVAL (Retired binary gatekeeper files) |
| **Category F** | Temporary & Generated Files | 18+ | EXCLUDE FROM GIT (Build caches, `.venv`, `dist`, scratch scripts) |
| **Category G** | Sensitive & Private Files | 2 | EXCLUDE FROM GIT / SECURITY REVIEW REQUIRED (`.env`, `.env.example`) |
| **Category H** | Documentation & Specifications | 12 | KEEP AND ORGANISE (Specifications, QA reports, architecture guides) |
| **Total** | **Comprehensive Workspace Inventory** | **163+** | **Controlled, Non-Destructive Hygiene** |

---

## 2. CLASSIFICATION METHODOLOGY & RECOMMENDATION RULES

Each file in the project has been mapped to one of eight functional categories:
- **Category A (Essential Application Source):** Core React components, pages, services, Flask routes, entry points, auth flows, and core test suites.
- **Category B (Essential Database Files):** Authoritative DDL schema, seed initialization, and sequential versioned migrations (002 through 006).
- **Category C (Essential ML Implementation):** Production feature engineering, inference services, metadata specifications, and active trained model artifacts.
- **Category D (Research & Experimental Evidence):** Synthetic dataset generators, 3-phase refinement experimental logs, Chapter 5 thesis figures, ROC curves, confusion matrices, and research notebooks.
- **Category E (Obsolete & Legacy Implementation):** Retired binary classification code, legacy notebooks, superseded training scripts, and legacy data files.
- **Category F (Temporary & Generated Files):** Python bytecode (`__pycache__`), virtual environment files (`.venv`), node modules, build outputs (`dist/`), and scratch scripts.
- **Category G (Sensitive & Private Files):** Local environment secrets (`.env`) and configuration templates.
- **Category H (Documentation):** Root README, functional specifications, system audit reports, test plans, and architectural documentation.

### Permitted Recommendations
1. **KEEP:** Critical to active system execution; retain under version control.
2. **KEEP AND ORGANISE:** Essential research or documentation; retain and ensure proper directory placement.
3. **ARCHIVE:** Historically or academically valuable, but no longer part of active production runtime; relocate to a dedicated historical archive folder.
4. **REMOVE AFTER APPROVAL:** Fully superseded, dead, or duplicate file with zero active dependencies and no historical value; delete only upon explicit user consent.
5. **EXCLUDE FROM GIT:** Runtime cache, local secret, or build artifact; enforce exclusion via `.gitignore` and `git rm --cached` where previously tracked.
6. **SECURITY REVIEW REQUIRED:** Contains or manages sensitive configuration; requires credential audit, rotation verification, or sanitization.

---

## 3. COMPLETE FILE INVENTORY TABLE

| File Path | Category | Current Purpose | Referenced By | Git Status | Recommendation | Reason |
|---|---|---|---|---|---|---|
| `.env` | **G** | Local environment variables & secrets (DB credentials, secret keys) | `backend/config.py` | Ignored (`!!`) | **EXCLUDE FROM GIT / SECURITY REVIEW REQUIRED** | Contains active local secrets; must never be committed. |
| `.env.example` | **G / H** | Safe environment variable template with placeholder values | Setup documentation | Tracked | **KEEP** | Essential for reproducible developer setup. |
| `.gitignore` | **A** | Repository ignore rules for environments, build outputs, and caches | Git tooling | Tracked | **KEEP AND ORGANISE** | Essential repository hygiene; needs selective rule refinement. |
| `README.md` | **H** | Root project documentation, architecture overview, and setup guide | Repository root | Tracked | **KEEP AND ORGANISE** | Primary project entry documentation; needs alignment with Stage 2 architecture. |
| `requirements.txt` | **A** | Python dependency manifest for backend and ML modules | Virtualenv setup | Tracked | **KEEP** | Core reproducibility manifest. |
| `VerifyMesh_End_to_End_Functional_Specification.md` | **H** | Complete functional specification for VerifyMesh dual-layer workflow | Architecture docs | Untracked (`??`) | **KEEP AND ORGANISE** | Foundational architectural specification document. |
| `VerifyMesh_System_Test_Report.md` | **H** | System integration test summary and verification log | Testing docs | Tracked | **KEEP AND ORGANISE** | Valuable QA baseline report. |
| `backend/app.py` | **A** | Flask application factory, CORS setup, and blueprint registration | WSGI entry point | Tracked (Modified) | **KEEP** | Core backend application entry point. |
| `backend/config.py` | **A** | Centralized application configuration and secret validation | `backend/app.py`, `backend/db.py` | Tracked | **KEEP** | Core configuration loader. |
| `backend/db.py` | **A** | Database connection pooling, Stage 1 Deterministic Engine, and data access functions | All route modules, tests | Tracked (Modified) | **KEEP** | Single source of truth for authoritative database operations. |
| `backend/admin_routes.py` | **A** | REST blueprint for workforce officer task management, verifications, and applicant reviews | Frontend `adminService.js` | Tracked (Modified) | **KEEP** | Core administration API surface. |
| `backend/auth_routes.py` | **A** | REST blueprint for authentication, OTP verification, password reset, and supervisor loop | Frontend `authService.js` | Tracked (Modified) | **KEEP** | Core security and authentication API surface. |
| `backend/competency_routes.py` | **A** | REST blueprint for competency assessments, topic attempts, and retake transitions | Frontend `competencyService.js` | Tracked (Modified) | **KEEP** | Core assessment and verification API surface. |
| `backend/email_service.py` | **A** | Transactional email delivery service (OTP codes, supervisor verification links) | Auth & admin routes | Tracked (Modified) | **KEEP** | Critical transactional communication service. |
| `backend/init_db.py` | **B** | Database schema initialization and seed script | Setup scripts | Tracked | **KEEP** | Essential for fresh database bootstrapping. |
| `backend/schema.sql` | **B** | Authoritative MySQL 8.0 DDL schema definition | `backend/init_db.py` | Tracked (Modified) | **KEEP** | Canonical database structure definition. |
| `backend/migrations/002_assessment_integrity.sql` | **B** | Migration 002: Assessment cooldown, timer, and integrity schema | DB migrations | Tracked | **KEEP** | Sequential database migration history. |
| `backend/migrations/migrate_002_assessment_integrity.py` | **B** | Migration 002 execution script | Migration runners | Tracked | **KEEP** | Sequential database migration runner. |
| `backend/migrations/003_assessment_topics_framework.sql` | **B** | Migration 003: Assessment topics and questions schema | DB migrations | Tracked | **KEEP** | Sequential database migration history. |
| `backend/migrations/migrate_003_assessment_topics_framework.py` | **B** | Migration 003 execution script | Migration runners | Tracked | **KEEP** | Sequential database migration runner. |
| `backend/migrations/004_binary_eligibility_alignment.sql` | **B** | Migration 004: Assessment attempts schema alignment | DB migrations | Tracked | **KEEP** | Sequential database migration history. |
| `backend/migrations/migrate_004_binary_eligibility_alignment.py` | **B** | Migration 004 execution script | Migration runners | Tracked | **KEEP** | Sequential database migration runner. |
| `backend/migrations/005_supervisor_reference_loop.sql` | **B** | Migration 005: Supervisor reference verification loop schema | DB migrations | Untracked (`??`) | **KEEP** | Active migration for supervisor verification. |
| `backend/migrations/migrate_005_supervisor_reference_loop.py` | **B** | Migration 005 execution script | Migration runners | Untracked (`??`) | **KEEP** | Active migration runner for supervisor verification. |
| `backend/migrations/006_task_multi_certifications.sql` | **B** | Migration 006: Multi-certification support (`task_certifications`) | DB migrations | Untracked (`??`) | **KEEP** | Active migration for multi-cert task requirements. |
| `backend/migrations/migrate_006_task_multi_certifications.py` | **B** | Migration 006 execution script | Migration runners | Untracked (`??`) | **KEEP** | Active migration runner for multi-cert task requirements. |
| `backend/models/binary_eligibility_model.pkl` | **E** | Legacy trained binary Random Forest model artifact (3.45 MB) | Previously `src/inference.py` | Tracked | **ARCHIVE** | Superseded by deterministic Stage 1 engine & Stage 2 model; archive for thesis reproduction. |
| `src/stage2_feature_engineering.py` | **C** | Canonical 5-feature Stage 2 feature engineering module | `src/task_suitability_inference.py`, `backend/db.py` | Untracked (`??`) | **KEEP** | Core production feature engineering logic. |
| `src/task_suitability_inference.py` | **C** | Stage 2 L2-logistic regression suitability prediction engine | `backend/db.py`, `backend/admin_routes.py` | Untracked (`??`) | **KEEP** | Core production ML inference engine. |
| `src/inference.py` | **E** | Legacy binary inference engine | Superseded | Tracked (Deleted in tree) | **ARCHIVE / REMOVE AFTER APPROVAL** | Obsolete binary model inference; superseded by `task_suitability_inference.py`. |
| `frontend/package.json` | **A** | Frontend npm dependency manifest and scripts | npm tooling | Tracked | **KEEP** | Core frontend configuration. |
| `frontend/package-lock.json` | **A** | Deterministic npm dependency lockfile | `npm ci` | Tracked | **KEEP** | Critical for reproducible frontend builds. |
| `frontend/vite.config.js` | **A** | Vite bundler, plugin, and dev server configuration | Vite build | Tracked | **KEEP** | Core build configuration. |
| `frontend/index.html` | **A** | Single-page application HTML entry point and web fonts | Vite build | Tracked (Modified) | **KEEP** | Core application HTML shell. |
| `frontend/.gitignore` | **A** | Frontend local gitignore rules | Git tooling | Tracked | **KEEP** | Standard frontend ignore rules. |
| `frontend/.oxlintrc.json` | **A** | Oxlint linter configuration | Frontend tooling | Tracked | **KEEP** | Code quality configuration. |
| `frontend/README.md` | **H** | Frontend development guide and component overview | Documentation | Tracked | **KEEP** | Useful frontend instructions. |
| `frontend/src/main.jsx` | **A** | React 19 application root mounting | `frontend/index.html` | Tracked (Modified) | **KEEP** | Core React mounting script. |
| `frontend/src/App.jsx` | **A** | Client-side routing, route protection, and navigation layout | `frontend/src/main.jsx` | Tracked (Modified) | **KEEP** | Central application routing controller. |
| `frontend/src/App.css` | **A** | Global styles and resets | `frontend/src/App.jsx` | Tracked | **KEEP** | Global application styling. |
| `frontend/src/index.css` | **A** | Tailwind CSS utility imports and core theme directives | `frontend/src/main.jsx` | Tracked | **KEEP** | Core stylesheet. |
| `frontend/src/context/AuthContext.jsx` | **A** | React context managing session state, tokens, and active user | Components and pages | Tracked | **KEEP** | Core state management for authentication. |
| `frontend/src/services/api.js` | **A** | Base Axios client with request/response interceptors for JWT | All frontend services | Tracked (Modified) | **KEEP** | Foundational HTTP transport service. |
| `frontend/src/services/adminService.js` | **A** | API client methods for workforce officer operations | `AdminDashboard.jsx`, `CreateTaskPage.jsx` | Tracked (Modified) | **KEEP** | Administrative API client. |
| `frontend/src/services/authService.js` | **A** | API client methods for login, registration, and OTP | Auth components | Tracked | **KEEP** | Authentication API client. |
| `frontend/src/services/competencyService.js` | **A** | API client methods for assessments, topic questions, and retakes | Assessment pages | Tracked (Modified) | **KEEP** | Assessment API client. |
| `frontend/src/services/workforceService.js` | **A** | API client methods for public supervisor verification loop | `SupervisorVerifyPage.jsx` | Untracked (`??`) | **KEEP** | Supervisor verification API client. |
| `frontend/src/pages/AdminDashboard.jsx` | **A** | Workforce Officer management portal (Tasks, Applications, Verifications) | `App.jsx` | Tracked (Modified) | **KEEP** | Critical primary officer dashboard. |
| `frontend/src/pages/AgentDashboard.jsx` | **A** | Agent portal (Available Tasks, Eligibility Feed, Active Applications) | `App.jsx` | Tracked (Modified) | **KEEP** | Critical primary agent dashboard. |
| `frontend/src/pages/AssessmentPage.jsx` | **A** | Interactive timed competency assessment test engine | `App.jsx` | Tracked (Modified) | **KEEP** | Core assessment execution interface. |
| `frontend/src/pages/AssessmentResultsPage.jsx` | **A** | Assessment score report, retake guidance, and feedback | `App.jsx` | Tracked (Modified) | **KEEP** | Assessment feedback interface. |
| `frontend/src/pages/CreateTaskPage.jsx` | **A** | Restructured 5-section task authoring form with live preview | `App.jsx` | Tracked (Modified) | **KEEP** | Restructured task creation module. |
| `frontend/src/pages/LoginPage.jsx` | **A** | User authentication portal | `App.jsx` | Tracked (Modified) | **KEEP** | Primary login page. |
| `frontend/src/pages/RegisterPage.jsx` | **A** | Agent and Workforce Officer onboarding portal | `App.jsx` | Tracked (Modified) | **KEEP** | Primary registration page. |
| `frontend/src/pages/ProfilePage.jsx` | **A** | Agent profile, experience submission, and cert upload management | `App.jsx` | Tracked (Modified) | **KEEP** | Primary profile management page. |
| `frontend/src/pages/SupervisorVerifyPage.jsx` | **A** | Public supervisor reference verification and endorsement form | `App.jsx` | Untracked (`??`) | **KEEP** | Public reference loop page. |
| `frontend/src/components/ui/Alert.jsx` | **A** | Reusable notification and status alert UI component | Multiple pages | Tracked | **KEEP** | Core design system primitive. |
| `frontend/src/components/ui/Button.jsx` | **A** | Reusable interactive button UI component | Multiple pages | Tracked | **KEEP** | Core design system primitive. |
| `frontend/src/components/ui/Checkbox.jsx` | **A** | Reusable checkbox UI component | Multiple pages | Tracked | **KEEP** | Core design system primitive. |
| `frontend/src/components/ui/Input.jsx` | **A** | Reusable form text input UI component | Multiple pages | Tracked | **KEEP** | Core design system primitive. |
| `frontend/src/components/ui/Modal.jsx` | **A** | Reusable dialog and modal window container | Multiple pages | Tracked | **KEEP** | Core design system primitive. |
| `frontend/src/components/auth/AuthCard.jsx` | **A** | Card wrapper for authentication pages | Login / Register | Untracked (`??`) | **KEEP** | Core auth design component. |
| `frontend/src/components/auth/AuthIllustration.jsx` | **A** | SVG illustrations for authentication visual layout | Login / Register | Tracked (Modified) | **KEEP** | Design asset component. |
| `frontend/src/components/auth/AuthLayout.jsx` | **A** | Split-pane authentication page layout wrapper | Login / Register | Untracked (`??`) | **KEEP** | Design layout component. |
| `frontend/src/components/auth/BrandLogo.jsx` | **A** | VerifyMesh branded logo component | Navbars and headers | Tracked | **KEEP** | Brand identity component. |
| `frontend/src/components/auth/ForgotPasswordModal.jsx` | **A** | Modal dialogue for password recovery flow | `LoginPage.jsx` | Tracked | **KEEP** | Auth recovery component. |
| `frontend/src/components/auth/HeroIllustration.jsx` | **A** | Hero branding graphic component | Auth pages | Untracked (`??`) | **KEEP** | Design asset component. |
| `frontend/src/components/auth/LoginForm.jsx` | **A** | Credential entry and authentication form component | `LoginPage.jsx` | Tracked | **KEEP** | Auth form component. |
| `frontend/src/components/auth/RegisterForm.jsx` | **A** | Registration and role selection form component | `RegisterPage.jsx` | Tracked (Modified) | **KEEP** | Onboarding form component. |
| `frontend/src/components/auth/VerifyEmailForm.jsx` | **A** | Email verification OTP input component | Auth flows | Tracked (Modified) | **KEEP** | OTP verification component. |
| `frontend/src/components/dashboard/AllTasksModal.jsx` | **A** | Modal displaying all agent tasks | `AgentDashboard.jsx` | Tracked | **KEEP** | Dashboard modal component. |
| `frontend/src/components/dashboard/CompetencyDetailsModal.jsx` | **A** | Modal presenting deterministic competency scoring breakdown | Dashboard pages | Tracked (Modified) | **KEEP** | Competency explanation modal. |
| `frontend/src/components/dashboard/HelpModal.jsx` | **A** | User guide, FAQs, and system help modal | Dashboard pages | Tracked (Modified) | **KEEP** | System help component. |
| `frontend/src/components/dashboard/ProfileModal.jsx` | **A** | Quick-edit modal for agent profile | `AgentDashboard.jsx` | Tracked | **KEEP** | Profile quick-action modal. |
| `frontend/src/components/dashboard/TakeAssessmentModal.jsx` | **A** | Pre-assessment rules, instructions, and launch modal | `AgentDashboard.jsx` | Tracked | **KEEP** | Assessment launch modal. |
| `frontend/src/components/dashboard/TaskModal.jsx` | **A** | Task details, compensation, and eligibility prerequisite modal | Dashboard pages | Tracked (Modified) | **KEEP** | Task application modal. |
| `frontend/src/styles/dashboard.css` | **A** | Dashboard styling and badge styles | Dashboard pages | Untracked (`??`) | **KEEP** | Dashboard stylesheet. |
| `frontend/src/styles/login-theme.css` | **A** | Obsidian Dark theme styling for auth pages | Auth components | Untracked (`??`) | **KEEP** | Auth stylesheet. |
| `frontend/src/assets/hero.png` | **A** | Visual branding illustration | Auth pages | Tracked | **KEEP** | Static asset. |
| `frontend/src/assets/react.svg` | **A** | React framework icon | Templates | Tracked | **KEEP** | Static asset. |
| `frontend/src/assets/vite.svg` | **A** | Vite framework icon | Templates | Tracked | **KEEP** | Static asset. |
| `frontend/public/favicon.svg` | **A** | Browser tab favicon icon | `index.html` | Tracked | **KEEP** | Static asset. |
| `frontend/public/icons.svg` | **A** | SVG sprite sheet | UI components | Tracked | **KEEP** | Static asset. |
| `frontend/public/logo-icon.svg` | **A** | Brand logo SVG asset | Brand components | Tracked | **KEEP** | Static asset. |
| `ml/README.md` | **H** | Comprehensive Stage 2 ML architecture, training, and evaluation guide | ML documentation | Tracked (Modified) | **KEEP AND ORGANISE** | Essential ML documentation. |
| `ml/metadata/verifymesh_stage2_metadata_v2.json` | **C** | Authoritative Stage 2 model metadata, hyperparameters, and feature schema | `src/task_suitability_inference.py` | Untracked (`??`) | **KEEP** | Critical model traceability metadata. |
| `ml/metadata/verifymesh_threshold_metadata.json` | **C** | Advisory threshold configuration metadata (0.60 threshold) | `src/task_suitability_inference.py` | Untracked (`??`) | **KEEP** | Critical threshold metadata. |
| `ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib` | **C** | Approved Stage 2 L2-logistic regression model pipeline (2.6 KB) | `src/task_suitability_inference.py` | Ignored by `*.joblib` | **KEEP AND ORGANISE** | Active production suitability model artifact; must be tracked. |
| `ml/models/verifymesh_final_optimized_pipeline.joblib` | **D** | Optimized Random Forest candidate pipeline (709 KB) | Research experiments | Ignored by `*.joblib` | **ARCHIVE** | Candidate model evaluated in Chapter 5 research; retain in research archive. |
| `ml/notebooks/VerifyMesh_Task_Suitability_Experiment.ipynb` | **D** | Active research notebook reproducing Stage 2 training & validation | Research documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Reproducible research experiment notebook. |
| `ml/notebooks/Verify_Mesh.ipynb` | **E** | Legacy initial binary training notebook | Superseded | Tracked (Deleted in tree) | **ARCHIVE** | Superseded notebook; preserve in research archive if needed for thesis citations. |
| `ml/train.py` | **E** | Legacy CLI training script for binary model | Superseded | Tracked (Deleted in tree) | **ARCHIVE / REMOVE AFTER APPROVAL** | Superseded by `train_and_serialize_stage2_v2.py`. |
| `ml/evaluate.py` | **E** | Legacy CLI evaluation script for binary model | Superseded | Tracked (Deleted in tree) | **ARCHIVE / REMOVE AFTER APPROVAL** | Superseded by Phase 1/2 benchmark scripts. |
| `ml/experiments/task_specific_synthetic_data/generate_synthetic_dataset.py` | **D** | Synthetic workforce dataset generation script | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Generates authoritative simulation data for task suitability. |
| `ml/experiments/task_specific_synthetic_data/data_dictionary.md` | **D** | Feature documentation and dictionary for synthetic workforce dataset | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Data documentation. |
| `ml/experiments/task_specific_synthetic_data/simulation_methodology.md` | **D** | Algorithmic specification of applicant-task simulation | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Research methodology documentation. |
| `ml/experiments/task_specific_synthetic_data/dataset_validation_report.md` | **D** | Data quality and distribution validation report | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Research verification report. |
| `ml/experiments/task_specific_synthetic_data/synthetic_applicants.csv` | **D** | Generated applicant pool (N=1,000) | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Reproducible synthetic research dataset. |
| `ml/experiments/task_specific_synthetic_data/synthetic_tasks.csv` | **D** | Generated task requirements pool (N=100) | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Reproducible synthetic research dataset. |
| `ml/experiments/task_specific_synthetic_data/synthetic_applicant_task_pairs.csv` | **D** | Cartesian applicant-task evaluation pairs | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Reproducible synthetic research dataset. |
| `ml/experiments/task_specific_synthetic_data/task_suitability_training.csv` | **D** | Complete Scenario A/B dataset for model training | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Authoritative dataset used to train Stage 2 models. |
| `ml/experiments/stage2_refinement/run_phase1_benchmark.py` | **D** | Phase 1 model comparison benchmark runner | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Research benchmark script. |
| `ml/experiments/stage2_refinement/run_phase2_scenario_comparison.py` | **D** | Phase 2 Scenario A vs B comparison runner | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Research scenario comparison script. |
| `ml/experiments/stage2_refinement/run_phase3_final_audit.py` | **D** | Phase 3 calibration, threshold, and feature audit runner | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Research audit script. |
| `ml/experiments/stage2_refinement/train_and_serialize_stage2_v2.py` | **D** | Active Stage 2 training & model serialization script | Active model training | Untracked (`??`) | **KEEP AND ORGANISE** | Authoritative script that trains `verifymesh_stage2_suitability_pipeline_v2.joblib`. |
| `ml/experiments/stage2_refinement/phase1_benchmark_report.md` | **D** | Benchmark report comparing RF, XGBoost, and Logistic Regression | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Thesis experimental evidence. |
| `ml/experiments/stage2_refinement/phase1_benchmark_results.json` | **D** | Raw JSON results of Phase 1 benchmark | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase1_benchmark_summary.csv` | **D** | Summary performance metrics table (AUC, F1, Log Loss) | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase1_fold_details.csv` | **D** | 5-fold cross-validation fold-by-fold results | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase2_scenario_comparison_report.md` | **D** | Research report on Scenario A vs B bottleneck impact | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Thesis experimental evidence. |
| `ml/experiments/stage2_refinement/phase2_scenario_comparison_results.json` | **D** | Raw JSON results of Scenario comparison | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase2_scenario_comparison_summary.csv` | **D** | Summary table for Scenario comparison | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase2_scenario_comparison_folds.csv` | **D** | Fold metrics for Scenario comparison | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase3_calibration_and_model_report.md` | **D** | Calibration analysis, Brier score, and threshold selection report | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Thesis experimental evidence. |
| `ml/experiments/stage2_refinement/phase3_calibration_comparison.csv` | **D** | Empirical calibration comparison table | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase3_final_audit_report.md` | **D** | 5-feature vs 6-feature representation audit report | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Thesis experimental evidence. |
| `ml/experiments/stage2_refinement/phase3_final_audit_results.json` | **D** | JSON results for 5v6 feature audit | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/phase3_final_audit_5v6_summary.csv` | **D** | Performance table for 5v6 feature audit | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Experimental data artifact. |
| `ml/experiments/stage2_refinement/scenario_b_data/*` | **D** | Partitioned Scenario B training and validation datasets (4 files) | Research experiments | Untracked (`??`) | **KEEP AND ORGANISE** | Authoritative dataset partition for active model. |
| `ml/outputs/chapter5/*` | **D** | 19 academic thesis assets: ROC curves, confusion matrices, distributions, tables, and chapter draft | Academic thesis | Untracked (`??`) | **KEEP AND ORGANISE** | Crucial academic research evidence for DSR evaluation chapter. |
| `data/README.md` | **E** | Legacy binary dataset description | Superseded | Tracked (Deleted in tree) | **ARCHIVE / REMOVE AFTER APPROVAL** | Superseded by `task_specific_synthetic_data/data_dictionary.md`. |
| `data/raw/VerifyMesh_Competency_Dataset_V2.csv` | **E** | Legacy 2,000-row binary dataset (116 KB) | Superseded | Tracked (Deleted in tree) | **ARCHIVE** | Retain in historical research archive. |
| `docs/PHASE_1_BINARY_ALIGNMENT_AUDIT.md` | **E** | Legacy audit report on binary gatekeeper alignment | Superseded | Tracked (Deleted in tree) | **ARCHIVE / REMOVE AFTER APPROVAL** | Superseded by Phase 4 handover report. |
| `docs/PHASE_4_HANDOVER.md` | **H** | Production handover report covering deterministic Stage 1 & Stage 2 | Documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Comprehensive system handover documentation. |
| `docs/testing/defect_report.md` | **H** | System QA defect tracking log | QA documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Testing documentation. |
| `docs/testing/panel_demo_checklist.md` | **H** | Live demonstration checklist for thesis examination panel | Academic / QA | Untracked (`??`) | **KEEP AND ORGANISE** | Panel presentation guide. |
| `docs/testing/system_audit.md` | **H** | Architectural security and logic audit | QA documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Testing documentation. |
| `docs/testing/test_plan.md` | **H** | Test specifications and execution plan | QA documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Testing documentation. |
| `docs/testing/test_results.md` | **H** | Test suite execution outcome records | QA documentation | Untracked (`??`) | **KEEP AND ORGANISE** | Testing documentation. |
| `docs/repository/01_git_forensic_audit.md` | **H** | Phase 0.1 Git forensic audit deliverable | Repository documentation | Untracked (`??`) | **KEEP** | Core Phase 0 deliverable. |
| `docs/repository/02_file_inventory.md` | **H** | Phase 0.2 File inventory & classification deliverable | Repository documentation | Active Document | **KEEP** | Core Phase 0 deliverable. |
| `tests/test_assessment_integrity.py` | **A** | Automated tests for assessment cooldown, timer, and tamper resistance | Test suite | Tracked | **KEEP** | Critical regression test suite. |
| `tests/test_assessment_topics_workflow.py` | **A** | Automated tests for topic scoring and exam aggregation | Test suite | Tracked | **KEEP** | Critical regression test suite. |
| `tests/test_competency_consistency.py` | **A** | Automated tests for competency score mathematical consistency | Test suite | Tracked (Modified) | **KEEP** | Critical regression test suite. |
| `tests/test_exam_pass_thresholds.py` | **A** | Automated tests for pass/fail decision boundaries | Test suite | Tracked (Modified) | **KEEP** | Critical regression test suite. |
| `tests/test_security_remediation.py` | **A** | Automated tests for authentication, authorization, and SQL injection checks | Test suite | Tracked | **KEEP** | Critical security test suite. |
| `tests/test_system_suite.py` | **A** | Automated end-to-end integration test suite | Test suite | Tracked (Modified) | **KEEP** | Critical system regression suite. |
| `tests/test_task_management.py` | **A** | Automated tests for task deactivation, status transitions, and deletion | Test suite | Tracked (Modified) | **KEEP** | Critical task management test suite. |
| `tests/test_create_task_restructuring.py` | **A** | Automated tests for 5-section task form, multi-certs, and topics | Test suite | Untracked (`??`) | **KEEP** | Critical newly restructured task test suite. |
| `tests/test_panel_demonstration_readiness.py` | **A** | Automated tests verifying system readiness for panel review | Test suite | Untracked (`??`) | **KEEP** | Verification suite for academic demonstration. |
| `tests/test_supervisor_reference_loop.py` | **A** | Automated tests for supervisor verification token, expiry, and endorsement | Test suite | Untracked (`??`) | **KEEP** | Critical supervisor verification test suite. |
| `tests/test_task_eligibility_enforcement.py` | **A** | Automated tests for authoritative deterministic Stage 1 qualification | Test suite | Untracked (`??`) | **KEEP** | Critical deterministic eligibility engine suite. |
| `tests/test_task_suitability_optimized_rf.py` | **D** | Automated tests verifying candidate Random Forest suitability predictions | Research tests | Untracked (`??`) | **KEEP** | Research test suite. |
| `scratch/migrate_profile_schema.py` | **E** | Temporary migration helper committed in historical branch | Superseded | Tracked | **EXCLUDE FROM GIT / REMOVE AFTER APPROVAL** | Temporary script accidentally committed in `b25c8da`; untrack via `git rm --cached`. |
| `scratch/migrate_task_form_schema.py` | **E** | Temporary migration helper committed in historical branch | Superseded | Tracked | **EXCLUDE FROM GIT / REMOVE AFTER APPROVAL** | Temporary script accidentally committed in `b25c8da`; untrack via `git rm --cached`. |
| `scratch/test_admin_task_form.py` | **E** | Temporary test script committed in historical branch | Superseded | Tracked | **EXCLUDE FROM GIT / REMOVE AFTER APPROVAL** | Temporary script accidentally committed in `b25c8da`; untrack via `git rm --cached`. |
| `scratch/test_agent_dashboard_metrics.py` | **E** | Temporary test script committed in historical branch | Superseded | Tracked | **EXCLUDE FROM GIT / REMOVE AFTER APPROVAL** | Temporary script accidentally committed in `b25c8da`; untrack via `git rm --cached`. |
| `scratch/test_profile_workflow.py` | **E** | Temporary test script committed in historical branch | Superseded | Tracked | **EXCLUDE FROM GIT / REMOVE AFTER APPROVAL** | Temporary script accidentally committed in `b25c8da`; untrack via `git rm --cached`. |
| `scratch/audit_alex_suitability.py` | **F** | Developer diagnostic script for Alex Morgan audit | Audit task | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer debugging tool. |
| `scratch/audit_model_math.py` | **F** | Developer diagnostic script for Logistic Regression math | Audit task | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer debugging tool. |
| `scratch/inspect_alex_task4.py` | **F** | Developer diagnostic script for Task 4 data inspection | Audit task | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer debugging tool. |
| `scratch/reproduce_alex_prediction.py` | **F** | Developer reproduction script for Alex Morgan prediction | Audit task | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer debugging tool. |
| `scratch/run_model_experiments.py` | **F** | Developer sensitivity experiment script | Audit task | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer debugging tool. |
| `scratch/seed_realistic_exam_questions.py` | **F** | Developer helper for seeding mock exam questions | Developer utility | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer utility. |
| `scratch/test_e2e_3topic_flow.py` | **F** | Developer helper for 3-topic manual flow verification | Developer utility | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer utility. |
| `scratch/update_sample_references.py` | **F** | Developer helper for supervisor reference seed data | Developer utility | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer utility. |
| `scratch/update_schema_sql.py` | **F** | Developer helper for synchronizing schema DDL | Developer utility | Ignored (`!!`) | **EXCLUDE FROM GIT** | Ephemeral developer utility. |
| `.venv/` | **F** | Python 3.13 local virtual environment | Local runtime | Ignored (`!!`) | **EXCLUDE FROM GIT** | Machine-specific runtime dependencies. |
| `frontend/node_modules/` | **F** | Node.js dependencies installed locally | Frontend runtime | Ignored (`!!`) | **EXCLUDE FROM GIT** | Machine-specific node modules. |
| `frontend/dist/` | **F** | Production build assets generated by Vite | Build artifacts | Ignored (`!!`) | **EXCLUDE FROM GIT** | Generated bundle output; reproducible via `npm run build`. |
| `__pycache__/` | **F** | Python compiled bytecode caches across backend and tests | Python runtime | Ignored (`!!`) | **EXCLUDE FROM GIT** | Temporary bytecode cache. |

---

## 4. DETAILED CATEGORY FINDINGS & RECOMMENDATIONS

### Category A: Essential Application Source (47 files)
- **Status:** Active, robust, verified.
- **Components:** Flask application factory, routes, core database layer, React frontend components, pages, design system primitives, and test suites.
- **Action:** Retain under version control; incorporate all local improvements.

### Category B: Essential Database Files (14 files)
- **Status:** Complete sequential database migration chain.
- **Components:** `backend/schema.sql`, `backend/init_db.py`, and migrations `002`, `003`, `004`, `005`, and `006` (both SQL DDL and Python runner scripts).
- **Action:** Preserve all migrations. Check and verify that seed data and SQL files contain zero real personal credentials or PII.

### Category C: Essential ML Implementation (4 files)
- **Status:** Authoritative Stage 2 task suitability prediction system.
- **Components:**
  1. `src/stage2_feature_engineering.py` (Feature engineering pipeline)
  2. `src/task_suitability_inference.py` (Inference prediction service)
  3. `ml/metadata/verifymesh_stage2_metadata_v2.json` (Model hyperparameters & traceability)
  4. `ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib` (Active trained model artifact, 2.6 KB)
- **Action:** Retain all 4 files. Update `.gitignore` to explicitly allow `!ml/models/verifymesh_stage2_suitability_pipeline_v2.joblib` so that anyone cloning the repository has the active model out of the box.

### Category D: Research & Experimental Evidence (52 files)
- **Status:** Comprehensive academic evidence supporting Chapter 5 of the thesis.
- **Components:**
  - `ml/experiments/task_specific_synthetic_data/`: Dataset generators, simulation methodologies, and synthetic CSV datasets.
  - `ml/experiments/stage2_refinement/`: 3-phase experimental benchmark scripts, scenario comparisons, calibration reports, and fold metrics.
  - `ml/outputs/chapter5/`: 19 thesis-ready figures, ROC curves, confusion matrices, and tables.
  - `ml/notebooks/VerifyMesh_Task_Suitability_Experiment.ipynb`: Interactive Jupyter research notebook.
- **Action:** **KEEP AND ORGANISE.** Do not discard this evidence. It proves the rigorous design science research methodology, baseline benchmarking, and cross-validation required for thesis defense.

### Category E: Obsolete & Legacy Implementation (14 files)
- **Status:** Superseded by the retirement of the binary gatekeeper in favor of the deterministic Stage 1 engine.
- **Components:**
  - `ml/train.py`, `ml/evaluate.py`, `src/inference.py`, `ml/notebooks/Verify_Mesh.ipynb`
  - `data/raw/VerifyMesh_Competency_Dataset_V2.csv`, `data/README.md`
  - `backend/models/binary_eligibility_model.pkl` (3.45 MB)
  - 5 tracked developer scripts in `scratch/` (`migrate_profile_schema.py`, etc.)
- **Action:**
  - The 5 tracked scratch scripts should be untracked using `git rm --cached`.
  - The legacy binary files (`binary_eligibility_model.pkl`, legacy notebook, dataset) should be archived in a clean `archive/legacy_binary_gatekeeper/` directory or preserved in Git history rather than cluttering production namespaces.

### Category F: Temporary & Generated Files (18+ items)
- **Status:** Ephemeral developer scripts, local caches, and build outputs.
- **Components:** `.venv/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`, developer scratch tools in `scratch/`.
- **Action:** **EXCLUDE FROM GIT.** Enforce strict ignore rules.

### Category G: Sensitive & Private Files (2 files)
- **Status:** `.env` and `.env.example`.
- **Components:** `.env` contains local development database passwords and secrets. `.env.example` provides safe templates.
- **Action:** Confirm `.env` is never committed. Verify `.env.example` contains zero exposed secrets.

### Category H: Documentation & Specifications (12 files)
- **Status:** Specifications, QA logs, handover notes, and repository audit logs.
- **Action:** Retain and consolidate under `docs/`.

---

## 5. PROPOSED NEXT STEPS & APPROVAL GATE

Phase 0.2 has cataloged every file in the repository without performing any destructive actions.

Before proceeding to **Phase 0.3 (Dependency & Legacy Code Audit)** and **Phase 0.4 (Security & Secrets Audit)**, please review these classifications and confirm approval to proceed.

