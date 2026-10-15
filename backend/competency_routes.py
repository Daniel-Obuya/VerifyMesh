from flask import Blueprint, request, jsonify
from src.inference import inference_engine
from backend.auth_routes import decode_auth_token
from backend.db import save_agent_assessment, get_agent_assessment, reset_agent_assessment

competency_bp = Blueprint("competency", __name__, url_prefix="/api/competency")


def get_authenticated_agent():
    """
    Verify the Bearer token and enforce the Agent role.
    Returns (user_id, role, None) on success.
    Returns (None, None, (response, http_code)) on failure.
    Accepts both raw DB role 'AGENT' and normalised 'Agent'.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None, (
            jsonify({"success": False, "error": "Authorization token required."}), 401
        )
    token = auth_header[len("Bearer "):]
    payload = decode_auth_token(token)
    if not payload:
        return None, None, (
            jsonify({"success": False, "error": "Invalid or expired token."}), 401
        )
    role = payload.get("role", "")
    if role not in ("AGENT", "Agent"):
        return None, None, (
            jsonify({"success": False, "error": "Agent role required."}), 403
        )
    user_id = payload.get("uid")
    if not user_id:
        return None, None, (
            jsonify({"success": False, "error": "Malformed token: missing uid."}), 401
        )
    return user_id, role, None


@competency_bp.route("/evaluate", methods=["POST"])
def evaluate_eligibility():
    """
    Evaluate agent eligibility using the 11-feature ML model and persist the result.

    Authentication: Bearer token required; Agent role enforced server-side.
    Any user_id or agent_id in the request body is silently ignored.
    The assessment result, model prediction, and audit event are saved in a
    single transaction; the endpoint returns 500 if persistence fails.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload provided"}), 400

    # Strip any client-supplied identity fields — never trust them
    data.pop("user_id", None)
    data.pop("agent_id", None)

    try:
        result = inference_engine.predict(data)
    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred during inference", "details": str(e)}), 500

    competency_label = result.get("prediction", "Ineligible")
    confidence = result.get("confidence", 0.0)
    prediction_data = {
        "decision": result.get("decision"),
        "prediction": competency_label,
        "predicted_competency": competency_label,
        "confidence": confidence,
        "probabilities": result.get("probabilities", {}),
    }

    try:
        saved = save_agent_assessment(
            user_id=user_id,
            assessment_data=dict(data),
            competency_level=competency_label,
            confidence=confidence,
            prediction_data=prediction_data,
        )
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 422
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 500

    return jsonify({
        "status": "success",
        "data": {
            "decision": result["decision"],
            "confidence": confidence,
            "probabilities": result.get("probabilities", {}),
        },
        "saved": {
            "attempt_number": saved["attempt_number"],
            "exam_result_id": saved["exam_result_id"],
            "prediction_id": saved["prediction_id"],
        },
    }), 200


@competency_bp.route("/agent-status", methods=["GET"])
def agent_status():
    """
    Return the latest persisted competency assessment for the authenticated agent.
    User identity comes from the Bearer token only; any query-string user_id is ignored.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    rec = get_agent_assessment(user_id)
    if not rec:
        return jsonify({"success": True, "has_assessed": False}), 200

    return jsonify({
        "success": True,
        "has_assessed": True,
        "competency_level": rec.get("competency_level"),
        "confidence": rec.get("confidence"),
        "attempt_number": rec.get("attempt_number"),
        "assessment": rec.get("assessment"),
        "prediction_data": rec.get("prediction_data"),
        "completed_at": rec.get("completed_at"),
    }), 200


@competency_bp.route("/reset-assessment", methods=["POST"])
def reset_assessment():
    """
    Safe, non-destructive demo/testing reset.

    Behaviour: inserts an ASSESSMENT_RESET_REQUESTED event into audit_logs only.
    No exam_results or ml_predictions rows are deleted; full history is preserved.
    get_agent_assessment returns None for this agent until a new attempt is
    persisted after the reset timestamp.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    ok = reset_agent_assessment(user_id)
    if not ok:
        return jsonify({"success": False, "error": "Failed to log reset event."}), 500

    return jsonify({
        "success": True,
        "message": (
            "Reset logged. Assessment history is preserved. "
            "Submit a new assessment to update your competency record."
        ),
    }), 200