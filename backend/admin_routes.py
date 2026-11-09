import logging
from flask import Blueprint, request, jsonify
from backend.auth_routes import decode_auth_token
from backend.db import (
    normalize_role,
    find_user_by_id,
    get_mysql_connection,
    get_admin_overview_metrics,
    get_admin_agents,
    get_admin_tasks,
    get_admin_task_detail,
    get_task_metadata,
    create_task_with_requirements,
    update_task_with_requirements,
    set_task_status,
    delete_task,
    get_task_applicants,
    update_task_application_status,
    assign_task_application,
    get_admin_assessments,
    get_admin_reviews,
    get_admin_review_detail,
    update_admin_review_decision,
    get_admin_pending_verifications,
    review_agent_certification,
    review_agent_experience,
    get_agent_profile_data,
)

logger = logging.getLogger("verifymesh.admin")

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def get_authenticated_admin():
    """
    Verify the Bearer token, check active account status, and enforce
    the Administrator role against the live MySQL database on every request.
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
            jsonify({"success": False, "error": "Malformed token: missing user id."}), 401
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
    if canonical_role not in ("Administrator", "ADMIN", "Workforce Officer", "WORKFORCE_OFFICER"):
        return None, None, (
            jsonify({"success": False, "error": "Workforce Officer or Administrator role required."}), 403
        )

    return user_id, canonical_role, None


# =====================================================================
# OVERVIEW METRICS
# =====================================================================

@admin_bp.route("/overview", methods=["GET"])
def admin_overview():
    """Return system-wide KPIs, active model info, and recent assessments."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        metrics = get_admin_overview_metrics()
        if metrics is None:
            return jsonify({"success": False, "error": "Failed to load overview metrics"}), 500

        # Runtime model metadata: Deterministic Eligibility is active; task suitability model configured
        from src.task_suitability_inference import task_suitability_engine
        model_info = task_suitability_engine.get_info()
        metrics["runtime_model"] = {
            "model_file": model_info.get("model_file", "verifymesh_stage2_suitability_pipeline_v2.joblib"),
            "model_name": model_info.get("model_name", "VerifyMesh_Stage2_Suitability_LR_v2"),
            "model_version": model_info.get("model_version", "2.0.0"),
            "model_path": model_info.get("model_path"),
            "model_sha256": model_info.get("model_sha256"),
            "model_loaded": model_info.get("model_loaded", True),
            "classes": model_info.get("classes", ["Not Suitable (0)", "Suitable (1)"]),
            "feature_count": model_info.get("features_count", 5),
            "features_count": model_info.get("features_count", 5),
            "expected_features": model_info.get("expected_features", []),
            "feature_descriptions": model_info.get("feature_descriptions", {}),
            "is_binary_gatekeeper": False,
            "eligibility_engine": "Deterministic Server-Side Rules",
            "decision_threshold": model_info.get("decision_threshold", 0.60),
            "moderate_threshold": model_info.get("moderate_threshold", 0.48),
            "advisory_tiers": model_info.get("advisory_tiers", {}),
            "is_advisory": True,
            "training_scenario": model_info.get("training_scenario"),
            "synthetic_data_disclaimer": model_info.get("synthetic_data_disclaimer")
        }

        return jsonify({
            "success": True,
            "data": metrics
        }), 200
    except Exception as e:
        logger.error(f"Error in admin overview: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================================
# AGENT DIRECTORY
# =====================================================================

@admin_bp.route("/agents", methods=["GET"])
def admin_agents():
    """Return directory of all agents with profile, attempts, and latest competency prediction."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        agents = get_admin_agents()
        return jsonify({
            "success": True,
            "data": agents,
            "count": len(agents)
        }), 200
    except Exception as e:
        logger.error(f"Error in admin agents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/agents/<int:agent_id>/profile", methods=["GET"])
def admin_agent_profile(agent_id):
    """Fetch comprehensive profile data for an agent (contact, exp, certs, assessments)."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"success": False, "error": "Database unavailable"}), 503
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM agents WHERE agent_id = %s LIMIT 1", (agent_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"success": False, "error": "Agent not found"}), 404
            agent_user_id = row["user_id"] if isinstance(row, dict) else row[0]

        profile = get_agent_profile_data(agent_user_id)
        if not profile:
            return jsonify({"success": False, "error": "Agent profile not found"}), 404

        return jsonify({"success": True, "data": profile}), 200
    except Exception as e:
        logger.error(f"Error fetching agent profile for agent {agent_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================================
# TASK MANAGEMENT
# =====================================================================

@admin_bp.route("/tasks", methods=["GET"])
def admin_tasks():
    """Return all tasks with their configured eligibility requirements."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        tasks = get_admin_tasks()
        return jsonify({
            "success": True,
            "data": tasks,
            "count": len(tasks)
        }), 200
    except Exception as e:
        logger.error(f"Error in admin tasks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/metadata", methods=["GET"])
def admin_tasks_metadata():
    """Return category, certification, and skill lookup lists for task configuration."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        metadata = get_task_metadata()
        return jsonify({
            "success": True,
            "data": metadata
        }), 200
    except Exception as e:
        logger.error(f"Error in admin tasks metadata: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>", methods=["GET"])
def admin_get_task(task_id):
    """Retrieve full details for a single task."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        task = get_admin_task_detail(task_id)
        if not task:
            return jsonify({"success": False, "error": f"Task {task_id} not found."}), 404
        return jsonify({
            "success": True,
            "data": task
        }), 200
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks", methods=["POST"])
def admin_create_task():
    """Create a new task and its eligibility requirements."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        res = create_task_with_requirements(data, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": "Task created successfully.",
            "data": res
        }), 201
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def admin_update_task(task_id):
    """Update an existing task and its eligibility requirements."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        update_task_with_requirements(task_id, data, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": f"Task {task_id} updated successfully."
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>/status", methods=["PATCH"])
def admin_set_task_status(task_id):
    """Update task lifecycle status (e.g. ACTIVE, INACTIVE, DRAFT, COMPLETED)."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"success": False, "error": "Status is required."}), 400

    try:
        set_task_status(task_id, status, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": f"Task {task_id} status updated to {status}."
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error updating status for task {task_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def admin_delete_task(task_id):
    """Permanently delete a task and its associated configurations."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        delete_task(task_id, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": f"Task {task_id} deleted successfully."
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tasks/<int:task_id>/applications", methods=["GET"])
def admin_get_task_applications(task_id):
    """Retrieve all applicants for a given task with requirement fulfillment details."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        applicants = get_task_applicants(task_id)
        return jsonify({
            "success": True,
            "data": applicants,
            "count": len(applicants)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching applicants for task {task_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/applications/<int:application_id>/assign", methods=["POST"])
def admin_assign_task_application(application_id):
    """
    Assign a task application to an applicant.
    Authoritatively validates eligibility prerequisites before updating.
    """
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        res = assign_task_application(application_id, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": "Task successfully assigned to applicant.",
            "data": res
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error assigning task application {application_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
def admin_update_application_status(application_id):
    """Update status of an application (e.g., Shortlisted, Under Review, Rejected)."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    notes = data.get("notes")
    if not status:
        return jsonify({"success": False, "error": "Status is required."}), 400

    try:
        res = update_task_application_status(application_id, status, notes=notes, admin_user_id=user_id)
        return jsonify({
            "success": True,
            "message": f"Application status updated to {status}.",
            "data": res
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error updating application {application_id} status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================================
# ASSESSMENT AUDIT HISTORY
# =====================================================================

@admin_bp.route("/assessments", methods=["GET"])
def admin_assessments():
    """Return historical assessment attempts across all agents with ML predictions."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        assessments = get_admin_assessments()
        return jsonify({
            "success": True,
            "data": assessments,
            "count": len(assessments)
        }), 200
    except Exception as e:
        logger.error(f"Error in admin assessments: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================================
# ELIGIBILITY REVIEWS
# =====================================================================

@admin_bp.route("/reviews", methods=["GET"])
def admin_reviews():
    """Return eligibility evaluations from v_eligibility_summary."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        reviews = get_admin_reviews()
        return jsonify({
            "success": True,
            "data": reviews,
            "count": len(reviews)
        }), 200
    except Exception as e:
        logger.error(f"Error in admin reviews: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/reviews/<int:evaluation_id>", methods=["GET"])
def admin_review_detail(evaluation_id):
    """Return full detail of an eligibility evaluation including check criteria."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        detail = get_admin_review_detail(evaluation_id)
        if not detail:
            return jsonify({"success": False, "error": "Eligibility review record not found."}), 404

        return jsonify({
            "success": True,
            "data": detail
        }), 200
    except Exception as e:
        logger.error(f"Error in admin review detail: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/reviews/<int:evaluation_id>/review", methods=["POST"])
def admin_submit_review(evaluation_id):
    """Record officer review decision on an eligibility evaluation."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    decision = payload.get("decision", "").upper()
    comments = payload.get("comments", "").strip()

    if decision not in ["APPROVED", "REJECTED"]:
        return jsonify({"success": False, "error": "Decision must be APPROVED or REJECTED."}), 400

    success, msg = update_admin_review_decision(evaluation_id, decision, user_id, comments)
    if not success:
        return jsonify({"success": False, "error": msg}), 500

    return jsonify({"success": True, "message": msg}), 200


# =====================================================================
# AGENT CREDENTIAL & WORK VERIFICATION
# =====================================================================

@admin_bp.route("/verifications", methods=["GET"])
def admin_verifications():
    """Return all pending and historical certification and experience verification requests."""
    user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    try:
        verifs = get_admin_pending_verifications()
        return jsonify({
            "success": True,
            "data": verifs
        }), 200
    except Exception as e:
        logger.error(f"Error in admin verifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/verifications/certifications/<int:cert_id>/review", methods=["POST"])
def admin_review_certification(cert_id):
    """Approve or reject a submitted agent certification."""
    admin_user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    decision = payload.get("decision")
    rejection_reason = payload.get("rejection_reason")

    if not decision:
        return jsonify({"success": False, "error": "Decision ('VERIFIED' or 'REJECTED') is required."}), 400

    try:
        res = review_agent_certification(admin_user_id, cert_id, decision, rejection_reason=rejection_reason)
        return jsonify({
            "success": True,
            "message": f"Certification successfully marked as {decision}.",
            "data": res
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error reviewing certification {cert_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/verifications/experiences/<int:exp_id>/review", methods=["POST"])
def admin_review_experience(exp_id):
    """Approve or reject a submitted agent work experience."""
    admin_user_id, _role, err = get_authenticated_admin()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    decision = payload.get("decision")
    rejection_reason = payload.get("rejection_reason")

    if not decision:
        return jsonify({"success": False, "error": "Decision ('VERIFIED' or 'REJECTED') is required."}), 400

    try:
        res = review_agent_experience(admin_user_id, exp_id, decision, rejection_reason=rejection_reason)
        return jsonify({
            "success": True,
            "message": f"Work experience successfully marked as {decision}. Recalculated verified months: {res.get('recalculated_months')}.",
            "data": res
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error reviewing experience {exp_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

