import logging
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import os

logger = logging.getLogger('verifymesh.db')

ROLE_MAP = {
    "ADMIN": "Administrator",
    "AGENT": "Agent",
    "Administrator": "Administrator",
    "Agent": "Agent",
}

def normalize_role(raw_role):
    """Convert DB role strings (ADMIN/AGENT) to frontend role strings (Administrator/Agent)."""
    return ROLE_MAP.get(raw_role, raw_role)

FALLBACK_ASSESSMENTS = {}
PENDING_VERIFICATIONS = {}
PENDING_SIGNUPS = {}

FALLBACK_USERS = [
    {
        "id": 1,
        "email": "alex.morgan@university.edu",
        "username": "alex.morgan",
        "password_hash": generate_password_hash("password123"),
        "full_name": "Alex Morgan",
        "role": "Agent",
        "is_active": True,
        "assessment": None,
        "competency_level": None
    },
    {
        "id": 2,
        "email": "admin@verifymesh.io",
        "username": "admin",
        "password_hash": generate_password_hash("password123"),
        "full_name": "System Administrator",
        "role": "Administrator",
        "is_active": True
    },
    {
        "id": 3,
        "email": "daniel.obuya@verifymesh.io",
        "username": "daniel.obuya",
        "password_hash": generate_password_hash("password123"),
        "full_name": "Daniel Obuya",
        "role": "Agent",
        "is_active": True,
        "assessment": None,
        "competency_level": None
    }
]

def get_mysql_connection():
    """Attempt to establish a MySQL connection using configured parameters."""
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=DictCursor,
            connect_timeout=2
        )
        return connection
    except Exception as e:
        logger.debug(f"MySQL connection error: {e}")
        return None

def check_mysql_status():
    """Verify if MySQL database and tables exist."""
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'users'")
                result = cursor.fetchone()
                return bool(result)
        finally:
            conn.close()
    return False

DECISION_TO_ENUM = {
    "0": "NEEDS_IMPROVEMENT",
    "1": "BASIC",
    "2": "COMPETENT",
    0: "NEEDS_IMPROVEMENT",
    1: "BASIC",
    2: "COMPETENT"
}

# Concept A: Agent Competency Labels (4 model-supported classes)
COMPETENCY_ENUM_TO_LABEL = {
    "NEEDS_IMPROVEMENT": "Needs Improvement",
    "BASIC": "Basic",
    "COMPETENT": "Competent",
    "ADVANCED": "Advanced",
}

# Competency hierarchy ranking for requirement evaluations
COMPETENCY_RANKS = {
    "NEEDS_IMPROVEMENT": 1,
    "Needs Improvement": 1,
    "BASIC": 2,
    "Basic": 2,
    "COMPETENT": 3,
    "Competent": 3,
    "ADVANCED": 4,
    "Advanced": 4,
}

# Concept B: Agent Evaluation Decisions (separate from competency class)
DECISION_TO_LABEL = {
    "0": "Ineligible",
    "1": "Send to Review",
    "2": "Eligible",
    0: "Ineligible",
    1: "Send to Review",
    2: "Eligible"
}

ENUM_TO_DECISION = {
    "NEEDS_IMPROVEMENT": {"decision": "0", "label": "Ineligible"},
    "BASIC": {"decision": "1", "label": "Send to Review"},
    "COMPETENT": {"decision": "2", "label": "Eligible"},
    "ADVANCED": {"decision": "2", "label": "Eligible"}
}

def get_or_create_reference_records(cursor):
    """
    Ensure the required exam and model reference records exist in MySQL using unique constraints.
    Does not assume IDs 1 or overwrite existing records.
    """
    # 1. Category
    cursor.execute("SELECT category_id FROM categories ORDER BY category_id ASC LIMIT 1")
    cat_row = cursor.fetchone()
    if not cat_row:
        cursor.execute("INSERT INTO categories (category_name, description) VALUES ('Competency Assessment', 'Default assessment category')")
        category_id = cursor.lastrowid
    else:
        category_id = cat_row["category_id"] if isinstance(cat_row, dict) else cat_row[0]

    # 2. Exam
    cursor.execute("SELECT exam_id FROM exams WHERE exam_name = %s LIMIT 1", ('VerifyMesh Competency Assessment',))
    exam_row = cursor.fetchone()
    if not exam_row:
        cursor.execute("""
            INSERT INTO exams (category_id, exam_name, description, passing_score, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
        """, (category_id, 'VerifyMesh Competency Assessment', 'Standard assessment for agent competency & eligibility', 70.00))
        exam_id = cursor.lastrowid
    else:
        exam_id = exam_row["exam_id"] if isinstance(exam_row, dict) else exam_row[0]

    # 3. Model
    cursor.execute("SELECT model_id FROM ml_models WHERE model_name = %s AND model_version = %s LIMIT 1",
                   ('ThreeWayDecisionRandomForest', '1.0.0'))
    model_row = cursor.fetchone()
    if not model_row:
        cursor.execute("""
            INSERT INTO ml_models (model_name, model_version, algorithm, feature_set_version, is_active)
            VALUES (%s, %s, %s, %s, 1)
        """, ('ThreeWayDecisionRandomForest', '1.0.0', 'RandomForestClassifier', '11-features-leverage'))
        model_id = cursor.lastrowid
    else:
        model_id = model_row["model_id"] if isinstance(model_row, dict) else model_row[0]

    return exam_id, model_id

def get_agent_assessment(user_id):
    """
    Retrieve latest completed assessment and competency details from MySQL.
    Uses real tables agents, ml_predictions, exam_results, and audit_logs.
    Preserves audit history and respects non-destructive resets.
    """
    conn = get_mysql_connection()
    if not conn:
        logger.warning(f"MySQL unavailable when retrieving assessment for user_id {user_id}")
        return None

    try:
        with conn.cursor() as cursor:
            # Verify user has an agent record
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                return None
            agent_id = agent_row["agent_id"]

            # Check for non-destructive reset using auto-increment log_id
            cursor.execute("""
                SELECT log_id, created_at FROM audit_logs 
                WHERE user_id = %s AND action = 'ASSESSMENT_RESET_REQUESTED'
                ORDER BY log_id DESC LIMIT 1
            """, (user_id,))
            reset_row = cursor.fetchone()
            reset_log_id = reset_row["log_id"] if reset_row else None

            cursor.execute("""
                SELECT log_id FROM audit_logs
                WHERE user_id = %s AND action = 'ASSESSMENT_COMPLETED'
                ORDER BY log_id DESC LIMIT 1
            """, (user_id,))
            completed_row = cursor.fetchone()
            completed_log_id = completed_row["log_id"] if completed_row else None

            # If reset occurred without a subsequent assessment completion, treat as unassessed
            if reset_log_id and (not completed_log_id or reset_log_id > completed_log_id):
                return None

            # Retrieve latest prediction and exam result
            cursor.execute("""
                SELECT 
                    mp.prediction_id,
                    mp.agent_id,
                    mp.predicted_competency,
                    mp.confidence,
                    mp.predicted_at,
                    er.exam_result_id,
                    er.assessment_score,
                    er.passed,
                    er.attempt_number,
                    er.completed_at
                FROM ml_predictions mp
                JOIN exam_results er ON er.exam_result_id = mp.exam_result_id
                WHERE mp.agent_id = %s
                ORDER BY mp.predicted_at DESC, mp.prediction_id DESC
                LIMIT 1
            """, (agent_id,))
            pred_row = cursor.fetchone()

            if not pred_row:
                return None

            # Retrieve detailed assessment payload from audit log if available
            cursor.execute("""
                SELECT description FROM audit_logs
                WHERE user_id = %s AND action = 'ASSESSMENT_COMPLETED' AND entity_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, pred_row["prediction_id"]))
            audit_row = cursor.fetchone()

            raw_payload = {}
            if audit_row and audit_row.get("description"):
                try:
                    raw_payload = json.loads(audit_row["description"])
                except Exception:
                    raw_payload = {}

            enum_val = pred_row["predicted_competency"]
            competency_label = COMPETENCY_ENUM_TO_LABEL.get(enum_val, "Competent")
            mapped = ENUM_TO_DECISION.get(enum_val, {"decision": "0", "label": "Ineligible"})
            decision_label = mapped["label"]

            raw_conf = float(pred_row["confidence"]) if pred_row["confidence"] is not None else 0.0
            conf_pct = raw_conf * 100.0 if raw_conf <= 1.0 else raw_conf

            assessment_data = raw_payload.get("assessment_data") or {
                "assessment_score": float(pred_row["assessment_score"])
            }
            prediction_data = raw_payload.get("prediction_data") or {
                "decision": mapped["decision"],
                "prediction": competency_label,
                "predicted_competency": competency_label,
                "evaluation_decision": decision_label,
                "confidence": conf_pct
            }

            return {
                "user_id": user_id,
                "agent_id": agent_id,
                "attempt_number": pred_row["attempt_number"],
                "assessment": assessment_data,
                "competency_level": competency_label,
                "evaluation_decision": decision_label,
                "confidence": conf_pct,
                "prediction_data": prediction_data,
                "completed_at": pred_row["completed_at"].isoformat() if hasattr(pred_row["completed_at"], "isoformat") else str(pred_row["completed_at"])
            }
    except Exception as e:
        logger.error(f"Error reading agent assessment from MySQL: {e}")
        return None
    finally:
        conn.close()

def save_agent_assessment(user_id, assessment_data, competency_level, confidence, prediction_data=None):
    """
    Save agent assessment result, model prediction, and corresponding audit event transactionally into MySQL.
    Rolls back on failure and raises RuntimeError if persistence fails.
    Preserves historical attempts by incrementing attempt_number for each retake.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable. Cannot persist assessment.")

    try:
        with conn.cursor() as cursor:
            # 1. Resolve agent_id strictly from server-side user_id
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                raise ValueError(f"No agent profile found for user_id {user_id}. Assessment cannot be associated.")
            agent_id = agent_row["agent_id"]

            # 2. Seed or retrieve required exam and model reference records
            exam_id, model_id = get_or_create_reference_records(cursor)

            # 3. Determine attempt number (strictly incremented to preserve history)
            cursor.execute("""
                SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
                FROM exam_results
                WHERE agent_id = %s AND exam_id = %s
            """, (agent_id, exam_id))
            attempt_row = cursor.fetchone()
            attempt_number = attempt_row["next_attempt"] if attempt_row else 1

            # 4. Extract assessment score and determine pass status
            raw_score = float(assessment_data.get("assessment_score", 0.0))
            score = max(0.0, min(100.0, raw_score))  # satisfies chk_exam_result_score
            passed = 1 if score >= 70.0 else 0

            # 5. Insert into exam_results
            cursor.execute("""
                INSERT INTO exam_results (exam_id, agent_id, assessment_score, passed, attempt_number, completed_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (exam_id, agent_id, score, passed, attempt_number))
            exam_result_id = cursor.lastrowid

            # 6. Map decision to enum: 0 -> NEEDS_IMPROVEMENT, 1 -> BASIC, 2 -> COMPETENT
            decision = str(prediction_data.get("decision", "0")) if prediction_data else "0"
            predicted_enum = DECISION_TO_ENUM.get(decision, "NEEDS_IMPROVEMENT")

            # Validate confidence (decimal 6,4, value between 0 and 1)
            raw_conf = float(confidence) if confidence is not None else 0.0
            conf_val = raw_conf / 100.0 if raw_conf > 1.0 else raw_conf
            conf_val = max(0.0, min(1.0, conf_val))

            # 7. Insert into ml_predictions
            cursor.execute("""
                INSERT INTO ml_predictions (agent_id, model_id, exam_result_id, predicted_competency, confidence, predicted_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (agent_id, model_id, exam_result_id, predicted_enum, conf_val))
            prediction_id = cursor.lastrowid

            # 8. Update agent experience_months if provided
            exp_months = int(float(assessment_data.get("previous_experience_months", 0)))
            if exp_months > 0:
                cursor.execute("""
                    UPDATE agents SET experience_months = %s, updated_at = NOW()
                    WHERE agent_id = %s
                """, (exp_months, agent_id))

            # 9. Insert audit log event with full assessment payload
            audit_payload = {
                "assessment_data": assessment_data,
                "prediction_data": prediction_data,
                "attempt_number": attempt_number,
                "score": score,
                "decision": decision,
                "competency_level": competency_level
            }
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_COMPLETED', 'ml_predictions', %s, %s, NOW())
            """, (user_id, prediction_id, json.dumps(audit_payload)))

        conn.commit()
        logger.info(f"Persisted assessment attempt {attempt_number} for agent {agent_id} (user {user_id}), prediction {prediction_id}")
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "attempt_number": attempt_number,
            "exam_result_id": exam_result_id,
            "prediction_id": prediction_id,
            "competency_level": competency_level,
            "confidence": conf_val,
            "assessment": assessment_data,
            "prediction_data": prediction_data
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist assessment for user {user_id}: {e}")
        raise RuntimeError(f"Database persistence failure: {str(e)}")
    finally:
        conn.close()

def reset_agent_assessment(user_id):
    """
    Safe, non-destructive assessment reset for testing/demo purposes.
    Inserts an ASSESSMENT_RESET_REQUESTED audit event.
    Historical exam_results and ml_predictions are strictly preserved.
    """
    conn = get_mysql_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            agent_id = agent_row["agent_id"] if agent_row else None

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_RESET_REQUESTED', 'agents', %s, 
                        'Safe demo reset requested. Historical attempts preserved.', NOW())
            """, (user_id, agent_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error logging assessment reset in MySQL: {e}")
        return False
    finally:
        conn.close()


def get_agent_tasks_with_eligibility(user_id):
    """
    Retrieve all active tasks with independently evaluated requirements and status
    for the authenticated agent based on genuine database records.

    Evaluates:
      1. Mandatory certification requirements (from agent_certifications)
      2. Task assessment completion & validity (from exam_results)
      3. Competency threshold check (from ml_predictions)
      4. Experience months (from agents)
      5. Application status (from task_applications)

    Follows the 8-step precedence rule:
      1. If already assigned -> 'Assigned'
      2. If application exists -> actual application status (e.g. 'Application Submitted', 'Under Review', 'Shortlisted', 'Rejected', 'Withdrawn')
      3. If mandatory certification is missing -> 'Certification Required'
      4. If mandatory requirement unresolved or awaiting administrative decision -> 'Verification Pending'
      5. If required task-specific assessment has not been completed -> 'Assessment Needed'
      6. If assessment results are pending review -> 'Under Review'
      7. If all prerequisites and required evaluation passed -> 'Ready to Apply'
      8. Otherwise -> actual blocking requirement (e.g. 'Requires Advanced', 'Requires 12 Months Experience')
    """
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            # 1. Agent Record
            cursor.execute("""
                SELECT agent_id, experience_months, availability_status, status
                FROM agents WHERE user_id = %s LIMIT 1
            """, (user_id,))
            agent = cursor.fetchone()
            if not agent:
                return []
            agent_id = agent["agent_id"]
            agent_exp_months = int(agent["experience_months"] or 0)
            agent_status = agent["status"]

            # 2. Check for non-destructive reset using auto-increment log_id
            cursor.execute("""
                SELECT log_id, created_at FROM audit_logs 
                WHERE user_id = %s AND action = 'ASSESSMENT_RESET_REQUESTED'
                ORDER BY log_id DESC LIMIT 1
            """, (user_id,))
            reset_row = cursor.fetchone()
            reset_log_id = reset_row["log_id"] if reset_row else None

            cursor.execute("""
                SELECT log_id FROM audit_logs
                WHERE user_id = %s AND action = 'ASSESSMENT_COMPLETED'
                ORDER BY log_id DESC LIMIT 1
            """, (user_id,))
            completed_row = cursor.fetchone()
            completed_log_id = completed_row["log_id"] if completed_row else None

            is_reset = bool(reset_log_id and (not completed_log_id or reset_log_id > completed_log_id))

            # 3. Retrieve latest completed assessment and prediction
            cursor.execute("""
                SELECT 
                    mp.prediction_id,
                    mp.predicted_competency,
                    mp.confidence,
                    mp.predicted_at,
                    er.exam_result_id,
                    er.exam_id,
                    er.assessment_score,
                    er.passed,
                    er.completed_at
                FROM ml_predictions mp
                JOIN exam_results er ON er.exam_result_id = mp.exam_result_id
                WHERE mp.agent_id = %s
                ORDER BY mp.predicted_at DESC, mp.prediction_id DESC
                LIMIT 1
            """, (agent_id,))
            pred_row = cursor.fetchone()

            has_assessed = False
            agent_comp_enum = None
            agent_comp_label = "Not Yet Assessed"
            agent_decision = "Not Yet Evaluated"

            if pred_row and not is_reset:
                has_assessed = bool(pred_row["passed"])
                agent_comp_enum = pred_row["predicted_competency"]
                agent_comp_label = COMPETENCY_ENUM_TO_LABEL.get(agent_comp_enum, "Competent")
                decision_info = ENUM_TO_DECISION.get(agent_comp_enum, {"label": "Eligible"})
                agent_decision = decision_info.get("label", "Eligible")

            # 4. Agent's active certifications
            cursor.execute("""
                SELECT ac.certification_id, c.certification_name, ac.status, ac.expiry_date
                FROM agent_certifications ac
                JOIN certifications c ON ac.certification_id = c.certification_id
                WHERE ac.agent_id = %s AND ac.status = 'ACTIVE' AND (ac.expiry_date IS NULL OR ac.expiry_date >= CURDATE())
            """, (agent_id,))
            active_certs = {r["certification_id"]: r["certification_name"] for r in cursor.fetchall()}

            # Check if agent has pending certifications
            cursor.execute("""
                SELECT ac.certification_id, c.certification_name
                FROM agent_certifications ac
                JOIN certifications c ON ac.certification_id = c.certification_id
                WHERE ac.agent_id = %s AND ac.status = 'PENDING'
            """, (agent_id,))
            pending_certs = {r["certification_id"]: r["certification_name"] for r in cursor.fetchall()}

            # 5. Agent's existing task applications
            cursor.execute("""
                SELECT task_id, status, applied_at, notes
                FROM task_applications
                WHERE agent_id = %s
            """, (agent_id,))
            applications = {r["task_id"]: r for r in cursor.fetchall()}

            # 6. Retrieve all active tasks and requirements
            cursor.execute("""
                SELECT 
                    t.task_id,
                    t.category_id,
                    c.category_name,
                    t.task_name,
                    t.description,
                    t.status,
                    t.work_arrangement,
                    t.location,
                    t.deliverables,
                    t.required_skills,
                    t.payment_type,
                    t.currency,
                    t.hourly_rate_min,
                    t.hourly_rate_max,
                    t.fixed_budget,
                    t.positions_count,
                    t.application_deadline,
                    t.expected_duration,
                    t.exam_id,
                    tr.requirement_id,
                    tr.minimum_competency,
                    tr.required_certification_id,
                    cert.certification_name AS required_certification_name,
                    tr.minimum_experience_months,
                    tr.exam_required
                FROM tasks t
                JOIN categories c ON t.category_id = c.category_id
                LEFT JOIN task_requirements tr ON t.task_id = tr.task_id
                LEFT JOIN certifications cert ON tr.required_certification_id = cert.certification_id
                WHERE t.status = 'ACTIVE'
                ORDER BY t.task_id ASC
            """)
            tasks = cursor.fetchall()

            result = []
            for t in tasks:
                t_id = t["task_id"]
                req_cert_id = t["required_certification_id"]
                req_cert_name = t["required_certification_name"]
                min_comp = t["minimum_competency"] or "BASIC"
                min_exp = int(t["minimum_experience_months"] or 0)
                exam_req = bool(t["exam_required"])

                # Check 1: Mandatory Certification
                if req_cert_id is not None:
                    has_cert = req_cert_id in active_certs
                    cert_pending = req_cert_id in pending_certs
                else:
                    has_cert = True
                    cert_pending = False

                # Check 2: Task Assessment
                if exam_req:
                    has_assessment = has_assessed
                else:
                    has_assessment = True

                # Check 3: Competency Threshold
                agent_rank = COMPETENCY_RANKS.get(agent_comp_enum, 0)
                task_rank = COMPETENCY_RANKS.get(min_comp, 2)
                meets_comp = has_assessed and (agent_rank >= task_rank)

                # Check 4: Experience
                meets_exp = agent_exp_months >= min_exp

                # Check 5: Application Status
                app = applications.get(t_id)
                app_status = app["status"] if app else "Not Applied"
                applied_at = app["applied_at"].isoformat() if app and hasattr(app["applied_at"], "isoformat") else (str(app["applied_at"]) if app else None)

                # Determine State using 8-step precedence
                can_apply = False
                is_eligible = False
                blocking_reason = None

                if app_status == "Assigned":
                    state = "Assigned"
                elif app_status in ("Application Submitted", "Under Review", "Shortlisted", "Rejected", "Withdrawn"):
                    state = app_status
                elif not has_cert:
                    if cert_pending:
                        state = "Verification Pending"
                        blocking_reason = f"Required certification '{req_cert_name}' is pending review"
                    else:
                        state = "Certification Required"
                        blocking_reason = f"Mandatory certification required: {req_cert_name}"
                elif agent_status == "SUSPENDED":
                    state = "Verification Pending"
                    blocking_reason = "Agent account is awaiting administrative verification"
                elif not has_assessment:
                    state = "Assessment Needed"
                    blocking_reason = "Task-specific competency evaluation required"
                elif agent_decision == "Send to Review":
                    state = "Under Review"
                    blocking_reason = "Assessment evaluation results are pending administrative review"
                elif has_cert and has_assessment and meets_comp and meets_exp and agent_decision == "Eligible":
                    state = "Ready to Apply"
                    can_apply = True
                    is_eligible = True
                else:
                    # Specific blocking reason
                    if not meets_comp:
                        req_comp_label = COMPETENCY_ENUM_TO_LABEL.get(min_comp, min_comp)
                        state = f"Requires {req_comp_label}"
                        blocking_reason = f"Current competency ({agent_comp_label}) does not meet threshold ({req_comp_label})"
                    elif not meets_exp:
                        state = f"Requires {min_exp} Months Exp"
                        blocking_reason = f"Agent has {agent_exp_months} months verified experience; task requires {min_exp} months"
                    elif agent_decision == "Ineligible":
                        state = "Ineligible"
                        blocking_reason = "Agent overall evaluation status is currently Ineligible"
                    else:
                        state = "Prerequisites Unmet"
                        blocking_reason = "Task requirements not met"

                # Calculate structured payout string
                pay_type = t.get("payment_type") or "Fixed Budget"
                curr = t.get("currency") or "KES"
                h_min = t.get("hourly_rate_min")
                h_max = t.get("hourly_rate_max")
                f_bud = t.get("fixed_budget")

                if pay_type == "Hourly" and h_min is not None:
                    if h_max and float(h_max) > float(h_min):
                        payout_str = f"{curr} {float(h_min):,.0f} - {float(h_max):,.0f} / hr"
                    else:
                        payout_str = f"{curr} {float(h_min):,.0f} / hr"
                elif f_bud is not None:
                    payout_str = f"{curr} {float(f_bud):,.0f} (Fixed Budget)"
                else:
                    payout_str = f"{curr} 2,500 / hr"

                result.append({
                    "task_id": t_id,
                    "title": t["task_name"],
                    "category": t["category_name"],
                    "description": t["description"],
                    "work_arrangement": t.get("work_arrangement") or "Remote",
                    "location": t.get("location"),
                    "deliverables": t.get("deliverables"),
                    "required_skills": t.get("required_skills"),
                    "payment_type": pay_type,
                    "currency": curr,
                    "hourly_rate_min": float(h_min) if h_min is not None else None,
                    "hourly_rate_max": float(h_max) if h_max is not None else None,
                    "fixed_budget": float(f_bud) if f_bud is not None else None,
                    "positions_count": int(t.get("positions_count") or 1),
                    "application_deadline": str(t.get("application_deadline")) if t.get("application_deadline") else None,
                    "expected_duration": t.get("expected_duration"),
                    "exam_id": t.get("exam_id"),
                    "required_competency": COMPETENCY_ENUM_TO_LABEL.get(min_comp, min_comp),
                    "required_certification": req_cert_name or "None required",
                    "minimum_experience_months": min_exp,
                    "exam_required": exam_req,
                    "payout": payout_str,
                    "state": state,
                    "is_eligible": is_eligible,
                    "can_apply": can_apply,
                    "blocking_reason": blocking_reason,
                    "application_status": app_status,
                    "applied_at": applied_at,
                    "prerequisites": {
                        "certification_met": has_cert,
                        "assessment_met": has_assessment,
                        "competency_met": meets_comp,
                        "experience_met": meets_exp,
                        "evaluation_decision": agent_decision
                    }
                })

            return result
    except Exception as e:
        logger.error(f"Error fetching agent tasks with eligibility: {e}")
        return []
    finally:
        conn.close()


def apply_for_task(user_id, task_id, notes=None):
    """
    Submit task application after re-verifying all requirements server-side.
    Rejects application if mandatory certification, assessment, or competency is not met.
    Never trusts client-side assertions.
    """
    tasks = get_agent_tasks_with_eligibility(user_id)
    target = next((t for t in tasks if t["task_id"] == task_id), None)
    if not target:
        raise ValueError("Task not found or is no longer active.")

    if not target["can_apply"]:
        if target.get("application_status") and target["application_status"] != "Not Applied":
            raise ValueError(f"Cannot apply: An active application has already been submitted (Status: {target['application_status']}).")
        raise ValueError(f"Cannot apply: {target['blocking_reason'] or target['state']}")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                raise ValueError(f"Agent profile not found for user {user_id}")
            agent_id = agent_row["agent_id"]

            # Check if already applied
            cursor.execute("SELECT application_id, status FROM task_applications WHERE agent_id = %s AND task_id = %s", (agent_id, task_id))
            existing = cursor.fetchone()
            if existing:
                raise ValueError(f"Application already submitted (status: {existing['status']}).")

            cursor.execute("""
                INSERT INTO task_applications (agent_id, task_id, status, notes, applied_at)
                VALUES (%s, %s, 'Application Submitted', %s, NOW())
            """, (agent_id, task_id, notes))
            application_id = cursor.lastrowid

            # Log audit event
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_APPLICATION_SUBMITTED', 'task_applications', %s, %s, NOW())
            """, (user_id, application_id, json.dumps({
                "task_id": task_id,
                "task_name": target["title"],
                "status": "Application Submitted"
            })))

        conn.commit()
        return {
            "success": True,
            "application_id": application_id,
            "task_id": task_id,
            "status": "Application Submitted"
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error applying for task {task_id}: {e}")
        raise
    finally:
        conn.close()


def get_agent_recent_activities(user_id):
    """
    Retrieve genuine historical activity records for the authenticated agent
    from audit_logs, exam_results, and task_applications.
    """
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            agent_id = agent_row["agent_id"] if agent_row else None

            cursor.execute("""
                SELECT log_id, action, entity_type, entity_id, description, created_at
                FROM audit_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            rows = cursor.fetchall()

            activities = []
            for r in rows:
                action = r["action"]
                ts = r["created_at"]
                time_str = ts.strftime("%b %d, %Y %H:%M") if hasattr(ts, "strftime") else str(ts)

                title = action
                is_pending = False

                if action == "ASSESSMENT_COMPLETED":
                    title = "Competency assessment completed"
                elif action == "ASSESSMENT_RESET_REQUESTED":
                    title = "Assessment state reset (Demo)"
                    is_pending = True
                elif action == "TASK_APPLICATION_SUBMITTED":
                    desc_data = {}
                    if r.get("description"):
                        try:
                            desc_data = json.loads(r["description"])
                        except Exception:
                            desc_data = {}
                    task_name = desc_data.get("task_name", "task")
                    title = f"Application submitted for {task_name}"
                elif action == "TASK_APPLICATION_STATUS_UPDATED":
                    title = "Task application status updated"
                else:
                    title = action.replace("_", " ").capitalize()

                activities.append({
                    "id": r["log_id"],
                    "action": action,
                    "title": title,
                    "time": time_str,
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    "isPending": is_pending
                })

            return activities
    except Exception as e:
        logger.error(f"Error fetching agent activities: {e}")
        return []
    finally:
        conn.close()

def find_user_by_credential(identifier):
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = "SELECT user_id as id, email, email as username, password_hash, full_name, role, is_active FROM users WHERE email = %s LIMIT 1"
                cursor.execute(sql, (identifier,))
                user = cursor.fetchone()
                if user:
                    return user
        except Exception as e:
            logger.error(f"Error querying MySQL: {e}")
        finally:
            conn.close()

    clean_id = identifier.strip().lower()
    for user in FALLBACK_USERS:
        if user["email"].lower() == clean_id or user["username"].lower() == clean_id:
            return user
    return None

def find_user_by_id(user_id):
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = "SELECT user_id as id, email, email as username, full_name, role, is_active FROM users WHERE user_id = %s LIMIT 1"
                cursor.execute(sql, (user_id,))
                user = cursor.fetchone()
                if user:
                    assessment_rec = get_agent_assessment(user["id"])
                    user["assessment"] = assessment_rec.get("assessment") if assessment_rec else None
                    user["competency_level"] = assessment_rec.get("competency_level") if assessment_rec else None
                    user["confidence"] = assessment_rec.get("confidence") if assessment_rec else None
                    return user
        except Exception as e:
            logger.error(f"Error querying MySQL: {e}")
        finally:
            conn.close()

    for user in FALLBACK_USERS:
        if user["id"] == int(user_id):
            assessment_rec = get_agent_assessment(user["id"])
            safe_u = {k: v for k, v in user.items() if k != "password_hash"}
            safe_u["assessment"] = assessment_rec.get("assessment") if assessment_rec else user.get("assessment")
            safe_u["competency_level"] = assessment_rec.get("competency_level") if assessment_rec else user.get("competency_level")
            safe_u["confidence"] = assessment_rec.get("confidence") if assessment_rec else None
            return safe_u
    return None

def verify_credentials(identifier, password):
    if not identifier or not password:
        return None, "Both email/username and password are required."

    user = find_user_by_credential(identifier)
    if not user:
        return None, "Invalid email/username or password."

    if not user.get("is_active", True):
        return None, "This account is inactive. Please contact your administrator."

    if not check_password_hash(user["password_hash"], password):
        return None, "Invalid email/username or password."

    canonical_role = normalize_role(user["role"])
    assessment_rec = get_agent_assessment(user["id"])
    assessment = assessment_rec.get("assessment") if assessment_rec else user.get("assessment", None)
    competency_level = assessment_rec.get("competency_level") if assessment_rec else user.get("competency_level", None)
    confidence = assessment_rec.get("confidence") if assessment_rec else None

    safe_user = {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "fullName": user["full_name"],
        "role": canonical_role,
        "assessment": assessment,
        "competency_level": competency_level,
        "confidence": confidence,
        "dashboardUrl": "/admin/dashboard" if canonical_role == "Administrator" else "/agent/dashboard"
    }
    return safe_user, None

def create_agent_user(full_name, email, phone, password_hash, email_verified=True):
    conn = get_mysql_connection()
    if not conn:
        return False, "Database connection error"

    try:
        with conn.cursor() as cursor:
            email_lower = email.lower()
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email_lower,))
            if cursor.fetchone():
                return False, "An account with this email already exists."

            sql_user = """
                INSERT INTO users (email, password_hash, full_name, role, is_active, email_verified)
                VALUES (%s, %s, %s, 'AGENT', TRUE, %s)
            """
            cursor.execute(sql_user, (email_lower, password_hash, full_name, bool(email_verified)))
            user_id = cursor.lastrowid

            sql_agent = """
                INSERT INTO agents (user_id, phone, experience_months, availability_status, status)
                VALUES (%s, %s, 0, 'AVAILABLE', 'ACTIVE')
            """
            cursor.execute(sql_agent, (user_id, phone))

        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating agent user: {e}")
        return False, "An error occurred during registration."
    finally:
        conn.close()

def find_or_create_google_user(email, full_name):
    user = find_user_by_credential(email)
    if user:
        canonical_role = normalize_role(user["role"])
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user.get("username", user["email"]),
            "fullName": user.get("full_name", full_name),
            "role": canonical_role,
            "dashboardUrl": "/admin/dashboard" if canonical_role == "Administrator" else "/agent/dashboard"
        }, None

    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                dummy_hash = generate_password_hash(os.urandom(24).hex())
                sql_user = """
                    INSERT INTO users (email, username, password_hash, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, 'Agent', TRUE)
                """
                cursor.execute(sql_user, (email.lower(), email.lower(), dummy_hash, full_name))
                user_id = cursor.lastrowid
                conn.commit()

                return {
                    "id": user_id,
                    "email": email,
                    "username": email,
                    "fullName": full_name,
                    "role": "Agent",
                    "dashboardUrl": "/agent/dashboard"
                }, None
        except Exception as e:
            logger.error(f"Error creating Google user in MySQL: {e}")
        finally:
            conn.close()

    new_id = len(FALLBACK_USERS) + 1
    new_user = {
        "id": new_id,
        "email": email,
        "username": email,
        "password_hash": generate_password_hash("google-auth-placeholder"),
        "full_name": full_name,
        "role": "Agent",
        "is_active": True,
    }
    FALLBACK_USERS.append(new_user)
    return {
        "id": new_id,
        "email": email,
        "username": email,
        "fullName": full_name,
        "role": "Agent",
        "dashboardUrl": "/agent/dashboard"
    }, None

def store_otp(email, code):
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM email_verifications WHERE email = %s", (email.lower(),))
                sql = """
                    INSERT INTO email_verifications (email, code, expires_at, used)
                    VALUES (%s, %s, %s, FALSE)
                """
                cursor.execute(sql, (email.lower(), code, datetime.now() + timedelta(minutes=10)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing OTP: {e}")
        finally:
            conn.close()

    PENDING_VERIFICATIONS[email.lower()] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=10),
        "used": False
    }
    return True

def verify_otp(email, code):
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT id FROM email_verifications
                    WHERE email = %s AND code = %s AND expires_at > NOW() AND used = FALSE
                    LIMIT 1
                """
                cursor.execute(sql, (email.lower(), code))
                row = cursor.fetchone()
                if row:
                    cursor.execute("UPDATE email_verifications SET used = TRUE WHERE id = %s", (row["id"],))
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
        finally:
            conn.close()

    record = PENDING_VERIFICATIONS.get(email.lower())
    if record and not record["used"] and record["code"] == code:
        if datetime.now() < record["expires_at"]:
            record["used"] = True
            return True
    return False


# =====================================================================
# ADMIN DASHBOARD DATABASE HELPERS
# =====================================================================

def serialize_sql_value(val):
    """Serialize MySQL Decimal, datetime, and timedelta values safely for JSON."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, timedelta)):
        return val.isoformat() if hasattr(val, "isoformat") else str(val)
    return val


def serialize_sql_row(row):
    """Serialize a dictionary row returned by DictCursor."""
    if not row or not isinstance(row, dict):
        return row
    return {k: serialize_sql_value(v) for k, v in row.items()}


def get_admin_overview_metrics():
    """Aggregate KPIs, active model info, and recent assessments for admin overview."""
    conn = get_mysql_connection()
    if not conn:
        return {
            "total_agents": len([u for u in FALLBACK_USERS if u.get("role") == "Agent"]),
            "active_agents": len([u for u in FALLBACK_USERS if u.get("role") == "Agent"]),
            "total_tasks": 0,
            "active_tasks": 0,
            "total_assessments": len(FALLBACK_ASSESSMENTS),
            "passed_assessments": 0,
            "pending_reviews": 0,
            "completed_reviews": 0,
            "active_model": None,
            "recent_assessments": []
        }

    try:
        with conn.cursor() as cursor:
            # 1. Metric counts
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM agents) AS total_agents,
                    (SELECT COUNT(*) FROM agents WHERE status = 'ACTIVE') AS active_agents,
                    (SELECT COUNT(*) FROM tasks) AS total_tasks,
                    (SELECT COUNT(*) FROM tasks WHERE status = 'ACTIVE') AS active_tasks,
                    (SELECT COUNT(*) FROM exam_results) AS total_assessments,
                    (SELECT COUNT(*) FROM exam_results WHERE passed = 1) AS passed_assessments,
                    (SELECT COUNT(*) FROM eligibility_evaluations WHERE review_status = 'PENDING') AS pending_reviews,
                    (SELECT COUNT(*) FROM eligibility_evaluations WHERE review_status IN ('APPROVED', 'REJECTED')) AS completed_reviews
            """)
            counts = serialize_sql_row(cursor.fetchone() or {})

            # 2. Active Model Record
            cursor.execute("""
                SELECT model_id, model_name, model_version, algorithm, feature_set_version, is_active, created_at
                FROM ml_models
                WHERE is_active = 1
                ORDER BY model_id DESC LIMIT 1
            """)
            active_model = serialize_sql_row(cursor.fetchone())

            # 3. Recent assessments
            cursor.execute("""
                SELECT 
                    er.exam_result_id,
                    er.agent_id,
                    u.full_name AS agent_name,
                    u.email AS agent_email,
                    er.assessment_score,
                    er.passed,
                    er.attempt_number,
                    er.completed_at,
                    mp.prediction_id,
                    mp.predicted_competency,
                    mp.confidence
                FROM exam_results er
                JOIN agents a ON er.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                LEFT JOIN ml_predictions mp ON er.exam_result_id = mp.exam_result_id
                ORDER BY er.completed_at DESC, er.exam_result_id DESC
                LIMIT 5
            """)
            recent_assessments = [serialize_sql_row(row) for row in cursor.fetchall()]

            counts["active_model"] = active_model
            counts["recent_assessments"] = recent_assessments
            return counts
    except Exception as e:
        logger.error(f"Error fetching admin overview metrics: {e}")
        return None
    finally:
        conn.close()


def get_admin_agents():
    """Retrieve agent directory with user profile data, total attempts, and latest prediction."""
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.agent_id,
                    a.user_id,
                    u.full_name,
                    u.email,
                    a.phone,
                    a.education,
                    a.experience_months,
                    a.availability_status,
                    a.status,
                    u.created_at,
                    u.last_login_at,
                    latest_p.predicted_competency,
                    latest_p.confidence,
                    latest_p.predicted_at,
                    latest_er.assessment_score,
                    latest_er.attempt_number,
                    (SELECT COUNT(*) FROM exam_results WHERE agent_id = a.agent_id) AS total_attempts
                FROM agents a
                JOIN users u ON a.user_id = u.user_id
                LEFT JOIN (
                    SELECT mp1.agent_id, mp1.predicted_competency, mp1.confidence, mp1.predicted_at, mp1.exam_result_id
                    FROM ml_predictions mp1
                    JOIN (
                        SELECT agent_id, MAX(prediction_id) AS max_pid
                        FROM ml_predictions
                        GROUP BY agent_id
                    ) sub ON mp1.prediction_id = sub.max_pid
                ) latest_p ON a.agent_id = latest_p.agent_id
                LEFT JOIN exam_results latest_er ON latest_p.exam_result_id = latest_er.exam_result_id
                ORDER BY a.agent_id ASC
            """)
            rows = cursor.fetchall()
            agents = []
            for r in rows:
                row = serialize_sql_row(r)
                if row.get("confidence") is not None:
                    c = float(row["confidence"])
                    row["confidence_percent"] = round(c * 100.0 if c <= 1.0 else c, 1)
                else:
                    row["confidence_percent"] = None
                agents.append(row)
            return agents
    except Exception as e:
        logger.error(f"Error fetching admin agents directory: {e}")
        return []
    finally:
        conn.close()


def get_admin_tasks():
    """Retrieve list of tasks with category, configured requirements, compensation, and application count."""
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    t.task_id,
                    t.category_id,
                    c.category_name,
                    t.task_name,
                    t.description,
                    t.status,
                    t.work_arrangement,
                    t.location,
                    t.deliverables,
                    t.required_skills,
                    t.payment_type,
                    t.currency,
                    t.hourly_rate_min,
                    t.hourly_rate_max,
                    t.fixed_budget,
                    t.positions_count,
                    t.application_deadline,
                    t.expected_duration,
                    t.exam_id,
                    e.exam_name,
                    e.passing_score,
                    t.created_at,
                    t.updated_at,
                    tr.requirement_id,
                    tr.minimum_competency,
                    tr.required_certification_id,
                    cert.certification_name,
                    tr.minimum_experience_months,
                    tr.required_skill_id,
                    sk.skill_name,
                    tr.minimum_skill_score,
                    tr.exam_required,
                    (SELECT COUNT(*) FROM eligibility_evaluations ee WHERE ee.task_id = t.task_id) AS evaluation_count,
                    (SELECT COUNT(*) FROM task_applications ta WHERE ta.task_id = t.task_id) AS application_count
                FROM tasks t
                JOIN categories c ON t.category_id = c.category_id
                LEFT JOIN task_requirements tr ON t.task_id = tr.task_id
                LEFT JOIN certifications cert ON tr.required_certification_id = cert.certification_id
                LEFT JOIN skills sk ON tr.required_skill_id = sk.skill_id
                LEFT JOIN exams e ON t.exam_id = e.exam_id
                ORDER BY t.task_id DESC
            """)
            return [serialize_sql_row(r) for r in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching admin tasks: {e}")
        return []
    finally:
        conn.close()


def get_task_metadata():
    """Retrieve category, certification, skill, and exam template lookup lists for task creation/editing."""
    conn = get_mysql_connection()
    if not conn:
        return {"categories": [], "certifications": [], "skills": [], "exams": []}

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT category_id, category_name, description FROM categories ORDER BY category_name ASC")
            categories = [serialize_sql_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT certification_id, category_id, certification_name, description, validity_period_months FROM certifications ORDER BY certification_name ASC")
            certifications = [serialize_sql_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT skill_id, category_id, skill_name, description FROM skills ORDER BY skill_name ASC")
            skills = [serialize_sql_row(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT 
                    e.exam_id, 
                    e.category_id, 
                    c.category_name, 
                    e.exam_name, 
                    e.description, 
                    e.passing_score, 
                    e.status,
                    (SELECT COUNT(*) FROM exam_questions eq WHERE eq.exam_id = e.exam_id) AS question_count
                FROM exams e
                JOIN categories c ON e.category_id = c.category_id
                WHERE e.status = 'ACTIVE'
                ORDER BY e.exam_name ASC
            """)
            exams = [serialize_sql_row(r) for r in cursor.fetchall()]

            return {
                "categories": categories,
                "certifications": certifications,
                "skills": skills,
                "exams": exams
            }
    except Exception as e:
        logger.error(f"Error fetching task metadata: {e}")
        return {"categories": [], "certifications": [], "skills": [], "exams": []}
    finally:
        conn.close()


def get_admin_task_detail(task_id):
    """Retrieve complete task details, requirements, and metadata for a single task."""
    conn = get_mysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    t.task_id,
                    t.category_id,
                    c.category_name,
                    t.task_name,
                    t.description,
                    t.status,
                    t.work_arrangement,
                    t.location,
                    t.deliverables,
                    t.required_skills,
                    t.payment_type,
                    t.currency,
                    t.hourly_rate_min,
                    t.hourly_rate_max,
                    t.fixed_budget,
                    t.positions_count,
                    t.application_deadline,
                    t.expected_duration,
                    t.exam_id,
                    e.exam_name,
                    e.passing_score,
                    t.created_at,
                    t.updated_at,
                    tr.requirement_id,
                    tr.minimum_competency,
                    tr.required_certification_id,
                    cert.certification_name,
                    tr.minimum_experience_months,
                    tr.required_skill_id,
                    sk.skill_name,
                    tr.minimum_skill_score,
                    tr.exam_required,
                    (SELECT COUNT(*) FROM task_applications ta WHERE ta.task_id = t.task_id) AS application_count
                FROM tasks t
                JOIN categories c ON t.category_id = c.category_id
                LEFT JOIN task_requirements tr ON t.task_id = tr.task_id
                LEFT JOIN certifications cert ON tr.required_certification_id = cert.certification_id
                LEFT JOIN skills sk ON tr.required_skill_id = sk.skill_id
                LEFT JOIN exams e ON t.exam_id = e.exam_id
                WHERE t.task_id = %s
                LIMIT 1
            """, (task_id,))
            row = cursor.fetchone()
            return serialize_sql_row(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching task {task_id} detail: {e}")
        return None
    finally:
        conn.close()


def _validate_task_payload(task_data, cursor=None):
    """
    Independently validate and normalize task creation/update payload.
    Enforces business rules for title, category, description, compensation,
    eligibility requirements, and assessment configuration.
    """
    task_name = (task_data.get("task_name") or "").strip()
    if not task_name:
        raise ValueError("Task title is required.")
    if len(task_name) < 5:
        raise ValueError("Task title must be at least 5 characters long.")
    if len(task_name) > 150:
        raise ValueError("Task title cannot exceed 150 characters.")

    # Generic title rejection
    generic_names = {"task 1", "task 2", "task", "test", "test task", "new task", "sample task", "untitled"}
    if task_name.lower() in generic_names:
        raise ValueError(f"Task title '{task_name}' is too generic. Please provide a descriptive title (e.g. 'Customer Support Specialist').")

    # Category validation
    raw_cat = task_data.get("category_id")
    if not raw_cat:
        raise ValueError("Task category is required.")
    try:
        category_id = int(raw_cat)
    except (ValueError, TypeError):
        raise ValueError("Invalid category ID format.")

    if cursor:
        cursor.execute("SELECT category_id FROM categories WHERE category_id = %s", (category_id,))
        if not cursor.fetchone():
            raise ValueError(f"Category ID {category_id} does not exist.")

    # Status
    status = (task_data.get("status") or "DRAFT").upper().strip()
    if status not in ("DRAFT", "ACTIVE", "INACTIVE", "COMPLETED"):
        raise ValueError("Invalid task status. Must be DRAFT, ACTIVE, INACTIVE, or COMPLETED.")

    is_publish = (status == "ACTIVE")

    # Description
    description = (task_data.get("description") or "").strip()
    if is_publish and len(description) < 20:
        raise ValueError("Detailed task description is required when publishing (minimum 20 characters).")

    # Work Arrangement
    work_arrangement = (task_data.get("work_arrangement") or "Remote").strip()
    if work_arrangement not in ("Remote", "Hybrid", "On-site"):
        work_arrangement = "Remote"

    location = (task_data.get("location") or "").strip() or None
    if is_publish and work_arrangement in ("Hybrid", "On-site") and not location:
        raise ValueError(f"Location or eligible region is required for {work_arrangement} work arrangement.")

    deliverables = (task_data.get("deliverables") or "").strip() or None

    # Required skills
    raw_skills = task_data.get("required_skills")
    if isinstance(raw_skills, list):
        required_skills = ", ".join([str(s).strip() for s in raw_skills if str(s).strip()]) or None
    elif isinstance(raw_skills, str):
        required_skills = raw_skills.strip() or None
    else:
        required_skills = None

    # Compensation
    payment_type = (task_data.get("payment_type") or "Fixed Budget").strip()
    if payment_type not in ("Hourly", "Fixed Budget"):
        payment_type = "Fixed Budget"

    currency = (task_data.get("currency") or "KES").strip().upper()[:10]

    hourly_rate_min = None
    hourly_rate_max = None
    fixed_budget = None

    if payment_type == "Hourly":
        raw_h_min = task_data.get("hourly_rate_min")
        raw_h_max = task_data.get("hourly_rate_max")

        if is_publish:
            if raw_h_min in (None, ""):
                raise ValueError("Minimum hourly rate is required for hourly compensation.")
            try:
                hourly_rate_min = float(raw_h_min)
                if hourly_rate_min <= 0:
                    raise ValueError("Minimum hourly rate must be greater than zero.")
            except (ValueError, TypeError):
                raise ValueError("Minimum hourly rate must be a valid positive number.")

            if raw_h_max not in (None, ""):
                try:
                    hourly_rate_max = float(raw_h_max)
                    if hourly_rate_max < hourly_rate_min:
                        raise ValueError("Maximum hourly rate cannot be less than minimum hourly rate.")
                except (ValueError, TypeError):
                    raise ValueError("Maximum hourly rate must be a valid number.")
        else:
            if raw_h_min not in (None, ""):
                try:
                    hourly_rate_min = float(raw_h_min)
                except:
                    pass
            if raw_h_max not in (None, ""):
                try:
                    hourly_rate_max = float(raw_h_max)
                except:
                    pass

    elif payment_type == "Fixed Budget":
        raw_budget = task_data.get("fixed_budget")
        if is_publish:
            if raw_budget in (None, ""):
                raise ValueError("Total fixed budget is required for fixed-price work.")
            try:
                fixed_budget = float(raw_budget)
                if fixed_budget <= 0:
                    raise ValueError("Total fixed budget must be greater than zero.")
            except (ValueError, TypeError):
                raise ValueError("Total fixed budget must be a valid positive number.")
        else:
            if raw_budget not in (None, ""):
                try:
                    fixed_budget = float(raw_budget)
                except:
                    pass

    # Positions count
    raw_positions = task_data.get("positions_count", 1)
    try:
        positions_count = max(1, int(raw_positions or 1))
    except (ValueError, TypeError):
        positions_count = 1

    # Application deadline
    raw_deadline = task_data.get("application_deadline")
    application_deadline = None
    if raw_deadline:
        try:
            if isinstance(raw_deadline, str):
                deadline_date = datetime.strptime(raw_deadline.split("T")[0], "%Y-%m-%d").date()
            else:
                deadline_date = raw_deadline

            if is_publish and deadline_date < datetime.now().date():
                raise ValueError("Application deadline must be a future date.")
            application_deadline = deadline_date.strftime("%Y-%m-%d")
        except ValueError as ve:
            if "future date" in str(ve):
                raise ve
            raise ValueError("Application deadline must be a valid date in YYYY-MM-DD format.")
    elif is_publish:
        raise ValueError("Application deadline is required when publishing a task.")

    expected_duration = (task_data.get("expected_duration") or "").strip() or None

    # Section C: Eligibility requirements
    min_comp = (task_data.get("minimum_competency") or "BASIC").upper().strip()
    if min_comp not in ("NEEDS_IMPROVEMENT", "BASIC", "COMPETENT", "ADVANCED"):
        min_comp = "BASIC"

    raw_min_exp = task_data.get("minimum_experience_months", 0)
    try:
        min_exp = max(0, int(raw_min_exp or 0))
    except (ValueError, TypeError):
        min_exp = 0

    raw_cert_id = task_data.get("required_certification_id")
    cert_id = None
    if raw_cert_id not in (None, "", "NONE", 0, "0"):
        try:
            cert_id = int(raw_cert_id)
            if cursor:
                cursor.execute("SELECT certification_id FROM certifications WHERE certification_id = %s", (cert_id,))
                if not cursor.fetchone():
                    raise ValueError(f"Certification ID {cert_id} does not exist.")
        except (ValueError, TypeError):
            raise ValueError("Invalid certification ID.")

    raw_skill_id = task_data.get("required_skill_id")
    skill_id = None
    if raw_skill_id not in (None, "", "NONE", 0, "0"):
        try:
            skill_id = int(raw_skill_id)
        except (ValueError, TypeError):
            skill_id = None

    raw_skill_score = task_data.get("minimum_skill_score")
    min_skill_score = None
    if raw_skill_score not in (None, ""):
        try:
            min_skill_score = max(0.0, min(100.0, float(raw_skill_score)))
        except (ValueError, TypeError):
            min_skill_score = None

    # Section D: Assessment configuration
    exam_req = 1 if bool(task_data.get("exam_required", False)) else 0
    raw_exam_id = task_data.get("exam_id")
    exam_id = None

    if exam_req:
        if raw_exam_id not in (None, "", 0, "0"):
            try:
                exam_id = int(raw_exam_id)
            except (ValueError, TypeError):
                raise ValueError("Invalid exam template ID.")

        if cursor:
            if exam_id:
                cursor.execute("SELECT exam_id, category_id, status FROM exams WHERE exam_id = %s", (exam_id,))
                exam_row = cursor.fetchone()
                if not exam_row:
                    raise ValueError(f"Assessment template ID {exam_id} does not exist.")
                if exam_row["status"] != "ACTIVE":
                    raise ValueError("Selected assessment template is not ACTIVE.")
            else:
                cursor.execute("SELECT exam_id FROM exams WHERE category_id = %s AND status = 'ACTIVE' LIMIT 1", (category_id,))
                matching_exam = cursor.fetchone()
                if matching_exam:
                    exam_id = matching_exam["exam_id"]
                elif is_publish:
                    raise ValueError("No active assessment template found for this category.")

            if is_publish and exam_id:
                cursor.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id = %s", (exam_id,))
                q_count = cursor.fetchone()["cnt"]
                if q_count == 0:
                    raise ValueError(f"Assessment template ID {exam_id} has no configured questions in the server bank.")

    return {
        "task_name": task_name,
        "category_id": category_id,
        "description": description,
        "status": status,
        "work_arrangement": work_arrangement,
        "location": location,
        "deliverables": deliverables,
        "required_skills": required_skills,
        "payment_type": payment_type,
        "currency": currency,
        "hourly_rate_min": hourly_rate_min,
        "hourly_rate_max": hourly_rate_max,
        "fixed_budget": fixed_budget,
        "positions_count": positions_count,
        "application_deadline": application_deadline,
        "expected_duration": expected_duration,
        "minimum_competency": min_comp,
        "required_certification_id": cert_id,
        "minimum_experience_months": min_exp,
        "required_skill_id": skill_id,
        "minimum_skill_score": min_skill_score,
        "exam_required": exam_req,
        "exam_id": exam_id
    }


def create_task_with_requirements(task_data, admin_user_id=None):
    """
    Create a new task and its requirements transactionally.
    Logs an audit event for tracking.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")

    try:
        with conn.cursor() as cursor:
            validated = _validate_task_payload(task_data, cursor=cursor)

            cursor.execute("""
                INSERT INTO tasks (
                    category_id, task_name, description, status,
                    work_arrangement, location, deliverables, required_skills,
                    payment_type, currency, hourly_rate_min, hourly_rate_max, fixed_budget,
                    positions_count, application_deadline, expected_duration, exam_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                validated["category_id"], validated["task_name"], validated["description"], validated["status"],
                validated["work_arrangement"], validated["location"], validated["deliverables"], validated["required_skills"],
                validated["payment_type"], validated["currency"], validated["hourly_rate_min"], validated["hourly_rate_max"], validated["fixed_budget"],
                validated["positions_count"], validated["application_deadline"], validated["expected_duration"], validated["exam_id"]
            ))
            task_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO task_requirements (
                    task_id, minimum_competency, required_certification_id,
                    minimum_experience_months, required_skill_id,
                    minimum_skill_score, exam_required
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id, validated["minimum_competency"], validated["required_certification_id"],
                validated["minimum_experience_months"], validated["required_skill_id"],
                validated["minimum_skill_score"], validated["exam_required"]
            ))
            requirement_id = cursor.lastrowid

            # Audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_CREATED', 'tasks', %s, %s, NOW())
            """, (admin_user_id, task_id, json.dumps({
                "task_name": validated["task_name"],
                "category_id": validated["category_id"],
                "status": validated["status"],
                "minimum_competency": validated["minimum_competency"],
                "payment_type": validated["payment_type"]
            })))

        conn.commit()
        return {
            "task_id": task_id,
            "requirement_id": requirement_id,
            "task_name": validated["task_name"],
            "status": validated["status"]
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating task: {e}")
        if isinstance(e, ValueError):
            raise e
        raise RuntimeError(f"Failed to create task: {str(e)}")
    finally:
        conn.close()


def update_task_with_requirements(task_id, task_data, admin_user_id=None):
    """Update an existing task and its requirements transactionally."""
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT task_id, status FROM tasks WHERE task_id = %s", (task_id,))
            existing = cursor.fetchone()
            if not existing:
                raise ValueError(f"Task with ID {task_id} not found.")

            validated = _validate_task_payload(task_data, cursor=cursor)

            cursor.execute("""
                UPDATE tasks
                SET 
                    category_id = %s, task_name = %s, description = %s, status = %s,
                    work_arrangement = %s, location = %s, deliverables = %s, required_skills = %s,
                    payment_type = %s, currency = %s, hourly_rate_min = %s, hourly_rate_max = %s, fixed_budget = %s,
                    positions_count = %s, application_deadline = %s, expected_duration = %s, exam_id = %s,
                    updated_at = NOW()
                WHERE task_id = %s
            """, (
                validated["category_id"], validated["task_name"], validated["description"], validated["status"],
                validated["work_arrangement"], validated["location"], validated["deliverables"], validated["required_skills"],
                validated["payment_type"], validated["currency"], validated["hourly_rate_min"], validated["hourly_rate_max"], validated["fixed_budget"],
                validated["positions_count"], validated["application_deadline"], validated["expected_duration"], validated["exam_id"],
                task_id
            ))

            cursor.execute("SELECT requirement_id FROM task_requirements WHERE task_id = %s LIMIT 1", (task_id,))
            req_row = cursor.fetchone()
            if req_row:
                cursor.execute("""
                    UPDATE task_requirements
                    SET minimum_competency = %s, required_certification_id = %s,
                        minimum_experience_months = %s, required_skill_id = %s,
                        minimum_skill_score = %s, exam_required = %s
                    WHERE task_id = %s
                """, (
                    validated["minimum_competency"], validated["required_certification_id"],
                    validated["minimum_experience_months"], validated["required_skill_id"],
                    validated["minimum_skill_score"], validated["exam_required"],
                    task_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO task_requirements (
                        task_id, minimum_competency, required_certification_id,
                        minimum_experience_months, required_skill_id,
                        minimum_skill_score, exam_required
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    task_id, validated["minimum_competency"], validated["required_certification_id"],
                    validated["minimum_experience_months"], validated["required_skill_id"],
                    validated["minimum_skill_score"], validated["exam_required"]
                ))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_UPDATED', 'tasks', %s, %s, NOW())
            """, (admin_user_id, task_id, json.dumps({
                "task_name": validated["task_name"],
                "category_id": validated["category_id"],
                "status": validated["status"]
            })))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating task {task_id}: {e}")
        if isinstance(e, ValueError):
            raise e
        raise RuntimeError(f"Failed to update task: {str(e)}")
    finally:
        conn.close()


def set_task_status(task_id, status, admin_user_id=None):
    """Toggle or update status of a task (e.g. ACTIVE, INACTIVE, DRAFT, COMPLETED)."""
    if status not in ("DRAFT", "ACTIVE", "INACTIVE", "COMPLETED"):
        raise ValueError(f"Invalid status: {status}")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT task_id, task_name, status FROM tasks WHERE task_id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise ValueError(f"Task {task_id} not found.")

            cursor.execute("UPDATE tasks SET status = %s, updated_at = NOW() WHERE task_id = %s", (status, task_id))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_STATUS_CHANGED', 'tasks', %s, %s, NOW())
            """, (admin_user_id, task_id, json.dumps({
                "previous_status": task["status"],
                "new_status": status,
                "task_name": task["task_name"]
            })))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error changing status for task {task_id}: {e}")
        raise RuntimeError(f"Failed to set status: {str(e)}")
    finally:
        conn.close()


def get_admin_assessments():
    """Retrieve all historical competency assessments across all agents."""
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    er.exam_result_id,
                    er.exam_id,
                    er.agent_id,
                    u.full_name AS agent_name,
                    u.email AS agent_email,
                    er.assessment_score,
                    er.passed,
                    er.attempt_number,
                    er.completed_at,
                    mp.prediction_id,
                    mp.predicted_competency,
                    mp.confidence,
                    mp.predicted_at,
                    al.description AS audit_payload
                FROM exam_results er
                JOIN agents a ON er.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                LEFT JOIN ml_predictions mp ON er.exam_result_id = mp.exam_result_id
                LEFT JOIN audit_logs al ON (al.entity_type = 'ml_predictions' AND al.entity_id = mp.prediction_id AND al.action = 'ASSESSMENT_COMPLETED')
                ORDER BY er.completed_at DESC, er.exam_result_id DESC
            """)
            rows = cursor.fetchall()
            assessments = []
            for r in rows:
                item = serialize_sql_row(r)
                if item.get("confidence") is not None:
                    c = float(item["confidence"])
                    item["confidence_percent"] = round(c * 100.0 if c <= 1.0 else c, 1)
                else:
                    item["confidence_percent"] = None

                raw_payload = item.pop("audit_payload", None)
                features = {}
                if raw_payload:
                    try:
                        parsed = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                        features = parsed.get("assessment_data", {})
                    except Exception:
                        features = {}
                item["features"] = features
                assessments.append(item)
            return assessments
    except Exception as e:
        logger.error(f"Error fetching admin assessments: {e}")
        return []
    finally:
        conn.close()


def get_admin_reviews():
    """Retrieve eligibility evaluations from v_eligibility_summary view."""
    conn = get_mysql_connection()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    evaluation_id,
                    agent_id,
                    agent_name,
                    agent_email,
                    task_id,
                    task_name,
                    prediction_id,
                    predicted_competency,
                    prediction_confidence,
                    eligibility_status,
                    review_status,
                    explanation,
                    evaluated_at,
                    reviewed_at
                FROM v_eligibility_summary
                ORDER BY evaluated_at DESC
            """)
            reviews = []
            for r in cursor.fetchall():
                row = serialize_sql_row(r)
                if row.get("prediction_confidence") is not None:
                    c = float(row["prediction_confidence"])
                    row["confidence_percent"] = round(c * 100.0 if c <= 1.0 else c, 1)
                else:
                    row["confidence_percent"] = None
                reviews.append(row)
            return reviews
    except Exception as e:
        logger.error(f"Error fetching admin reviews: {e}")
        return []
    finally:
        conn.close()


def get_admin_review_detail(evaluation_id):
    """Retrieve detailed breakdown of an eligibility evaluation including check criteria."""
    conn = get_mysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            # 1. Summary details
            cursor.execute("""
                SELECT 
                    ee.evaluation_id,
                    ee.agent_id,
                    u.full_name AS agent_name,
                    u.email AS agent_email,
                    ee.task_id,
                    t.task_name,
                    ee.prediction_id,
                    mp.predicted_competency,
                    mp.confidence AS prediction_confidence,
                    ee.eligibility_status,
                    ee.review_status,
                    ee.explanation,
                    ee.reviewer_id,
                    rev_u.full_name AS reviewer_name,
                    ee.review_comments,
                    ee.evaluated_at,
                    ee.reviewed_at
                FROM eligibility_evaluations ee
                JOIN agents a ON ee.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                JOIN tasks t ON ee.task_id = t.task_id
                LEFT JOIN ml_predictions mp ON ee.prediction_id = mp.prediction_id
                LEFT JOIN users rev_u ON ee.reviewer_id = rev_u.user_id
                WHERE ee.evaluation_id = %s
                LIMIT 1
            """, (evaluation_id,))
            detail_row = cursor.fetchone()
            if not detail_row:
                return None

            detail = serialize_sql_row(detail_row)
            if detail.get("prediction_confidence") is not None:
                c = float(detail["prediction_confidence"])
                detail["confidence_percent"] = round(c * 100.0 if c <= 1.0 else c, 1)

            # 2. Individual requirement checks
            cursor.execute("""
                SELECT 
                    check_id,
                    evaluation_id,
                    requirement_type,
                    expected_value,
                    actual_value,
                    passed,
                    failure_reason
                FROM eligibility_checks
                WHERE evaluation_id = %s
                ORDER BY check_id ASC
            """, (evaluation_id,))
            checks = [serialize_sql_row(c) for c in cursor.fetchall()]
            detail["checks"] = checks
            return detail
    except Exception as e:
        logger.error(f"Error fetching review detail {evaluation_id}: {e}")
        return None
    finally:
        conn.close()


# =====================================================================
# AGENT PROFILE, EXPERIENCE, AND CERTIFICATION WORKFLOWS
# =====================================================================

def calculate_agent_verified_experience(agent_id, cursor=None):
    """
    Safely calculate verified experience months for an agent from approved records.
    Merges overlapping date intervals within categories to prevent double-counting.
    """
    def _calc_with_cursor(cur):
        cur.execute("""
            SELECT job_title, company, work_category, start_date, end_date, is_current
            FROM agent_experience
            WHERE agent_id = %s AND verification_status = 'VERIFIED'
            ORDER BY start_date ASC
        """, (agent_id,))
        rows = cur.fetchall()

        today = datetime.now().date()

        def _merge_intervals(intervals):
            if not intervals:
                return []
            sorted_ints = sorted(intervals, key=lambda x: (x[0], x[1]))
            merged = []
            for start, end in sorted_ints:
                if not merged:
                    merged.append([start, end])
                else:
                    prev_start, prev_end = merged[-1]
                    if start <= prev_end:
                        merged[-1][1] = max(prev_end, end)
                    else:
                        merged.append([start, end])
            return merged

        def _duration_months(merged):
            total = 0
            for start, end in merged:
                months = (end.year - start.year) * 12 + (end.month - start.month)
                total += max(1, months)
            return total

        sales_intervals = []
        cs_intervals = []
        all_intervals = []

        for r in rows:
            start = r["start_date"]
            if isinstance(start, str):
                start = datetime.strptime(start, "%Y-%m-%d").date()

            end = r["end_date"]
            if r["is_current"] or not end:
                end = today
            elif isinstance(end, str):
                end = datetime.strptime(end, "%Y-%m-%d").date()

            if start > end:
                continue

            interval = (start, end)
            all_intervals.append(interval)

            cat = r["work_category"]
            if cat == "Sales":
                sales_intervals.append(interval)
            elif cat == "Customer Service":
                cs_intervals.append(interval)

        merged_sales = _merge_intervals(sales_intervals)
        merged_cs = _merge_intervals(cs_intervals)
        merged_all = _merge_intervals(all_intervals)

        sales_months = _duration_months(merged_sales)
        cs_months = _duration_months(merged_cs)
        total_months = _duration_months(merged_all)

        # Update agents.experience_months
        cur.execute("""
            UPDATE agents 
            SET experience_months = %s, updated_at = NOW() 
            WHERE agent_id = %s
        """, (total_months, agent_id))

        return {
            "previous_experience_months": total_months,
            "total_experience_months": total_months,
            "sales_experience_months": sales_months,
            "customer_service_experience_months": cs_months,
            "other_experience_months": max(0, total_months - (sales_months + cs_months)),
            "verified_entries_count": len(rows)
        }

    if cursor:
        return _calc_with_cursor(cursor)

    conn = get_mysql_connection()
    if not conn:
        return {
            "previous_experience_months": 0,
            "total_experience_months": 0,
            "sales_experience_months": 0,
            "customer_service_experience_months": 0,
            "other_experience_months": 0,
            "verified_entries_count": 0
        }
    try:
        with conn.cursor() as cur:
            res = _calc_with_cursor(cur)
            conn.commit()
            return res
    except Exception as e:
        conn.rollback()
        logger.error(f"Error calculating verified experience for agent {agent_id}: {e}")
        return {
            "previous_experience_months": 0,
            "sales_experience_months": 0,
            "customer_service_experience_months": 0,
            "verified_entries_count": 0
        }
    finally:
        conn.close()


def calculate_agent_verified_certifications(agent_id, cursor=None):
    """
    Safely derive certification metrics from authoritative verified credentials.
    """
    def _calc_with_cursor(cur):
        cur.execute("""
            SELECT ac.agent_certification_id, ac.certification_id, ac.status, ac.expiry_date,
                   c.category_id, c.certification_name
            FROM agent_certifications ac
            LEFT JOIN certifications c ON ac.certification_id = c.certification_id
            WHERE ac.agent_id = %s 
              AND ac.status IN ('ACTIVE', 'VERIFIED')
              AND (ac.expiry_date IS NULL OR ac.expiry_date >= CURDATE())
        """, (agent_id,))
        rows = cur.fetchall()
        cert_count = len(rows)
        relevant_cert = 1.0 if cert_count > 0 else 0.0
        certified_leverage = cert_count * (1.0 + relevant_cert)
        return {
            "certification_count": float(cert_count),
            "relevant_certification": relevant_cert,
            "certified_leverage": certified_leverage,
            "active_cert_ids": [r["certification_id"] for r in rows if r["certification_id"]]
        }

    if cursor:
        return _calc_with_cursor(cursor)

    conn = get_mysql_connection()
    if not conn:
        return {"certification_count": 0.0, "relevant_certification": 0.0, "certified_leverage": 0.0, "active_cert_ids": []}
    try:
        with conn.cursor() as cur:
            return _calc_with_cursor(cur)
    finally:
        conn.close()


def get_agent_profile_data(user_id):
    """
    Retrieve comprehensive agent profile data including verified work experience,
    certifications, assessment summary, and reliable readiness percentage.
    """
    conn = get_mysql_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    u.user_id,
                    u.full_name,
                    u.email,
                    u.role,
                    u.is_active,
                    u.email_verified,
                    u.created_at AS member_since,
                    a.agent_id,
                    a.phone,
                    a.education,
                    a.bio,
                    a.location,
                    a.availability_status,
                    a.status AS agent_status,
                    a.experience_months
                FROM users u
                JOIN agents a ON u.user_id = a.user_id
                WHERE u.user_id = %s
                LIMIT 1
            """, (user_id,))
            user_row = cur.fetchone()
            if not user_row:
                return None

            profile = serialize_sql_row(user_row)
            agent_id = profile["agent_id"]

            exp_metrics = calculate_agent_verified_experience(agent_id, cur)
            profile["verified_experience"] = exp_metrics

            cert_metrics = calculate_agent_verified_certifications(agent_id, cur)
            profile["verified_certifications"] = cert_metrics

            assessment_rec = get_agent_assessment(user_id)
            profile["assessment_summary"] = {
                "has_assessed": bool(assessment_rec and assessment_rec.get("has_assessed")),
                "competency_level": assessment_rec.get("competency_level", "Not Yet Assessed") if assessment_rec else "Not Yet Assessed",
                "evaluation_decision": assessment_rec.get("evaluation_decision", "Not Yet Evaluated") if assessment_rec else "Not Yet Evaluated",
                "confidence": assessment_rec.get("confidence") if assessment_rec else None,
                "attempt_number": assessment_rec.get("attempt_number", 0) if assessment_rec else 0,
                "completed_at": assessment_rec.get("completed_at") if assessment_rec else None,
                "overall_score": assessment_rec.get("assessment", {}).get("assessment_score") if assessment_rec and assessment_rec.get("assessment") else None,
                "scores": {
                    "communication": assessment_rec.get("assessment", {}).get("communication_score") if assessment_rec and assessment_rec.get("assessment") else None,
                    "product_knowledge": assessment_rec.get("assessment", {}).get("product_knowledge_score") if assessment_rec and assessment_rec.get("assessment") else None,
                    "sales_skill": assessment_rec.get("assessment", {}).get("sales_skill_score") if assessment_rec and assessment_rec.get("assessment") else None,
                    "customer_service": assessment_rec.get("assessment", {}).get("customer_service_score") if assessment_rec and assessment_rec.get("assessment") else None,
                }
            }

            readiness = 0
            readiness_checks = {
                "personal_info": bool(profile.get("phone") and profile.get("location") and profile.get("bio")),
                "assessment": bool(profile["assessment_summary"]["has_assessed"]),
                "experience": exp_metrics["verified_entries_count"] > 0,
                "certification": cert_metrics["certification_count"] > 0
            }
            if readiness_checks["personal_info"]:
                readiness += 25
            if readiness_checks["assessment"]:
                readiness += 25
            if readiness_checks["experience"]:
                readiness += 25
            if readiness_checks["certification"]:
                readiness += 25

            profile["readiness_score"] = readiness
            profile["readiness_checks"] = readiness_checks

            conn.commit()
            return profile
    except Exception as e:
        logger.error(f"Error loading agent profile for user {user_id}: {e}")
        return None
    finally:
        conn.close()


def update_agent_profile(user_id, data):
    """
    Update editable personal information for an agent.
    Strictly prevents modification of system role, agent_id, verification statuses, or experience counts.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT agent_id FROM agents WHERE user_id = %s", (user_id,))
            ag = cur.fetchone()
            if not ag:
                raise ValueError("Agent profile not found")
            agent_id = ag["agent_id"]

            full_name = data.get("full_name")
            if full_name is not None:
                full_name = str(full_name).strip()
                if len(full_name) < 2:
                    raise ValueError("Full legal name must be at least 2 characters")
                cur.execute("UPDATE users SET full_name = %s, updated_at = NOW() WHERE user_id = %s", (full_name, user_id))

            phone = data.get("phone")
            location = data.get("location")
            bio = data.get("bio")

            cur.execute("""
                UPDATE agents 
                SET phone = %s, location = %s, bio = %s, updated_at = NOW()
                WHERE agent_id = %s
            """, (
                str(phone).strip() if phone else None,
                str(location).strip() if location else None,
                str(bio).strip() if bio else None,
                agent_id
            ))

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'AGENT_PROFILE_UPDATED', 'agents', %s, 'Personal profile details updated', NOW())
            """, (user_id, agent_id))

            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating agent profile for user {user_id}: {e}")
        raise
    finally:
        conn.close()


def get_agent_experiences(user_id):
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ae.experience_id, ae.agent_id, ae.job_title, ae.company, ae.work_category,
                       ae.description, ae.start_date, ae.end_date, ae.is_current,
                       ae.verification_status, ae.rejection_reason, ae.reviewed_at, ae.created_at,
                       rev.full_name AS reviewer_name
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                LEFT JOIN users rev ON ae.reviewed_by = rev.user_id
                WHERE a.user_id = %s
                ORDER BY ae.is_current DESC, ae.end_date DESC, ae.start_date DESC
            """, (user_id,))
            return [serialize_sql_row(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_agent_experience(user_id, exp_data):
    job_title = str(exp_data.get("job_title", "")).strip()
    company = str(exp_data.get("company", "")).strip()
    work_category = exp_data.get("work_category", "Other")
    start_date = exp_data.get("start_date")
    end_date = exp_data.get("end_date")
    is_current = bool(exp_data.get("is_current", False))
    description = exp_data.get("description", "").strip()

    if len(job_title) < 2:
        raise ValueError("Job title is required (minimum 2 characters)")
    if len(company) < 2:
        raise ValueError("Company or organization name is required (minimum 2 characters)")
    if work_category not in ("Sales", "Customer Service", "Other"):
        raise ValueError("Work category must be 'Sales', 'Customer Service', or 'Other'")
    if not start_date:
        raise ValueError("Start date is required")

    try:
        s_date = datetime.strptime(str(start_date), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Start date must be in YYYY-MM-DD format")

    if not is_current and end_date:
        try:
            e_date = datetime.strptime(str(end_date), "%Y-%m-%d").date()
            if s_date > e_date:
                raise ValueError("End date must be on or after start date")
        except ValueError:
            raise ValueError("End date must be in YYYY-MM-DD format")
    elif is_current:
        end_date = None

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT agent_id FROM agents WHERE user_id = %s", (user_id,))
            ag = cur.fetchone()
            if not ag:
                raise ValueError("Agent profile not found")
            agent_id = ag["agent_id"]

            cur.execute("""
                INSERT INTO agent_experience
                (agent_id, job_title, company, work_category, description, start_date, end_date, is_current, verification_status, created_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())
            """, (agent_id, job_title, company, work_category, description, start_date, end_date, 1 if is_current else 0))
            exp_id = cur.lastrowid

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'EXPERIENCE_SUBMITTED', 'agent_experience', %s, 'Submitted work experience for verification', NOW())
            """, (user_id, exp_id))

            conn.commit()
            return {"experience_id": exp_id, "verification_status": "PENDING"}
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_agent_experience(user_id, experience_id):
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ae.experience_id, ae.agent_id, ae.verification_status 
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                WHERE ae.experience_id = %s AND a.user_id = %s
            """, (experience_id, user_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Experience record not found or unauthorized")

            if row["verification_status"] == "VERIFIED":
                raise ValueError("Verified work experience cannot be deleted directly. Contact an administrator.")

            cur.execute("DELETE FROM agent_experience WHERE experience_id = %s", (experience_id,))
            conn.commit()
            return True
    finally:
        conn.close()


def get_agent_certifications_list(user_id):
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    ac.agent_certification_id,
                    ac.agent_id,
                    ac.certification_id,
                    COALESCE(c.certification_name, ac.issuing_organization, 'Professional Certification') AS certification_name,
                    ac.certificate_number,
                    ac.issuing_organization,
                    ac.credential_url,
                    ac.issue_date,
                    ac.expiry_date,
                    ac.status,
                    ac.rejection_reason,
                    ac.reviewed_at,
                    ac.created_at,
                    rev.full_name AS reviewer_name,
                    cat.category_name
                FROM agent_certifications ac
                JOIN agents a ON ac.agent_id = a.agent_id
                LEFT JOIN certifications c ON ac.certification_id = c.certification_id
                LEFT JOIN categories cat ON c.category_id = cat.category_id
                LEFT JOIN users rev ON ac.reviewed_by = rev.user_id
                WHERE a.user_id = %s
                ORDER BY ac.created_at DESC
            """, (user_id,))
            return [serialize_sql_row(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_agent_certification(user_id, cert_data):
    cert_id = cert_data.get("certification_id")
    custom_name = str(cert_data.get("certification_name", "")).strip()
    issuing_org = str(cert_data.get("issuing_organization", "")).strip()
    cert_number = str(cert_data.get("certificate_number", "")).strip()
    credential_url = str(cert_data.get("credential_url", "")).strip()
    issue_date = cert_data.get("issue_date")
    expiry_date = cert_data.get("expiry_date")

    if not cert_number:
        raise ValueError("Certificate or Credential ID is required")
    if not issue_date:
        raise ValueError("Issue date is required")

    try:
        i_date = datetime.strptime(str(issue_date), "%Y-%m-%d").date()
        if i_date > datetime.now().date():
            raise ValueError("Issue date cannot be in the future")
    except ValueError as ve:
        raise ValueError(str(ve) if "future" in str(ve) else "Issue date must be in YYYY-MM-DD format")

    if expiry_date:
        try:
            e_date = datetime.strptime(str(expiry_date), "%Y-%m-%d").date()
            if e_date <= i_date:
                raise ValueError("Expiry date must be after issue date")
        except ValueError as ve:
            raise ValueError(str(ve) if "after" in str(ve) else "Expiry date must be in YYYY-MM-DD format")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT agent_id FROM agents WHERE user_id = %s", (user_id,))
            ag = cur.fetchone()
            if not ag:
                raise ValueError("Agent profile not found")
            agent_id = ag["agent_id"]

            final_cert_id = None
            if cert_id:
                cur.execute("SELECT certification_id FROM certifications WHERE certification_id = %s", (cert_id,))
                c_row = cur.fetchone()
                if c_row:
                    final_cert_id = c_row["certification_id"]

            if not final_cert_id:
                cur.execute("SELECT certification_id FROM certifications ORDER BY certification_id ASC LIMIT 1")
                first_cert = cur.fetchone()
                final_cert_id = first_cert["certification_id"] if first_cert else 1

            cur.execute("SELECT agent_certification_id FROM agent_certifications WHERE certificate_number = %s", (cert_number,))
            if cur.fetchone():
                raise ValueError(f"A certificate with credential number '{cert_number}' is already registered")

            cur.execute("""
                INSERT INTO agent_certifications
                (agent_id, certification_id, certificate_number, issuing_organization, credential_url, issue_date, expiry_date, status, created_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())
            """, (agent_id, final_cert_id, cert_number, issuing_org or custom_name or "Accredited Body", credential_url or None, issue_date, expiry_date or None))
            new_id = cur.lastrowid

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'CERTIFICATION_SUBMITTED', 'agent_certifications', %s, 'Submitted certification for verification', NOW())
            """, (user_id, new_id))

            conn.commit()
            return {
                "agent_certification_id": new_id,
                "agent_cert_id": new_id,
                "status": "PENDING"
            }
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_agent_certification(user_id, cert_id):
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ac.agent_certification_id, ac.agent_id, ac.status 
                FROM agent_certifications ac
                JOIN agents a ON ac.agent_id = a.agent_id
                WHERE ac.agent_certification_id = %s AND a.user_id = %s
            """, (cert_id, user_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Certification record not found or unauthorized")

            if row["status"] in ("ACTIVE", "VERIFIED"):
                raise ValueError("Verified credentials cannot be deleted directly. Contact an administrator.")

            cur.execute("DELETE FROM agent_certifications WHERE agent_certification_id = %s", (cert_id,))
            conn.commit()
            return True
    finally:
        conn.close()


def get_admin_pending_verifications():
    conn = get_mysql_connection()
    if not conn:
        return {"certifications": [], "experiences": []}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    ac.agent_certification_id,
                    ac.agent_certification_id AS agent_cert_id,
                    ac.agent_id,
                    u.full_name AS agent_name,
                    u.email AS agent_email,
                    COALESCE(c.certification_name, ac.issuing_organization, 'Certification') AS certification_name,
                    ac.certificate_number,
                    ac.issuing_organization,
                    ac.credential_url,
                    ac.issue_date,
                    ac.expiry_date,
                    ac.status,
                    ac.rejection_reason,
                    ac.created_at AS submitted_at
                FROM agent_certifications ac
                JOIN agents a ON ac.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                LEFT JOIN certifications c ON ac.certification_id = c.certification_id
                WHERE ac.status = 'PENDING'
                ORDER BY ac.created_at DESC
            """)
            certs = [serialize_sql_row(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT 
                    ae.experience_id,
                    ae.agent_id,
                    u.full_name AS agent_name,
                    u.email AS agent_email,
                    ae.job_title,
                    ae.company,
                    ae.work_category,
                    ae.description,
                    ae.start_date,
                    ae.end_date,
                    ae.is_current,
                    ae.verification_status,
                    ae.rejection_reason,
                    ae.created_at AS submitted_at
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ae.verification_status = 'PENDING'
                ORDER BY ae.created_at DESC
            """)
            exps = [serialize_sql_row(r) for r in cur.fetchall()]

            return {
                "certifications": certs,
                "experiences": exps,
                "pending_certs_count": len(certs),
                "pending_exps_count": len(exps),
            }
    finally:
        conn.close()


def review_agent_certification(admin_user_id, cert_id, decision, rejection_reason=None):
    if decision not in ("VERIFIED", "REJECTED"):
        raise ValueError("Decision must be 'VERIFIED' or 'REJECTED'")
    if decision == "REJECTED" and not rejection_reason:
        raise ValueError("A rejection reason is required when rejecting a certification")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT agent_certification_id, agent_id, certificate_number, status
                FROM agent_certifications
                WHERE agent_certification_id = %s
            """, (cert_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Certification record not found")

            agent_id = row["agent_id"]
            new_status = "VERIFIED" if decision == "VERIFIED" else "REJECTED"

            cur.execute("""
                UPDATE agent_certifications
                SET status = %s,
                    rejection_reason = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE agent_certification_id = %s
            """, (new_status, rejection_reason if decision == "REJECTED" else None, admin_user_id, cert_id))

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, %s, 'agent_certifications', %s, %s, NOW())
            """, (admin_user_id, f"CERTIFICATION_{decision}", cert_id, f"Admin marked certification as {decision}: {rejection_reason or 'Approved'}"))

            conn.commit()
            return {"agent_certification_id": cert_id, "status": new_status}
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def review_agent_experience(admin_user_id, exp_id, decision, rejection_reason=None):
    if decision not in ("VERIFIED", "REJECTED"):
        raise ValueError("Decision must be 'VERIFIED' or 'REJECTED'")
    if decision == "REJECTED" and not rejection_reason:
        raise ValueError("A rejection reason is required when rejecting work experience")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT experience_id, agent_id, job_title, company
                FROM agent_experience
                WHERE experience_id = %s
            """, (exp_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Experience record not found")

            agent_id = row["agent_id"]
            new_status = "VERIFIED" if decision == "VERIFIED" else "REJECTED"

            cur.execute("""
                UPDATE agent_experience
                SET verification_status = %s,
                    rejection_reason = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE experience_id = %s
            """, (new_status, rejection_reason if decision == "REJECTED" else None, admin_user_id, exp_id))

            calc = calculate_agent_verified_experience(agent_id, cur)

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, %s, 'agent_experience', %s, %s, NOW())
            """, (admin_user_id, f"EXPERIENCE_{decision}", exp_id, f"Admin marked experience as {decision}. Recalculated verified months: {calc['previous_experience_months']}"))

            conn.commit()
            return {"experience_id": exp_id, "verification_status": new_status, "recalculated_months": calc["previous_experience_months"]}
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()