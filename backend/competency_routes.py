from flask import Blueprint, request, jsonify
from src.inference import inference_engine
from backend.auth_routes import decode_auth_token
from backend.db import (
    save_agent_assessment, 
    get_agent_assessment, 
    reset_agent_assessment,
    get_agent_tasks_with_eligibility,
    apply_for_task,
    get_agent_recent_activities,
    COMPETENCY_ENUM_TO_LABEL,
    DECISION_TO_ENUM,
    DECISION_TO_LABEL,
    get_agent_profile_data,
    update_agent_profile,
    get_agent_experiences,
    create_agent_experience,
    delete_agent_experience,
    get_agent_certifications_list,
    create_agent_certification,
    delete_agent_certification,
    calculate_agent_verified_experience,
    calculate_agent_verified_certifications,
    get_mysql_connection
)

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
    if data is None:
        data = {}

    # Strip any client-supplied identity fields — never trust them
    data.pop("user_id", None)
    data.pop("agent_id", None)

    # If subscores are not provided, populate from agent's latest assessment battery
    existing_assessment = get_agent_assessment(user_id)
    existing_scores = existing_assessment.get("assessment", {}) if existing_assessment else {}
    for score_key in [
        "assessment_score",
        "communication_score",
        "product_knowledge_score",
        "sales_skill_score",
        "customer_service_score",
    ]:
        if score_key not in data:
            data[score_key] = float(existing_scores.get(score_key, 75.0))

    # Reconcile profile features with authoritative verified database records
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT agent_id FROM agents WHERE user_id = %s", (user_id,))
                ag_row = cur.fetchone()
                if ag_row:
                    ag_id = ag_row["agent_id"]
                    v_exp = calculate_agent_verified_experience(ag_id, cur)
                    v_cert = calculate_agent_verified_certifications(ag_id, cur)
                    if v_exp.get("verified_entries_count", 0) > 0:
                        data["previous_experience_months"] = float(v_exp["previous_experience_months"])
                        data["sales_experience_months"] = float(v_exp["sales_experience_months"])
                        data["customer_service_experience_months"] = float(v_exp["customer_service_experience_months"])
                    data["certification_count"] = float(v_cert["certification_count"])
                    data["relevant_certification"] = float(v_cert["relevant_certification"])
        finally:
            conn.close()

    try:
        result = inference_engine.predict(data)
    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": "An error occurred during inference", "details": str(e)}), 500

    raw_decision = str(result.get("decision", "0"))
    predicted_enum = DECISION_TO_ENUM.get(raw_decision, "NEEDS_IMPROVEMENT")
    
    # Check if high performance merits Advanced tier
    score = float(data.get("assessment_score", 0.0))
    exp_m = float(data.get("previous_experience_months", 0.0))
    if raw_decision == "2" and score >= 88.0 and exp_m >= 18.0:
        predicted_enum = "ADVANCED"

    competency_label = COMPETENCY_ENUM_TO_LABEL.get(predicted_enum, "Competent")
    decision_label = DECISION_TO_LABEL.get(raw_decision, "Eligible")
    confidence = result.get("confidence", 0.0)

    prediction_data = {
        "decision": raw_decision,
        "prediction": competency_label,
        "predicted_competency": competency_label,
        "evaluation_decision": decision_label,
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
            "decision": raw_decision,
            "competency_level": competency_label,
            "evaluation_decision": decision_label,
            "confidence": confidence,
            "probabilities": result.get("probabilities", {}),
        },
        "feature_vector": dict(data),
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
        return jsonify({
            "success": True, 
            "has_assessed": False,
            "competency_level": "Not Yet Assessed",
            "evaluation_decision": "Not Yet Evaluated",
            "confidence": None,
            "completed_at": None,
        }), 200

    return jsonify({
        "success": True,
        "has_assessed": True,
        "competency_level": rec.get("competency_level", "Competent"),
        "evaluation_decision": rec.get("evaluation_decision", "Eligible"),
        "confidence": rec.get("confidence"),
        "attempt_number": rec.get("attempt_number"),
        "assessment": rec.get("assessment"),
        "prediction_data": rec.get("prediction_data"),
        "completed_at": rec.get("completed_at"),
    }), 200


@competency_bp.route("/tasks", methods=["GET"])
def agent_tasks():
    """
    Return all active tasks with server-calculated eligibility and application statuses
    for the authenticated agent based on actual database records.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    try:
        tasks = get_agent_tasks_with_eligibility(user_id)
        rec = get_agent_assessment(user_id)
        overall_comp = rec.get("competency_level", "Not Yet Assessed") if rec else "Not Yet Assessed"
        overall_decision = rec.get("evaluation_decision", "Not Yet Evaluated") if rec else "Not Yet Evaluated"

        return jsonify({
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
            "competency_level": overall_comp,
            "evaluation_decision": overall_decision
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@competency_bp.route("/tasks/<int:task_id>/apply", methods=["POST"])
def apply_task(task_id):
    """
    Submit an application for a task after server-side validation.
    Enforces that all mandatory certifications, evaluations, and prerequisites are met.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    notes = payload.get("notes")

    try:
        res = apply_for_task(user_id, task_id, notes=notes)
        return jsonify({
            "success": True,
            "message": "Application submitted successfully.",
            "data": res
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"success": False, "error": str(re)}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to submit application: {str(e)}"}), 500


@competency_bp.route("/activities", methods=["GET"])
def agent_activities():
    """Return genuine chronological activity records for the authenticated agent."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    try:
        activities = get_agent_recent_activities(user_id)
        return jsonify({
            "success": True,
            "activities": activities
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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


# =====================================================================
# AGENT PROFILE MANAGEMENT
# =====================================================================

@competency_bp.route("/profile", methods=["GET"])
def agent_profile():
    """Retrieve verified profile information for the authenticated agent."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    profile = get_agent_profile_data(user_id)
    if not profile:
        return jsonify({"success": False, "error": "Agent profile not found."}), 404

    return jsonify({"success": True, "data": profile}), 200


@competency_bp.route("/profile", methods=["PUT"])
def update_profile():
    """Update editable personal details for the authenticated agent."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    try:
        update_agent_profile(user_id, payload)
        updated = get_agent_profile_data(user_id)
        return jsonify({
            "success": True,
            "message": "Profile updated successfully.",
            "data": updated
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to update profile: {str(e)}"}), 500


# =====================================================================
# WORK HISTORY / EXPERIENCE
# =====================================================================

@competency_bp.route("/experiences", methods=["GET"])
def agent_experiences():
    """List all work-history entries for the authenticated agent."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    experiences = get_agent_experiences(user_id)
    return jsonify({"success": True, "data": experiences, "count": len(experiences)}), 200


@competency_bp.route("/experiences", methods=["POST"])
def add_experience():
    """Submit a new work-history entry for verification."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    try:
        res = create_agent_experience(user_id, payload)
        return jsonify({
            "success": True,
            "message": "Work experience submitted for verification.",
            "data": res
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to submit experience: {str(e)}"}), 500


@competency_bp.route("/experiences/<int:experience_id>", methods=["DELETE"])
def remove_experience(experience_id):
    """Withdraw or delete a pending/rejected work-history entry."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    try:
        delete_agent_experience(user_id, experience_id)
        return jsonify({"success": True, "message": "Experience entry removed successfully."}), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to remove experience: {str(e)}"}), 500


# =====================================================================
# CERTIFICATIONS
# =====================================================================

@competency_bp.route("/certifications", methods=["GET"])
def agent_certifications():
    """List all submitted certifications for the authenticated agent."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    certs = get_agent_certifications_list(user_id)
    return jsonify({"success": True, "data": certs, "count": len(certs)}), 200


@competency_bp.route("/certifications", methods=["POST"])
def add_certification():
    """Submit a new certification for verification."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    try:
        res = create_agent_certification(user_id, payload)
        return jsonify({
            "success": True,
            "message": "Certification submitted for verification.",
            "data": res
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to submit certification: {str(e)}"}), 500


@competency_bp.route("/certifications/<int:cert_id>", methods=["DELETE"])
def remove_certification(cert_id):
    """Withdraw or delete a pending/rejected certification."""
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    try:
        delete_agent_certification(user_id, cert_id)
        return jsonify({"success": True, "message": "Certification removed successfully."}), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to remove certification: {str(e)}"}), 500