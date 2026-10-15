import logging
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from datetime import datetime, timedelta
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

            # Check for non-destructive reset timestamp
            cursor.execute("""
                SELECT created_at FROM audit_logs 
                WHERE user_id = %s AND action = 'ASSESSMENT_RESET_REQUESTED'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            reset_row = cursor.fetchone()
            reset_time = reset_row["created_at"] if reset_row else None

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

            # If a reset occurred after this assessment attempt, treat active state as unassessed
            if reset_time and reset_time > pred_row["predicted_at"]:
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
            mapped = ENUM_TO_DECISION.get(enum_val, {"decision": "0", "label": "Ineligible"})

            raw_conf = float(pred_row["confidence"]) if pred_row["confidence"] is not None else 0.0
            conf_pct = raw_conf * 100.0 if raw_conf <= 1.0 else raw_conf

            assessment_data = raw_payload.get("assessment_data") or {
                "assessment_score": float(pred_row["assessment_score"])
            }
            prediction_data = raw_payload.get("prediction_data") or {
                "decision": mapped["decision"],
                "prediction": mapped["label"],
                "predicted_competency": mapped["label"],
                "confidence": conf_pct
            }

            return {
                "user_id": user_id,
                "agent_id": agent_id,
                "attempt_number": pred_row["attempt_number"],
                "assessment": assessment_data,
                "competency_level": mapped["label"],
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