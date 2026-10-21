import os
import joblib
import pandas as pd
import numpy as np


class BinaryEligibilityInference:
    """
    VerifyMesh Binary Eligibility Inference Engine:
    Authoritative inference pipeline executing the high-accuracy Binary Gatekeeper
    Pipeline (StandardScaler + RandomForestClassifier, 15 features).
    Directly produces exactly two outcomes: 'Eligible' and 'Not Eligible'.
    """
    RAW_FEATURES = [
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

    EXPECTED_FEATURES = RAW_FEATURES + ["certified_leverage"]
    ENGINEERED_FEATURES = EXPECTED_FEATURES + [
        "total_experience_months",
        "mean_score",
        "min_score",
        "max_score"
    ]

    def __init__(self, model_filename="binary_eligibility_model.pkl"):
        self.model_filename = model_filename
        
        # Calculate absolute paths relative to project layout
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Priority search paths: Check binary_eligibility_model.pkl first, then fallback paths
        candidate_paths = [
            os.path.join(base_dir, "backend", "models", model_filename),
            os.path.join(base_dir, "models", model_filename),
            os.path.join(base_dir, model_filename),
            os.path.join(base_dir, "src", model_filename),
            os.path.abspath(model_filename),
            # Fallback paths
            os.path.join(base_dir, "backend", "models", "threeway_decision_model.joblib"),
            os.path.join(base_dir, "threeway_decision_model.joblib"),
        ]

        self.model_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
        self.model = None
        self.is_binary_gatekeeper = False
        self.required_features = self.EXPECTED_FEATURES

    def load_model(self) -> bool:
        """Loads the serialized pipeline and inspects feature contracts."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                
                # Inspect model feature requirements
                feature_names = getattr(self.model, "feature_names_in_", None)
                if feature_names is None and hasattr(self.model, "named_steps"):
                    # Pipeline object (e.g. StandardScaler + RandomForest)
                    first_step = list(self.model.named_steps.values())[0]
                    feature_names = getattr(first_step, "feature_names_in_", None)

                if feature_names is not None:
                    self.required_features = list(feature_names)
                else:
                    self.required_features = self.EXPECTED_FEATURES

                # Check if classes are binary [0, 1]
                classes = getattr(self.model, "classes_", None)
                if classes is None and hasattr(self.model, "named_steps"):
                    last_step = list(self.model.named_steps.values())[-1]
                    classes = getattr(last_step, "classes_", None)

                self.is_binary_gatekeeper = (classes is not None and len(classes) == 2)

                print(
                    f"[VerifyMesh ML] Loaded model from: {self.model_path} "
                    f"({'Binary Gatekeeper (Eligible / Not Eligible)' if self.is_binary_gatekeeper else 'Multi-Class Legacy'}, "
                    f"{len(self.required_features)} features)"
                )
                return True
            else:
                print(f"[VerifyMesh ML] Warning: Model file not found at: {self.model_path}")
                return False
        except Exception as e:
            print(f"[VerifyMesh ML] Failed to load model: {e}")
            return False

    def get_info(self) -> dict:
        """Returns metadata regarding active model load status."""
        if self.model is None:
            self.load_model()
        return {
            "model_loaded": self.model is not None,
            "model_file": os.path.basename(self.model_path) if self.model else "None",
            "model_path": self.model_path if self.model else "None",
            "features_count": len(self.required_features),
            "feature_count": len(self.required_features),
            "classes": ["Not Eligible", "Eligible"] if self.is_binary_gatekeeper else [str(c) for c in getattr(self.model, "classes_", [])],
            "is_binary_gatekeeper": self.is_binary_gatekeeper,
            "model_version": "2.0.0" if self.is_binary_gatekeeper else "1.0.0"
        }

    def predict(self, feature_data: dict) -> dict:
        """
        Validates input keys, performs automated feature engineering (certified_leverage,
        total_experience_months, subscore aggregations), converts to DataFrame in exact expected order,
        and returns clean binary predictions alongside class probabilities.
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError(f"ML model is not loaded or unavailable at '{self.model_path}'.")

        # 1. Validate that all 10 raw features are present in input
        missing_raw = [f for f in self.RAW_FEATURES if f not in feature_data]
        if missing_raw:
            raise ValueError(f"Missing required feature keys: {missing_raw}")

        # 2. Validate and convert raw metrics to numeric float values
        processed = {}
        for f in self.RAW_FEATURES:
            val = feature_data[f]
            try:
                processed[f] = float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Feature '{f}' must be a numeric value, got: {val!r}")

        # 3. Derive certified_leverage if not explicitly provided:
        # certified_leverage = certification_count * (1 + relevant_certification)
        if "certified_leverage" in feature_data and feature_data["certified_leverage"] is not None:
            try:
                processed["certified_leverage"] = float(feature_data["certified_leverage"])
            except (ValueError, TypeError):
                raise ValueError(f"Feature 'certified_leverage' must be numeric, got: {feature_data['certified_leverage']!r}")
        else:
            cert_count = processed["certification_count"]
            rel_cert = processed["relevant_certification"]
            processed["certified_leverage"] = cert_count * (1.0 + rel_cert)

        # 4. Derive 15-feature engineered metrics if expected by the pipeline
        if len(self.required_features) == 15 or "total_experience_months" in self.required_features:
            processed["total_experience_months"] = (
                processed["previous_experience_months"] +
                processed["sales_experience_months"] +
                processed["customer_service_experience_months"]
            )
            score_vals = [
                processed["assessment_score"],
                processed["communication_score"],
                processed["product_knowledge_score"],
                processed["sales_skill_score"],
                processed["customer_service_score"]
            ]
            processed["mean_score"] = float(np.mean(score_vals))
            processed["min_score"] = float(np.min(score_vals))
            processed["max_score"] = float(np.max(score_vals))

        # 5. Build DataFrame in the exact feature column order expected by the estimator
        df = pd.DataFrame([{f: processed[f] for f in self.required_features}])

        # 6. Predict using Binary Gatekeeper or Legacy Multi-class
        if self.is_binary_gatekeeper:
            probabilities = self.model.predict_proba(df)[0]
            # classes_ are [0, 1] -> [P(Not Eligible), P(Eligible)]
            p_not_eligible = float(probabilities[0])
            p_eligible = float(probabilities[1])

            # Direct binary classification at standard 0.5 decision boundary
            if p_eligible >= 0.5:
                prediction_label = "Eligible"
                decision_code = 1
                confidence = p_eligible
            else:
                prediction_label = "Not Eligible"
                decision_code = 0
                confidence = p_not_eligible

            class_probs = {
                "Not Eligible": round(p_not_eligible, 4),
                "Eligible": round(p_eligible, 4),
            }

            return {
                "prediction": prediction_label,          # "Eligible" | "Not Eligible"
                "decision_code": decision_code,           # 1 | 0
                "decision": str(decision_code),           # "1" | "0"
                "confidence": round(confidence, 4),       # Continuous probability of chosen class
                "p_eligible": round(p_eligible, 4),       # P(Eligible)
                "p_not_eligible": round(p_not_eligible, 4), # P(Not Eligible)
                "probabilities": class_probs,
                "is_binary_gatekeeper": True
            }

        else:
            # Fallback legacy 3-class model if explicitly configured
            prediction = self.model.predict(df)[0]
            probabilities = self.model.predict_proba(df)[0]

            class_probs = {
                str(cls): float(prob)
                for cls, prob in zip(self.model.classes_, probabilities)
            }

            max_confidence = float(np.max(probabilities))

            return {
                "prediction": "Eligible" if str(prediction) == "2" else ("Ineligible" if str(prediction) == "0" else "Send to Review"),
                "decision": str(prediction),
                "decision_code": int(prediction) if str(prediction).isdigit() else 0,
                "confidence": max_confidence,
                "probabilities": class_probs,
                "is_binary_gatekeeper": False
            }


# Backward-compatibility alias
ThreeWayDecisionInference = BinaryEligibilityInference

# Global singleton instance exported for application routes
inference_engine = BinaryEligibilityInference()