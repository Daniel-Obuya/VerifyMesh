import os
import joblib
import pandas as pd
import numpy as np

class ThreeWayDecisionInference:
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

    def __init__(self, model_filename="threeway_decision_model.joblib"):
        self.model_filename = model_filename
        
        # Calculate absolute paths relative to project layout
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Priority search paths: backend/models/ -> project root -> src/ -> models/ -> direct relative
        candidate_paths = [
            os.path.join(base_dir, "backend", "models", model_filename),
            os.path.join(base_dir, model_filename),
            os.path.join(base_dir, "src", model_filename),
            os.path.join(base_dir, "models", model_filename),
            os.path.abspath(model_filename),
        ]

        self.model_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
        self.model = None

    def load_model(self) -> bool:
        """Loads the serialized joblib model if present."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print(f"[VerifyMesh ML] Successfully loaded model from: {self.model_path}")
                return True
            else:
                print(f"[VerifyMesh ML] Warning: Model file not found at: {self.model_path}")
                return False
        except Exception as e:
            print(f"[VerifyMesh ML] Failed to load model: {e}")
            return False

    def get_info(self) -> dict:
        """Returns metadata regarding model load status."""
        return {
            "model_loaded": self.model is not None,
            "model_file": os.path.basename(self.model_path) if self.model else "None",
            "features_count": len(self.EXPECTED_FEATURES)
        }

    def predict(self, feature_data: dict) -> dict:
        """
        Validates input keys, derives certified_leverage if missing using the confirmed formula,
        converts to DataFrame in model expected order, and returns predictions alongside class probabilities.
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError(f"ML model is not loaded or unavailable at '{self.model_path}'.")

        # Validate that all 10 raw features are present in input
        missing_raw = [f for f in self.RAW_FEATURES if f not in feature_data]
        if missing_raw:
            raise ValueError(f"Missing required feature keys: {missing_raw}")

        # Validate and convert raw metrics to numeric float values
        processed = {}
        for f in self.RAW_FEATURES:
            val = feature_data[f]
            try:
                processed[f] = float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Feature '{f}' must be a numeric value, got: {val!r}")

        # Derive certified_leverage if not explicitly provided using confirmed formula:
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

        # Build DataFrame with exactly the 11 expected features in exact expected order
        df = pd.DataFrame([{f: processed[f] for f in self.EXPECTED_FEATURES}])

        prediction = self.model.predict(df)[0]
        probabilities = self.model.predict_proba(df)[0]

        class_probs = {
            str(cls): float(prob) 
            for cls, prob in zip(self.model.classes_, probabilities)
        }

        max_confidence = float(np.max(probabilities))

        return {
            "decision": str(prediction),
            "confidence": max_confidence,
            "probabilities": class_probs
        }

# Global singleton instance exported for application routes
inference_engine = ThreeWayDecisionInference()