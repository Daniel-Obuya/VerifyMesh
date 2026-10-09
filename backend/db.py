import logging
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from datetime import datetime, timedelta
import os

logger = logging.getLogger('verifymesh.db')

# Map raw DB role values to canonical frontend role names
ROLE_MAP = {
    "ADMIN": "Administrator",
    "AGENT": "Agent",
    "Administrator": "Administrator",
    "Agent": "Agent",
}

def normalize_role(raw_role):
    """Convert DB role strings (ADMIN/AGENT) to frontend role strings (Administrator/Agent)."""
    return ROLE_MAP.get(raw_role, raw_role)

# In-memory development repository used when MySQL is unavailable or offline
# Standard test credentials (passwords hashed with PBKDF2/scrypt via werkzeug):
FALLBACK_ASSESSMENTS = {}

# Stores pending OTP codes when MySQL is offline: { email: {code, expires_at, used} }
PENDING_VERIFICATIONS = {}

# Stores registration data before email is verified: { email: {full_name, email, phone, password_hash} }
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

def get_agent_assessment(user_id):
    """Retrieve agent assessment and competency details."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None
    return FALLBACK_ASSESSMENTS.get(uid)

def save_agent_assessment(user_id, assessment_data, competency_level, confidence, prediction_data=None):
    """Save or update agent assessment record."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None
    
    record = {
        "user_id": uid,
        "assessment": assessment_data,
        "competency_level": competency_level,
        "confidence": confidence,
        "prediction_data": prediction_data
    }
    FALLBACK_ASSESSMENTS[uid] = record
    for u in FALLBACK_USERS:
        if u["id"] == uid:
            u["assessment"] = assessment_data
            u["competency_level"] = competency_level
    return record

def reset_agent_assessment(user_id):
    """Reset agent back to unassessed state for testing/demo purposes."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None
    if uid in FALLBACK_ASSESSMENTS:
        del FALLBACK_ASSESSMENTS[uid]
    for u in FALLBACK_USERS:
        if u["id"] == uid:
            u["assessment"] = None
            u["competency_level"] = None
    return True

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

def find_user_by_credential(identifier):
    """
    Search for a user by email or username.
    Queries MySQL if connected; otherwise checks fallback repository.
    """
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

    # Fallback to repository
    clean_id = identifier.strip().lower()
    for user in FALLBACK_USERS:
        if user["email"].lower() == clean_id or user["username"].lower() == clean_id:
            return user
    return None

def find_user_by_id(user_id):
    """Find user by numeric ID."""
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
    """
    Validate identifier (email or username) and password.
    Returns (user_dict, error_message).
    """
    if not identifier or not password:
        return None, "Both email/username and password are required."

    user = find_user_by_credential(identifier)
    if not user:
        return None, "Invalid email/username or password."

    if not user.get("is_active", True):
        return None, "This account is inactive. Please contact your administrator."

    if not check_password_hash(user["password_hash"], password):
        return None, "Invalid email/username or password."

    # Return safe user dict without password hash
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
    """
    Create a users + agents record.
    Called from /verify-email after the OTP has been validated,
    so email_verified defaults to True.
    """
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


    # Helper function to find or auto-create a user when authenticated via Google
def find_or_create_google_user(email, full_name):
    """Find existing user by email or auto-provision a new Agent account."""
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

    # New user: auto-create as Agent
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Password hash can be a random placeholder since Google handles authentication
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

    # Fallback in-memory support (if MySQL is offline)
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
    """Store OTP in DB (or in-memory fallback). Overwrites any previous code for that email."""
    conn = get_mysql_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Delete any existing OTP for this email first
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

    # Fallback: store in memory when MySQL is offline
    PENDING_VERIFICATIONS[email.lower()] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=10),
        "used": False
    }
    return True


def verify_otp(email, code):
    """Check if OTP is valid. Returns True if valid, False otherwise. Marks it used on success."""
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

    # Fallback: verify from memory
    record = PENDING_VERIFICATIONS.get(email.lower())
    if record and not record["used"] and record["code"] == code:
        if datetime.now() < record["expires_at"]:
            record["used"] = True
            return True
    return False

    

    
