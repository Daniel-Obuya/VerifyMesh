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
from backend.db import check_mysql_status
from src.inference import inference_engine


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

    # Initialize ML model at startup
    model_loaded = inference_engine.load_model()
    app.logger.info(f"[VerifyMesh ML] Startup model initialization: {'SUCCESS' if model_loaded else 'PENDING'}")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(competency_bp)
    app.register_blueprint(admin_bp)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        mysql_ready = check_mysql_status()
        model_info = inference_engine.get_info()
        return jsonify({
            "status": "healthy" if mysql_ready else "degraded",
            "service": "VerifyMesh API",
            "version": "1.0.0",
            "database": {
                "engine": "MySQL",
                "connected": mysql_ready,
                "mode": "MySQL Database" if mysql_ready else "Unavailable"
            },
            "machine_learning": {
                "source": "Google Colab",
                "role": "Inference & Prediction",
                "model_loaded": model_info.get("model_loaded", False),
                "active_model": model_info.get("model_file")
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
