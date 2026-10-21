import json
import logging
import math
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.inference import inference_engine
from backend.auth_routes import decode_auth_token
from backend.db import (
    find_user_by_id,
    normalize_role,
    save_agent_assessment, 
    get_agent_assessment, 
    reset_agent_assessment,
    get_agent_tasks_with_eligibility,
    apply_for_task,
    get_agent_recent_activities,
    COMPETENCY_ENUM_TO_LABEL,
    COMPETENCY_LABEL_TO_ENUM,
    DECISION_TO_ENUM,
    DECISION_TO_LABEL,
    ENUM_TO_DECISION,
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
    get_mysql_connection,
    create_assessment_attempt,
    get_assessment_attempt,
    get_agent_active_attempt,
    check_agent_assessment_cooldown,
    finalize_assessment_attempt,
    CooldownActiveError,
    save_agent_topic_result,
    get_assessment_topics_list,
    get_assessment_topic_by_id,
    get_topic_questions
)

logger = logging.getLogger("verifymesh.competency")

competency_bp = Blueprint("competency", __name__, url_prefix="/api/competency")

FORBIDDEN_PROTECTED_FEATURES = {
    "assessment_score",
    "communication_score",
    "product_knowledge_score",
    "sales_skill_score",
    "customer_service_score",
    "previous_experience_months",
    "sales_experience_months",
    "customer_service_experience_months",
    "certification_count",
    "relevant_certification",
    "certified_leverage",
}



def get_authenticated_agent():
    """
    Verify the Bearer token, check active account status, and enforce
    the Agent role against the live MySQL database on every request.
    Returns (user_id, role, None) on success.
    Returns (None, None, (response, http_code)) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None, (
            jsonify({"success": False, "error": "Authorization token required."}), 401
        )
    token = auth_header[len("Bearer "):].strip()
    payload = decode_auth_token(token)
    if not payload:
        return None, None, (
            jsonify({"success": False, "error": "Invalid or expired token."}), 401
        )

    user_id = payload.get("uid")
    if not user_id:
        return None, None, (
            jsonify({"success": False, "error": "Malformed token: missing uid."}), 401
        )

    user, db_err = find_user_by_id(user_id)
    if db_err:
        return None, None, (
            jsonify({"success": False, "error": "Database service is currently unavailable."}), 503
        )
    if not user:
        return None, None, (
            jsonify({"success": False, "error": "User account no longer exists or session is invalid."}), 401
        )

    if not user.get("is_active", True):
        return None, None, (
            jsonify({"success": False, "error": "Account is inactive or suspended. Please contact your administrator."}), 403
        )

    canonical_role = normalize_role(user.get("role", ""))
    if canonical_role not in ("Agent", "AGENT"):
        return None, None, (
            jsonify({"success": False, "error": "Agent role required."}), 403
        )

    return user_id, canonical_role, None


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

    payload = request.get_json(silent=True) or {}

    # Reject client-supplied protected features / scores (Requirement 8)
    supplied_forbidden = [k for k in payload.keys() if k in FORBIDDEN_PROTECTED_FEATURES]
    if supplied_forbidden:
        return jsonify({
            "success": False,
            "error": f"Client-supplied assessment scores or protected model features are strictly forbidden: {', '.join(supplied_forbidden)}. Scores are calculated server-side only."
        }), 400

    # Retrieve authoritative assessment from database
    existing_assessment = get_agent_assessment(user_id)
    if not existing_assessment or not existing_assessment.get("assessment"):
        return jsonify({
            "success": False,
            "error": "No verified assessment found. You must complete an authoritative scenario assessment first."
        }), 400

    existing_scores = existing_assessment.get("assessment", {})
    data = {}
    for score_key in [
        "assessment_score",
        "communication_score",
        "product_knowledge_score",
        "sales_skill_score",
        "customer_service_score",
    ]:
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

    prediction_label = result.get("prediction", "Eligible" if str(result.get("decision", "0")) == "1" else "Not Eligible")
    decision_code = int(result.get("decision_code", 1 if prediction_label == "Eligible" else 0))
    raw_decision = str(decision_code)
    predicted_enum = "ELIGIBLE" if prediction_label == "Eligible" else "NOT_ELIGIBLE"
    confidence = float(result.get("confidence", 0.0))
    p_eligible = float(result.get("p_eligible", confidence if prediction_label == "Eligible" else 1.0 - confidence))
    p_not_eligible = float(result.get("p_not_eligible", 1.0 - p_eligible))

    competency_label = prediction_label
    decision_label = prediction_label

    prediction_data = {
        "decision": raw_decision,
        "decision_code": decision_code,
        "predicted_enum": predicted_enum,
        "prediction": competency_label,
        "predicted_competency": competency_label,
        "competency_status": competency_label,
        "evaluation_decision": decision_label,
        "is_eligible": prediction_label == "Eligible",
        "confidence": round(confidence * 100 if confidence <= 1.0 else confidence, 1),
        "p_eligible": p_eligible,
        "p_not_eligible": p_not_eligible,
        "probabilities": {
            "Eligible": round(p_eligible * 100, 1),
            "Not Eligible": round(p_not_eligible * 100, 1)
        },
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


# =====================================================================
# DYNAMIC TASK-DRIVEN EXAMS & MODEL METADATA
# =====================================================================

@competency_bp.route("/model-info", methods=["GET"])
def get_model_info():
    """Return runtime metadata about the active ML inference model."""
    info = inference_engine.get_info()
    return jsonify({
        "success": True,
        "data": {
            "model_loaded": info.get("model_loaded"),
            "model_file": info.get("model_file"),
            "features_count": info.get("features_count", 11),
            "expected_features": inference_engine.EXPECTED_FEATURES,
            "classes": (
                ["Not Eligible (0)", "Eligible (1)"]
                if info.get("is_binary_gatekeeper", False)
                else ["Needs Improvement (0)", "Basic (1)", "Competent / Advanced (2)"]
            )
        }
    }), 200


@competency_bp.route("/sample-inputs", methods=["GET"])
def get_sample_inputs():
    """Return pre-configured sample profile inputs for simulation and testing."""
    return jsonify({
        "success": True,
        "data": {
            "competent": {
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
            "advanced": {
                "previous_experience_months": 48,
                "sales_experience_months": 36,
                "customer_service_experience_months": 24,
                "certification_count": 4,
                "relevant_certification": 1,
                "assessment_score": 93.5,
                "communication_score": 95.0,
                "product_knowledge_score": 92.0,
                "sales_skill_score": 94.0,
                "customer_service_score": 96.0
            },
            "basic": {
                "previous_experience_months": 6,
                "sales_experience_months": 2,
                "customer_service_experience_months": 4,
                "certification_count": 0,
                "relevant_certification": 0,
                "assessment_score": 58.0,
                "communication_score": 60.0,
                "product_knowledge_score": 55.0,
                "sales_skill_score": 50.0,
                "customer_service_score": 56.0
            }
        }
    }), 200


@competency_bp.route("/exams/<int:exam_id>/questions", methods=["GET"])
def get_exam_questions(exam_id):
    """
    Fetch questions and options for a specific exam template from MySQL.
    Omits correct_answer and scoring logic to prevent client-side inspection.
    Includes active or auto-initiated attempt details.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag = cursor.fetchone()
            if not ag:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag["agent_id"]

            cursor.execute("""
                SELECT e.exam_id, e.exam_name, e.description, e.passing_score, e.category_id, c.category_name
                FROM exams e
                JOIN categories c ON e.category_id = c.category_id
                WHERE e.exam_id = %s AND e.status = 'ACTIVE'
                LIMIT 1
            """, (exam_id,))
            exam = cursor.fetchone()
            if not exam:
                return jsonify({"success": False, "error": f"Active exam {exam_id} not found."}), 404

            cursor.execute("""
                SELECT question_id, question_text, question_type, options_json, question_order
                FROM exam_questions
                WHERE exam_id = %s
                ORDER BY question_order ASC
            """, (exam_id,))
            raw_questions = cursor.fetchall()

            OPTION_LETTERS = ["A", "B", "C", "D"]
            questions = []
            for q in raw_questions:
                raw_opts = json.loads(q["options_json"]) if isinstance(q["options_json"], str) else (q["options_json"] or [])
                formatted_opts = []
                for idx, opt in enumerate(raw_opts):
                    opt_letter = OPTION_LETTERS[idx] if idx < len(OPTION_LETTERS) else str(idx + 1)
                    if isinstance(opt, dict):
                        formatted_opts.append({
                            "option_id": opt.get("option_id", opt_letter),
                            "text": opt.get("text", str(opt))
                        })
                    else:
                        formatted_opts.append({
                            "option_id": opt_letter,
                            "text": str(opt)
                        })
                questions.append({
                    "question_id": q["question_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "options": formatted_opts,
                    "question_order": q["question_order"]
                })

            attempt = None
            try:
                attempt = create_assessment_attempt(agent_id, exam_id)
            except CooldownActiveError:
                attempt = get_agent_active_attempt(agent_id, exam_id)
            except Exception as ae:
                logger.warning(f"Could not auto-create attempt in get_exam_questions: {ae}")

            resp_data = {
                "exam": {
                    "exam_id": exam["exam_id"],
                    "name": exam["exam_name"],
                    "description": exam["description"],
                    "category_name": exam["category_name"],
                    "passing_score": float(exam["passing_score"]),
                    "total_questions": len(questions)
                },
                "questions": questions
            }
            if attempt:
                resp_data["attempt_id"] = attempt["attempt_id"]
                resp_data["attempt_uuid"] = attempt.get("attempt_uuid")
                resp_data["attempt_number"] = attempt.get("attempt_number")
                resp_data["expires_at"] = attempt.get("expires_at")

            return jsonify({
                "success": True,
                "data": resp_data
            }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve questions: {e}")
        return jsonify({"success": False, "error": f"Failed to retrieve questions: {str(e)}"}), 500
    finally:
        conn.close()


@competency_bp.route("/exams/<int:exam_id>/start-attempt", methods=["POST"])
def start_exam_attempt(exam_id):
    """
    Explicitly initiate an authoritative assessment attempt.
    Validates agent identity, role, active account status, exam existence, and retake cooldown.
    Returns attempt_id, attempt_number, expiration timestamp, and questions.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag = cursor.fetchone()
            if not ag:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag["agent_id"]

            cursor.execute("""
                SELECT e.exam_id, e.exam_name, e.description, e.passing_score, e.category_id, c.category_name
                FROM exams e
                JOIN categories c ON e.category_id = c.category_id
                WHERE e.exam_id = %s AND e.status = 'ACTIVE'
                LIMIT 1
            """, (exam_id,))
            exam = cursor.fetchone()
            if not exam:
                return jsonify({"success": False, "error": f"Active exam {exam_id} not found."}), 404

            payload = request.get_json(silent=True) or {}
            task_id = payload.get("task_id")

            try:
                attempt = create_assessment_attempt(agent_id, exam_id, task_id)
            except CooldownActiveError as cae:
                return jsonify({
                    "success": False,
                    "error": str(cae),
                    "cooldown_remaining_seconds": cae.remaining_seconds
                }), 429

            cursor.execute("""
                SELECT question_id, question_text, question_type, options_json, question_order
                FROM exam_questions
                WHERE exam_id = %s
                ORDER BY question_order ASC
            """, (exam_id,))
            raw_questions = cursor.fetchall()

            OPTION_LETTERS = ["A", "B", "C", "D"]
            questions = []
            for q in raw_questions:
                raw_opts = json.loads(q["options_json"]) if isinstance(q["options_json"], str) else (q["options_json"] or [])
                formatted_opts = []
                for idx, opt in enumerate(raw_opts):
                    opt_letter = OPTION_LETTERS[idx] if idx < len(OPTION_LETTERS) else str(idx + 1)
                    if isinstance(opt, dict):
                        formatted_opts.append({
                            "option_id": opt.get("option_id", opt_letter),
                            "text": opt.get("text", str(opt))
                        })
                    else:
                        formatted_opts.append({
                            "option_id": opt_letter,
                            "text": str(opt)
                        })
                questions.append({
                    "question_id": q["question_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "options": formatted_opts,
                    "question_order": q["question_order"]
                })

            return jsonify({
                "success": True,
                "data": {
                    "attempt_id": attempt["attempt_id"],
                    "attempt_uuid": attempt.get("attempt_uuid"),
                    "attempt_number": attempt["attempt_number"],
                    "status": attempt["status"],
                    "started_at": attempt["started_at"],
                    "expires_at": attempt["expires_at"],
                    "exam": {
                        "exam_id": exam["exam_id"],
                        "name": exam["exam_name"],
                        "description": exam["description"],
                        "category_name": exam["category_name"],
                        "passing_score": float(exam["passing_score"]),
                        "total_questions": len(questions)
                    },
                    "questions": questions
                }
            }), 201
    except Exception as e:
        logger.error(f"Error starting assessment attempt: {e}")
        return jsonify({"success": False, "error": f"Failed to start assessment attempt: {str(e)}"}), 500
    finally:
        conn.close()


@competency_bp.route("/exams/<int:exam_id>/submit", methods=["POST"])
def submit_exam_answers(exam_id):
    """
    Score submitted exam answers server-side, reconcile verified experience and certifications,
    execute ML model prediction, persist result in assessment_attempts, exam_results and ml_predictions,
    record eligibility evaluation, and return comprehensive performance breakdown.
    Strictly validates attempt ownership, status, completeness, and rejects client-supplied scores.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}

    # 1. Reject client-supplied protected features / scores (Requirement 8)
    supplied_forbidden = [k for k in payload.keys() if k in FORBIDDEN_PROTECTED_FEATURES]
    if supplied_forbidden:
        return jsonify({
            "success": False,
            "error": f"Client-supplied assessment scores or protected model features are strictly forbidden: {', '.join(supplied_forbidden)}. Scores are calculated server-side only."
        }), 400

    answers = payload.get("answers")
    task_id = payload.get("task_id")
    attempt_id = payload.get("attempt_id")

    # 2. Resolve agent_id for authenticated user
    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag_row = cursor.fetchone()
            if not ag_row:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag_row["agent_id"]

            # If attempt_id not passed, try to resolve active in-progress attempt
            if not attempt_id:
                active_att = get_agent_active_attempt(agent_id, exam_id)
                if active_att:
                    attempt_id = active_att["attempt_id"]
                else:
                    return jsonify({
                        "success": False,
                        "error": "Valid assessment attempt_id is required for submission."
                    }), 400

            # 3. Validate Attempt Existence & Ownership (Requirements 5 & 10)
            attempt = get_assessment_attempt(attempt_id)
            if not attempt:
                return jsonify({"success": False, "error": f"Assessment attempt {attempt_id} not found."}), 404

            if attempt["agent_id"] != agent_id:
                return jsonify({"success": False, "error": "Unauthorized: assessment attempt belongs to another agent."}), 403

            if attempt["exam_id"] != exam_id:
                return jsonify({"success": False, "error": f"Attempt {attempt_id} does not match exam {exam_id}."}), 400

            # 4. Validate Attempt Status & Expiration (Requirements 5 & 10)
            if attempt["status"] == "SUBMITTED":
                return jsonify({"success": False, "error": "This assessment attempt has already been submitted and finalized."}), 409

            if attempt["status"] in ("EXPIRED", "CLOSED"):
                return jsonify({"success": False, "error": "This assessment attempt has expired or is closed."}), 400

            now = datetime.now()
            expires_at = attempt["expires_at"]
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except Exception:
                    expires_at = now
            if now > expires_at:
                cursor.execute("UPDATE assessment_attempts SET status = 'EXPIRED', updated_at = NOW() WHERE attempt_id = %s", (attempt["attempt_id"],))
                conn.commit()
                return jsonify({"success": False, "error": "This assessment attempt has expired. Please start a new attempt."}), 400

            # 5. Fetch authoritative exam record and validate configured passing threshold
            cursor.execute("""
                SELECT exam_id, exam_name, passing_score, status
                FROM exams
                WHERE exam_id = %s
                LIMIT 1
            """, (exam_id,))
            exam_record = cursor.fetchone()
            if not exam_record:
                return jsonify({"success": False, "error": f"Exam {exam_id} not found."}), 404

            raw_passing = exam_record.get("passing_score")
            if raw_passing is None:
                return jsonify({
                    "success": False,
                    "error": f"Exam {exam_id} has no configured passing score."
                }), 500

            try:
                passing_score = float(raw_passing)
                if passing_score < 0.0 or passing_score > 100.0 or math.isnan(passing_score):
                    raise ValueError(f"Passing score {passing_score} out of valid range [0, 100].")
            except (ValueError, TypeError) as pe:
                return jsonify({
                    "success": False,
                    "error": f"Exam {exam_id} has an invalid passing score configuration ({raw_passing})."
                }), 500

            # 5b. Fetch authoritative exam questions and scoring
            cursor.execute("""
                SELECT question_id, points, correct_answer, question_order, question_text, options_json
                FROM exam_questions
                WHERE exam_id = %s
                ORDER BY question_order ASC
            """, (exam_id,))
            questions = cursor.fetchall()
            if not questions:
                return jsonify({"success": False, "error": f"No questions found for exam {exam_id}"}), 404

            # 6. Validate Answers Completeness & Option IDs (Requirement 5)
            if not isinstance(answers, dict):
                return jsonify({"success": False, "error": "Answers must be a JSON object mapping question IDs to selected option IDs."}), 400

            expected_q_ids = [str(q["question_id"]) for q in questions]
            submitted_q_ids = [str(k) for k in answers.keys()]

            # Check for unknown question IDs
            invalid_q_ids = [qid for qid in submitted_q_ids if qid not in expected_q_ids]
            if invalid_q_ids:
                return jsonify({
                    "success": False,
                    "error": f"Invalid question ID(s) submitted: {invalid_q_ids}. Questions do not belong to this exam."
                }), 400

            # Check for missing answers
            missing_q_ids = [qid for qid in expected_q_ids if qid not in answers or answers[qid] is None or answers[qid] == ""]
            if missing_q_ids:
                return jsonify({
                    "success": False,
                    "error": f"Incomplete submission: missing answers for question(s) {missing_q_ids}. All questions must be answered."
                }), 400

            OPTION_LETTERS = ["A", "B", "C", "D"]
            VALID_OPTIONS_SET = {"A", "B", "C", "D", 0, 1, 2, 3, "0", "1", "2", "3"}

            total_possible_points = 0.0
            earned_points = 0.0
            question_feedback = []
            normalized_answers = {}

            # Subscore tracking
            diagnostic_points = 0.0
            diagnostic_total = 0.0
            communication_points = 0.0
            communication_total = 0.0
            triage_points = 0.0
            triage_total = 0.0

            for q in questions:
                q_id = str(q["question_id"])
                pts = float(q["points"])
                correct = q["correct_answer"].strip().upper()
                total_possible_points += pts

                raw_ans = answers.get(q_id)
                if raw_ans not in VALID_OPTIONS_SET:
                    return jsonify({
                        "success": False,
                        "error": f"Invalid option ID '{raw_ans}' for question {q_id}. Must be one of {OPTION_LETTERS}."
                    }), 400

                if isinstance(raw_ans, int) and 0 <= raw_ans < len(OPTION_LETTERS):
                    user_ans = OPTION_LETTERS[raw_ans]
                elif str(raw_ans).isdigit() and int(raw_ans) in (0, 1, 2, 3):
                    user_ans = OPTION_LETTERS[int(raw_ans)]
                else:
                    user_ans = str(raw_ans).strip().upper()

                normalized_answers[q_id] = user_ans
                is_correct = (user_ans == correct)
                if is_correct:
                    earned_points += pts

                q_order = q["question_order"]
                if q_order in (1, 2):
                    diagnostic_total += pts
                    if is_correct: diagnostic_points += pts
                elif q_order in (3, 4):
                    communication_total += pts
                    if is_correct: communication_points += pts
                else:
                    triage_total += pts
                    if is_correct: triage_points += pts

                question_feedback.append({
                    "question_id": q["question_id"],
                    "question_order": q["question_order"],
                    "is_correct": is_correct,
                    "points_earned": pts if is_correct else 0.0,
                    "max_points": pts
                })

            composite_pct = (earned_points / total_possible_points * 100.0) if total_possible_points > 0 else 0.0
            diagnostic_pct = (diagnostic_points / diagnostic_total * 100.0) if diagnostic_total > 0 else composite_pct
            communication_pct = (communication_points / communication_total * 100.0) if communication_total > 0 else composite_pct
            triage_pct = (triage_points / triage_total * 100.0) if triage_total > 0 else composite_pct

            # Determine pass/fail based on authoritative exam passing_score
            rounded_score = round(composite_pct, 2)
            rounded_passing = round(passing_score, 2)
            passed = bool(rounded_score >= rounded_passing)

            # 7. Verified DB metrics for feature vector
            v_exp = calculate_agent_verified_experience(agent_id, cursor)
            v_cert = calculate_agent_verified_certifications(agent_id, cursor)

            # Close read connection before ML inference
            cursor.close()
            conn.close()
            conn = None

            if exam_id == 1:
                feat_product = diagnostic_pct
                feat_sales = communication_pct
                feat_cs = 75.0
                feat_comm = triage_pct
            else:
                feat_product = diagnostic_pct
                feat_sales = 75.0
                feat_cs = communication_pct
                feat_comm = communication_pct

            ml_features = {
                "previous_experience_months": float(v_exp["previous_experience_months"]),
                "sales_experience_months": float(v_exp["sales_experience_months"]),
                "customer_service_experience_months": float(v_exp["customer_service_experience_months"]),
                "certification_count": float(v_cert["certification_count"]),
                "relevant_certification": float(v_cert["relevant_certification"]),
                "assessment_score": float(composite_pct),
                "communication_score": float(feat_comm),
                "product_knowledge_score": float(feat_product),
                "sales_skill_score": float(feat_sales),
                "customer_service_score": float(feat_cs),
            }

            # 8. ML prediction and canonical binary competency classification
            ml_result = inference_engine.predict(ml_features)
            prediction_label = ml_result.get("prediction", "Eligible" if str(ml_result.get("decision", "0")) == "1" else "Not Eligible")
            decision_code = int(ml_result.get("decision_code", 1 if prediction_label == "Eligible" else 0))
            raw_decision = str(decision_code)
            predicted_enum = "ELIGIBLE" if prediction_label == "Eligible" else "NOT_ELIGIBLE"
            confidence = float(ml_result.get("confidence", 0.0))
            p_eligible = float(ml_result.get("p_eligible", confidence if prediction_label == "Eligible" else 1.0 - confidence))
            p_not_eligible = float(ml_result.get("p_not_eligible", 1.0 - p_eligible))

            competency_label = prediction_label
            decision_label = prediction_label

            prediction_data = {
                "decision": raw_decision,
                "decision_code": decision_code,
                "predicted_enum": predicted_enum,
                "prediction": competency_label,
                "predicted_competency": competency_label,
                "competency_status": competency_label,
                "evaluation_decision": decision_label,
                "is_eligible": prediction_label == "Eligible",
                "confidence": confidence,
                "p_eligible": p_eligible,
                "p_not_eligible": p_not_eligible,
                "probabilities": {
                    "Eligible": round(p_eligible * 100, 1),
                    "Not Eligible": round(p_not_eligible * 100, 1)
                }
            }

            # 9. Persist assessment attempt, exam result, and prediction transactionally
            saved = save_agent_assessment(
                user_id=user_id,
                assessment_data=ml_features,
                competency_level=competency_label,
                confidence=confidence,
                prediction_data=prediction_data,
                exam_id=exam_id,
                task_id=task_id,
                attempt_id=attempt["attempt_id"]
            )

            # Record into agent_topic_results for topic qualification consistency (1-to-1 mapping)
            topic_mapping = {1: [2], 2: [1], 3: [3], 4: [4]}
            for tid in topic_mapping.get(exam_id, [exam_id]):
                try:
                    save_agent_topic_result(
                        agent_id=agent_id,
                        topic_id=tid,
                        score=round(composite_pct, 2),
                        passed=passed,
                        answers_json=normalized_answers,
                        attempt_id=attempt["attempt_id"]
                    )
                except Exception as te:
                    logger.warning(f"Could not save agent topic result: {te}")

            labeled_probs = {
                "Eligible": round(p_eligible * 100, 1),
                "Not Eligible": round(p_not_eligible * 100, 1)
            }
            conf_pct = round(confidence * 100 if confidence <= 1.0 else confidence)

            subscores_dict = {
                "diagnostics": round(diagnostic_pct, 1),
                "communication": round(communication_pct, 1),
                "triage": round(triage_pct, 1),
                "product_knowledge_score": round(diagnostic_pct, 1),
                "communication_score": round(communication_pct, 1),
                "customer_service_score": round(triage_pct, 1),
                "sales_skill_score": round(diagnostic_pct, 1)
            }

            decision_details = {
                "decision": raw_decision,
                "competency_label": competency_label,
                "decision_label": decision_label,
                "confidence": conf_pct,
                "probabilities": labeled_probs,
                "features_used": ml_features
            }

            engine_info = inference_engine.get_info()
            model_ver = engine_info.get("model_version", "1.0.0")

            finalize_assessment_attempt(
                attempt_id=attempt["attempt_id"],
                score=round(composite_pct, 2),
                passed=passed,
                answers_json=normalized_answers,
                subscores_json=subscores_dict,
                model_version=model_ver,
                exam_result_id=saved["exam_result_id"],
                prediction_id=saved["prediction_id"],
                decision_details=decision_details
            )

            return jsonify({
                "success": True,
                "data": {
                    "attempt_id": attempt["attempt_id"],
                    "attempt_uuid": attempt.get("attempt_uuid"),
                    "exam_id": exam_id,
                    "task_id": task_id,
                    "score": round(composite_pct, 1),
                    "composite_score": round(composite_pct, 1),
                    "passed": passed,
                    "passing_score": round(passing_score, 1),
                    "competency_level": competency_label,
                    "evaluation_decision": decision_label,
                    "confidence": conf_pct,
                    "probabilities": labeled_probs,
                    "prediction": {
                        "decision_label": decision_label,
                        "decision_code": int(raw_decision),
                        "competency_label": competency_label,
                        "confidence": conf_pct,
                        "probabilities": labeled_probs
                    },
                    "model_version": model_ver,
                    "subscores": subscores_dict,
                    "features_used": ml_features,
                    "feedback": question_feedback,
                    "saved": {
                        "attempt_id": attempt["attempt_id"],
                        "exam_result_id": saved["exam_result_id"],
                        "prediction_id": saved["prediction_id"],
                        "attempt_number": saved["attempt_number"]
                    }
                }
            }), 200
    except Exception as e:
        logger.error(f"Failed to submit assessment: {e}")
        return jsonify({"success": False, "error": f"Failed to submit assessment: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# =====================================================================
# ASSESSMENT TOPICS & DEDICATED ASSESSMENT PAGE ROUTES
# =====================================================================

@competency_bp.route("/topics", methods=["GET"])
def get_topics_list():
    """
    Retrieve all active assessment topics with metadata.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err
    topics = get_assessment_topics_list()
    return jsonify({
        "success": True,
        "data": topics
    }), 200


@competency_bp.route("/topics/<int:topic_id>", methods=["GET"])
def get_topic_detail(topic_id):
    """
    Fetch single topic by topic_id including reuse status for authenticated agent.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    topic = get_assessment_topic_by_id(topic_id)
    if not topic:
        return jsonify({"success": False, "error": f"Topic {topic_id} not found."}), 404

    # Check if agent already passed this topic
    conn = get_mysql_connection()
    already_passed = False
    latest_score = None
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
                ag = cursor.fetchone()
                if ag:
                    cursor.execute("""
                        SELECT score, passed, completed_at FROM agent_topic_results
                        WHERE agent_id = %s AND topic_id = %s
                        ORDER BY completed_at DESC LIMIT 1
                    """, (ag["agent_id"], topic_id))
                    atr = cursor.fetchone()
                    if atr:
                        already_passed = bool(atr["passed"])
                        latest_score = float(atr["score"])
        finally:
            conn.close()

    topic["already_passed"] = already_passed
    topic["latest_score"] = latest_score
    return jsonify({
        "success": True,
        "data": topic
    }), 200


@competency_bp.route("/topics/<int:topic_id>/questions", methods=["GET"])
def get_topic_assessment_questions(topic_id):
    """
    Fetch questions for a specific topic (omits correct_answer).
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    topic = get_assessment_topic_by_id(topic_id)
    if not topic:
        return jsonify({"success": False, "error": f"Topic {topic_id} not found."}), 404

    questions = get_topic_questions(topic_id)
    return jsonify({
        "success": True,
        "data": questions,
        "topic": topic
    }), 200


@competency_bp.route("/topics/<int:topic_id>/start-attempt", methods=["POST"])
def start_topic_attempt(topic_id):
    """
    Initiate an authoritative assessment attempt for a specific topic and optional task.
    Enforces cooldown on retakes, checks active account status.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    topic = get_assessment_topic_by_id(topic_id)
    if not topic:
        return jsonify({"success": False, "error": f"Topic {topic_id} not found."}), 404

    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id")

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag = cursor.fetchone()
            if not ag:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag["agent_id"]

            # Map topic to corresponding legacy exam_id for attempt tracking
            topic_to_exam = {1: 2, 2: 1, 3: 3, 4: 4}
            mapped_exam_id = topic_to_exam.get(topic_id, 3)

            try:
                attempt = create_assessment_attempt(agent_id, mapped_exam_id, task_id, topic_id)
            except CooldownActiveError as cae:
                return jsonify({
                    "success": False,
                    "error": str(cae),
                    "cooldown_remaining_seconds": cae.remaining_seconds
                }), 429

            questions = get_topic_questions(topic_id)

            return jsonify({
                "success": True,
                "data": {
                    "attempt_id": attempt["attempt_id"],
                    "attempt_uuid": attempt.get("attempt_uuid"),
                    "attempt_number": attempt["attempt_number"],
                    "status": attempt["status"],
                    "started_at": attempt["started_at"],
                    "expires_at": attempt["expires_at"],
                    "topic": topic,
                    "questions": questions
                }
            }), 201
    except Exception as e:
        logger.error(f"Error starting topic attempt: {e}")
        return jsonify({"success": False, "error": f"Failed to start topic attempt: {str(e)}"}), 500
    finally:
        conn.close()


@competency_bp.route("/topics/<int:topic_id>/submit", methods=["POST"])
def submit_topic_answers(topic_id):
    """
    Score submitted topic answers server-side, record in agent_topic_results,
    reconcile verified experience and certs, run ML inference with 11-feature model,
    evaluate task eligibility separately, and return comprehensive results.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    payload = request.get_json(silent=True) or {}

    # 1. Reject client-supplied protected features / scores
    supplied_forbidden = [k for k in payload.keys() if k in FORBIDDEN_PROTECTED_FEATURES]
    if supplied_forbidden:
        return jsonify({
            "success": False,
            "error": f"Client-supplied assessment scores or protected model features are strictly forbidden: {', '.join(supplied_forbidden)}. Scores are calculated server-side only."
        }), 400

    answers = payload.get("answers")
    task_id = payload.get("task_id")
    attempt_id = payload.get("attempt_id")

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag_row = cursor.fetchone()
            if not ag_row:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag_row["agent_id"]

            topic_to_exam = {1: 2, 2: 1, 3: 3, 4: 4}
            mapped_exam_id = topic_to_exam.get(topic_id, 3)

            # If attempt_id not passed, find active in-progress attempt for topic
            if not attempt_id:
                cursor.execute("""
                    SELECT * FROM assessment_attempts
                    WHERE agent_id = %s AND (topic_id = %s OR exam_id = %s) AND status = 'IN_PROGRESS'
                    ORDER BY started_at DESC LIMIT 1
                """, (agent_id, topic_id, mapped_exam_id))
                active_att = cursor.fetchone()
                if active_att:
                    attempt_id = active_att["attempt_id"]
                else:
                    return jsonify({
                        "success": False,
                        "error": "Valid assessment attempt_id is required for submission."
                    }), 400

            attempt = get_assessment_attempt(attempt_id)
            if not attempt:
                return jsonify({"success": False, "error": f"Assessment attempt {attempt_id} not found."}), 404

            if attempt["agent_id"] != agent_id:
                return jsonify({"success": False, "error": "Unauthorized: assessment attempt belongs to another agent."}), 403

            if attempt["status"] == "SUBMITTED":
                return jsonify({"success": False, "error": "This assessment attempt has already been submitted and finalized."}), 409

            if attempt["status"] in ("EXPIRED", "CLOSED"):
                return jsonify({"success": False, "error": "This assessment attempt has expired or is closed."}), 400

            now = datetime.now()
            expires_at = attempt["expires_at"]
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except Exception:
                    expires_at = now
            if now > expires_at:
                cursor.execute("UPDATE assessment_attempts SET status = 'EXPIRED', updated_at = NOW() WHERE attempt_id = %s", (attempt["attempt_id"],))
                conn.commit()
                return jsonify({"success": False, "error": "This assessment attempt has expired. Please start a new attempt."}), 400

            # 2. Fetch Authoritative Topic
            cursor.execute("""
                SELECT topic_id, topic_name, passing_score, description
                FROM assessment_topics
                WHERE topic_id = %s AND status = 'ACTIVE'
                LIMIT 1
            """, (topic_id,))
            topic_record = cursor.fetchone()
            if not topic_record:
                return jsonify({"success": False, "error": f"Active topic {topic_id} not found."}), 404

            passing_score = float(topic_record["passing_score"])

            # 3. Fetch Topic Questions
            cursor.execute("""
                SELECT question_id, points, correct_answer, question_order, question_text, options_json
                FROM exam_questions
                WHERE topic_id = %s
                ORDER BY question_order ASC
            """, (topic_id,))
            questions = cursor.fetchall()
            if not questions:
                return jsonify({"success": False, "error": f"No questions configured for topic {topic_id}."}), 404

            if not isinstance(answers, dict):
                return jsonify({"success": False, "error": "Answers must be a JSON object mapping question IDs to selected option IDs."}), 400

            expected_q_ids = [str(q["question_id"]) for q in questions]
            submitted_q_ids = [str(k) for k in answers.keys()]

            invalid_q_ids = [qid for qid in submitted_q_ids if qid not in expected_q_ids]
            if invalid_q_ids:
                return jsonify({
                    "success": False,
                    "error": f"Invalid question ID(s) submitted: {invalid_q_ids}."
                }), 400

            missing_q_ids = [qid for qid in expected_q_ids if qid not in answers or answers[qid] is None or answers[qid] == ""]
            if missing_q_ids:
                return jsonify({
                    "success": False,
                    "error": f"Incomplete submission: missing answers for question(s) {missing_q_ids}. All questions must be answered."
                }), 400

            OPTION_LETTERS = ["A", "B", "C", "D"]
            VALID_OPTIONS_SET = {"A", "B", "C", "D", 0, 1, 2, 3, "0", "1", "2", "3"}

            total_possible_points = 0.0
            earned_points = 0.0
            question_feedback = []
            normalized_answers = {}

            for q in questions:
                q_id = str(q["question_id"])
                pts = float(q["points"])
                correct = q["correct_answer"].strip().upper()
                total_possible_points += pts

                raw_ans = answers.get(q_id)
                if raw_ans not in VALID_OPTIONS_SET:
                    return jsonify({
                        "success": False,
                        "error": f"Invalid option ID '{raw_ans}' for question {q_id}."
                    }), 400

                if isinstance(raw_ans, int) and 0 <= raw_ans < len(OPTION_LETTERS):
                    user_ans = OPTION_LETTERS[raw_ans]
                elif str(raw_ans).isdigit() and int(raw_ans) in (0, 1, 2, 3):
                    user_ans = OPTION_LETTERS[int(raw_ans)]
                else:
                    user_ans = str(raw_ans).strip().upper()

                normalized_answers[q_id] = user_ans
                is_correct = (user_ans == correct)
                if is_correct:
                    earned_points += pts

                question_feedback.append({
                    "question_id": q["question_id"],
                    "question_order": q["question_order"],
                    "is_correct": is_correct,
                    "points_earned": pts if is_correct else 0.0,
                    "max_points": pts
                })

            composite_pct = (earned_points / total_possible_points * 100.0) if total_possible_points > 0 else 0.0
            rounded_score = round(composite_pct, 2)
            rounded_passing = round(passing_score, 2)
            passed = bool(rounded_score >= rounded_passing)

            # 4. Save into agent_topic_results
            save_agent_topic_result(
                agent_id=agent_id,
                topic_id=topic_id,
                score=rounded_score,
                passed=passed,
                answers_json=normalized_answers,
                attempt_id=attempt["attempt_id"]
            )

            # 5. Fetch all available topic scores for ML feature vector
            cursor.execute("""
                SELECT atr.topic_id, atr.score
                FROM agent_topic_results atr
                INNER JOIN (
                    SELECT topic_id, MAX(result_id) as max_id
                    FROM agent_topic_results
                    WHERE agent_id = %s
                    GROUP BY topic_id
                ) latest ON atr.result_id = latest.max_id
            """, (agent_id,))
            topic_scores = {r["topic_id"]: float(r["score"]) for r in cursor.fetchall()}
            topic_scores[topic_id] = rounded_score

            feat_product = topic_scores.get(1, rounded_score if topic_id == 1 else 75.0)
            feat_sales = topic_scores.get(2, rounded_score if topic_id == 2 else 75.0)
            feat_comm = topic_scores.get(3, rounded_score if topic_id == 3 else 75.0)
            feat_cs = topic_scores.get(4, rounded_score if topic_id == 4 else 75.0)

            all_scores = list(topic_scores.values())
            overall_assessment_score = sum(all_scores) / len(all_scores) if all_scores else composite_pct

            v_exp = calculate_agent_verified_experience(agent_id, cursor)
            v_cert = calculate_agent_verified_certifications(agent_id, cursor)

            cursor.close()
            conn.close()
            conn = None

            ml_features = {
                "previous_experience_months": float(v_exp["previous_experience_months"]),
                "sales_experience_months": float(v_exp["sales_experience_months"]),
                "customer_service_experience_months": float(v_exp["customer_service_experience_months"]),
                "certification_count": float(v_cert["certification_count"]),
                "relevant_certification": float(v_cert["relevant_certification"]),
                "assessment_score": float(overall_assessment_score),
                "communication_score": float(feat_comm),
                "product_knowledge_score": float(feat_product),
                "sales_skill_score": float(feat_sales),
                "customer_service_score": float(feat_cs),
            }

            # 6. ML Prediction and canonical binary competency classification
            ml_result = inference_engine.predict(ml_features)
            prediction_label = ml_result.get("prediction", "Eligible" if str(ml_result.get("decision", "0")) == "1" else "Not Eligible")
            decision_code = int(ml_result.get("decision_code", 1 if prediction_label == "Eligible" else 0))
            raw_decision = str(decision_code)
            predicted_enum = "ELIGIBLE" if prediction_label == "Eligible" else "NOT_ELIGIBLE"
            confidence = float(ml_result.get("confidence", 0.0))
            p_eligible = float(ml_result.get("p_eligible", confidence if prediction_label == "Eligible" else 1.0 - confidence))
            p_not_eligible = float(ml_result.get("p_not_eligible", 1.0 - p_eligible))

            competency_label = prediction_label
            decision_label = prediction_label

            prediction_data = {
                "decision": raw_decision,
                "decision_code": decision_code,
                "predicted_enum": predicted_enum,
                "prediction": competency_label,
                "predicted_competency": competency_label,
                "competency_status": competency_label,
                "evaluation_decision": decision_label,
                "is_eligible": prediction_label == "Eligible",
                "confidence": confidence,
                "p_eligible": p_eligible,
                "p_not_eligible": p_not_eligible,
                "probabilities": {
                    "Eligible": round(p_eligible * 100, 1),
                    "Not Eligible": round(p_not_eligible * 100, 1)
                }
            }

            saved = save_agent_assessment(
                user_id=user_id,
                assessment_data=ml_features,
                competency_level=competency_label,
                confidence=confidence,
                prediction_data=prediction_data,
                exam_id=mapped_exam_id,
                task_id=task_id,
                attempt_id=attempt["attempt_id"]
            )

            labeled_probs = {
                "Eligible": round(p_eligible * 100, 1),
                "Not Eligible": round(p_not_eligible * 100, 1)
            }
            conf_pct = round(confidence * 100 if confidence <= 1.0 else confidence)

            subscores_dict = {
                "product_knowledge_score": round(feat_product, 1),
                "sales_skill_score": round(feat_sales, 1),
                "communication_score": round(feat_comm, 1),
                "customer_service_score": round(feat_cs, 1)
            }

            decision_details = {
                "decision": raw_decision,
                "competency_label": competency_label,
                "decision_label": decision_label,
                "confidence": conf_pct,
                "probabilities": labeled_probs,
                "features_used": ml_features
            }

            engine_info = inference_engine.get_info()
            model_ver = engine_info.get("model_version", "1.0.0")

            finalize_assessment_attempt(
                attempt_id=attempt["attempt_id"],
                score=round(composite_pct, 2),
                passed=passed,
                answers_json=normalized_answers,
                subscores_json=subscores_dict,
                model_version=model_ver,
                exam_result_id=saved["exam_result_id"],
                prediction_id=saved["prediction_id"],
                decision_details=decision_details
            )

            # 7. Evaluate Task Eligibility (if task_id provided)
            task_eligibility = None
            if task_id:
                agent_tasks = get_agent_tasks_with_eligibility(user_id)
                target_task = next((t for t in agent_tasks if t["task_id"] == task_id), None)
                if target_task:
                    next_topic = None
                    if target_task.get("required_topics"):
                        next_topic = next((top for top in target_task["required_topics"] if top["status"] != "Passed"), None)
                    task_eligibility = {
                        "task_id": target_task["task_id"],
                        "task_title": target_task["title"],
                        "can_apply": target_task["can_apply"],
                        "is_eligible": target_task["is_eligible"],
                        "blocking_reason": target_task["blocking_reason"],
                        "state": target_task["state"],
                        "all_topics_passed": target_task.get("all_topics_passed", False),
                        "required_topics": target_task.get("required_topics", []),
                        "next_topic_needed": next_topic,
                        "prerequisites": target_task["prerequisites"]
                    }

            return jsonify({
                "success": True,
                "data": {
                    "attempt_id": attempt["attempt_id"],
                    "attempt_uuid": attempt.get("attempt_uuid"),
                    "topic_id": topic_id,
                    "topic_name": topic_record["topic_name"],
                    "task_id": task_id,
                    "score": round(composite_pct, 1),
                    "composite_score": round(composite_pct, 1),
                    "passed": passed,
                    "passing_score": round(passing_score, 1),
                    "total_questions": len(questions),
                    "correct_count": int(earned_points),
                    "competency_level": competency_label,
                    "evaluation_decision": decision_label,
                    "confidence": conf_pct,
                    "probabilities": labeled_probs,
                    "prediction": {
                        "decision_label": decision_label,
                        "decision_code": int(raw_decision),
                        "competency_label": competency_label,
                        "confidence": conf_pct,
                        "probabilities": labeled_probs
                    },
                    "model_version": model_ver,
                    "subscores": subscores_dict,
                    "features_used": ml_features,
                    "feedback": question_feedback,
                    "task_eligibility": task_eligibility,
                    "saved": {
                        "attempt_id": attempt["attempt_id"],
                        "exam_result_id": saved["exam_result_id"],
                        "prediction_id": saved["prediction_id"]
                    }
                }
            }), 200
    except Exception as e:
        logger.error(f"Failed to submit topic assessment: {e}")
        return jsonify({"success": False, "error": f"Failed to submit assessment: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@competency_bp.route("/attempts/<int:attempt_id>", methods=["GET"])
def get_attempt_details(attempt_id):
    """
    Retrieve stored assessment result for a given attempt.
    Enforces attempt ownership and agent authentication.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    conn = get_mysql_connection()
    if not conn:
        return jsonify({"success": False, "error": "Database unavailable"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            ag = cursor.fetchone()
            if not ag:
                return jsonify({"success": False, "error": "Agent profile not found."}), 404
            agent_id = ag["agent_id"]

            cursor.execute("""
                SELECT 
                    att.attempt_id,
                    att.attempt_uuid,
                    att.agent_id,
                    att.exam_id,
                    att.topic_id,
                    att.task_id,
                    att.attempt_number,
                    att.status,
                    att.score,
                    att.passed,
                    att.started_at,
                    att.expires_at,
                    att.submitted_at,
                    att.subscores_json,
                    att.decision_details,
                    top.topic_name,
                    top.passing_score AS topic_passing_score,
                    t.task_name
                FROM assessment_attempts att
                LEFT JOIN assessment_topics top ON att.topic_id = top.topic_id
                LEFT JOIN tasks t ON att.task_id = t.task_id
                WHERE att.attempt_id = %s
                LIMIT 1
            """, (attempt_id,))
            attempt = cursor.fetchone()
            if not attempt:
                return jsonify({"success": False, "error": f"Attempt {attempt_id} not found."}), 404

            if attempt["agent_id"] != agent_id:
                return jsonify({"success": False, "error": "Unauthorized: attempt belongs to another agent."}), 403

            subscores = json.loads(attempt["subscores_json"]) if isinstance(attempt["subscores_json"], str) else (attempt["subscores_json"] or {})
            decision_det = json.loads(attempt["decision_details"]) if isinstance(attempt["decision_details"], str) else (attempt["decision_details"] or {})

            # Also retrieve current task eligibility if task_id exists
            task_eligibility = None
            if attempt["task_id"]:
                tasks = get_agent_tasks_with_eligibility(user_id)
                target = next((t for t in tasks if t["task_id"] == attempt["task_id"]), None)
                if target:
                    next_topic = None
                    if target.get("required_topics"):
                        next_topic = next((top for top in target["required_topics"] if top["status"] != "Passed"), None)
                    task_eligibility = {
                        "task_id": target["task_id"],
                        "task_title": target["title"],
                        "can_apply": target["can_apply"],
                        "is_eligible": target["is_eligible"],
                        "blocking_reason": target["blocking_reason"],
                        "state": target["state"],
                        "all_topics_passed": target.get("all_topics_passed", False),
                        "required_topics": target.get("required_topics", []),
                        "next_topic_needed": next_topic,
                        "prerequisites": target["prerequisites"]
                    }

            return jsonify({
                "success": True,
                "data": {
                    "attempt_id": attempt["attempt_id"],
                    "attempt_uuid": attempt["attempt_uuid"],
                    "topic_id": attempt["topic_id"],
                    "topic_name": attempt["topic_name"] or "Assessment",
                    "task_id": attempt["task_id"],
                    "task_title": attempt["task_name"],
                    "status": attempt["status"],
                    "score": float(attempt["score"]) if attempt["score"] is not None else None,
                    "passed": bool(attempt["passed"]) if attempt["passed"] is not None else False,
                    "passing_score": float(attempt["topic_passing_score"]) if attempt.get("topic_passing_score") is not None else 70.0,
                    "started_at": attempt["started_at"].isoformat() if hasattr(attempt["started_at"], "isoformat") else str(attempt["started_at"]),
                    "submitted_at": attempt["submitted_at"].isoformat() if attempt["submitted_at"] and hasattr(attempt["submitted_at"], "isoformat") else (str(attempt["submitted_at"]) if attempt["submitted_at"] else None),
                    "subscores": subscores,
                    "prediction": {
                        "competency_label": decision_det.get("competency_label", "Competent"),
                        "decision_label": decision_det.get("decision_label", "Eligible"),
                        "confidence": decision_det.get("confidence", 78),
                        "probabilities": decision_det.get("probabilities", {})
                    },
                    "task_eligibility": task_eligibility
                }
            }), 200
    except Exception as e:
        logger.error(f"Error fetching attempt detail {attempt_id}: {e}")
        return jsonify({"success": False, "error": f"Failed to fetch attempt: {str(e)}"}), 500
    finally:
        conn.close()


@competency_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task_details(task_id):
    """
    Fetch single task with evaluated requirements and required topics checklist.
    """
    user_id, _role, err = get_authenticated_agent()
    if err:
        return err

    tasks = get_agent_tasks_with_eligibility(user_id)
    target = next((t for t in tasks if t["task_id"] == task_id), None)
    if not target:
        return jsonify({"success": False, "error": f"Task {task_id} not found."}), 404

    return jsonify({
        "success": True,
        "data": target
    }), 200