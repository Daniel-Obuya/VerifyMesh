"""
VerifyMesh - Competency Prediction REST API Routes
Integrates Flask with the preloaded Google Colab Random Forest Model.
"""

from flask import Blueprint, request, jsonify
from src.inference import inference_engine
from backend.auth_routes import decode_auth_token
from backend.db import get_agent_assessment, save_agent_assessment, reset_agent_assessment

competency_bp = Blueprint('competency', __name__, url_prefix='/api/competency')

@competency_bp.route('/predict', methods=['POST'])
def predict_competency():
    """
    Run real-time inference on agent assessment and experience data
    using the final Google Colab Random Forest model.
    Persists assessment to agent profile if user is authenticated.
    """
    data = request.get_json(silent=True) or {}
    
    if not data:
        return jsonify({
            "success": False,
            "error": "Request body must be a valid JSON object containing agent features."
        }), 400

    result = inference_engine.predict(data)
    
    # Check if user is authenticated or user_id provided
    user_id = data.get("user_id")
    if not user_id:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else None
        if token:
            payload = decode_auth_token(token)
            if payload:
                user_id = payload.get("uid")

    if user_id and result.get("success"):
        comp_level = result.get("predicted_competency") or result.get("prediction")
        conf = result.get("confidence")
        save_agent_assessment(user_id, data, comp_level, conf, prediction_data=result)
        result["saved_to_profile"] = True
        result["user_id"] = user_id

    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@competency_bp.route('/agent-status', methods=['GET'])
def get_agent_status():
    """
    Return whether the current agent has completed an assessment,
    along with their verified competency level and assessment history.
    """
    user_id = request.args.get('user_id')
    if not user_id:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else None
        if token:
            payload = decode_auth_token(token)
            if payload:
                user_id = payload.get("uid")

    if not user_id:
        return jsonify({
            "success": True,
            "has_assessed": False,
            "competency_level": None,
            "confidence": None,
            "assessment": None
        }), 200

    record = get_agent_assessment(user_id)
    if record and record.get("competency_level"):
        return jsonify({
            "success": True,
            "has_assessed": True,
            "competency_level": record.get("competency_level"),
            "confidence": record.get("confidence"),
            "assessment": record.get("assessment"),
            "prediction_data": record.get("prediction_data")
        }), 200

    return jsonify({
        "success": True,
        "has_assessed": False,
        "competency_level": None,
        "confidence": None,
        "assessment": None
    }), 200

@competency_bp.route('/reset-assessment', methods=['POST'])
def reset_assessment():
    """Reset agent back to unassessed state for testing/demoing."""
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else None
        if token:
            payload = decode_auth_token(token)
            if payload:
                user_id = payload.get("uid")

    if user_id:
        reset_agent_assessment(user_id)
        return jsonify({"success": True, "message": "Agent assessment reset to unassessed state."}), 200

    return jsonify({"success": False, "error": "User identification required."}), 400

@competency_bp.route('/model-info', methods=['GET'])
def get_model_info():
    """Return status and metadata of the active Google Colab model."""
    info = inference_engine.get_info()
    return jsonify({
        "success": True,
        "info": info
    }), 200

@competency_bp.route('/sample-inputs', methods=['GET'])
def get_sample_inputs():
    """Return pre-configured sample inputs for rapid demonstration and validation."""
    samples = {
        "competent_agent": {
            "previous_experience_months": 24,
            "sales_experience_months": 18,
            "customer_service_experience_months": 12,
            "certification_count": 2,
            "relevant_certification": 1,
            "assessment_score": 78.5,
            "communication_score": 82.0,
            "product_knowledge_score": 79.0,
            "sales_skill_score": 80.0,
            "customer_service_score": 85.0
        },
        "advanced_agent": {
            "previous_experience_months": 48,
            "sales_experience_months": 36,
            "customer_service_experience_months": 24,
            "certification_count": 4,
            "relevant_certification": 1,
            "assessment_score": 92.0,
            "communication_score": 94.0,
            "product_knowledge_score": 90.0,
            "sales_skill_score": 95.0,
            "customer_service_score": 93.0
        },
        "needs_improvement": {
            "previous_experience_months": 3,
            "sales_experience_months": 2,
            "customer_service_experience_months": 1,
            "certification_count": 0,
            "relevant_certification": 0,
            "assessment_score": 48.0,
            "communication_score": 52.0,
            "product_knowledge_score": 45.0,
            "sales_skill_score": 46.0,
            "customer_service_score": 50.0
        }
    }
    return jsonify({
        "success": True,
        "samples": samples
    }), 200
