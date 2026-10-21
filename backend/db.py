import logging
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import os
import uuid
import math

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

PENDING_SIGNUPS = {}

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
        logger.error(f"MySQL connection error: {e}")
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

# Binary Competency Mappings
# Model predicts exactly two outcomes: 'Eligible' (code 1) and 'Not Eligible' (code 0).
DECISION_TO_ENUM = {
    "1": "ELIGIBLE",
    "0": "NOT_ELIGIBLE",
    1: "ELIGIBLE",
    0: "NOT_ELIGIBLE",
    # Legacy fallbacks for historical tests/records
    "2": "ELIGIBLE",
    2: "ELIGIBLE",
}

# Concept A: Agent Competency Labels (Binary permitted outcomes)
COMPETENCY_ENUM_TO_LABEL = {
    "ELIGIBLE": "Eligible",
    "NOT_ELIGIBLE": "Not Eligible",
    # Legacy fallbacks
    "COMPETENT": "Eligible",
    "ADVANCED": "Eligible",
    "BASIC": "Not Eligible",
    "NEEDS_IMPROVEMENT": "Not Eligible",
    "Needs Improvement": "Not Eligible",
    "Basic": "Not Eligible",
    "Competent": "Eligible",
    "Advanced": "Eligible",
}

# Bidirectional mapping from display labels / enum names back to MySQL ENUM values
COMPETENCY_LABEL_TO_ENUM = {
    "Eligible": "ELIGIBLE",
    "Not Eligible": "NOT_ELIGIBLE",
    "ELIGIBLE": "ELIGIBLE",
    "NOT_ELIGIBLE": "NOT_ELIGIBLE",
    # Legacy fallbacks
    "Needs Improvement": "NOT_ELIGIBLE",
    "Basic": "NOT_ELIGIBLE",
    "Competent": "ELIGIBLE",
    "Advanced": "ELIGIBLE",
    "NEEDS_IMPROVEMENT": "NOT_ELIGIBLE",
    "BASIC": "NOT_ELIGIBLE",
    "COMPETENT": "ELIGIBLE",
    "ADVANCED": "ELIGIBLE",
}

# Competency hierarchy ranking for requirement evaluations (Binary scale: 1=Not Eligible, 2=Eligible)
COMPETENCY_RANKS = {
    "NOT_ELIGIBLE": 1,
    "Not Eligible": 1,
    "ELIGIBLE": 2,
    "Eligible": 2,
    # Legacy ranks
    "NEEDS_IMPROVEMENT": 1,
    "Needs Improvement": 1,
    "BASIC": 1,
    "Basic": 1,
    "COMPETENT": 2,
    "Competent": 2,
    "ADVANCED": 2,
    "Advanced": 2,
}

# Concept B: Agent Evaluation Decisions (Identical to binary competency outcome)
DECISION_TO_LABEL = {
    "1": "Eligible",
    "0": "Not Eligible",
    1: "Eligible",
    0: "Not Eligible",
    # Legacy fallback
    "2": "Eligible",
    2: "Eligible"
}

ENUM_TO_DECISION = {
    "ELIGIBLE": {"decision": "1", "code": 1, "label": "Eligible"},
    "NOT_ELIGIBLE": {"decision": "0", "code": 0, "label": "Not Eligible"},
    # Legacy fallbacks
    "NEEDS_IMPROVEMENT": {"decision": "0", "code": 0, "label": "Not Eligible"},
    "BASIC": {"decision": "0", "code": 0, "label": "Not Eligible"},
    "COMPETENT": {"decision": "1", "code": 1, "label": "Eligible"},
    "ADVANCED": {"decision": "1", "code": 1, "label": "Eligible"}
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
    cursor.execute("SELECT model_id FROM ml_models WHERE is_active = 1 ORDER BY model_id DESC LIMIT 1")
    model_row = cursor.fetchone()
    if not model_row:
        cursor.execute("""
            INSERT INTO ml_models (model_name, model_version, algorithm, feature_set_version, accuracy, macro_f1, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """, ('BinaryGatekeeperRandomForest', '2.0.0', 'StandardScaler + RandomForestClassifier', '15-features-engineered', 0.7450, 0.7400))
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
            competency_label = COMPETENCY_ENUM_TO_LABEL.get(enum_val, "Eligible" if enum_val in ("ELIGIBLE", "COMPETENT", "ADVANCED") else "Not Eligible")
            mapped = ENUM_TO_DECISION.get(enum_val, {"decision": "1" if competency_label == "Eligible" else "0", "label": competency_label})
            decision_label = mapped["label"]
            is_eligible = (competency_label == "Eligible")

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
                "confidence": conf_pct,
                "is_eligible": is_eligible,
                "probabilities": {
                    "Eligible": round(conf_pct if is_eligible else (100.0 - conf_pct), 1),
                    "Not Eligible": round((100.0 - conf_pct) if is_eligible else conf_pct, 1)
                }
            }

            return {
                "user_id": user_id,
                "agent_id": agent_id,
                "attempt_number": pred_row["attempt_number"],
                "assessment": assessment_data,
                "competency_level": competency_label,
                "competency_status": competency_label,
                "evaluation_decision": decision_label,
                "is_eligible": is_eligible,
                "confidence": conf_pct,
                "prediction_data": prediction_data,
                "completed_at": pred_row["completed_at"].isoformat() if hasattr(pred_row["completed_at"], "isoformat") else str(pred_row["completed_at"])
            }
    except Exception as e:
        logger.error(f"Error reading agent assessment from MySQL: {e}")
        return None
    finally:
        conn.close()

class CooldownActiveError(Exception):
    """Raised when an agent attempts a retake before the configured cooldown window has elapsed."""
    def __init__(self, remaining_seconds, message=None):
        self.remaining_seconds = remaining_seconds
        super().__init__(message or f"Assessment retake cooldown is active. Please wait {int(remaining_seconds)} seconds before retaking.")


def check_agent_assessment_cooldown(agent_id, exam_id, cooldown_seconds=None):
    """
    Check if the agent is within the configurable cooldown period following their last submitted attempt.
    Also honors ASSESSMENT_RESET_REQUESTED audit events (which reset demo/testing cooldown).
    Returns (in_cooldown: bool, remaining_seconds: float, last_submitted_at: datetime).
    """
    if cooldown_seconds is None:
        cooldown_seconds = getattr(Config, 'ASSESSMENT_COOLDOWN_SECONDS', 300)

    if cooldown_seconds <= 0:
        return False, 0.0, None

    conn = get_mysql_connection()
    if not conn:
        return False, 0.0, None

    try:
        with conn.cursor() as cursor:
            # Check for demo reset event
            cursor.execute("SELECT user_id FROM agents WHERE agent_id = %s LIMIT 1", (agent_id,))
            ag = cursor.fetchone()
            user_id = ag["user_id"] if ag else None

            last_reset_time = None
            last_reset_attempt_id = 0
            if user_id:
                cursor.execute("""
                    SELECT entity_id, created_at FROM audit_logs 
                    WHERE user_id = %s AND action = 'ASSESSMENT_RESET_REQUESTED'
                    ORDER BY log_id DESC LIMIT 1
                """, (user_id,))
                reset_row = cursor.fetchone()
                if reset_row:
                    last_reset_time = reset_row["created_at"]
                    last_reset_attempt_id = int(reset_row.get("entity_id") or 0)

            # Query most recent submitted attempt on this exam
            cursor.execute("""
                SELECT attempt_id, submitted_at FROM assessment_attempts
                WHERE agent_id = %s AND exam_id = %s AND status = 'SUBMITTED'
                ORDER BY submitted_at DESC, attempt_id DESC LIMIT 1
            """, (agent_id, exam_id))
            row = cursor.fetchone()

            last_submitted = row["submitted_at"] if row and row.get("submitted_at") else None
            last_attempt_id = int(row.get("attempt_id") or 0) if row else 0

            if not last_submitted:
                cursor.execute("""
                    SELECT completed_at FROM exam_results
                    WHERE agent_id = %s AND exam_id = %s
                    ORDER BY completed_at DESC LIMIT 1
                """, (agent_id, exam_id))
                er_row = cursor.fetchone()
                if er_row and er_row.get("completed_at"):
                    last_submitted = er_row["completed_at"]

            if not last_submitted:
                return False, 0.0, None

            # If reset covered this attempt (by attempt_id or strict timestamp), cooldown is cleared
            if (last_reset_attempt_id and last_attempt_id and last_attempt_id <= last_reset_attempt_id) or \
               (last_reset_time and last_reset_time > last_submitted):
                return False, 0.0, None

            now = datetime.now()
            elapsed = (now - last_submitted).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = cooldown_seconds - elapsed
                return True, round(remaining, 1), last_submitted

            return False, 0.0, last_submitted
    except Exception as e:
        logger.error(f"Error checking assessment cooldown: {e}")
        return False, 0.0, None
    finally:
        conn.close()


def create_assessment_attempt(agent_id, exam_id, task_id=None, topic_id=None):
    """
    Initiate or resume an assessment attempt for the authenticated agent.
    Enforces cooldown on new attempts.
    If an existing IN_PROGRESS attempt exists and has not expired, returns it.
    If an existing IN_PROGRESS attempt has expired, marks it EXPIRED and creates a new one.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable. Cannot create assessment attempt.")

    try:
        with conn.cursor() as cursor:
            now = datetime.now()
            # 1. Check for existing IN_PROGRESS attempt
            if topic_id:
                cursor.execute("""
                    SELECT * FROM assessment_attempts
                    WHERE agent_id = %s AND (topic_id = %s OR exam_id = %s) AND status = 'IN_PROGRESS'
                    ORDER BY started_at DESC LIMIT 1
                """, (agent_id, topic_id, exam_id))
            else:
                cursor.execute("""
                    SELECT * FROM assessment_attempts
                    WHERE agent_id = %s AND exam_id = %s AND status = 'IN_PROGRESS'
                    ORDER BY started_at DESC LIMIT 1
                """, (agent_id, exam_id))
            existing = cursor.fetchone()
            if existing:
                if existing["expires_at"] > now:
                    # Valid attempt in progress, return it
                    return serialize_sql_row(existing)
                else:
                    # Expired, update status
                    cursor.execute("""
                        UPDATE assessment_attempts SET status = 'EXPIRED', updated_at = NOW()
                        WHERE attempt_id = %s
                    """, (existing["attempt_id"],))

            # 2. Check cooldown policy
            in_cooldown, remaining, _ = check_agent_assessment_cooldown(agent_id, exam_id)
            if in_cooldown:
                raise CooldownActiveError(remaining)

            # 3. Determine next attempt number
            cursor.execute("""
                SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
                FROM (
                    SELECT attempt_number FROM assessment_attempts WHERE agent_id = %s AND exam_id = %s
                    UNION ALL
                    SELECT attempt_number FROM exam_results WHERE agent_id = %s AND exam_id = %s
                ) AS combined_attempts
            """, (agent_id, exam_id, agent_id, exam_id))
            att_row = cursor.fetchone()
            attempt_number = att_row["next_attempt"] if att_row else 1

            duration_min = getattr(Config, 'ASSESSMENT_ATTEMPT_DURATION_MINUTES', 30)
            expires_at = now + timedelta(minutes=duration_min)
            attempt_uuid = str(uuid.uuid4())

            cursor.execute("""
                INSERT INTO assessment_attempts 
                (attempt_uuid, agent_id, exam_id, topic_id, task_id, attempt_number, status, started_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'IN_PROGRESS', %s, %s)
            """, (attempt_uuid, agent_id, exam_id, topic_id, task_id, attempt_number, now, expires_at))
            attempt_id = cursor.lastrowid

            cursor.execute("SELECT * FROM assessment_attempts WHERE attempt_id = %s", (attempt_id,))
            new_attempt = cursor.fetchone()

        conn.commit()
        return serialize_sql_row(new_attempt)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_agent_topic_result(agent_id, topic_id, score, passed, answers_json=None, attempt_id=None):
    """
    Persist an authoritative topic assessment result into agent_topic_results.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")
    try:
        with conn.cursor() as cursor:
            ans_str = json.dumps(answers_json) if isinstance(answers_json, (dict, list)) else answers_json
            cursor.execute("""
                INSERT INTO agent_topic_results (agent_id, topic_id, attempt_id, score, passed, answers_json, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (agent_id, topic_id, attempt_id, score, 1 if passed else 0, ans_str))
            result_id = cursor.lastrowid
        conn.commit()
        return result_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save agent topic result: {e}")
        raise
    finally:
        conn.close()


def get_assessment_topics_list():
    """Retrieve all active assessment topics with metadata."""
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    top.topic_id, 
                    top.topic_name, 
                    top.category_id, 
                    top.description, 
                    top.passing_score, 
                    top.estimated_minutes,
                    c.category_name,
                    COUNT(eq.question_id) AS total_questions,
                    COUNT(eq.question_id) AS question_count
                FROM assessment_topics top
                LEFT JOIN categories c ON top.category_id = c.category_id
                LEFT JOIN exam_questions eq ON top.topic_id = eq.topic_id
                WHERE top.status = 'ACTIVE'
                GROUP BY top.topic_id
                ORDER BY top.topic_id ASC
            """)
            rows = cursor.fetchall()
            return [serialize_sql_row(r) for r in rows]
    except Exception as e:
        logger.error(f"Error fetching assessment topics list: {e}")
        return []
    finally:
        conn.close()


def get_assessment_topic_by_id(topic_id):
    """Fetch single topic by topic_id."""
    conn = get_mysql_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    top.topic_id, 
                    top.topic_name, 
                    top.category_id, 
                    top.description, 
                    top.passing_score, 
                    top.estimated_minutes,
                    c.category_name,
                    COUNT(eq.question_id) AS total_questions
                FROM assessment_topics top
                LEFT JOIN categories c ON top.category_id = c.category_id
                LEFT JOIN exam_questions eq ON top.topic_id = eq.topic_id
                WHERE top.topic_id = %s AND top.status = 'ACTIVE'
                GROUP BY top.topic_id
                LIMIT 1
            """, (topic_id,))
            row = cursor.fetchone()
            return serialize_sql_row(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching topic {topic_id}: {e}")
        return None
    finally:
        conn.close()


def get_topic_questions(topic_id):
    """Fetch formatted questions for a specific topic (omits correct_answer)."""
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT question_id, topic_id, exam_id, question_text, question_type, points, options_json, question_order
                FROM exam_questions
                WHERE topic_id = %s
                ORDER BY question_order ASC
            """, (topic_id,))
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
                    "topic_id": q["topic_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "points": float(q["points"]),
                    "options": formatted_opts,
                    "question_order": q["question_order"]
                })
            return questions
    except Exception as e:
        logger.error(f"Error fetching questions for topic {topic_id}: {e}")
        return []
    finally:
        conn.close()


def get_assessment_attempt(attempt_id):
    """Fetch an assessment attempt by integer ID or UUID string."""
    conn = get_mysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            if isinstance(attempt_id, int) or (isinstance(attempt_id, str) and str(attempt_id).isdigit()):
                cursor.execute("SELECT * FROM assessment_attempts WHERE attempt_id = %s LIMIT 1", (int(attempt_id),))
            else:
                cursor.execute("SELECT * FROM assessment_attempts WHERE attempt_uuid = %s LIMIT 1", (str(attempt_id),))
            row = cursor.fetchone()
            return serialize_sql_row(row) if row else None
    finally:
        conn.close()


def get_agent_active_attempt(agent_id, exam_id):
    """Fetch current active in-progress assessment attempt for agent and exam."""
    conn = get_mysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM assessment_attempts
                WHERE agent_id = %s AND exam_id = %s AND status = 'IN_PROGRESS'
                ORDER BY started_at DESC LIMIT 1
            """, (agent_id, exam_id))
            row = cursor.fetchone()
            return serialize_sql_row(row) if row else None
    finally:
        conn.close()


def finalize_assessment_attempt(attempt_id, score, passed, answers_json, subscores_json, model_version, exam_result_id, prediction_id, decision_details):
    """
    Mark an assessment attempt as SUBMITTED with recorded scores and linked predictions.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable. Cannot finalize assessment attempt.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE assessment_attempts
                SET status = 'SUBMITTED',
                    score = %s,
                    passed = %s,
                    answers_json = %s,
                    subscores_json = %s,
                    model_version = %s,
                    exam_result_id = %s,
                    prediction_id = %s,
                    decision_details = %s,
                    submitted_at = NOW(),
                    updated_at = NOW()
                WHERE attempt_id = %s
            """, (
                score, 
                1 if passed else 0, 
                json.dumps(answers_json) if isinstance(answers_json, (dict, list)) else answers_json,
                json.dumps(subscores_json) if isinstance(subscores_json, (dict, list)) else subscores_json,
                model_version,
                exam_result_id,
                prediction_id,
                json.dumps(decision_details) if isinstance(decision_details, (dict, list)) else decision_details,
                attempt_id
            ))
            if exam_result_id:
                cursor.execute("UPDATE exam_results SET attempt_id = %s WHERE exam_result_id = %s", (attempt_id, exam_result_id))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_agent_assessment(user_id, assessment_data, competency_level, confidence, prediction_data=None, exam_id=None, task_id=None, attempt_id=None):
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
            default_exam_id, model_id = get_or_create_reference_records(cursor)
            active_exam_id = int(exam_id) if exam_id else default_exam_id

            # 3. Determine attempt number (strictly incremented to preserve history)
            cursor.execute("""
                SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
                FROM (
                    SELECT attempt_number FROM exam_results WHERE agent_id = %s AND exam_id = %s
                    UNION ALL
                    SELECT attempt_number FROM assessment_attempts WHERE agent_id = %s AND exam_id = %s
                ) AS combined
            """, (agent_id, active_exam_id, agent_id, active_exam_id))
            attempt_row = cursor.fetchone()
            attempt_number = attempt_row["next_attempt"] if attempt_row else 1

            # 4. Extract assessment score and determine pass status
            raw_score = float(assessment_data.get("assessment_score", 0.0))
            score = max(0.0, min(100.0, raw_score))  # satisfies chk_exam_result_score
            cursor.execute("SELECT passing_score FROM exams WHERE exam_id = %s", (active_exam_id,))
            ex_row = cursor.fetchone()
            if not ex_row:
                raise ValueError(f"Exam {active_exam_id} not found.")
            raw_passing = ex_row.get("passing_score")
            if raw_passing is None:
                raise ValueError(f"Exam {active_exam_id} has no configured passing score.")
            try:
                passing_score = float(raw_passing)
                if passing_score < 0.0 or passing_score > 100.0 or math.isnan(passing_score):
                    raise ValueError(f"Passing score {passing_score} out of valid range [0, 100].")
            except (ValueError, TypeError) as pe:
                raise ValueError(f"Exam {active_exam_id} has an invalid passing score configuration ({raw_passing}): {pe}")

            passed = 1 if round(score, 2) >= round(passing_score, 2) else 0

            # 5. Insert into exam_results (including attempt_id if provided)
            cursor.execute("""
                INSERT INTO exam_results (attempt_id, exam_id, agent_id, assessment_score, passed, attempt_number, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (attempt_id, active_exam_id, agent_id, score, passed, attempt_number))
            exam_result_id = cursor.lastrowid

            # 6. Map decision to binary enum ('ELIGIBLE' or 'NOT_ELIGIBLE')
            decision = str(prediction_data.get("decision", "0")) if prediction_data else "0"
            prediction_label = str(prediction_data.get("prediction", "")) if prediction_data else ""
            
            if competency_level in ("ELIGIBLE", "Eligible") or prediction_label == "Eligible" or decision == "1":
                predicted_enum = "ELIGIBLE"
            elif competency_level in ("NOT_ELIGIBLE", "Not Eligible") or prediction_label == "Not Eligible" or decision == "0":
                predicted_enum = "NOT_ELIGIBLE"
            elif competency_level:
                predicted_enum = COMPETENCY_LABEL_TO_ENUM.get(competency_level, "NOT_ELIGIBLE")
            else:
                predicted_enum = DECISION_TO_ENUM.get(decision, "NOT_ELIGIBLE")

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

            # 7b. Link attempt with exam_result and prediction if attempt_id supplied
            if attempt_id:
                cursor.execute("""
                    UPDATE assessment_attempts
                    SET exam_result_id = %s, prediction_id = %s
                    WHERE attempt_id = %s
                """, (exam_result_id, prediction_id, attempt_id))

            # 8. Update agent experience_months if provided
            exp_months = int(float(assessment_data.get("previous_experience_months", 0)))
            if exp_months > 0:
                cursor.execute("""
                    UPDATE agents SET experience_months = %s, updated_at = NOW()
                    WHERE agent_id = %s
                """, (exp_months, agent_id))

            # 9. If task_id provided, record in eligibility_evaluations and eligibility_checks
            eval_id = None
            if task_id:
                is_model_eligible = (predicted_enum in ("ELIGIBLE", "COMPETENT", "ADVANCED"))
                eligibility_status = "ELIGIBLE" if (passed and is_model_eligible) else "NOT_ELIGIBLE"
                review_status = "NOT_REQUIRED"
                explanation = f"Evaluated competency: {predicted_enum} with assessment score {score:.1f}% on Exam {active_exam_id}."

                cursor.execute("""
                    INSERT INTO eligibility_evaluations 
                    (agent_id, task_id, prediction_id, eligibility_status, explanation, review_status, evaluated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (agent_id, task_id, prediction_id, eligibility_status, explanation, review_status))
                eval_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO eligibility_checks (evaluation_id, requirement_type, expected_value, actual_value, passed, failure_reason)
                    VALUES 
                    (%s, 'EXAM', %s, %s, %s, %s),
                    (%s, 'COMPETENCY', 'ELIGIBLE', %s, %s, %s)
                """, (
                    eval_id, f"Passing Score >= {passing_score:.1f}%", f"{score:.1f}%", passed, None if passed else "Assessment score below passing threshold",
                    eval_id, predicted_enum, 1 if is_model_eligible else 0, None if is_model_eligible else f"Competency {predicted_enum} is not Eligible"
                ))

            # 10. Insert audit log event with full assessment payload
            audit_payload = {
                "exam_id": active_exam_id,
                "task_id": task_id,
                "attempt_id": attempt_id,
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
            "evaluation_id": eval_id,
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
    Inserts an ASSESSMENT_RESET_REQUESTED audit event with highest attempt_id.
    Closes any lingering IN_PROGRESS attempts so the agent can start fresh.
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

            max_attempt_id = 0
            if agent_id:
                cursor.execute("SELECT COALESCE(MAX(attempt_id), 0) AS max_att FROM assessment_attempts WHERE agent_id = %s", (agent_id,))
                max_row = cursor.fetchone()
                if max_row:
                    max_attempt_id = int(max_row["max_att"])

                # Mark lingering in-progress attempts as closed
                cursor.execute("""
                    UPDATE assessment_attempts SET status = 'CLOSED', updated_at = NOW()
                    WHERE agent_id = %s AND status = 'IN_PROGRESS'
                """, (agent_id,))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_RESET_REQUESTED', 'assessment_attempts', %s, 
                        'Safe demo reset requested. Historical attempts preserved.', NOW())
            """, (user_id, max_attempt_id))
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
                has_assessed = True
                agent_comp_enum = pred_row["predicted_competency"]
                agent_comp_label = COMPETENCY_ENUM_TO_LABEL.get(agent_comp_enum, "Competent")
                decision_info = ENUM_TO_DECISION.get(agent_comp_enum, {"label": "Eligible"})
                agent_decision = decision_info.get("label", "Eligible")

            # 3b. Query distinct passed exams and latest exam results for this agent
            cursor.execute("""
                SELECT DISTINCT exam_id 
                FROM exam_results 
                WHERE agent_id = %s AND passed = 1
            """, (agent_id,))
            passed_exam_ids = {r["exam_id"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT er.exam_id, er.assessment_score, er.passed, er.completed_at
                FROM exam_results er
                INNER JOIN (
                    SELECT exam_id, MAX(exam_result_id) AS max_id
                    FROM exam_results
                    WHERE agent_id = %s
                    GROUP BY exam_id
                ) latest ON er.exam_result_id = latest.max_id
            """, (agent_id,))
            latest_exam_results = {r["exam_id"]: r for r in cursor.fetchall()}

            # 4. Agent's active certifications
            cursor.execute("""
                SELECT ac.certification_id, c.certification_name, ac.status, ac.expiry_date
                FROM agent_certifications ac
                JOIN certifications c ON ac.certification_id = c.certification_id
                WHERE ac.agent_id = %s AND ac.status IN ('ACTIVE', 'VERIFIED') AND (ac.expiry_date IS NULL OR ac.expiry_date >= CURDATE())
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

            # 5b. Query passed topics for this agent from agent_topic_results
            passed_topic_ids = set()
            latest_topic_results = {}
            reset_time = reset_row["created_at"] if reset_row else None
            if not is_reset:
                cursor.execute("""
                    SELECT DISTINCT topic_id
                    FROM agent_topic_results
                    WHERE agent_id = %s AND passed = 1
                    AND (%s IS NULL OR completed_at >= %s)
                """, (agent_id, reset_time, reset_time))
                passed_topic_ids = {r["topic_id"] for r in cursor.fetchall()}

                cursor.execute("""
                    SELECT atr.topic_id, atr.score, atr.passed, atr.completed_at
                    FROM agent_topic_results atr
                    INNER JOIN (
                        SELECT topic_id, MAX(result_id) AS max_id
                        FROM agent_topic_results
                        WHERE agent_id = %s AND (%s IS NULL OR completed_at >= %s)
                        GROUP BY topic_id
                    ) latest ON atr.result_id = latest.max_id
                """, (agent_id, reset_time, reset_time))
                latest_topic_results = {r["topic_id"]: r for r in cursor.fetchall()}

            # 5c. Query all task-to-topic requirements
            task_topics_map = {}
            try:
                cursor.execute("""
                    SELECT 
                        tat.task_id, 
                        tat.topic_id, 
                        tat.is_mandatory,
                        top.topic_name,
                        top.description AS topic_description,
                        top.passing_score AS topic_passing_score,
                        top.estimated_minutes
                    FROM task_assessment_topics tat
                    JOIN assessment_topics top ON tat.topic_id = top.topic_id
                    WHERE top.status = 'ACTIVE'
                    ORDER BY tat.task_id, tat.topic_id
                """)
                for row in cursor.fetchall():
                    task_topics_map.setdefault(row["task_id"], []).append(row)
            except Exception as e:
                logger.warning(f"Could not load task_assessment_topics: {e}")

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
                    ex.exam_name,
                    ex.passing_score AS exam_passing_score,
                    ex.description AS exam_description,
                    tr.requirement_id,
                    tr.minimum_competency,
                    tr.required_certification_id,
                    cert.certification_name AS required_certification_name,
                    tr.minimum_experience_months,
                    tr.exam_required
                FROM tasks t
                JOIN categories c ON t.category_id = c.category_id
                LEFT JOIN exams ex ON t.exam_id = ex.exam_id
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

                # Check 2: Task Assessment Topics & Exams
                req_exam_id = t.get("exam_id")
                latest_res = latest_exam_results.get(req_exam_id) if req_exam_id else None
                exam_score = float(latest_res["assessment_score"]) if latest_res and latest_res.get("assessment_score") is not None else None
                exam_passed = bool(latest_res["passed"]) if latest_res and latest_res.get("passed") is not None else False

                configured_topics = task_topics_map.get(t_id, [])
                required_topics_details = []
                all_mandatory_topics_passed = True

                if configured_topics:
                    for c_top in configured_topics:
                        top_id = c_top["topic_id"]
                        is_mand = bool(c_top["is_mandatory"])
                        top_passing = float(c_top["topic_passing_score"])
                        top_passed = (top_id in passed_topic_ids) and not is_reset
                        top_latest = latest_topic_results.get(top_id) if not is_reset else None
                        top_score = float(top_latest["score"]) if top_latest and top_latest.get("score") is not None else None

                        if top_passed:
                            top_status = "Passed"
                        elif top_latest and not top_latest.get("passed"):
                            top_status = "Failed"
                        else:
                            top_status = "Needed"

                        if is_mand and not top_passed:
                            all_mandatory_topics_passed = False

                        required_topics_details.append({
                            "topic_id": top_id,
                            "topic_name": c_top["topic_name"],
                            "description": c_top["topic_description"],
                            "passing_score": top_passing,
                            "estimated_minutes": c_top["estimated_minutes"],
                            "is_mandatory": is_mand,
                            "status": top_status,
                            "score": top_score
                        })

                if exam_req:
                    if configured_topics:
                        has_assessment_completed = all(top["score"] is not None for top in required_topics_details if top["is_mandatory"]) if required_topics_details else False
                        has_assessment = all_mandatory_topics_passed
                    elif req_exam_id and not is_reset:
                        has_assessment_completed = latest_res is not None
                        has_assessment = req_exam_id in passed_exam_ids
                    else:
                        has_assessment_completed = has_assessed
                        has_assessment = bool(pred_row and pred_row["passed"] and not is_reset)
                else:
                    has_assessment_completed = True
                    has_assessment = True

                if not exam_req:
                    exam_status = "Not Required"
                elif has_assessment:
                    exam_status = "Passed"
                elif configured_topics:
                    passed_count = sum(1 for top in required_topics_details if top["status"] == "Passed")
                    failed_count = sum(1 for top in required_topics_details if top["status"] == "Failed")
                    if passed_count > 0:
                        exam_status = "Partially Completed"
                    elif failed_count > 0:
                        exam_status = "Failed"
                    else:
                        exam_status = "Assessment Needed"
                elif latest_res:
                    exam_status = "Failed"
                else:
                    exam_status = "Not Started"

                # Check 3: Competency Threshold
                # Under the binary workflow, model outputs 'Eligible' or 'Not Eligible'.
                # A task requires minimum_competency = 'ELIGIBLE' (or legacy COMPETENT/ADVANCED).
                agent_is_eligible = has_assessed and (agent_comp_enum in ("ELIGIBLE", "COMPETENT", "ADVANCED") or agent_comp_label == "Eligible")
                meets_comp = agent_is_eligible if min_comp in ("ELIGIBLE", "COMPETENT", "ADVANCED") else True

                # Check 4: Experience
                meets_exp = agent_exp_months >= min_exp

                # Check 5: Application Status
                app = applications.get(t_id)
                app_status = app["status"] if app else "Not Applied"
                applied_at = app["applied_at"].isoformat() if app and hasattr(app["applied_at"], "isoformat") else (str(app["applied_at"]) if app else None)

                # Determine State using precedence rules
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
                elif not has_assessment_completed:
                    state = "Assessment Needed"
                    blocking_reason = "Task-specific competency evaluation required"
                elif has_cert and has_assessment and meets_comp and meets_exp:
                    state = "Ready to Apply"
                    can_apply = True
                    is_eligible = True
                else:
                    # Specific blocking reason
                    if not meets_comp:
                        state = "Ineligible"
                        blocking_reason = "Competency evaluation result is Not Eligible"
                    elif not meets_exp:
                        state = f"Requires {min_exp} Months Exp"
                        blocking_reason = f"Agent has {agent_exp_months} months verified experience; task requires {min_exp} months"
                    elif not has_assessment:
                        state = "Assessment Needed"
                        blocking_reason = "Assessment passing score requirement not satisfied"
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
                    "exam_id": req_exam_id,
                    "exam_name": t.get("exam_name") or ("Diagnostic Assessment" if req_exam_id == 3 else "Sales Assessment"),
                    "exam_passing_score": float(t["exam_passing_score"]) if t.get("exam_passing_score") is not None else 70.0,
                    "exam_description": t.get("exam_description"),
                    "exam_status": exam_status,
                    "exam_score": exam_score,
                    "required_competency": COMPETENCY_ENUM_TO_LABEL.get(min_comp, min_comp),
                    "required_certification": req_cert_name or "None required",
                    "minimum_experience_months": min_exp,
                    "exam_required": exam_req,
                    "required_topics": required_topics_details,
                    "topics_total": len(required_topics_details),
                    "topics_passed_count": sum(1 for top in required_topics_details if top["status"] == "Passed"),
                    "all_topics_passed": all_mandatory_topics_passed if configured_topics else has_assessment,
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
    """
    Look up user by email in MySQL.
    Returns (user_dict, None) on success.
    Returns (None, "DB_UNAVAILABLE") if connection fails.
    Returns (None, None) if not found.
    """
    if not identifier:
        return None, None
    conn = get_mysql_connection()
    if not conn:
        logger.error("MySQL connection unavailable in find_user_by_credential")
        return None, "DB_UNAVAILABLE"
    try:
        with conn.cursor() as cursor:
            sql = "SELECT user_id as id, email, email as username, password_hash, full_name, role, is_active FROM users WHERE email = %s LIMIT 1"
            cursor.execute(sql, (identifier.strip().lower(),))
            user = cursor.fetchone()
            return user, None
    except Exception as e:
        logger.error(f"Error querying MySQL in find_user_by_credential: {e}")
        return None, "DB_ERROR"
    finally:
        conn.close()

def find_user_by_id(user_id):
    """
    Look up user by primary key user_id in MySQL.
    Returns (user_dict, None) on success.
    Returns (None, "DB_UNAVAILABLE") if connection fails.
    Returns (None, "DB_ERROR") on query error.
    Returns (None, None) if not found.
    """
    if not user_id:
        return None, None
    conn = get_mysql_connection()
    if not conn:
        logger.error(f"MySQL connection unavailable in find_user_by_id({user_id})")
        return None, "DB_UNAVAILABLE"
    try:
        with conn.cursor() as cursor:
            sql = "SELECT user_id as id, email, email as username, full_name, role, is_active FROM users WHERE user_id = %s LIMIT 1"
            cursor.execute(sql, (int(user_id),))
            user = cursor.fetchone()
            if user:
                assessment_rec = get_agent_assessment(user["id"])
                user["assessment"] = assessment_rec.get("assessment") if assessment_rec else None
                user["competency_level"] = assessment_rec.get("competency_level") if assessment_rec else None
                user["confidence"] = assessment_rec.get("confidence") if assessment_rec else None
                return user, None
            return None, None
    except Exception as e:
        logger.error(f"Error querying MySQL in find_user_by_id: {e}")
        return None, "DB_ERROR"
    finally:
        conn.close()

def verify_credentials(identifier, password):
    """
    Authenticate user credentials against MySQL.
    Never uses in-memory or fallback administrator accounts.
    Returns (safe_user_dict, None) on success.
    Returns (None, error_string) on invalid credentials, inactive account, or DB failure.
    """
    if not identifier or not password:
        return None, "Both email/username and password are required."

    user, db_status = find_user_by_credential(identifier)
    if db_status in ("DB_UNAVAILABLE", "DB_ERROR"):
        return None, "Authentication service is currently unavailable. Please try again later."

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
    """
    Authenticate or provision Google OAuth user in MySQL.
    Fails safely if MySQL is unavailable without in-memory fallback.
    """
    if not email:
        return None, "Email address is required."

    conn = get_mysql_connection()
    if not conn:
        logger.error("Database connection unavailable in find_or_create_google_user.")
        return None, "Authentication service is currently unavailable. Please try again later."

    try:
        with conn.cursor() as cursor:
            email_lower = email.lower()
            sql_check = "SELECT user_id as id, email, email as username, full_name, role, is_active FROM users WHERE email = %s LIMIT 1"
            cursor.execute(sql_check, (email_lower,))
            user = cursor.fetchone()
            if user:
                if not user.get("is_active", True):
                    return None, "This account is inactive. Please contact your administrator."
                canonical_role = normalize_role(user["role"])
                return {
                    "id": user["id"],
                    "email": user["email"],
                    "username": user.get("username", user["email"]),
                    "fullName": user.get("full_name", full_name),
                    "role": canonical_role,
                    "dashboardUrl": "/admin/dashboard" if canonical_role == "Administrator" else "/agent/dashboard"
                }, None

            # Provision new Google user in MySQL
            dummy_hash = generate_password_hash(os.urandom(24).hex())
            sql_user = """
                INSERT INTO users (email, password_hash, full_name, role, is_active, email_verified)
                VALUES (%s, %s, %s, 'AGENT', TRUE, TRUE)
            """
            cursor.execute(sql_user, (email_lower, dummy_hash, full_name))
            user_id = cursor.lastrowid

            sql_agent = """
                INSERT INTO agents (user_id, phone, experience_months, availability_status, status)
                VALUES (%s, NULL, 0, 'AVAILABLE', 'ACTIVE')
            """
            cursor.execute(sql_agent, (user_id,))
            conn.commit()

            return {
                "id": user_id,
                "email": email_lower,
                "username": email_lower,
                "fullName": full_name,
                "role": "Agent",
                "dashboardUrl": "/agent/dashboard"
            }, None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error authenticating Google user in MySQL: {e}")
        return None, "An error occurred while authenticating with Google."
    finally:
        conn.close()

def store_otp(email, code):
    """Store OTP code in MySQL database with 10-minute expiry."""
    conn = get_mysql_connection()
    if not conn:
        logger.error("MySQL connection unavailable when storing OTP.")
        return False

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
        conn.rollback()
        logger.error(f"Error storing OTP: {e}")
        return False
    finally:
        conn.close()

def verify_otp(email, code):
    """Verify OTP code against MySQL database."""
    conn = get_mysql_connection()
    if not conn:
        logger.error("MySQL connection unavailable when verifying OTP.")
        return False

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
        conn.rollback()
        logger.error(f"Error verifying OTP: {e}")
        return False
    finally:
        conn.close()


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
        logger.error("MySQL connection unavailable in get_admin_overview_metrics.")
        return None

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
    min_comp = (task_data.get("minimum_competency") or "ELIGIBLE").upper().strip()
    if min_comp not in ("ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_IMPROVEMENT", "BASIC", "COMPETENT", "ADVANCED"):
        min_comp = "ELIGIBLE"

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
    except ValueError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error changing status for task {task_id}: {e}")
        raise RuntimeError(f"Failed to set status: {str(e)}")
    finally:
        conn.close()


def delete_task(task_id, admin_user_id=None):
    """
    Permanently delete a task and its associated requirements, topic links, and evaluations.
    Safely nullifies task references in attempts and logs audit event.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT task_id, task_name, status FROM tasks WHERE task_id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise ValueError(f"Task {task_id} not found.")

            # 1. Nullify references in assessment_attempts
            cursor.execute("UPDATE assessment_attempts SET task_id = NULL WHERE task_id = %s", (task_id,))

            # 2. Delete recommendations linked to this task
            cursor.execute("DELETE FROM task_recommendations WHERE task_id = %s", (task_id,))

            # 3. Delete eligibility evaluations linked to this task
            cursor.execute("DELETE FROM eligibility_evaluations WHERE task_id = %s", (task_id,))

            # 4. Delete task applications linked to this task
            cursor.execute("DELETE FROM task_applications WHERE task_id = %s", (task_id,))

            # 5. Delete task topic associations
            cursor.execute("DELETE FROM task_assessment_topics WHERE task_id = %s", (task_id,))

            # 6. Delete task requirements
            cursor.execute("DELETE FROM task_requirements WHERE task_id = %s", (task_id,))

            # 7. Delete the task record itself
            cursor.execute("DELETE FROM tasks WHERE task_id = %s", (task_id,))

            # 8. Record audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_DELETED', 'tasks', %s, %s, NOW())
            """, (admin_user_id, task_id, json.dumps({
                "deleted_task_id": task_id,
                "task_name": task["task_name"],
                "last_status": task["status"]
            })))

        conn.commit()
        return True
    except ValueError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting task {task_id}: {e}")
        raise RuntimeError(f"Failed to delete task: {str(e)}")
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

            # Profile readiness is based on 3 profile pillars. Assessments are
            # task-specific and are evaluated per task, not as a profile pillar.
            readiness_checks = {
                "personal_info": bool(profile.get("phone") and profile.get("location") and profile.get("bio")),
                "experience": exp_metrics["verified_entries_count"] > 0,
                "certification": cert_metrics["certification_count"] > 0
            }
            completed_pillars = sum(1 for passed in readiness_checks.values() if passed)
            readiness = round(completed_pillars * 100 / len(readiness_checks))

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