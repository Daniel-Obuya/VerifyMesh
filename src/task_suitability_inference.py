import os
import json
import math
import hashlib
import logging
import warnings
import joblib
import pandas as pd
import numpy as np

from src.stage2_feature_engineering import (
    STAGE2_V2_FEATURES,
    STAGE2_V2_FEATURE_DESCRIPTIONS,
    LEGACY_28_FEATURES,
    build_complete_stage2_feature_dict,
    explain_stage2_prediction,
)

# Compatibility shim for scikit-learn version differences (e.g. 1.6.1 model in 1.9.0 runtime)
try:
    import sklearn.compose._column_transformer as _ct
    if not hasattr(_ct, '_RemainderColsList'):
        class _RemainderColsList(list):
            pass
        _ct._RemainderColsList = _RemainderColsList
except Exception:
    pass

logger = logging.getLogger("verifymesh.task_suitability")


class TaskSuitabilityInference:
    """
    Stage 2 Task-Specific Suitability Prediction Engine:
    Executes the approved Phase 3 L2-regularised Logistic Regression pipeline
    (ColumnTransformer(StandardScaler) + LogisticRegression(C=0.5, penalty='l2'), 5 features)
    trained on Scenario B (N = 4,675 Stage 1-eligible applicant-task pairs).

    Core Architectural Guarantees:
    1. Backend owns prediction: All feature engineering, probability estimation,
       advisory tiering, and factor explanations are computed server-side.
    2. Stage 1 Gatekeeper Authority: Stage 2 only scores candidates who have already
       passed all deterministic Stage 1 requirements (certification, experience, assessment).
    3. Advisory Ranking Only: Stage 2 never auto-assigns tasks or overrides Stage 1;
       the human Administrator retains final task allocation authority.
    4. Exact 5-Feature Schema: Uses ['weighted_skill_margin', 'min_skill_margin',
       'weakest_link_deficit', 'exp_surplus_tanh', 'difficulty_tier'].
    5. Safe Failure Handling: Rejects missing, non-numeric, NaN, or Inf inputs and
       never fabricates probabilities when inputs or artifacts are invalid.
    6. Synthetic-Data Disclosure: Explicitly discloses synthetic training provenance
       and model version/SHA-256 traceability in all outputs.
    """

    FEATURE_NAMES = list(STAGE2_V2_FEATURES)
    LEGACY_FEATURE_NAMES = list(LEGACY_28_FEATURES)

    DEFAULT_MODEL_FILENAME = "verifymesh_stage2_suitability_pipeline_v2.joblib"
    DEFAULT_METADATA_FILENAME = "verifymesh_stage2_metadata_v2.json"
    DEFAULT_THRESHOLD = 0.60
    DEFAULT_MODERATE_THRESHOLD = 0.48

    SYNTHETIC_DATA_DISCLAIMER = (
        "Trained on synthetic simulation data (Scenario B, N=4,675 eligible pairs); "
        "not yet validated against real-world employee task performance outcomes. "
        "Strictly advisory ranking for Stage 1-eligible candidates; the human Administrator "
        "retains final task assignment authority."
    )

    def __init__(
        self,
        model_filename: str = DEFAULT_MODEL_FILENAME,
        metadata_filename: str = DEFAULT_METADATA_FILENAME,
    ):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.model_filename = model_filename
        self.metadata_filename = metadata_filename
        self.is_legacy_rf = (model_filename == "verifymesh_final_optimized_pipeline.joblib")

        # Search candidate paths for model
        model_candidates = [
            os.path.join(base_dir, "ml", "models", model_filename),
            os.path.join(base_dir, "backend", "models", model_filename),
            os.path.join(base_dir, "models", model_filename),
            os.path.join(base_dir, model_filename),
        ]
        self.model_path = next((p for p in model_candidates if os.path.exists(p)), model_candidates[0])

        # Search candidate paths for metadata
        meta_candidates = [
            os.path.join(base_dir, "ml", "metadata", metadata_filename),
            os.path.join(base_dir, "backend", "metadata", metadata_filename),
            os.path.join(base_dir, metadata_filename),
        ]
        self.metadata_path = next((p for p in meta_candidates if os.path.exists(p)), meta_candidates[0])

        self.model = None
        self.model_sha256 = None
        self.threshold = 0.61 if self.is_legacy_rf else self.DEFAULT_THRESHOLD
        self.moderate_threshold = self.DEFAULT_MODERATE_THRESHOLD
        self.positive_class = 1
        self.negative_class = 0
        self.metadata = {}
        self.required_features = (
            list(self.LEGACY_FEATURE_NAMES) if self.is_legacy_rf else list(self.FEATURE_NAMES)
        )

        # Attempt initial load
        self.load_metadata()
        self.load_model()

    @staticmethod
    def _compute_file_sha256(filepath: str) -> str | None:
        if not filepath or not os.path.exists(filepath):
            return None
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def load_metadata(self) -> bool:
        """Loads decision threshold, advisory tiers, and traceability metadata from JSON."""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                default_tau = 0.61 if self.is_legacy_rf else self.DEFAULT_THRESHOLD
                self.threshold = float(self.metadata.get("threshold", default_tau))
                tiers = self.metadata.get("advisory_tiers", {})
                self.moderate_threshold = float(
                    tiers.get("moderate_fit_min_prob", self.DEFAULT_MODERATE_THRESHOLD)
                )
                self.positive_class = int(self.metadata.get("positive_class", 1))
                self.negative_class = int(self.metadata.get("negative_class", 0))
                logger.info(
                    f"[Task Suitability ML] Loaded metadata from {self.metadata_path} "
                    f"(tau={self.threshold}, moderate_tau={self.moderate_threshold})"
                )
                return True
            else:
                logger.warning(
                    f"[Task Suitability ML] Metadata not found at {self.metadata_path}, "
                    f"defaulting to tau={self.threshold}"
                )
                return False
        except Exception as e:
            logger.error(f"[Task Suitability ML] Error loading metadata: {e}")
            return False

    def load_model(self) -> bool:
        """Loads the serialized scikit-learn pipeline and verifies SHA-256 integrity."""
        try:
            if os.path.exists(self.model_path):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.model = joblib.load(self.model_path)

                self.model_sha256 = self._compute_file_sha256(self.model_path)

                feature_names = getattr(self.model, "feature_names_in_", None)
                if feature_names is not None:
                    self.required_features = list(feature_names)
                else:
                    self.required_features = (
                        list(self.LEGACY_FEATURE_NAMES)
                        if self.is_legacy_rf
                        else list(self.FEATURE_NAMES)
                    )

                logger.info(
                    f"[Task Suitability ML] Successfully loaded model from {self.model_path} "
                    f"({len(self.required_features)} features, tau={self.threshold}, sha256={self.model_sha256})"
                )
                return True
            else:
                logger.warning(f"[Task Suitability ML] Model artifact not found at: {self.model_path}")
                self.model = None
                self.model_sha256 = None
                return False
        except Exception as e:
            logger.error(f"[Task Suitability ML] Failed to load pipeline: {e}")
            self.model = None
            self.model_sha256 = None
            return False

    def classify_advisory_tier(self, p_suitable: float) -> tuple[str, str]:
        """
        Map calibrated predicted probability P(Suitable) to the approved 3-level
        human-in-the-loop advisory tier:
          - Strong Fit:   P >= 0.60 (or self.threshold)
          - Moderate Fit: 0.48 <= P < 0.60
          - Needs Review: P < 0.48
        """
        if p_suitable >= self.threshold:
            return "Strong Fit", "strong"
        if p_suitable >= self.moderate_threshold:
            return "Moderate Fit", "moderate"
        return "Needs Review", "needs_review"

    def get_traceability_metadata(self) -> dict:
        """Returns structured model provenance and traceability metadata for auditing."""
        model_name = self.metadata.get(
            "model_name",
            "VerifyMesh_Legacy_RF_v1" if self.is_legacy_rf else "VerifyMesh_Stage2_Suitability_LR_v2",
        )
        model_version = self.metadata.get(
            "model_version",
            "2.1.0-optimized-rf" if self.is_legacy_rf else "2.0.0",
        )
        algorithm = (
            "ColumnTransformer + RandomForestClassifier (Legacy 28-Feature)"
            if self.is_legacy_rf
            else "StandardScaler + LogisticRegression (L2, C=0.5, 5-Feature Weakest-Link)"
        )
        return {
            "model_name": model_name,
            "model_version": model_version,
            "model_file": os.path.basename(self.model_path) if self.model else self.model_filename,
            "model_sha256": self.model_sha256 or self.metadata.get("model_sha256"),
            "algorithm": algorithm,
            "feature_count": len(self.required_features),
            "ordered_features": list(self.required_features),
            "applied_threshold": self.threshold,
            "moderate_threshold": self.moderate_threshold,
            "advisory_tiers": {
                "strong_fit": f"P >= {self.threshold:.2f}",
                "moderate_fit": f"{self.moderate_threshold:.2f} <= P < {self.threshold:.2f}",
                "needs_review": f"P < {self.moderate_threshold:.2f}",
            },
            "training_scenario": self.metadata.get("training_dataset", {}).get(
                "simulation_scenario",
                "scenario_b (Strict Bottleneck / Weakest-Link, N=4,675 eligible pairs)",
            ),
            "is_advisory": True,
            "stage1_authority": "Stage 1 Deterministic Eligibility Engine is mandatory and authoritative.",
            "admin_decision_authority": "Administrator retains final task assignment authority.",
            "synthetic_data_disclaimer": self.SYNTHETIC_DATA_DISCLAIMER,
        }

    def get_info(self) -> dict:
        """Returns runtime information about the active suitability model."""
        if self.model is None:
            self.load_model()
        traceability = self.get_traceability_metadata()
        return {
            "model_loaded": self.model is not None,
            "model_name": traceability["model_name"],
            "model_version": traceability["model_version"],
            "model_file": os.path.basename(self.model_path) if self.model else "None",
            "active_model": os.path.basename(self.model_path) if self.model else "None",
            "model_path": self.model_path if self.model else "None",
            "model_sha256": traceability["model_sha256"],
            "algorithm": traceability["algorithm"],
            "features_count": len(self.required_features),
            "feature_count": len(self.required_features),
            "expected_features": list(self.required_features),
            "feature_descriptions": (
                STAGE2_V2_FEATURE_DESCRIPTIONS if not self.is_legacy_rf else {}
            ),
            "decision_threshold": self.threshold,
            "moderate_threshold": self.moderate_threshold,
            "advisory_tiers": self.metadata.get(
                "advisory_tiers",
                {
                    "strong_fit_min_prob": self.threshold,
                    "moderate_fit_min_prob": self.moderate_threshold,
                    "needs_review_max_prob": self.moderate_threshold,
                    "labels": {
                        "strong": "Strong Fit",
                        "moderate": "Moderate Fit",
                        "caution": "Needs Review",
                        "ineligible": "Ineligible — Stage 1 Gate Failed",
                    },
                },
            ),
            "classes": ["Not Suitable (0)", "Suitable (1)"],
            "positive_class": self.positive_class,
            "negative_class": self.negative_class,
            "role": "Stage 2 Task-Specific Suitability Prediction (Advisory Ranking)",
            "eligibility_engine": "Stage 1 Deterministic Server-Side Gatekeeper",
            "binary_gatekeeper_status": "Retired",
            "is_advisory": True,
            "training_scenario": traceability["training_scenario"],
            "synthetic_data_disclaimer": self.SYNTHETIC_DATA_DISCLAIMER,
            "limitations_and_disclaimers": self.metadata.get(
                "limitations_and_disclaimers",
                [self.SYNTHETIC_DATA_DISCLAIMER],
            ),
        }

    @staticmethod
    def _validate_finite_numeric(val, field_name: str) -> float:
        """Strictly validate that a feature value is a finite number (not None, bool, str, NaN, or Inf)."""
        if val is None or isinstance(val, bool):
            raise ValueError(f"Feature '{field_name}' must be numeric, got: {val!r}")
        try:
            fval = float(val)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Feature '{field_name}' must be numeric, got: {val!r}") from exc
        if math.isnan(fval) or math.isinf(fval):
            raise ValueError(f"Feature '{field_name}' must be a finite number (not NaN or Inf), got: {val!r}")
        return fval

    def predict(self, feature_data: dict) -> dict:
        """
        Runs advisory Stage 2 suitability inference on an applicant-task feature dictionary.
        Strictly enforces:
          - Model availability check (raises RuntimeError if model is not loaded)
          - Stage 1 eligibility guard (raises ValueError if is_eligible is explicitly False)
          - Complete, finite numeric feature validation (raises ValueError on missing/invalid/NaN/Inf)
          - Threshold tau = 0.60 and 3-tier advisory classification
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError(
                    f"Task Suitability model is not loaded or unavailable at '{self.model_path}'."
                )

        if not isinstance(feature_data, dict):
            raise ValueError("Input feature_data must be a dictionary.")

        # Never score a candidate marked ineligible by Stage 1
        if feature_data.get("is_eligible") is False or feature_data.get("meets_prerequisites") is False:
            raise ValueError(
                "Stage 1 Gate Failed: Ineligible applicant-task pairs cannot be scored by Stage 2."
            )

        # Check if all required features are directly present
        missing_direct = [f for f in self.required_features if f not in feature_data]
        complete_context = dict(feature_data)

        if missing_direct:
            # If running the 5-feature v2 model and the caller supplied a complete 28-feature legacy dict,
            # deterministically engineer the 5 Stage 2 v2 features after validating all 28 legacy features.
            if not self.is_legacy_rf and all(f in feature_data for f in self.LEGACY_FEATURE_NAMES):
                for lf in self.LEGACY_FEATURE_NAMES:
                    self._validate_finite_numeric(feature_data[lf], lf)
                complete_context = build_complete_stage2_feature_dict(feature_data)
            else:
                raise ValueError(
                    f"Missing required task suitability feature keys: {missing_direct}"
                )

        # Validate every required feature is numeric and finite (neither NaN nor Inf)
        row = {}
        for f in self.required_features:
            row[f] = self._validate_finite_numeric(complete_context[f], f)

        if not self.is_legacy_rf and row.get("difficulty_tier") not in (1.0, 2.0, 3.0):
            raise ValueError(
                f"Feature 'difficulty_tier' must be 1, 2, or 3, got: {row.get('difficulty_tier')}"
            )

        df = pd.DataFrame([row], columns=self.required_features)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            probabilities = self.model.predict_proba(df)[0]

        p_not_suitable = float(probabilities[0])
        p_suitable = float(probabilities[1])

        if math.isnan(p_suitable) or math.isinf(p_suitable):
            raise RuntimeError("Model produced a non-finite probability value.")

        is_suitable = bool(p_suitable >= self.threshold)
        predicted_class = self.positive_class if is_suitable else self.negative_class
        suitability_label = "Suitable" if is_suitable else "Not Suitable"
        advisory_tier, advisory_tier_code = self.classify_advisory_tier(p_suitable)

        # Build human-readable factor explanations using complete feature context
        try:
            full_for_explanation = build_complete_stage2_feature_dict({**complete_context, **row})
            contributing_factors = explain_stage2_prediction(full_for_explanation)
        except Exception:
            contributing_factors = []

        traceability = self.get_traceability_metadata()

        return {
            "suitability_score": round(p_suitable, 4),
            "suitability_percent": round(p_suitable * 100.0, 1),
            "p_suitable": round(p_suitable, 4),
            "p_not_suitable": round(p_not_suitable, 4),
            "predicted_class": predicted_class,
            "suitability_label": suitability_label,
            "advisory_tier": advisory_tier,
            "advisory_tier_code": advisory_tier_code,
            "applied_threshold": self.threshold,
            "moderate_threshold": self.moderate_threshold,
            "engineered_features": {k: round(v, 4) for k, v in row.items()},
            "contributing_factors": contributing_factors,
            "model_traceability": traceability,
            "model_name": traceability["model_name"],
            "model_version": traceability["model_version"],
            "model_sha256": traceability["model_sha256"],
            "threshold_metadata": {
                "threshold": self.threshold,
                "moderate_threshold": self.moderate_threshold,
                "positive_class": self.positive_class,
                "negative_class": self.negative_class,
                "source": os.path.basename(self.metadata_path),
            },
            "is_advisory": True,
            "synthetic_data_disclaimer": self.SYNTHETIC_DATA_DISCLAIMER,
            "disclaimer": (
                "Advisory Task Suitability Score: Administrator retains final assignment authority. "
                "Trained on synthetic simulation data; not yet validated on real-world task outcomes."
            ),
            "probabilities": {
                "Not Suitable": round(p_not_suitable, 4),
                "Suitable": round(p_suitable, 4),
            },
        }


# Global singleton instance exported for application routes and db queries (Stage 2 v2 5-Feature LR)
task_suitability_engine = TaskSuitabilityInference()

# Preserved legacy singleton for historical audit / backward-compatibility testing
legacy_rf_suitability_engine = TaskSuitabilityInference(
    model_filename="verifymesh_final_optimized_pipeline.joblib",
    metadata_filename="verifymesh_threshold_metadata.json",
)
