import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.auth_routes import auth_bp
from backend.competency_routes import competency_bp
from backend.db import check_mysql_status
from src.inference import inference_engine
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS for frontend Vite development & production hosts
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize Google Colab model once at startup
    model_loaded = inference_engine.load_model()
    app.logger.info(f"[VerifyMesh ML] Startup model initialization: {'SUCCESS' if model_loaded else 'PENDING'}")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(competency_bp)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        mysql_ready = check_mysql_status()
        model_info = inference_engine.get_info()
        return jsonify({
            "status": "healthy",
            "service": "VerifyMesh API",
            "version": "1.0.0",
            "database": {
                "engine": "MySQL",
                "connected": mysql_ready,
                "mode": "MySQL Database" if mysql_ready else "Development Fallback Store"
            },
            "machine_learning": {
                "source": "Google Colab",
                "role": "Inference & Prediction",
                "model_loaded": model_info["model_loaded"],
                "active_model": model_info["model_file"]
            }
        }), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    print(f"Starting VerifyMesh API server on http://127.0.0.1:{port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
