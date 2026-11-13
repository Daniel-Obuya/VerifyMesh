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
import secrets

logger = logging.getLogger('verifymesh.db')

ROLE_MAP = {
    "ADMIN": "Administrator",
    "AGENT": "Agent",
    "Administrator": "Administrator",
    "Agent": "Agent",
    "WORKFORCE_OFFICER": "Workforce Officer",
    "Workforce Officer": "Workforce Officer",
    "PLATFORM_ADMIN": "Platform Administrator",
    "Platform Administrator": "Platform Administrator",
}

def normalize_role(raw_role):
    """Convert DB role strings (ADMIN/AGENT) to frontend role strings (Administrator/Agent)."""
    return ROLE_MAP.get(raw_role, raw_role)

def log_audit_event(user_id, action, entity_type=None, entity_id=None, description=None, cursor=None):
    """Insert a record into audit_logs table transactionally."""
    def _do_log(cur):
        cur.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, action, entity_type, entity_id, description))

    if cursor:
        _do_log(cursor)
        return True

    conn = get_mysql_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            _do_log(cur)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log audit event: {e}")
        return False
    finally:
        conn.close()

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

class AttemptLimitReachedError(Exception):
    """Raised when an agent has reached the maximum permitted attempts for a topic or exam."""
    def __init__(self, message="Maximum assessment attempts reached. Contact a workforce officer."):
        super().__init__(message)


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
    Enforces cooldown on new attempts and checks maximum attempt limits.
    Generates a cryptographically randomized question selection and option permutation snapshot.
    If an existing IN_PROGRESS attempt exists and has not expired, returns it with its snapshot.
    If an existing IN_PROGRESS attempt has expired, marks it EXPIRED (score=NULL, passed=0) and creates a new one.
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
                    # Expired, update status to EXPIRED (score=NULL, passed=0)
                    cursor.execute("""
                        UPDATE assessment_attempts 
                        SET status = 'EXPIRED', score = NULL, passed = 0, updated_at = NOW()
                        WHERE attempt_id = %s
                    """, (existing["attempt_id"],))

            # 2. Check maximum attempts quota (default 3)
            max_attempts = 3
            if topic_id:
                cursor.execute("SELECT max_attempts FROM assessment_topics WHERE topic_id = %s", (topic_id,))
                top_row = cursor.fetchone()
                if top_row and top_row.get("max_attempts"):
                    max_attempts = int(top_row["max_attempts"])

                # Check if agent has already passed this topic
                cursor.execute("SELECT passed FROM agent_topic_results WHERE agent_id = %s AND topic_id = %s AND passed = 1 LIMIT 1", (agent_id, topic_id))
                if not cursor.fetchone():
                    # Check for administrative overrides in audit_logs
                    cursor.execute("""
                        SELECT COUNT(*) as override_count FROM audit_logs
                        WHERE entity_type = 'agents' AND entity_id = %s AND action = 'ATTEMPT_LIMIT_OVERRIDE_GRANTED'
                    """, (agent_id,))
                    ov_row = cursor.fetchone()
                    extra_attempts = int(ov_row["override_count"] or 0)
                    effective_max = max_attempts + extra_attempts

                    cursor.execute("""
                        SELECT COUNT(*) as att_count FROM assessment_attempts
                        WHERE agent_id = %s AND topic_id = %s AND status IN ('SUBMITTED', 'EXPIRED', 'ABANDONED')
                    """, (agent_id, topic_id))
                    cnt_row = cursor.fetchone()
                    past_attempts = cnt_row["att_count"] if cnt_row else 0
                    if past_attempts >= effective_max:
                        raise AttemptLimitReachedError(f"Maximum assessment attempts ({effective_max}) reached for this topic. Please contact a workforce officer.")

            # 3. Check cooldown policy
            in_cooldown, remaining, _ = check_agent_assessment_cooldown(agent_id, exam_id)
            if in_cooldown:
                raise CooldownActiveError(remaining)

            # 4. Determine next attempt number
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

            # 5. Generate cryptographically randomized question & option snapshot
            import secrets
            rng = secrets.SystemRandom()

            cursor.execute("""
                SELECT question_id, topic_id, exam_id, question_text, question_type, points, correct_answer, options_json, question_order
                FROM exam_questions
                WHERE (topic_id = %s OR (topic_id IS NULL AND exam_id = %s)) AND (status = 'ACTIVE' OR status IS NULL)
                ORDER BY question_order ASC
            """, (topic_id, exam_id))
            raw_questions = cursor.fetchall()

            OPTION_LETTERS = ["A", "B", "C", "D"]
            snapshot_questions = []

            if raw_questions:
                shuffled_q = list(raw_questions)
                rng.shuffle(shuffled_q)

                for q in shuffled_q:
                    q_id = q["question_id"]
                    raw_opts = json.loads(q["options_json"]) if isinstance(q["options_json"], str) else (q["options_json"] or [])
                    shuffled_opts = list(raw_opts)
                    rng.shuffle(shuffled_opts)

                    display_to_original = {}
                    formatted_opts = []
                    for idx, opt in enumerate(shuffled_opts):
                        opt_letter = OPTION_LETTERS[idx] if idx < len(OPTION_LETTERS) else str(idx + 1)
                        if isinstance(opt, dict):
                            orig_id = opt.get("option_id", opt_letter)
                            opt_text = opt.get("text", str(opt))
                        else:
                            orig_id = opt_letter
                            opt_text = str(opt)
                        display_to_original[opt_letter] = orig_id
                        formatted_opts.append({
                            "option_id": opt_letter,
                            "text": opt_text
                        })

                    snapshot_questions.append({
                        "question_id": q_id,
                        "display_to_original": display_to_original,
                        "options": formatted_opts
                    })

            snapshot_json = json.dumps({
                "version": 1,
                "topic_id": topic_id,
                "exam_id": exam_id,
                "questions": snapshot_questions
            }) if snapshot_questions else None

            topic_ver = 1
            if topic_id:
                cursor.execute("SELECT version FROM assessment_topics WHERE topic_id = %s", (topic_id,))
                ver_row = cursor.fetchone()
                if ver_row and ver_row.get("version"):
                    topic_ver = int(ver_row["version"])

            cursor.execute("""
                INSERT INTO assessment_attempts 
                (attempt_uuid, agent_id, exam_id, topic_id, task_id, attempt_number, status, started_at, expires_at, question_snapshot_json, topic_version)
                VALUES (%s, %s, %s, %s, %s, %s, 'IN_PROGRESS', %s, %s, %s, %s)
            """, (attempt_uuid, agent_id, exam_id, topic_id, task_id, attempt_number, now, expires_at, snapshot_json, topic_ver))
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


def save_agent_topic_result(agent_id, topic_id, score, passed, answers_json=None, attempt_id=None, cursor=None):
    """
    Persist an authoritative topic assessment result into agent_topic_results.
    Supports sharing an active cursor/transaction to prevent deadlock.
    """
    ans_str = json.dumps(answers_json) if isinstance(answers_json, (dict, list)) else answers_json
    if cursor is not None:
        cursor.execute("""
            INSERT INTO agent_topic_results (agent_id, topic_id, attempt_id, score, passed, answers_json, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (agent_id, topic_id, attempt_id, score, 1 if passed else 0, ans_str))
        return cursor.lastrowid

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable.")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_topic_results (agent_id, topic_id, attempt_id, score, passed, answers_json, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (agent_id, topic_id, attempt_id, score, 1 if passed else 0, ans_str))
            result_id = cur.lastrowid
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
                    top.max_attempts,
                    top.version,
                    top.status,
                    c.category_name,
                    MAX(eq.exam_id) AS exam_id,
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
                    top.max_attempts,
                    top.version,
                    top.status,
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


def admin_create_assessment_topic(admin_user_id, data):
    """
    Workforce Officer creates an assessment topic with audit logging.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            name = data.get("topic_name")
            cat_id = data.get("category_id")
            desc = data.get("description", "")
            passing = float(data.get("passing_score", 70.0))
            est_min = int(data.get("estimated_minutes", 10))
            max_att = int(data.get("max_attempts", 3))

            cursor.execute("""
                INSERT INTO assessment_topics (topic_name, category_id, description, passing_score, estimated_minutes, max_attempts, status, version)
                VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE', 1)
            """, (name, cat_id, desc, passing, est_min, max_att))
            new_id = cursor.lastrowid

            # Audit trail
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_TOPIC_CREATED', 'assessment_topics', %s, %s, NOW())
            """, (admin_user_id, new_id, json.dumps({
                "topic_id": new_id,
                "topic_name": name,
                "passing_score": passing,
                "max_attempts": max_att,
                "version": 1,
                "created_by": admin_user_id
            })))
            conn.commit()
            return new_id
    finally:
        conn.close()


def admin_update_assessment_topic(admin_user_id, topic_id, data):
    """
    Workforce Officer updates an assessment topic configuration.
    Increments topic version so future attempts reflect new version while
    historical attempts remain locked to their snapshot version.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assessment_topics WHERE topic_id = %s", (topic_id,))
            current = cursor.fetchone()
            if not current:
                return False, f"Topic {topic_id} not found."

            new_name = data.get("topic_name", current["topic_name"])
            new_desc = data.get("description", current["description"])
            new_passing = float(data.get("passing_score", current["passing_score"]))
            new_est_min = int(data.get("estimated_minutes", current["estimated_minutes"]))
            new_max_att = int(data.get("max_attempts", current.get("max_attempts", 3)))
            new_status = data.get("status", current["status"])

            old_version = int(current.get("version") or 1)
            new_version = old_version + 1

            cursor.execute("""
                UPDATE assessment_topics
                SET topic_name = %s,
                    description = %s,
                    passing_score = %s,
                    estimated_minutes = %s,
                    max_attempts = %s,
                    status = %s,
                    version = %s,
                    updated_at = NOW()
                WHERE topic_id = %s
            """, (new_name, new_desc, new_passing, new_est_min, new_max_att, new_status, new_version, topic_id))

            # Audit trail
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_TOPIC_UPDATED', 'assessment_topics', %s, %s, NOW())
            """, (admin_user_id, topic_id, json.dumps({
                "topic_id": topic_id,
                "previous_passing_score": float(current["passing_score"]),
                "new_passing_score": new_passing,
                "previous_max_attempts": int(current.get("max_attempts") or 3),
                "new_max_attempts": new_max_att,
                "previous_version": old_version,
                "new_version": new_version,
                "updated_by": admin_user_id
            })))
            conn.commit()
            return True, None
    finally:
        conn.close()


def admin_get_topic_questions(topic_id):
    """
    Admin-only: Retrieve all questions for a topic including correct_answer and internal points.
    """
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT question_id, topic_id, exam_id, question_text, question_type, points, correct_answer, options_json, question_order, status
                FROM exam_questions
                WHERE topic_id = %s
                ORDER BY question_order ASC, question_id ASC
            """, (topic_id,))
            rows = cursor.fetchall()
            return [serialize_sql_row(r) for r in rows]
    finally:
        conn.close()


def get_topic_questions(topic_id, attempt_id=None):
    """
    Fetch formatted questions for a specific topic (omits correct_answer).
    If attempt_id is provided and holds a frozen question_snapshot_json,
    returns the exact randomized questions and options assigned to that attempt.
    """
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            # Check for attempt snapshot
            if attempt_id:
                cursor.execute("SELECT question_snapshot_json FROM assessment_attempts WHERE attempt_id = %s", (attempt_id,))
                att_row = cursor.fetchone()
                if att_row and att_row.get("question_snapshot_json"):
                    snapshot = json.loads(att_row["question_snapshot_json"]) if isinstance(att_row["question_snapshot_json"], str) else att_row["question_snapshot_json"]
                    snap_questions = snapshot.get("questions", [])
                    if snap_questions:
                        q_ids = [sq["question_id"] for sq in snap_questions]
                        format_strings = ','.join(['%s'] * len(q_ids))
                        cursor.execute(f"""
                            SELECT question_id, topic_id, exam_id, question_text, question_type, points
                            FROM exam_questions
                            WHERE question_id IN ({format_strings})
                        """, tuple(q_ids))
                        db_q_map = {r["question_id"]: r for r in cursor.fetchall()}

                        result_questions = []
                        for idx, sq in enumerate(snap_questions):
                            q_id = sq["question_id"]
                            db_q = db_q_map.get(q_id)
                            if db_q:
                                result_questions.append({
                                    "question_id": q_id,
                                    "topic_id": db_q.get("topic_id"),
                                    "question_text": db_q["question_text"],
                                    "question_type": db_q["question_type"],
                                    "points": float(db_q["points"]),
                                    "options": sq.get("options", []),
                                    "question_order": idx + 1
                                })
                        return result_questions

            cursor.execute("""
                SELECT question_id, topic_id, exam_id, question_text, question_type, points, options_json, question_order
                FROM exam_questions
                WHERE topic_id = %s AND (status = 'ACTIVE' OR status IS NULL)
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


def get_agent_active_topic_attempt(agent_id, topic_id):
    """
    Fetch current active in-progress assessment attempt for agent and topic.
    If the attempt has expired, updates status to 'EXPIRED' and returns None.
    """
    conn = get_mysql_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM assessment_attempts
                WHERE agent_id = %s AND topic_id = %s AND status = 'IN_PROGRESS'
                ORDER BY started_at DESC LIMIT 1
            """, (agent_id, topic_id))
            row = cursor.fetchone()
            if not row:
                return None

            now = datetime.now()
            expires_at = row["expires_at"]
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except Exception:
                    expires_at = now

            if now > expires_at:
                cursor.execute("""
                    UPDATE assessment_attempts
                    SET status = 'EXPIRED', score = NULL, passed = 0, updated_at = NOW()
                    WHERE attempt_id = %s
                """, (row["attempt_id"],))
                conn.commit()
                return None

            return serialize_sql_row(row)
    finally:
        conn.close()


def save_attempt_draft_answers(attempt_id, agent_id, answers, incoming_version=None):
    """
    Autosave in-progress draft answers for an active assessment attempt.
    Enforces concurrency control via monotonically increasing answers_version.
    Validates attempt ownership, active IN_PROGRESS status, and expiration.
    Returns (success, new_version, last_saved_at, error_message).
    """
    conn = get_mysql_connection()
    if not conn:
        return False, None, None, "Database unavailable."

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assessment_attempts WHERE attempt_id = %s LIMIT 1", (attempt_id,))
            attempt = cursor.fetchone()
            if not attempt:
                return False, None, None, f"Assessment attempt {attempt_id} not found."

            if attempt["agent_id"] != agent_id:
                return False, None, None, "Unauthorized: attempt belongs to another agent."

            if attempt["status"] != "IN_PROGRESS":
                return False, None, None, f"Attempt is in '{attempt['status']}' state; only active in-progress attempts can be autosaved."

            now = datetime.now()
            expires_at = attempt["expires_at"]
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except Exception:
                    expires_at = now

            if now > expires_at:
                cursor.execute("""
                    UPDATE assessment_attempts
                    SET status = 'EXPIRED', score = NULL, passed = 0, updated_at = NOW()
                    WHERE attempt_id = %s
                """, (attempt_id,))
                conn.commit()
                return False, None, None, "This assessment attempt has expired."

            curr_ver = int(attempt.get("answers_version") or 0)
            if incoming_version is not None and int(incoming_version) < curr_ver:
                # Stale autosave request, ignore and return current state without overwriting newer answers
                last_saved = attempt.get("last_saved_at")
                last_saved_str = last_saved.isoformat() if last_saved and hasattr(last_saved, "isoformat") else str(last_saved)
                return True, curr_ver, last_saved_str, "Stale autosave request ignored; newer revision already persisted."

            if not isinstance(answers, dict):
                return False, None, None, "Answers must be a JSON object mapping question IDs to selected option IDs."

            # Merge with existing draft answers if present
            existing_answers = attempt.get("answers_json")
            if isinstance(existing_answers, str):
                try:
                    existing_answers = json.loads(existing_answers)
                except Exception:
                    existing_answers = {}
            elif not isinstance(existing_answers, dict):
                existing_answers = {}

            merged_answers = dict(existing_answers)
            for k, v in answers.items():
                merged_answers[str(k)] = v

            next_ver = curr_ver + 1
            if incoming_version is not None and int(incoming_version) >= curr_ver:
                next_ver = int(incoming_version) + 1

            cursor.execute("""
                UPDATE assessment_attempts
                SET answers_json = %s,
                    answers_version = %s,
                    last_saved_at = NOW(),
                    updated_at = NOW()
                WHERE attempt_id = %s
            """, (json.dumps(merged_answers), next_ver, attempt_id))
            conn.commit()

            cursor.execute("SELECT last_saved_at FROM assessment_attempts WHERE attempt_id = %s", (attempt_id,))
            saved_row = cursor.fetchone()
            saved_dt = saved_row["last_saved_at"] if saved_row else now
            saved_str = saved_dt.isoformat() if saved_dt and hasattr(saved_dt, "isoformat") else str(saved_dt)

            return True, next_ver, saved_str, None
    except Exception as e:
        conn.rollback()
        return False, None, None, str(e)
    finally:
        conn.close()


def abandon_assessment_attempt(attempt_id, agent_id, reason="Candidate abandoned assessment"):
    """
    Explicitly forfeit and abandon an active in-progress assessment attempt.
    Status transitions from IN_PROGRESS to ABANDONED.
    Preserves question snapshot and draft answers; records audit log event.
    Counts towards attempt limits to prevent item harvesting.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM assessment_attempts WHERE attempt_id = %s LIMIT 1", (attempt_id,))
            att = cursor.fetchone()
            if not att:
                return False, "Assessment attempt not found."
            if att["agent_id"] != agent_id:
                return False, "Unauthorized: attempt belongs to another agent."
            if att["status"] != "IN_PROGRESS":
                return False, f"Attempt is in '{att['status']}' state; only active in-progress attempts can be abandoned."

            cursor.execute("""
                UPDATE assessment_attempts
                SET status = 'ABANDONED',
                    closure_reason = %s,
                    updated_at = NOW()
                WHERE attempt_id = %s
            """, (reason, attempt_id))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'ASSESSMENT_ATTEMPT_ABANDONED', 'assessment_attempts', %s, %s, NOW())
            """, (agent_id, attempt_id, json.dumps({
                "attempt_id": attempt_id,
                "topic_id": att.get("topic_id"),
                "exam_id": att.get("exam_id"),
                "reason": reason
            })))
            conn.commit()
            return True, None
    finally:
        conn.close()


def admin_override_assessment_attempt(admin_user_id, agent_id, topic_id, action, reason, attempt_id=None):
    """
    Workforce Officer administrative exception process.
    Supported actions:
      - 'GRANT_EXTRA_ATTEMPT': Grants +1 attempt exception recorded in audit_logs.
      - 'REOPEN_ATTEMPT': Reopens an expired/closed attempt for 30 minutes with audit reason.
      - 'CANCEL_ATTEMPT': Marks an attempt CANCELLED so it does NOT count against candidate quota.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            if action == 'GRANT_EXTRA_ATTEMPT':
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                    VALUES (%s, 'ATTEMPT_LIMIT_OVERRIDE_GRANTED', 'agents', %s, %s, NOW())
                """, (admin_user_id, agent_id, json.dumps({
                    "agent_id": agent_id,
                    "topic_id": topic_id,
                    "action": action,
                    "reason": reason,
                    "granted_by_user_id": admin_user_id
                })))
                conn.commit()
                return True, f"Extra attempt successfully granted for agent {agent_id} on topic {topic_id}."

            elif action == 'REOPEN_ATTEMPT':
                if not attempt_id:
                    cursor.execute("""
                        SELECT attempt_id FROM assessment_attempts
                        WHERE agent_id = %s AND (topic_id = %s OR exam_id = %s) AND status IN ('EXPIRED', 'CLOSED', 'ABANDONED')
                        ORDER BY started_at DESC LIMIT 1
                    """, (agent_id, topic_id, topic_id))
                    row = cursor.fetchone()
                    if not row:
                        return False, "No expired, closed, or abandoned attempt found to reopen."
                    attempt_id = row["attempt_id"]

                cursor.execute("""
                    UPDATE assessment_attempts
                    SET status = 'IN_PROGRESS',
                        expires_at = DATE_ADD(NOW(), INTERVAL 30 MINUTE),
                        closure_reason = %s,
                        updated_at = NOW()
                    WHERE attempt_id = %s
                """, (f"Reopened by Admin {admin_user_id}: {reason}", attempt_id))

                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                    VALUES (%s, 'ATTEMPT_REOPENED_BY_ADMIN', 'assessment_attempts', %s, %s, NOW())
                """, (admin_user_id, attempt_id, json.dumps({
                    "attempt_id": attempt_id,
                    "agent_id": agent_id,
                    "topic_id": topic_id,
                    "reason": reason,
                    "reopened_by": admin_user_id
                })))
                conn.commit()
                return True, f"Attempt {attempt_id} successfully reopened for 30 minutes."

            elif action == 'CANCEL_ATTEMPT':
                if not attempt_id:
                    return False, "attempt_id is required to cancel an attempt."

                cursor.execute("""
                    UPDATE assessment_attempts
                    SET status = 'CANCELLED',
                        closure_reason = %s,
                        updated_at = NOW()
                    WHERE attempt_id = %s
                """, (f"Cancelled by Admin {admin_user_id}: {reason}", attempt_id))

                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                    VALUES (%s, 'ATTEMPT_CANCELLED_BY_ADMIN', 'assessment_attempts', %s, %s, NOW())
                """, (admin_user_id, attempt_id, json.dumps({
                    "attempt_id": attempt_id,
                    "agent_id": agent_id,
                    "reason": reason,
                    "cancelled_by": admin_user_id
                })))
                conn.commit()
                return True, f"Attempt {attempt_id} marked as CANCELLED (exempt from quota)."

            else:
                return False, f"Unknown override action: '{action}'."
    finally:
        conn.close()


def expire_stale_assessment_attempts():
    """
    Authoritative background sweep for expired in-progress attempts.
    Updates status to 'EXPIRED', score=NULL, passed=0, closure_reason='Attempt window expired'.
    Preserves all saved draft answers and question snapshots.
    Returns count of expired attempts.
    """
    conn = get_mysql_connection()
    if not conn:
        return 0
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE assessment_attempts
                SET status = 'EXPIRED',
                    score = NULL,
                    passed = 0,
                    closure_reason = 'Attempt window expired',
                    updated_at = NOW()
                WHERE status = 'IN_PROGRESS' AND expires_at < NOW()
            """)
            affected = cursor.rowcount
            conn.commit()
            return affected
    finally:
        conn.close()


def get_agent_assessment_history(agent_id, topic_id=None):
    """
    Retrieve full historical audit trail of assessment attempts for an agent,
    including SUBMITTED, EXPIRED, ABANDONED, and CANCELLED attempts.
    """
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    att.attempt_id,
                    att.attempt_uuid,
                    att.agent_id,
                    att.exam_id,
                    att.topic_id,
                    top.topic_name,
                    att.task_id,
                    att.attempt_number,
                    att.status,
                    att.started_at,
                    att.expires_at,
                    att.submitted_at,
                    att.score,
                    att.passed,
                    att.answers_version,
                    att.last_saved_at,
                    att.closure_reason,
                    att.created_at,
                    att.updated_at
                FROM assessment_attempts att
                LEFT JOIN assessment_topics top ON att.topic_id = top.topic_id
                WHERE att.agent_id = %s
            """
            params = [agent_id]
            if topic_id:
                query += " AND att.topic_id = %s"
                params.append(topic_id)
            query += " ORDER BY att.started_at DESC, att.attempt_id DESC"
            cursor.execute(query, tuple(params))
            return [serialize_sql_row(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def finalize_assessment_attempt(attempt_id, score, passed, answers_json, subscores_json, model_version, exam_result_id, prediction_id, decision_details, cursor=None):
    """
    Mark an assessment attempt as SUBMITTED with recorded scores and linked predictions.
    Supports sharing an active cursor/transaction to prevent deadlock.
    """
    def _execute_update(cur):
        cur.execute("""
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
            cur.execute("UPDATE exam_results SET attempt_id = %s WHERE exam_result_id = %s", (attempt_id, exam_result_id))
        return True

    if cursor is not None:
        return _execute_update(cursor)

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable. Cannot finalize assessment attempt.")

    try:
        with conn.cursor() as cur:
            res = _execute_update(cur)
        conn.commit()
        return res
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_agent_assessment(user_id, assessment_data, competency_level, confidence, prediction_data=None, exam_id=None, task_id=None, attempt_id=None, cursor=None):
    """
    Save agent assessment result, model prediction, and corresponding audit event transactionally into MySQL.
    Rolls back on failure and raises RuntimeError if persistence fails.
    Preserves historical attempts by incrementing attempt_number for each retake.
    Supports sharing an active cursor/transaction to prevent deadlock.
    """
    def _do_save(cur):
        # 1. Resolve agent_id strictly from server-side user_id
        cur.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
        agent_row = cur.fetchone()
        if not agent_row:
            raise ValueError(f"No agent profile found for user_id {user_id}. Assessment cannot be associated.")
        agent_id = agent_row["agent_id"]

        # 2. Seed or retrieve required exam and model reference records
        default_exam_id, model_id = get_or_create_reference_records(cur)
        active_exam_id = int(exam_id) if exam_id else default_exam_id

        # 3. Determine attempt number (strictly incremented to preserve history)
        cur.execute("""
            SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
            FROM (
                SELECT attempt_number FROM exam_results WHERE agent_id = %s AND exam_id = %s
                UNION ALL
                SELECT attempt_number FROM assessment_attempts WHERE agent_id = %s AND exam_id = %s
            ) AS combined
        """, (agent_id, active_exam_id, agent_id, active_exam_id))
        attempt_row = cur.fetchone()
        attempt_number = attempt_row["next_attempt"] if attempt_row else 1

        # 4. Extract assessment score and determine pass status
        raw_score = float(assessment_data.get("attempt_score") if assessment_data.get("attempt_score") is not None else assessment_data.get("assessment_score", 0.0))
        score = max(0.0, min(100.0, raw_score))  # satisfies chk_exam_result_score
        cur.execute("SELECT passing_score FROM exams WHERE exam_id = %s", (active_exam_id,))
        ex_row = cur.fetchone()
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
        cur.execute("""
            INSERT INTO exam_results (attempt_id, exam_id, agent_id, assessment_score, passed, attempt_number, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (attempt_id, active_exam_id, agent_id, score, passed, attempt_number))
        exam_result_id = cur.lastrowid

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
        cur.execute("""
            INSERT INTO ml_predictions (agent_id, model_id, exam_result_id, predicted_competency, confidence, predicted_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (agent_id, model_id, exam_result_id, predicted_enum, conf_val))
        prediction_id = cur.lastrowid

        # 7b. Link attempt with exam_result and prediction if attempt_id supplied
        if attempt_id:
            cur.execute("""
                UPDATE assessment_attempts
                SET exam_result_id = %s, prediction_id = %s
                WHERE attempt_id = %s
            """, (exam_result_id, prediction_id, attempt_id))

        # 8. Update agent experience_months if provided
        exp_months = int(float(assessment_data.get("previous_experience_months", 0)))
        if exp_months > 0:
            cur.execute("""
                UPDATE agents SET experience_months = %s, updated_at = NOW()
                WHERE agent_id = %s
            """, (exp_months, agent_id))

        # 9. If task_id provided, record in eligibility_evaluations and eligibility_checks
        eval_id = None
        if task_id:
            # Deterministic evaluation: eligibility is governed strictly by exam pass status
            eligibility_status = "ELIGIBLE" if passed else "NOT_ELIGIBLE"
            review_status = "NOT_REQUIRED"
            explanation = f"Evaluated deterministically: {'PASSED' if passed else 'FAILED'} assessment with score {score:.1f}% on Exam {active_exam_id}."

            cur.execute("""
                INSERT INTO eligibility_evaluations 
                (agent_id, task_id, prediction_id, eligibility_status, explanation, review_status, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (agent_id, task_id, prediction_id, eligibility_status, explanation, review_status))
            eval_id = cur.lastrowid

            cur.execute("""
                INSERT INTO eligibility_checks (evaluation_id, requirement_type, expected_value, actual_value, passed, failure_reason)
                VALUES 
                (%s, 'EXAM', %s, %s, %s, %s),
                (%s, 'COMPETENCY', 'ELIGIBLE', %s, %s, %s)
            """, (
                eval_id, f"Passing Score >= {passing_score:.1f}%", f"{score:.1f}%", passed, None if passed else "Assessment score below passing threshold",
                eval_id, "ELIGIBLE" if passed else "NOT_ELIGIBLE", 1 if passed else 0, None if passed else "Assessment score below passing threshold"
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
        cur.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
            VALUES (%s, 'ASSESSMENT_COMPLETED', 'ml_predictions', %s, %s, NOW())
        """, (user_id, prediction_id, json.dumps(audit_payload)))

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

    if cursor is not None:
        return _do_save(cursor)

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database connection unavailable. Cannot persist assessment.")

    try:
        with conn.cursor() as cur:
            res = _do_save(cur)
        conn.commit()
        logger.info(f"Persisted assessment attempt for user {user_id}")
        return res
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

            # Query attempt counts per topic for this agent (including EXPIRED and ABANDONED)
            cursor.execute("""
                SELECT topic_id, COUNT(*) as att_count
                FROM assessment_attempts
                WHERE agent_id = %s AND status IN ('SUBMITTED', 'EXPIRED', 'ABANDONED') AND topic_id IS NOT NULL
                GROUP BY topic_id
            """, (agent_id,))
            topic_attempt_counts = {r["topic_id"]: r["att_count"] for r in cursor.fetchall()}

            # Query any admin override allowances for this agent
            cursor.execute("""
                SELECT COUNT(*) as override_count FROM audit_logs
                WHERE entity_type = 'agents' AND entity_id = %s AND action = 'ATTEMPT_LIMIT_OVERRIDE_GRANTED'
            """, (agent_id,))
            ov_row = cursor.fetchone()
            agent_extra_attempts = int(ov_row["override_count"] or 0) if ov_row else 0

            # 5c. Query all task-to-topic requirements and multi-cert requirements
            task_topics_map = {}
            exam_topics_map = {}
            task_certs_map = {}
            try:
                cursor.execute("""
                    SELECT tc.task_id, tc.certification_id, c.certification_name
                    FROM task_certifications tc
                    JOIN certifications c ON tc.certification_id = c.certification_id
                    WHERE tc.is_mandatory = 1
                    ORDER BY tc.task_id, tc.certification_id
                """)
                for row in cursor.fetchall():
                    task_certs_map.setdefault(row["task_id"], []).append(row)
            except Exception as e:
                logger.warning(f"Could not load task_certifications: {e}")

            try:
                cursor.execute("""
                    SELECT 
                        tat.task_id, 
                        tat.topic_id, 
                        tat.is_mandatory,
                        top.topic_name,
                        top.description AS topic_description,
                        top.passing_score AS topic_passing_score,
                        top.estimated_minutes,
                        top.max_attempts
                    FROM task_assessment_topics tat
                    JOIN assessment_topics top ON tat.topic_id = top.topic_id
                    WHERE top.status = 'ACTIVE'
                    ORDER BY tat.task_id, tat.topic_id
                """)
                for row in cursor.fetchall():
                    task_topics_map.setdefault(row["task_id"], []).append(row)
            except Exception as e:
                logger.warning(f"Could not load task_assessment_topics: {e}")

            try:
                cursor.execute("""
                    SELECT DISTINCT
                        eq.exam_id,
                        top.topic_id,
                        1 AS is_mandatory,
                        top.topic_name,
                        top.description AS topic_description,
                        top.passing_score AS topic_passing_score,
                        top.estimated_minutes
                    FROM exam_questions eq
                    JOIN assessment_topics top ON eq.topic_id = top.topic_id
                    WHERE top.status = 'ACTIVE'
                    ORDER BY eq.exam_id, top.topic_id
                """)
                for row in cursor.fetchall():
                    exam_topics_map.setdefault(row["exam_id"], []).append(row)
            except Exception as e:
                logger.warning(f"Could not load exam_topics_map: {e}")

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

                # Check 1: Mandatory Certifications (support multi-certifications via task_certifications)
                task_req_certs = task_certs_map.get(t_id, [])
                if not task_req_certs and req_cert_id is not None:
                    task_req_certs = [{"certification_id": req_cert_id, "certification_name": req_cert_name}]

                has_cert = True
                cert_pending = False
                missing_cert_names = []
                for c_item in task_req_certs:
                    c_id = c_item["certification_id"]
                    c_name = c_item["certification_name"]
                    if c_id not in active_certs:
                        has_cert = False
                        missing_cert_names.append(c_name)
                        if c_id in pending_certs:
                            cert_pending = True

                # Check 2: Task Assessment Topics & Exams
                req_exam_id = t.get("exam_id")
                latest_res = latest_exam_results.get(req_exam_id) if req_exam_id else None
                exam_score = float(latest_res["assessment_score"]) if latest_res and latest_res.get("assessment_score") is not None else None
                exam_passed = bool(latest_res["passed"]) if latest_res and latest_res.get("passed") is not None else False

                configured_topics = task_topics_map.get(t_id, [])
                if not configured_topics and req_exam_id and exam_req:
                    configured_topics = exam_topics_map.get(req_exam_id, [])

                required_topics_details = []
                all_mandatory_topics_passed = True
                has_attempt_limit_reached = False

                if configured_topics:
                    for c_top in configured_topics:
                        top_id = c_top["topic_id"]
                        is_mand = bool(c_top["is_mandatory"])
                        top_passing = float(c_top["topic_passing_score"])
                        top_latest = latest_topic_results.get(top_id) if not is_reset else None
                        top_score = float(top_latest["score"]) if top_latest and top_latest.get("score") is not None else None
                        # Authoritative latest attempt determines pass/fail against required threshold
                        top_passed = (
                            bool(top_latest and top_latest.get("passed"))
                            and not is_reset
                            and (top_score is not None and top_score >= top_passing)
                        )

                        if top_passed:
                            top_status = "Passed"
                        elif top_latest and not top_passed:
                            top_status = "Failed"
                        else:
                            top_status = "Needed"

                        if is_mand and not top_passed:
                            all_mandatory_topics_passed = False

                        top_max = int(c_top.get("max_attempts") or 3) + agent_extra_attempts
                        top_attempts_used = topic_attempt_counts.get(top_id, 0)
                        if is_mand and not top_passed and top_attempts_used >= top_max:
                            has_attempt_limit_reached = True

                        required_topics_details.append({
                            "topic_id": top_id,
                            "topic_name": c_top["topic_name"],
                            "name": c_top["topic_name"],
                            "description": c_top["topic_description"],
                            "passing_score": top_passing,
                            "passing_threshold": top_passing,
                            "estimated_minutes": c_top["estimated_minutes"],
                            "max_attempts": top_max,
                            "attempts_used": top_attempts_used,
                            "is_mandatory": is_mand,
                            "status": top_status,
                            "score": top_score,
                            "latest_score": top_score
                        })

                if exam_req:
                    if configured_topics:
                        has_assessment_completed = all(top["score"] is not None for top in required_topics_details if top["is_mandatory"]) if required_topics_details else False
                        has_assessment = all_mandatory_topics_passed and bool(required_topics_details)
                    elif req_exam_id and not is_reset:
                        has_assessment_completed = latest_res is not None
                        req_passing_score = float(t["exam_passing_score"]) if t.get("exam_passing_score") is not None else 70.0
                        has_assessment = bool(
                            latest_res is not None 
                            and latest_res.get("passed") 
                            and exam_score is not None 
                            and exam_score >= req_passing_score
                        )
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

                # Check 3: Competency / Deterministic Eligibility
                # Mandatory eligibility is evaluated entirely via deterministic server-side business rules.
                if not exam_req:
                    meets_comp = True
                elif has_assessed:
                    meets_comp = (agent_decision == "Eligible")
                else:
                    meets_comp = has_assessment

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
                    missing_label = ", ".join(missing_cert_names) if missing_cert_names else (req_cert_name or "Required certification")
                    if cert_pending:
                        state = "Verification Pending"
                        blocking_reason = f"Required certification '{missing_label}' is pending review"
                    else:
                        state = "Certification Required"
                        blocking_reason = f"Mandatory certification required: {missing_label}"
                elif agent_status == "SUSPENDED":
                    state = "Verification Pending"
                    blocking_reason = "Agent account is awaiting administrative verification"
                elif not meets_exp:
                    state = f"Requires {min_exp} Months Exp"
                    blocking_reason = f"Agent has {agent_exp_months} months verified experience; task requires {min_exp} months"
                elif has_attempt_limit_reached:
                    state = "Attempt Limit Reached"
                    blocking_reason = "Maximum assessment attempts (3) reached for mandatory qualification topic. Contact workforce officer."
                elif not has_assessment_completed:
                    state = "Assessment Needed"
                    blocking_reason = "Not Eligible: Mandatory task assessment exam required"
                elif not has_assessment:
                    state = "Assessment Needed"
                    blocking_reason = "Not Eligible: Assessment passing score requirement not satisfied"
                elif has_cert and has_assessment and meets_exp and agent_status == "ACTIVE":
                    state = "Ready to Apply"
                    can_apply = True
                    is_eligible = True
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
                    "required_certification": ", ".join([c["certification_name"] for c in task_req_certs]) if task_req_certs else (req_cert_name or "None required"),
                    "required_certifications": [serialize_sql_row(c) for c in task_req_certs],
                    "minimum_experience_months": min_exp,
                    "exam_required": exam_req,
                    "required_topics": required_topics_details,
                    "topics_total": len(required_topics_details),
                    "topics_passed_count": sum(1 for top in required_topics_details if top["status"] == "Passed"),
                    "all_topics_passed": "Not Required" if not exam_req else (all_mandatory_topics_passed and bool(required_topics_details) if configured_topics else has_assessment),
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

    # Independent server-side prerequisite validation (Hard Prerequisites First)
    prereqs = target.get("prerequisites", {})
    if not prereqs.get("certification_met"):
        raise ValueError("Cannot apply: Required certification not verified.")
    if not prereqs.get("experience_met"):
        raise ValueError("Cannot apply: Minimum experience requirement not met.")
    if target.get("exam_required") and not prereqs.get("assessment_met"):
        raise ValueError("Cannot apply: Mandatory task assessment has not been passed with the required score.")
    if not prereqs.get("competency_met"):
        raise ValueError("Cannot apply: Agent competency requirement not met.")

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
    Supports legacy 'admin@verifymesh.io' alias mapping to Robert Otieno (Workforce Officer).
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
            clean_id = identifier.strip().lower()
            sql = """
                SELECT user_id as id, email, email as username, password_hash, full_name, role, is_active 
                FROM users 
                WHERE email = %s 
                   OR (email = 'robert.otieno@verifymesh.io' AND %s IN ('admin@verifymesh.io', 'admin@verifymesh.com'))
                LIMIT 1
            """
            cursor.execute(sql, (clean_id, clean_id))
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
        "dashboardUrl": (
            "/platform-admin/dashboard" if canonical_role in ("Platform Administrator", "PLATFORM_ADMIN")
            else "/workforce/dashboard" if canonical_role in ("Administrator", "Workforce Officer", "ADMIN", "WORKFORCE_OFFICER")
            else "/dashboard"
        )
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
                    "dashboardUrl": (
            "/platform-admin/dashboard" if canonical_role in ("Platform Administrator", "PLATFORM_ADMIN")
            else "/workforce/dashboard" if canonical_role in ("Administrator", "Workforce Officer", "ADMIN", "WORKFORCE_OFFICER")
            else "/dashboard"
        )
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
                    (SELECT COUNT(*) FROM eligibility_evaluations WHERE review_status IN ('APPROVED', 'REJECTED')) AS completed_reviews,
                    (SELECT COUNT(*) FROM agent_certifications WHERE status = 'PENDING') AS pending_certifications,
                    (SELECT COUNT(*) FROM agent_experience WHERE verification_status = 'PENDING') AS pending_experiences,
                    (SELECT COUNT(*) FROM task_applications WHERE status IN ('Application Submitted', 'Under Review')) AS applications_under_review,
                    (SELECT COUNT(*) FROM task_applications) AS total_applications,
                    (SELECT COUNT(*) FROM task_applications WHERE status = 'Shortlisted') AS applications_shortlisted,
                    (SELECT COUNT(*) FROM task_applications WHERE status = 'Assigned') AS applications_assigned,
                    (SELECT COUNT(*) FROM task_applications WHERE status = 'Rejected') AS applications_rejected
            """)
            counts = serialize_sql_row(cursor.fetchone() or {})
            counts["pending_verifications"] = int(counts.get("pending_certifications") or 0) + int(counts.get("pending_experiences") or 0)

            # 2. Active Model Record
            cursor.execute("""
                SELECT model_id, model_name, model_version, algorithm, feature_set_version, accuracy, macro_f1, is_active, created_at
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
                    (SELECT COUNT(*) FROM exam_results WHERE agent_id = a.agent_id) AS total_attempts,
                    (SELECT COUNT(*) FROM agent_certifications WHERE agent_id = a.agent_id AND status = 'VERIFIED') AS verified_certifications_count,
                    (SELECT COUNT(*) FROM agent_experience WHERE agent_id = a.agent_id AND verification_status = 'VERIFIED') AS verified_experiences_count,
                    (SELECT COUNT(*) FROM agent_certifications WHERE agent_id = a.agent_id) AS total_certifications_count,
                    (SELECT COUNT(*) FROM agent_experience WHERE agent_id = a.agent_id) AS total_experiences_count
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

            cursor.execute("""
                SELECT 
                    top.topic_id, 
                    top.topic_name, 
                    top.category_id, 
                    c.category_name,
                    top.description, 
                    top.passing_score, 
                    top.estimated_minutes,
                    top.status
                FROM assessment_topics top
                LEFT JOIN categories c ON top.category_id = c.category_id
                WHERE top.status = 'ACTIVE'
                ORDER BY top.topic_name ASC
            """)
            topics = [serialize_sql_row(r) for r in cursor.fetchall()]

            return {
                "categories": categories,
                "certifications": certifications,
                "skills": skills,
                "exams": exams,
                "topics": topics
            }
    except Exception as e:
        logger.error(f"Error fetching task metadata: {e}")
        return {"categories": [], "certifications": [], "skills": [], "exams": [], "topics": []}
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
            if not row:
                return None

            task_data = serialize_sql_row(row)

            # Query multi-selected certifications
            try:
                cursor.execute("""
                    SELECT tc.certification_id, c.certification_name, c.description, c.validity_period_months
                    FROM task_certifications tc
                    JOIN certifications c ON tc.certification_id = c.certification_id
                    WHERE tc.task_id = %s
                """, (task_id,))
                cert_rows = cursor.fetchall()
                if cert_rows:
                    task_data["required_certification_ids"] = [r["certification_id"] for r in cert_rows]
                    task_data["certifications"] = [serialize_sql_row(r) for r in cert_rows]
                elif task_data.get("required_certification_id"):
                    task_data["required_certification_ids"] = [task_data["required_certification_id"]]
                    task_data["certifications"] = [{
                        "certification_id": task_data["required_certification_id"],
                        "certification_name": task_data.get("certification_name")
                    }]
                else:
                    task_data["required_certification_ids"] = []
                    task_data["certifications"] = []
            except Exception as e:
                logger.warning(f"Could not load task_certifications for detail: {e}")
                if task_data.get("required_certification_id"):
                    task_data["required_certification_ids"] = [task_data["required_certification_id"]]
                else:
                    task_data["required_certification_ids"] = []
                task_data["certifications"] = []

            # Query multi-selected assessment topics
            try:
                cursor.execute("""
                    SELECT tat.topic_id, top.topic_name, top.description, top.passing_score, top.estimated_minutes
                    FROM task_assessment_topics tat
                    JOIN assessment_topics top ON tat.topic_id = top.topic_id
                    WHERE tat.task_id = %s
                """, (task_id,))
                topic_rows = cursor.fetchall()
                task_data["required_topic_ids"] = [r["topic_id"] for r in topic_rows]
                task_data["topics"] = [serialize_sql_row(r) for r in topic_rows]
            except Exception as e:
                logger.warning(f"Could not load task_assessment_topics for detail: {e}")
                task_data["required_topic_ids"] = []
                task_data["topics"] = []

            return task_data
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
        raw_h_min = task_data.get("hourly_rate_min") if task_data.get("hourly_rate_min") is not None else task_data.get("hourly_rate")
        raw_h_max = task_data.get("hourly_rate_max") if task_data.get("hourly_rate_max") is not None else task_data.get("max_hourly_rate")

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
        raw_budget = task_data.get("fixed_budget") if task_data.get("fixed_budget") is not None else task_data.get("total_budget")
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
    raw_positions = task_data.get("positions_count") if task_data.get("positions_count") is not None else task_data.get("positions_available", 1)
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

    raw_min_exp = task_data.get("minimum_experience_months") if task_data.get("minimum_experience_months") is not None else task_data.get("min_experience_months", 0)
    try:
        min_exp = max(0, int(raw_min_exp or 0))
    except (ValueError, TypeError):
        min_exp = 0

    # Certifications: accept required_certification_ids (list) or legacy required_certification_id (int)
    raw_cert_ids = task_data.get("required_certification_ids")
    cert_ids = []
    if isinstance(raw_cert_ids, list):
        for cid in raw_cert_ids:
            try:
                if cid not in (None, "", 0, "0"):
                    cert_ids.append(int(cid))
            except (ValueError, TypeError):
                pass
    elif task_data.get("required_certification_id") not in (None, "", "NONE", 0, "0"):
        try:
            cert_ids.append(int(task_data["required_certification_id"]))
        except (ValueError, TypeError):
            pass

    if cursor and cert_ids:
        format_strings = ','.join(['%s'] * len(cert_ids))
        cursor.execute(f"SELECT certification_id FROM certifications WHERE certification_id IN ({format_strings})", tuple(cert_ids))
        existing_cids = {r["certification_id"] for r in cursor.fetchall()}
        invalid_cids = [cid for cid in cert_ids if cid not in existing_cids]
        if invalid_cids:
            raise ValueError(f"Certification ID(s) {invalid_cids} do not exist.")

    primary_cert_id = cert_ids[0] if cert_ids else None

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
    exam_req = 1 if bool(task_data.get("exam_required") or task_data.get("assessment_required")) else 0
    raw_exam_id = task_data.get("exam_id")
    raw_topic_ids = task_data.get("required_topic_ids")
    topic_ids = []
    if isinstance(raw_topic_ids, list):
        for tid in raw_topic_ids:
            try:
                if tid not in (None, "", 0, "0"):
                    topic_ids.append(int(tid))
            except (ValueError, TypeError):
                pass

    exam_id = None

    if exam_req:
        if raw_exam_id not in (None, "", 0, "0"):
            try:
                exam_id = int(raw_exam_id)
            except (ValueError, TypeError):
                raise ValueError("Invalid exam template ID.")

        if cursor:
            # Validate assessment topics if provided
            if topic_ids:
                format_strings = ','.join(['%s'] * len(topic_ids))
                cursor.execute(f"SELECT topic_id FROM assessment_topics WHERE topic_id IN ({format_strings}) AND status = 'ACTIVE'", tuple(topic_ids))
                existing_tids = {r["topic_id"] for r in cursor.fetchall()}
                invalid_tids = [tid for tid in topic_ids if tid not in existing_tids]
                if invalid_tids:
                    raise ValueError(f"Assessment topic ID(s) {invalid_tids} are not active or do not exist.")

                # If exam_id is not given, resolve it from topic_id
                if not exam_id:
                    cursor.execute(f"SELECT DISTINCT exam_id FROM exam_questions WHERE topic_id IN ({format_strings}) AND exam_id IS NOT NULL LIMIT 1", tuple(topic_ids))
                    mapped_row = cursor.fetchone()
                    if mapped_row and mapped_row.get("exam_id"):
                        exam_id = mapped_row["exam_id"]

            elif is_publish and not exam_id:
                raise ValueError("At least one assessment topic must be selected when task assessment is enabled.")

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
        "required_certification_id": primary_cert_id,
        "required_certification_ids": cert_ids,
        "minimum_experience_months": min_exp,
        "required_skill_id": skill_id,
        "minimum_skill_score": min_skill_score,
        "exam_required": exam_req,
        "exam_id": exam_id,
        "required_topic_ids": topic_ids
    }


def _sync_task_certifications(cursor, task_id, cert_ids):
    """Synchronize task_certifications table with selected certification IDs."""
    try:
        cursor.execute("DELETE FROM task_certifications WHERE task_id = %s", (task_id,))
        for cid in cert_ids:
            cursor.execute("""
                INSERT IGNORE INTO task_certifications (task_id, certification_id, is_mandatory)
                VALUES (%s, %s, 1)
            """, (task_id, cid))
    except Exception as e:
        logger.warning(f"Could not sync task_certifications: {e}")


def _sync_task_assessment_topics(cursor, task_id, exam_id, exam_required, category_id=None, topic_ids=None):
    """
    Synchronize task_assessment_topics with explicit topic_ids (or inferred from exam/category).
    """
    cursor.execute("DELETE FROM task_assessment_topics WHERE task_id = %s", (task_id,))
    if not exam_required:
        return

    final_topic_ids = list(topic_ids) if topic_ids else []
    if not final_topic_ids and exam_id:
        cursor.execute("SELECT DISTINCT topic_id FROM exam_questions WHERE exam_id = %s AND topic_id IS NOT NULL", (exam_id,))
        final_topic_ids = [r["topic_id"] for r in cursor.fetchall()]

    if not final_topic_ids and category_id:
        cursor.execute("SELECT topic_id FROM assessment_topics WHERE category_id = %s AND status = 'ACTIVE'", (category_id,))
        final_topic_ids = [r["topic_id"] for r in cursor.fetchall()]

    for tid in final_topic_ids:
        cursor.execute("""
            INSERT IGNORE INTO task_assessment_topics (task_id, topic_id, is_mandatory)
            VALUES (%s, %s, 1)
        """, (task_id, tid))


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

            # Synchronize task certifications
            _sync_task_certifications(cursor, task_id, validated["required_certification_ids"])

            # Synchronize task assessment topics
            _sync_task_assessment_topics(
                cursor, task_id, validated["exam_id"], validated["exam_required"], validated["category_id"], validated["required_topic_ids"]
            )

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

            # Synchronize task certifications
            _sync_task_certifications(cursor, task_id, validated["required_certification_ids"])

            # Synchronize task assessment topics
            _sync_task_assessment_topics(
                cursor, task_id, validated["exam_id"], validated["exam_required"], validated["category_id"], validated["required_topic_ids"]
            )

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


# Centralized competency and topic registry
COMPETENCY_TOPIC_REGISTRY = {
    1: {
        "topic_id": 1,
        "name": "Product Knowledge",
        "slug": "prod",
        "score_key": "applicant_prod_score",
        "gap_key": "product_knowledge_gap",
        "min_key": "task_min_prod",
        "default_min": 70.0,
    },
    2: {
        "topic_id": 2,
        "name": "Sales Techniques and Objection Handling",
        "slug": "sales",
        "score_key": "applicant_sales_score",
        "gap_key": "sales_skill_gap",
        "min_key": "task_min_sales",
        "default_min": 70.0,
    },
    3: {
        "topic_id": 3,
        "name": "Customer Communication",
        "slug": "comm",
        "score_key": "applicant_comm_score",
        "gap_key": "communication_gap",
        "min_key": "task_min_comm",
        "default_min": 75.0,
    },
    4: {
        "topic_id": 4,
        "name": "Customer Relationship Management",
        "slug": "cs",
        "score_key": "applicant_cs_score",
        "gap_key": "customer_service_gap",
        "min_key": "task_min_cs",
        "default_min": 75.0,
    },
}

# Explicit competency assessment states
COMPETENCY_STATE_ASSESSED_AND_PASSED = "ASSESSED_AND_PASSED"
COMPETENCY_STATE_ASSESSED_AND_FAILED = "ASSESSED_AND_FAILED"
COMPETENCY_STATE_NOT_ASSESSED = "NOT_ASSESSED"
COMPETENCY_STATE_NOT_REQUIRED = "NOT_REQUIRED"


def build_task_suitability_features(
    agent_data,
    task_data,
    certs=None,
    topic_scores=None,
    latest_score=None,
    strict=False,
    required_topic_ids=None,
):
    """
    Constructs the centralized Stage 2 feature dictionary containing the exact 5-feature
    Phase 3/4 schema (`STAGE2_V2_FEATURES`: weighted_skill_margin, min_skill_margin,
    weakest_link_deficit, exp_surplus_tanh, difficulty_tier) alongside the 28-feature
    legacy keys for backward compatibility.

    When `strict=True` (used in live Stage 2 inference), missing required assessment scores
    or experience values raise a ValueError rather than fabricating defaults.
    """
    from src.stage2_feature_engineering import build_complete_stage2_feature_dict

    if not isinstance(agent_data, dict) or not isinstance(task_data, dict):
        raise ValueError("agent_data and task_data must be dictionaries.")

    certs = certs or []
    topic_scores = topic_scores or {}

    if strict:
        if agent_data.get("experience_months") is None:
            raise ValueError("Missing applicant 'experience_months' for Stage 2 feature engineering.")
        if bool(task_data.get("exam_required")) and latest_score is None:
            raise ValueError("Missing required assessment score for Stage 2 feature engineering.")

    # Task minimums & difficulty
    task_min_exp = float(task_data.get("minimum_experience_months") or 0.0)
    task_min_assessment = float(task_data.get("exam_passing_score") or 70.0)
    task_category = task_data.get("category_name") or task_data.get("task_category")

    # Difficulty tier: 1 (Entry/Low), 2 (Intermediate/Medium), 3 (High/Advanced)
    if task_data.get("difficulty_tier") in (1, 2, 3, 1.0, 2.0, 3.0):
        diff_tier = int(task_data["difficulty_tier"])
    elif task_min_exp >= 24:
        diff_tier = 3
    elif task_min_exp >= 12:
        diff_tier = 2
    else:
        diff_tier = 1

    # Applicant attributes
    app_rel_exp = float(agent_data.get("experience_months") or 0.0)
    app_sales_exp = float(agent_data.get("sales_experience_months") or 0.0)
    app_cs_exp = float(agent_data.get("customer_service_experience_months") or 0.0)
    if app_sales_exp == 0.0 and app_rel_exp > 0.0:
        app_sales_exp = round(app_rel_exp * 0.4, 1)
    if app_cs_exp == 0.0 and app_rel_exp > 0.0:
        app_cs_exp = round(app_rel_exp * 0.4, 1)

    app_cert_count = float(len(certs))

    # Cert flags by category keyword
    has_sales_cert = 0.0
    has_cs_cert = 0.0
    has_tech_cert = 0.0
    for c in certs:
        c_name = (c.get("certification_name") or "").lower()
        if any(w in c_name for w in ("sale", "market", "negotiat", "retail", "business")):
            has_sales_cert = 1.0
        if any(w in c_name for w in ("customer", "support", "service", "client", "care")):
            has_cs_cert = 1.0
        if any(w in c_name for w in ("tech", "network", "develop", "it", "cloud", "secur", "data", "admin")):
            has_tech_cert = 1.0

    # Assessment & topic scores
    if latest_score is not None:
        app_assessment_score = float(latest_score)
    elif strict:
        if topic_scores:
            app_assessment_score = float(sum(float(v) for v in topic_scores.values()) / len(topic_scores))
        else:
            app_assessment_score = float(task_min_assessment)
    else:
        app_assessment_score = 75.0

    # Resolve required topic IDs from argument or task_data
    if required_topic_ids is None and "required_topic_ids" in task_data:
        required_topic_ids = set(task_data["required_topic_ids"])
    elif required_topic_ids is not None:
        required_topic_ids = set(required_topic_ids)

    # Sub-skill minimum thresholds
    task_min_comm = float(task_data.get("task_min_comm", 75.0 if task_category and "support" in str(task_category).lower() else 70.0))
    task_min_prod = float(task_data.get("task_min_prod", 70.0))
    task_min_sales = float(task_data.get("task_min_sales", 70.0))
    task_min_cs = float(task_data.get("task_min_cs", 75.0 if task_category and "support" in str(task_category).lower() else 70.0))

    # Dynamic topic score assignment with task-specific isolation:
    # If required_topic_ids is provided, non-required topics do NOT penalize the candidate.
    if required_topic_ids:
        # Topic 3: Customer Communication
        if 3 in required_topic_ids:
            app_comm_score = float(topic_scores.get(3, topic_scores.get("communication_score", app_assessment_score)))
        else:
            app_comm_score = max(task_min_comm, app_assessment_score)

        # Topic 1: Product Knowledge
        if 1 in required_topic_ids:
            app_prod_score = float(topic_scores.get(1, topic_scores.get("product_knowledge_score", app_assessment_score)))
        else:
            app_prod_score = max(task_min_prod, app_assessment_score)

        # Topic 2: Sales Techniques
        if 2 in required_topic_ids:
            app_sales_score = float(topic_scores.get(2, topic_scores.get("sales_skill_score", app_assessment_score)))
        else:
            app_sales_score = max(task_min_sales, app_assessment_score)

        # Topic 4: Customer Relationship Management
        if 4 in required_topic_ids:
            app_cs_score = float(topic_scores.get(4, topic_scores.get("customer_service_score", app_assessment_score)))
        else:
            app_cs_score = max(task_min_cs, app_assessment_score)

        # Active margins only consider the required topics
        active_margins = []
        if 3 in required_topic_ids:
            active_margins.append(app_comm_score - task_min_comm)
        if 1 in required_topic_ids:
            active_margins.append(app_prod_score - task_min_prod)
        if 2 in required_topic_ids:
            active_margins.append(app_sales_score - task_min_sales)
        if 4 in required_topic_ids:
            active_margins.append(app_cs_score - task_min_cs)

        if not active_margins:
            active_margins.append(app_assessment_score - task_min_assessment)

        isolated_min_margin = min(active_margins)
        isolated_weakest_deficit = min(0.0, isolated_min_margin)
    else:
        # Full backward compatibility mode (when required_topic_ids not specified)
        app_comm_score = float(topic_scores.get(3, topic_scores.get("communication_score", app_assessment_score)))
        app_prod_score = float(topic_scores.get(1, topic_scores.get("product_knowledge_score", app_assessment_score)))
        app_sales_score = float(topic_scores.get(2, topic_scores.get("sales_skill_score", app_assessment_score)))
        app_cs_score = float(topic_scores.get(4, topic_scores.get("customer_service_score", app_assessment_score)))
        isolated_min_margin = None
        isolated_weakest_deficit = None

    raw_context = {
        "task_category": task_category,
        "difficulty_tier": diff_tier,
        "task_min_exp": task_min_exp,
        "task_min_assessment": task_min_assessment,
        "task_min_comm": task_min_comm,
        "task_min_prod": task_min_prod,
        "task_min_sales": task_min_sales,
        "task_min_cs": task_min_cs,
        "applicant_relevant_exp": app_rel_exp,
        "applicant_sales_exp": app_sales_exp,
        "applicant_cs_exp": app_cs_exp,
        "applicant_cert_count": app_cert_count,
        "applicant_has_sales_cert": has_sales_cert,
        "applicant_has_cs_cert": has_cs_cert,
        "applicant_has_tech_cert": has_tech_cert,
        "applicant_assessment_score": app_assessment_score,
        "applicant_comm_score": app_comm_score,
        "applicant_prod_score": app_prod_score,
        "applicant_sales_score": app_sales_score,
        "applicant_cs_score": app_cs_score,
    }
    if required_topic_ids is not None:
        raw_context["required_topic_ids"] = list(required_topic_ids)
    if isolated_min_margin is not None:
        raw_context["min_skill_margin"] = isolated_min_margin
        raw_context["weakest_link_deficit"] = isolated_weakest_deficit

    return build_complete_stage2_feature_dict(raw_context)


def get_task_applicants(task_id):
    """
    Retrieve all applicants for a given task, including full agent profile,
    contact info, verification status, experience, certifications, topic results,
    Stage 1 deterministic eligibility status, and Stage 2 advisory task suitability score
    (computed strictly for Stage 1-eligible candidates).
    """
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT t.task_id, t.task_name, t.status, t.positions_count,
                       c.category_name, tr.minimum_competency, tr.minimum_experience_months,
                       tr.required_certification_id, tr.exam_required, t.exam_id,
                       e.passing_score AS exam_passing_score
                FROM tasks t
                JOIN categories c ON t.category_id = c.category_id
                LEFT JOIN task_requirements tr ON t.task_id = tr.task_id
                LEFT JOIN exams e ON t.exam_id = e.exam_id
                WHERE t.task_id = %s
            """, (task_id,))
            task = cursor.fetchone()
            if not task:
                return []

            # Retrieve configured assessment topics for this specific task (authoritative topic mapping)
            cursor.execute("""
                SELECT tat.topic_id, tat.is_mandatory, top.topic_name, top.passing_score,
                       top.description AS topic_description, top.estimated_minutes
                FROM task_assessment_topics tat
                JOIN assessment_topics top ON tat.topic_id = top.topic_id
                WHERE tat.task_id = %s AND top.status = 'ACTIVE'
                ORDER BY tat.topic_id
            """, (task_id,))
            configured_topic_rows = cursor.fetchall()
            configured_topics_map = {r["topic_id"]: r for r in configured_topic_rows}
            required_topic_ids = set(configured_topics_map.keys())

            # Fallback: if no explicit task_assessment_topics rows but exam_id exists and exam is required
            if not required_topic_ids and task.get("exam_id") and task.get("exam_required"):
                cursor.execute("""
                    SELECT DISTINCT eq.topic_id, 1 AS is_mandatory, top.topic_name, top.passing_score,
                           top.description AS topic_description, top.estimated_minutes
                    FROM exam_questions eq
                    JOIN assessment_topics top ON eq.topic_id = top.topic_id
                    WHERE eq.exam_id = %s AND top.status = 'ACTIVE'
                    ORDER BY eq.topic_id
                """, (task["exam_id"],))
                for r in cursor.fetchall():
                    configured_topics_map[r["topic_id"]] = r
                required_topic_ids = set(configured_topics_map.keys())

            # Map explicit task assessment topic thresholds into task specification
            if 3 in configured_topics_map:
                task["task_min_comm"] = float(configured_topics_map[3]["passing_score"])
            if 1 in configured_topics_map:
                task["task_min_prod"] = float(configured_topics_map[1]["passing_score"])
            if 2 in configured_topics_map:
                task["task_min_sales"] = float(configured_topics_map[2]["passing_score"])
            if 4 in configured_topics_map:
                task["task_min_cs"] = float(configured_topics_map[4]["passing_score"])

            # Retrieve all active assessment topics in the system for complete state classification
            cursor.execute("""
                SELECT topic_id, topic_name, passing_score, description, estimated_minutes
                FROM assessment_topics
                WHERE status = 'ACTIVE'
                ORDER BY topic_id
            """)
            all_system_topics = cursor.fetchall()

            cursor.execute("""
                SELECT 
                    ta.application_id,
                    ta.task_id,
                    ta.agent_id,
                    ta.status,
                    ta.applied_at,
                    ta.updated_at,
                    ta.notes,
                    u.user_id,
                    u.full_name,
                    u.email,
                    a.phone,
                    a.experience_months,
                    a.status AS agent_status
                FROM task_applications ta
                JOIN agents a ON ta.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ta.task_id = %s
                ORDER BY ta.applied_at DESC
            """, (task_id,))
            applicants = cursor.fetchall()

            from src.task_suitability_inference import task_suitability_engine
            traceability_meta = task_suitability_engine.get_traceability_metadata()
            default_threshold = float(traceability_meta.get("applied_threshold", 0.60))
            synthetic_disclaimer = traceability_meta.get("synthetic_data_disclaimer", "")

            results = []
            for app in applicants:
                user_id = app["user_id"]
                agent_id = app["agent_id"]

                # 1. Check for non-destructive assessment reset in audit_logs
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
                reset_time = reset_row["created_at"] if reset_row else None

                cursor.execute("""
                    SELECT predicted_competency, confidence, predicted_at
                    FROM ml_predictions
                    WHERE agent_id = %s
                    ORDER BY prediction_id DESC LIMIT 1
                """, (agent_id,))
                pred = cursor.fetchone()

                cursor.execute("""
                    SELECT c.certification_id, c.certification_name, ac.status, ac.expiry_date
                    FROM agent_certifications ac
                    JOIN certifications c ON ac.certification_id = c.certification_id
                    WHERE ac.agent_id = %s AND ac.status IN ('ACTIVE', 'VERIFIED')
                      AND (ac.expiry_date IS NULL OR ac.expiry_date >= CURDATE())
                """, (agent_id,))
                certs = cursor.fetchall()

                latest_score = None
                exam_passed = False
                if task.get("exam_id"):
                    cursor.execute("""
                        SELECT er.exam_result_id, er.assessment_score, er.passed, er.completed_at
                        FROM exam_results er
                        LEFT JOIN assessment_attempts att ON er.attempt_id = att.attempt_id
                        WHERE er.agent_id = %s AND er.exam_id = %s
                          AND (att.status IS NULL OR att.status = 'SUBMITTED')
                          AND (%s IS NULL OR er.completed_at >= %s)
                        ORDER BY er.completed_at DESC, er.exam_result_id DESC LIMIT 1
                    """, (agent_id, task["exam_id"], reset_time, reset_time))
                    er = cursor.fetchone()
                    if er and not is_reset:
                        latest_score = float(er["assessment_score"]) if er["assessment_score"] is not None else None
                        exam_passed = bool(er["passed"])
                else:
                    cursor.execute("""
                        SELECT atr.score, atr.passed, atr.completed_at
                        FROM agent_topic_results atr
                        LEFT JOIN assessment_attempts att ON atr.attempt_id = att.attempt_id
                        WHERE atr.agent_id = %s
                          AND (att.status IS NULL OR att.status = 'SUBMITTED')
                          AND (%s IS NULL OR atr.completed_at >= %s)
                        ORDER BY atr.completed_at DESC, atr.result_id DESC LIMIT 1
                    """, (agent_id, reset_time, reset_time))
                    atr = cursor.fetchone()
                    if atr and not is_reset:
                        latest_score = float(atr["score"]) if atr["score"] is not None else None
                        exam_passed = bool(atr["passed"])

                # 2. Strict Task-Specific Topic Retrieval:
                # Query ONLY the assessment topics configured for THIS task.
                # Exclude unrelated historical attempts, in-progress/invalidated attempts, and other agents.
                valid_task_topic_results = {}
                if required_topic_ids:
                    placeholders = ','.join(['%s'] * len(required_topic_ids))
                    cursor.execute(f"""
                        SELECT atr.result_id, atr.topic_id, atr.attempt_id, atr.score, atr.passed, atr.completed_at,
                               att.status AS attempt_status
                        FROM agent_topic_results atr
                        LEFT JOIN assessment_attempts att ON atr.attempt_id = att.attempt_id
                        WHERE atr.agent_id = %s
                          AND atr.topic_id IN ({placeholders})
                          AND (att.status IS NULL OR att.status = 'SUBMITTED')
                          AND (%s IS NULL OR atr.completed_at >= %s)
                        ORDER BY atr.completed_at DESC, atr.result_id DESC
                    """, [agent_id] + list(required_topic_ids) + [reset_time, reset_time])
                    for r in cursor.fetchall():
                        tid = r["topic_id"]
                        if tid not in valid_task_topic_results:
                            valid_task_topic_results[tid] = r

                # 3. Explicit Competency Assessment States
                competency_states = {}
                topic_evaluations = []
                all_mandatory_topics_passed = True

                for sys_top in all_system_topics:
                    tid = sys_top["topic_id"]
                    tname = sys_top["topic_name"]
                    if tid not in required_topic_ids:
                        c_state = COMPETENCY_STATE_NOT_REQUIRED
                        c_score = None
                        c_passed = None
                        c_mand = False
                        c_threshold = float(sys_top["passing_score"])
                        c_attempt_id = None
                    else:
                        c_mand = bool(configured_topics_map[tid].get("is_mandatory", True))
                        c_threshold = float(configured_topics_map[tid]["passing_score"])
                        if is_reset or tid not in valid_task_topic_results:
                            c_state = COMPETENCY_STATE_NOT_ASSESSED
                            c_score = None
                            c_passed = False
                            c_attempt_id = None
                            if c_mand:
                                all_mandatory_topics_passed = False
                        else:
                            top_res = valid_task_topic_results[tid]
                            c_score = float(top_res["score"]) if top_res["score"] is not None else None
                            c_attempt_id = top_res.get("attempt_id")
                            c_passed = bool(top_res["passed"]) and (c_score is not None and c_score >= c_threshold) and not is_reset
                            if c_passed:
                                c_state = COMPETENCY_STATE_ASSESSED_AND_PASSED
                            else:
                                c_state = COMPETENCY_STATE_ASSESSED_AND_FAILED
                                if c_mand:
                                    all_mandatory_topics_passed = False

                    competency_states[tid] = {
                        "topic_id": tid,
                        "topic_name": tname,
                        "state": c_state,
                        "score": c_score,
                        "passed": c_passed,
                        "is_mandatory": c_mand,
                        "passing_score": c_threshold,
                        "attempt_id": c_attempt_id,
                    }
                    topic_evaluations.append(competency_states[tid])

                # 4. Stage 1 Deterministic Prerequisite Evaluation (Authoritative Gatekeeper)
                req_cert_id = task.get("required_certification_id")
                has_cert = True
                if req_cert_id:
                    has_cert = any(c["certification_id"] == req_cert_id for c in certs)

                min_exp = int(task.get("minimum_experience_months") or 0)
                agent_exp = int(app.get("experience_months") or 0)
                meets_exp = agent_exp >= min_exp

                exam_req = bool(task.get("exam_required"))
                if exam_req:
                    if required_topic_ids:
                        has_assessment = all_mandatory_topics_passed and not is_reset
                    elif task.get("exam_id"):
                        has_assessment = exam_passed and not is_reset
                    else:
                        has_assessment = False
                else:
                    has_assessment = True
                assessment_passed = has_assessment

                pred_comp = pred["predicted_competency"] if pred else "Unassessed"
                meets_comp = True
                is_active_agent = app.get("agent_status", "ACTIVE") == "ACTIVE"
                meets_all = bool(has_cert and meets_exp and has_assessment and is_active_agent)

                # 5. Stage 2 Advisory Suitability Inference:
                # Evaluated strictly for Stage 1-eligible candidates.
                suitability_info = None
                stage2_status = "ineligible_not_scored"
                suitability_error = None

                task_topic_scores = {
                    tid: float(res["score"])
                    for tid, res in valid_task_topic_results.items()
                    if res.get("score") is not None
                }

                if meets_all:
                    try:
                        feat_dict = build_task_suitability_features(
                            agent_data=app,
                            task_data=task,
                            certs=certs,
                            topic_scores=task_topic_scores,
                            latest_score=latest_score if latest_score is not None else (
                                sum(task_topic_scores.values()) / len(task_topic_scores) if task_topic_scores else None
                            ),
                            strict=True,
                            required_topic_ids=required_topic_ids,
                        )
                        feat_dict["is_eligible"] = True
                        feat_dict["meets_prerequisites"] = True
                        feat_dict["applicant_id"] = app["agent_id"]
                        feat_dict["task_id"] = task_id
                        feat_dict["assessment_completeness_status"] = "complete"
                        feat_dict["competency_breakdown"] = topic_evaluations
                        suitability_info = task_suitability_engine.predict(feat_dict)
                        stage2_status = "scored"
                    except Exception as ex:
                        stage2_status = "error"
                        suitability_error = str(ex)
                        logger.warning(
                            f"Could not compute Stage 2 task suitability for eligible agent {agent_id} on task {task_id}: {ex}"
                        )

                if meets_all and suitability_info:
                    suitability_score = suitability_info.get("suitability_score")
                    suitability_percent = suitability_info.get("suitability_percent")
                    suitability_label = suitability_info.get("suitability_label")
                    advisory_tier = suitability_info.get("advisory_tier")
                    advisory_tier_code = suitability_info.get("advisory_tier_code")
                    suitability_class = suitability_info.get("predicted_class")
                    applied_threshold = suitability_info.get("applied_threshold", default_threshold)
                    engineered_features = suitability_info.get("engineered_features")
                    contributing_factors = suitability_info.get("contributing_factors", [])
                    model_trace = suitability_info.get("model_traceability", traceability_meta)
                elif not meets_all:
                    suitability_score = None
                    suitability_percent = None
                    suitability_label = "Ineligible — Stage 1 Gate Failed"
                    advisory_tier = "Ineligible — Stage 1 Gate Failed"
                    advisory_tier_code = "ineligible"
                    suitability_class = None
                    applied_threshold = default_threshold
                    engineered_features = None
                    contributing_factors = []
                    model_trace = traceability_meta
                else:
                    suitability_score = None
                    suitability_percent = None
                    suitability_label = "Score Unavailable"
                    advisory_tier = "Score Unavailable"
                    advisory_tier_code = "unavailable"
                    suitability_class = None
                    applied_threshold = default_threshold
                    engineered_features = None
                    contributing_factors = []
                    model_trace = traceability_meta

                results.append({
                    "application_id": app["application_id"],
                    "task_id": app["task_id"],
                    "agent_id": app["agent_id"],
                    "user_id": app["user_id"],
                    "full_name": app["full_name"],
                    "email": app["email"],
                    "phone": app["phone"],
                    "status": app["status"],
                    "applied_at": app["applied_at"].isoformat() if hasattr(app["applied_at"], "isoformat") else str(app["applied_at"]),
                    "updated_at": app["updated_at"].isoformat() if hasattr(app["updated_at"], "isoformat") else str(app["updated_at"]),
                    "notes": app["notes"],
                    "experience_months": agent_exp,
                    "certifications": [serialize_sql_row(c) for c in certs],
                    "predicted_competency": pred_comp if pred else "Unassessed",
                    "confidence": float(pred["confidence"]) if pred and pred.get("confidence") is not None else None,
                    "latest_score": latest_score,
                    "assessment_passed": assessment_passed,
                    "meets_prerequisites": meets_all,
                    "prerequisites": {
                        "cert_met": has_cert,
                        "exp_met": meets_exp,
                        "comp_met": meets_comp,
                        "assessment_met": has_assessment
                    },
                    "competency_states": competency_states,
                    "topic_evaluations": topic_evaluations,
                    "required_topic_ids": list(required_topic_ids),
                    "configured_topics": [serialize_sql_row(r) for r in configured_topic_rows],
                    "stage2_status": stage2_status,
                    "model_version": model_trace.get("model_version", "3.0.0"),
                    "prediction_score": suitability_score,
                    "prediction_timestamp": suitability_info.get("prediction_timestamp") if suitability_info else None,
                    "feature_values": engineered_features,
                    "assessment_completeness_status": suitability_info.get("assessment_completeness_status", "complete") if suitability_info else ("complete" if has_assessment else "incomplete"),
                    "competency_breakdown": topic_evaluations,
                    "suitability_score": suitability_score,
                    "suitability_percent": suitability_percent,
                    "suitability_label": suitability_label,
                    "advisory_tier": advisory_tier,
                    "advisory_tier_code": advisory_tier_code,
                    "advisory_classification": advisory_tier,
                    "suitability_class": suitability_class,
                    "applied_threshold": applied_threshold,
                    "advisory_threshold": applied_threshold,
                    "engineered_features": engineered_features,
                    "contributing_factors": contributing_factors,
                    "model_traceability": model_trace,
                    "eligible_rank": None,
                    "suitability_error": suitability_error,
                    "is_advisory": True,
                    "synthetic_data_disclaimer": synthetic_disclaimer,
                    "suitability_disclaimer": (
                        "Advisory Task Suitability Score (Stage 2 LR v3, tau=0.60): "
                        "Administrator retains final assignment authority. "
                        "Trained on synthetic simulation data (Scenario B); not yet validated on real-world outcomes."
                    ),
                })

            # Compute 1-based advisory ranking strictly among Stage 1-eligible scored candidates
            eligible_scored = [
                r for r in results
                if r.get("meets_prerequisites") and r.get("suitability_score") is not None
            ]
            eligible_scored.sort(
                key=lambda r: (
                    float(r.get("suitability_score") or 0.0),
                    float(r.get("latest_score") or 0.0),
                    int(r.get("experience_months") or 0),
                    -int(r.get("application_id") or 0),
                ),
                reverse=True,
            )
            for idx, item in enumerate(eligible_scored, start=1):
                item["eligible_rank"] = idx

            return results
    except Exception as e:
        logger.error(f"Error fetching task applicants for task {task_id}: {e}")
        return []
    finally:
        conn.close()


APPLICATION_STATUS_TRANSITIONS = {
    "Application Submitted": ("Under Review", "Shortlisted", "Rejected"),
    "Under Review": ("Shortlisted", "Rejected"),
    "Shortlisted": ("Under Review", "Rejected"),
    # Terminal states: no further administrative status change through the generic route.
    "Assigned": (),
    "Rejected": (),
    "Withdrawn": (),
}


def update_task_application_status(application_id, status, notes=None, admin_user_id=None):
    """
    Update application lifecycle status with audit logging.

    Administrative review transitions only (Under Review, Shortlisted, Rejected).
    Assignment must go through assign_task_application, which rechecks eligibility.
    Terminal applications (Assigned, Rejected, Withdrawn) cannot be changed here.
    """
    if status == "Assigned":
        raise ValueError("Applications can only be assigned through the assignment action, which rechecks eligibility.")
    if status == "Withdrawn":
        raise ValueError("Withdrawal is an agent action and cannot be set through the administrator review route.")
    valid_statuses = ("Under Review", "Shortlisted", "Rejected")
    if status not in valid_statuses:
        raise ValueError(f"Invalid application status: '{status}'. Allowed statuses: {', '.join(valid_statuses)}")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT application_id, task_id, agent_id, status FROM task_applications WHERE application_id = %s FOR UPDATE", (application_id,))
            app = cursor.fetchone()
            if not app:
                raise ValueError(f"Application {application_id} not found.")

            allowed_next = APPLICATION_STATUS_TRANSITIONS.get(app["status"], ())
            if status not in allowed_next:
                raise ValueError(
                    f"Cannot change application from '{app['status']}' to '{status}'."
                )

            cursor.execute("""
                UPDATE task_applications
                SET status = %s,
                    notes = COALESCE(%s, notes),
                    updated_at = NOW()
                WHERE application_id = %s
            """, (status, notes, application_id))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_APPLICATION_STATUS_UPDATED', 'task_applications', %s, %s, NOW())
            """, (admin_user_id or 1, application_id, json.dumps({
                "application_id": application_id,
                "previous_status": app["status"],
                "new_status": status,
                "notes": notes
            })))

        conn.commit()
        return {"application_id": application_id, "status": status, "notes": notes}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating task application {application_id}: {e}")
        raise
    finally:
        conn.close()


def assign_task_application(application_id, admin_user_id, override_reason=None):
    """
    Assign an application to a task.
    Authoritatively re-evaluates all server-side prerequisites.
    Updates application status to 'Assigned' and task status to 'COMPLETED'.
    Inserts audit log event 'TASK_APPLICATION_ASSIGNED' with model version, score, and override reason.
    """
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable.")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ta.application_id, ta.task_id, ta.agent_id, ta.status AS app_status,
                       t.task_name, t.status AS task_status, t.positions_count,
                       u.user_id, u.full_name, a.experience_months
                FROM task_applications ta
                JOIN tasks t ON ta.task_id = t.task_id
                JOIN agents a ON ta.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ta.application_id = %s
            """, (application_id,))
            app_row = cursor.fetchone()
            if not app_row:
                raise ValueError(f"Application {application_id} not found.")

            if app_row["task_status"] != "ACTIVE":
                raise ValueError(f"Cannot assign task: Task is currently in '{app_row['task_status']}' status.")

            if app_row["app_status"] not in ("Application Submitted", "Under Review", "Shortlisted"):
                raise ValueError(f"Cannot assign: application is '{app_row['app_status']}' and is not assignable.")

            task_id = app_row["task_id"]
            agent_id = app_row["agent_id"]

            cursor.execute("""
                SELECT minimum_competency, required_certification_id, minimum_experience_months, exam_required
                FROM task_requirements WHERE task_id = %s
            """, (task_id,))
            req = cursor.fetchone()

            if req:
                req_cert_id = req["required_certification_id"]
                if req_cert_id:
                    cursor.execute("""
                        SELECT certification_id FROM agent_certifications
                        WHERE agent_id = %s AND certification_id = %s AND status IN ('ACTIVE', 'VERIFIED')
                    """, (agent_id, req_cert_id))
                    if not cursor.fetchone():
                        raise ValueError("Cannot assign task: Applicant lacks required verified certification.")

                min_exp = int(req["minimum_experience_months"] or 0)
                agent_exp = int(app_row["experience_months"] or 0)
                if agent_exp < min_exp:
                    raise ValueError(f"Cannot assign task: Applicant has {agent_exp} months experience; task requires {min_exp} months.")

                if bool(req["exam_required"]):
                    cursor.execute("""
                        SELECT t.exam_id FROM tasks t WHERE t.task_id = %s
                    """, (task_id,))
                    t_exam = cursor.fetchone()
                    exam_id = t_exam["exam_id"] if t_exam else None
                    passed_assessment = False
                    if exam_id:
                        cursor.execute("""
                            SELECT passed FROM exam_results
                            WHERE agent_id = %s AND exam_id = %s
                            ORDER BY exam_result_id DESC LIMIT 1
                        """, (agent_id, exam_id))
                        er = cursor.fetchone()
                        passed_assessment = bool(er and er["passed"])
                    else:
                        cursor.execute("""
                            SELECT passed FROM agent_topic_results
                            WHERE agent_id = %s
                            ORDER BY result_id DESC LIMIT 1
                        """, (agent_id,))
                        atr = cursor.fetchone()
                        passed_assessment = bool(atr and atr["passed"])

                    if not passed_assessment:
                        raise ValueError("Cannot assign task: Applicant has not passed the required competency assessment.")

            cursor.execute("""
                UPDATE task_applications
                SET status = 'Assigned', updated_at = NOW()
                WHERE application_id = %s
            """, (application_id,))

            cursor.execute("""
                UPDATE tasks
                SET status = 'COMPLETED', updated_at = NOW()
                WHERE task_id = %s
            """, (task_id,))

            # Retrieve applicant's suitability record if available for audit trail
            suitability_score = None
            model_ver = "3.0.0"
            advisory_tau = 0.60
            try:
                applicants = get_task_applicants(task_id)
                matched = next((a for a in applicants if a.get("application_id") == application_id), None)
                if matched:
                    suitability_score = matched.get("suitability_score")
                    model_ver = matched.get("model_version", "3.0.0")
                    advisory_tau = matched.get("advisory_threshold", 0.60)
            except Exception:
                pass

            admin_decision = "ASSIGNED_WITH_OVERRIDE" if override_reason else "ASSIGNED"

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'TASK_APPLICATION_ASSIGNED', 'task_applications', %s, %s, NOW())
            """, (admin_user_id, application_id, json.dumps({
                "application_id": application_id,
                "task_id": task_id,
                "task_name": app_row["task_name"],
                "assigned_agent_id": agent_id,
                "assigned_agent_name": app_row["full_name"],
                "status": "Assigned",
                "model_version": model_ver,
                "prediction_score": suitability_score,
                "advisory_threshold": advisory_tau,
                "administrator_decision": admin_decision,
                "override_reason": override_reason,
            })))

        conn.commit()
        return {
            "application_id": application_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "Assigned",
            "task_status": "COMPLETED"
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error assigning task application {application_id}: {e}")
        raise
    finally:
        conn.close()


def get_agent_applications(user_id):
    """
    Retrieve all task applications submitted by an agent with live statuses,
    task details, deliverables, payout, and assignment outcome.
    """
    conn = get_mysql_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = %s LIMIT 1", (user_id,))
            agent_row = cursor.fetchone()
            if not agent_row:
                return []
            agent_id = agent_row["agent_id"]

            cursor.execute("""
                SELECT 
                    ta.application_id,
                    ta.task_id,
                    ta.status,
                    ta.applied_at,
                    ta.updated_at,
                    ta.notes,
                    t.task_name,
                    t.description AS task_description,
                    t.status AS task_status,
                    t.work_arrangement,
                    t.location,
                    t.payment_type,
                    t.currency,
                    t.hourly_rate_min,
                    t.hourly_rate_max,
                    t.fixed_budget,
                    t.expected_duration,
                    c.category_name
                FROM task_applications ta
                JOIN tasks t ON ta.task_id = t.task_id
                JOIN categories c ON t.category_id = c.category_id
                WHERE ta.agent_id = %s
                ORDER BY ta.applied_at DESC
            """, (agent_id,))
            rows = cursor.fetchall()

            results = []
            for r in rows:
                pay_type = r.get("payment_type") or "Fixed Budget"
                curr = r.get("currency") or "KES"
                h_min = r.get("hourly_rate_min")
                h_max = r.get("hourly_rate_max")
                f_bud = r.get("fixed_budget")

                if pay_type == "Hourly" and h_min is not None:
                    if h_max and float(h_max) > float(h_min):
                        payout_str = f"{curr} {float(h_min):,.0f} - {float(h_max):,.0f} / hr"
                    else:
                        payout_str = f"{curr} {float(h_min):,.0f} / hr"
                elif f_bud is not None:
                    payout_str = f"{curr} {float(f_bud):,.0f} (Fixed)"
                else:
                    payout_str = "Negotiable"

                results.append({
                    "application_id": r["application_id"],
                    "task_id": r["task_id"],
                    "task_name": r["task_name"],
                    "category_name": r["category_name"],
                    "status": r["status"],
                    "task_status": r["task_status"],
                    "work_arrangement": r["work_arrangement"],
                    "location": r["location"],
                    "expected_duration": r["expected_duration"],
                    "payout": payout_str,
                    "applied_at": r["applied_at"].isoformat() if hasattr(r["applied_at"], "isoformat") else str(r["applied_at"]),
                    "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
                    "notes": r["notes"]
                })
            return results
    except Exception as e:
        logger.error(f"Error fetching agent applications for user {user_id}: {e}")
        return []
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
                    ex.exam_name,
                    ex.passing_score,
                    c.category_name,
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
                LEFT JOIN exams ex ON er.exam_id = ex.exam_id
                LEFT JOIN categories c ON ex.category_id = c.category_id
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


def update_admin_review_decision(evaluation_id, decision, reviewer_id, comments=""):
    """Update review_status ('APPROVED'|'REJECTED') and eligibility_status for an evaluation."""
    conn = get_mysql_connection()
    if not conn:
        return False, "Database connection unavailable."

    valid_decisions = {"APPROVED", "REJECTED"}
    if decision not in valid_decisions:
        return False, f"Invalid decision '{decision}'. Expected APPROVED or REJECTED."

    new_eligibility = "ELIGIBLE" if decision == "APPROVED" else "NOT_ELIGIBLE"

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE eligibility_evaluations
                SET 
                    review_status = %s,
                    eligibility_status = %s,
                    reviewer_id = %s,
                    review_comments = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE evaluation_id = %s
            """, (decision, new_eligibility, reviewer_id, comments, evaluation_id))
            conn.commit()

            # Record audit log
            try:
                log_audit_event(
                    user_id=reviewer_id,
                    action=f"ELIGIBILITY_REVIEW_{decision}",
                    entity_type="eligibility_evaluations",
                    entity_id=evaluation_id,
                    details={
                        "decision": decision,
                        "new_eligibility": new_eligibility,
                        "comments": comments
                    }
                )
            except Exception as log_err:
                logger.warning(f"Failed to log audit event: {log_err}")

            return True, f"Review decision '{decision}' recorded successfully."
    except Exception as e:
        logger.error(f"Error updating review decision: {e}")
        return False, str(e)
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

        other_months = max(0, total_months - (sales_months + cs_months))

        return {
            "previous_experience_months": total_months,
            "total_experience_months": total_months,
            "sales_experience_months": sales_months,
            "customer_service_experience_months": cs_months,
            "other_experience_months": other_months,
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
            education = data.get("education")

            cur.execute("""
                UPDATE agents 
                SET phone = %s, location = %s, bio = %s, education = %s, updated_at = NOW()
                WHERE agent_id = %s
            """, (
                str(phone).strip() if phone else None,
                str(location).strip() if location else None,
                str(bio).strip() if bio else None,
                str(education).strip() if education else None,
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
                       ae.supervisor_name, ae.supervisor_email, ae.supervisor_phone,
                       ae.verification_status, ae.rejection_reason, ae.reviewed_at, ae.created_at,
                       ae.verification_token, ae.token_expires_at, ae.verified_via, ae.supervisor_feedback,
                       rev.full_name AS reviewer_name
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                LEFT JOIN users rev ON ae.reviewed_by = rev.user_id
                WHERE a.user_id = %s
                ORDER BY ae.is_current DESC, ae.end_date DESC, ae.start_date DESC
            """, (user_id,))
            rows = []
            for r in cur.fetchall():
                row = serialize_sql_row(r)
                row["status"] = row.get("verification_status")
                rows.append(row)
            return rows
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

    # Supervisor / Manager reference inputs
    supervisor_name = str(exp_data.get("supervisor_name", "")).strip() or None
    supervisor_email = str(exp_data.get("supervisor_email", "")).strip() or None
    supervisor_phone = str(exp_data.get("supervisor_phone", "")).strip() or None

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
        except ValueError:
            raise ValueError("End date must be in YYYY-MM-DD format")
        if s_date > e_date:
            raise ValueError("End date must be on or after start date")
    elif is_current:
        end_date = None
        e_date = None

    # Enforce mandatory former supervisor/manager reference
    if not supervisor_name or len(supervisor_name) < 2:
        raise ValueError("Supervisor / Manager name is mandatory for employment verification (minimum 2 characters)")
    if not supervisor_email or "@" not in supervisor_email or "." not in supervisor_email:
        raise ValueError("Supervisor corporate email is mandatory and must be a valid email address")

    # Generate verification token and 7-day expiration
    verification_token = secrets.token_urlsafe(32)
    token_expires_at = datetime.now() + timedelta(days=7)

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.agent_id, u.full_name AS agent_name, u.email AS agent_email
                FROM agents a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.user_id = %s
            """, (user_id,))
            ag = cur.fetchone()
            if not ag:
                raise ValueError("Agent profile not found")
            agent_id = ag["agent_id"]
            agent_name = ag["agent_name"]

            cur.execute("""
                INSERT INTO agent_experience
                (agent_id, job_title, company, work_category, description,
                 supervisor_name, supervisor_email, supervisor_phone,
                 start_date, end_date, is_current,
                 verification_status, verification_token, token_expires_at, created_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s, NOW())
            """, (
                agent_id, job_title, company, work_category, description,
                supervisor_name, supervisor_email, supervisor_phone,
                start_date, end_date, 1 if is_current else 0,
                verification_token, token_expires_at
            ))
            exp_id = cur.lastrowid

            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'EXPERIENCE_SUBMITTED', 'agent_experience', %s, 'Submitted work experience with supervisor reference for verification', NOW())
            """, (user_id, exp_id))

            conn.commit()

            return {
                "experience_id": exp_id,
                "verification_status": "PENDING",
                "verification_token": verification_token,
                "verification_link": f"http://localhost:5173/verify-experience?token={verification_token}",
                "supervisor_name": supervisor_name,
                "supervisor_email": supervisor_email,
                "supervisor_phone": supervisor_phone
            }
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
                    ac.agent_certification_id AS agent_cert_id,
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
            rows = []
            today = datetime.now().date()
            for r in cur.fetchall():
                row = serialize_sql_row(r)
                raw_status = (r.get("status") or "PENDING").upper()
                exp_date = r.get("expiry_date")
                
                is_expired = False
                if exp_date:
                    if hasattr(exp_date, "year"):
                        is_expired = exp_date < today
                    elif isinstance(exp_date, str):
                        try:
                            exp_date_obj = datetime.strptime(exp_date[:10], "%Y-%m-%d").date()
                            is_expired = exp_date_obj < today
                        except Exception:
                            is_expired = False

                if is_expired and raw_status in ("VERIFIED", "ACTIVE"):
                    row["status"] = "EXPIRED"
                    row["is_expired"] = True
                else:
                    row["status"] = raw_status
                    row["is_expired"] = is_expired

                row["verification_status"] = row["status"]
                rows.append(row)
            return rows
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
                SELECT ac.agent_certification_id, ac.agent_id, ac.status, ac.expiry_date 
                FROM agent_certifications ac
                JOIN agents a ON ac.agent_id = a.agent_id
                WHERE ac.agent_certification_id = %s AND a.user_id = %s
            """, (cert_id, user_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Certification record not found or unauthorized")

            raw_status = (row.get("status") or "").upper()
            exp_date = row.get("expiry_date")
            is_expired = False
            if exp_date:
                today = datetime.now().date()
                if hasattr(exp_date, "year"):
                    is_expired = exp_date < today
                elif isinstance(exp_date, str):
                    try:
                        exp_date_obj = datetime.strptime(exp_date[:10], "%Y-%m-%d").date()
                        is_expired = exp_date_obj < today
                    except Exception:
                        is_expired = False

            # Active, non-expired verified credentials cannot be deleted directly by the candidate
            if raw_status in ("ACTIVE", "VERIFIED") and not is_expired:
                raise ValueError("Active verified credentials cannot be deleted directly. Contact an administrator.")

            cur.execute("DELETE FROM agent_certifications WHERE agent_certification_id = %s", (cert_id,))
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (%s, 'CERTIFICATION_REMOVED', 'agent_certifications', %s, 'Removed certification record', NOW())
            """, (user_id, cert_id))
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
                    ae.supervisor_name,
                    ae.supervisor_email,
                    ae.supervisor_phone,
                    ae.start_date,
                    ae.end_date,
                    ae.is_current,
                    ae.verification_status,
                    ae.rejection_reason,
                    ae.verification_token,
                    ae.token_expires_at,
                    ae.verified_via,
                    ae.supervisor_feedback,
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
                    verified_via = 'ADMIN',
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
            """, (admin_user_id, f"EXPERIENCE_{decision}", exp_id, f"Admin marked experience as {decision}. Recalculated verified months: {calc['total_experience_months']}"))

            conn.commit()
            return {"experience_id": exp_id, "verification_status": new_status, "recalculated_months": calc["total_experience_months"]}
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_experience_by_verification_token(token):
    """Fetch public details of a work experience record for the supervisor verification screen."""
    if not token or len(token) < 10:
        return None, "Invalid verification token."
    conn = get_mysql_connection()
    if not conn:
        return None, "Database service is temporarily unavailable."
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ae.experience_id, ae.agent_id, u.full_name AS agent_name,
                       ae.job_title, ae.company, ae.work_category, ae.description,
                       ae.start_date, ae.end_date, ae.is_current,
                       ae.supervisor_name, ae.supervisor_email, ae.supervisor_phone,
                       ae.verification_status, ae.token_expires_at, ae.verified_via,
                       ae.supervisor_feedback
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ae.verification_token = %s
            """, (token,))
            row = cur.fetchone()
            if not row:
                return None, "Verification record not found or link is invalid."

            # Check expiration
            if row.get("token_expires_at") and row["token_expires_at"] < datetime.now():
                return None, "This verification link has expired (7-day validity period exceeded)."

            return serialize_sql_row(row), None
    finally:
        conn.close()


def submit_supervisor_experience_review(token, decision, feedback=None, answers=None):
    """
    Process the supervisor's 1-click confirmation or dispute.
    decision: 'CONFIRM' or 'DISPUTE'
    """
    if decision not in ("CONFIRM", "DISPUTE"):
        raise ValueError("Decision must be 'CONFIRM' or 'DISPUTE'")

    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ae.experience_id, ae.agent_id, ae.verification_status, ae.token_expires_at,
                       u.full_name AS agent_name, ae.job_title, ae.company
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ae.verification_token = %s
            """, (token,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Verification link is invalid or record does not exist.")

            if row["verification_status"] != "PENDING":
                raise ValueError(f"This experience record has already been reviewed (Current status: {row['verification_status']}).")

            if row.get("token_expires_at") and row["token_expires_at"] < datetime.now():
                raise ValueError("This verification link has expired.")

            exp_id = row["experience_id"]
            agent_id = row["agent_id"]
            agent_name = row["agent_name"]

            new_status = "VERIFIED" if decision == "CONFIRM" else "REJECTED"
            rej_reason = feedback if decision == "DISPUTE" else None

            cur.execute("""
                UPDATE agent_experience
                SET verification_status = %s,
                    verified_via = 'SUPERVISOR_REFERENCE',
                    supervisor_feedback = %s,
                    rejection_reason = %s,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE experience_id = %s
            """, (new_status, feedback, rej_reason, exp_id))

            recalculated_months = 0
            if decision == "CONFIRM":
                calc = calculate_agent_verified_experience(agent_id, cur)
                recalculated_months = calc.get("total_experience_months", 0)

            action = "EXPERIENCE_VERIFIED_BY_SUPERVISOR" if decision == "CONFIRM" else "EXPERIENCE_DISPUTED_BY_SUPERVISOR"
            desc = (
                f"Supervisor confirmed employment for {agent_name} at {row['company']}. Recalculated verified months: {recalculated_months}."
                if decision == "CONFIRM"
                else f"Supervisor disputed employment for {agent_name} at {row['company']}. Note: {feedback or 'None'}"
            )
            # Use user_id 1 (system/admin) for audit log
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, description, created_at)
                VALUES (1, %s, 'agent_experience', %s, %s, NOW())
            """, (action, exp_id, desc))

            conn.commit()
            return {
                "experience_id": exp_id,
                "verification_status": new_status,
                "recalculated_months": recalculated_months,
                "agent_name": agent_name,
                "decision": decision
            }
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def resend_supervisor_experience_email(experience_id, requester_user_id=None):
    """Generate a refreshed token and resend verification email to the supervisor."""
    conn = get_mysql_connection()
    if not conn:
        raise RuntimeError("Database unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ae.experience_id, ae.supervisor_name, ae.supervisor_email,
                       ae.job_title, ae.company, ae.start_date, ae.end_date, ae.is_current,
                       ae.verification_status, u.full_name AS agent_name
                FROM agent_experience ae
                JOIN agents a ON ae.agent_id = a.agent_id
                JOIN users u ON a.user_id = u.user_id
                WHERE ae.experience_id = %s
            """, (experience_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Experience record not found")

            if row["verification_status"] != "PENDING":
                raise ValueError(f"Cannot resend verification: record is already {row['verification_status']}.")

            if not row.get("supervisor_email"):
                raise ValueError("No supervisor email is associated with this experience entry.")

            new_token = secrets.token_urlsafe(32)
            new_expires = datetime.now() + timedelta(days=7)

            cur.execute("""
                UPDATE agent_experience
                SET verification_token = %s, token_expires_at = %s, updated_at = NOW()
                WHERE experience_id = %s
            """, (new_token, new_expires, experience_id))
            conn.commit()

            verification_link = f"http://localhost:5173/verify-experience?token={new_token}"
            from backend.email_service import send_supervisor_verification_email
            email_sent = send_supervisor_verification_email(
                supervisor_email=row["supervisor_email"],
                supervisor_name=row.get("supervisor_name"),
                agent_name=row["agent_name"],
                company=row["company"],
                job_title=row["job_title"],
                start_date=str(row["start_date"]),
                end_date_str="Present" if row["is_current"] else str(row["end_date"]),
                verification_link=verification_link
            )

            return {
                "experience_id": experience_id,
                "verification_link": verification_link,
                "email_dispatched": email_sent
            }
    finally:
        conn.close()
