import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.auth_routes import auth_bp
from backend.competency_routes import competency_bp
from backend.admin_routes import admin_bp
from backend.platform_admin_routes import platform_admin_bp
from backend.db import check_mysql_status


def create_app(config_class=Config):
    # Validate critical security configuration on startup unless in testing mode
    if not getattr(config_class, 'TESTING', False):
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Restrict CORS to explicitly configured trusted origins. Never allow wildcard with credentials.
    trusted_origins = [orig for orig in config_class.CORS_ORIGINS if orig != '*']
    if not trusted_origins:
        trusted_origins = ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000']

    CORS(app, resources={r"/api/*": {"origins": trusted_origins}}, supports_credentials=True)

    # Deterministic eligibility engine active; binary ML gatekeeper retired
    app.logger.info("[VerifyMesh Engine] Deterministic Eligibility Engine: ACTIVE (Binary ML Gatekeeper Retired)")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(competency_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(platform_admin_bp)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        mysql_ready = check_mysql_status()
        from src.task_suitability_inference import task_suitability_engine
        model_info = task_suitability_engine.get_info()
        return jsonify({
            "status": "healthy" if mysql_ready else "degraded",
            "service": "VerifyMesh API",
            "version": "2.0.0",
            "database": {
                "engine": "MySQL",
                "connected": mysql_ready,
                "mode": "MySQL Database" if mysql_ready else "Unavailable"
            },
            "machine_learning": {
                "source": "VerifyMesh Stage 2 Task Suitability Predictor v3",
                "role": model_info.get("role", "Task-Specific Suitability Prediction"),
                "eligibility_engine": model_info.get("eligibility_engine", "Deterministic Server-Side Rules"),
                "active_model": model_info.get("model_file", "verifymesh_stage2_suitability_pipeline_v3.joblib"),
                "model_name": model_info.get("model_name", "VerifyMesh_Stage2_Suitability_LR_v3"),
                "model_version": model_info.get("model_version", "3.0.0"),
                "model_sha256": model_info.get("model_sha256"),
                "features_count": model_info.get("features_count", 5),
                "decision_threshold": model_info.get("decision_threshold", 0.60),
                "model_loaded": model_info.get("model_loaded", True),
                "binary_gatekeeper_status": "Retired",
                "synthetic_data_disclaimer": model_info.get("synthetic_data_disclaimer")
            }
        }), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"success": False, "error": "Too many requests. Please try again later."}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Internal server error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', 5000))
    # Never default to debug=True. Strict production default.
    debug_mode = Config.DEBUG
    print(f"Starting VerifyMesh API server on http://{host}:{port} (debug={debug_mode})...")
    app.run(host=host, port=port, debug=debug_mode)
