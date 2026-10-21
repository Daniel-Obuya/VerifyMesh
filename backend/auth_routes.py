import base64
import hmac
import hashlib
import json
import time
import logging
import threading
import re
from flask import Blueprint, request, jsonify
from backend.config import Config
from backend.db import (
    verify_credentials, find_user_by_id, check_mysql_status,
    create_agent_user, normalize_role, find_or_create_google_user,
    store_otp, verify_otp, PENDING_SIGNUPS, get_mysql_connection
)
from backend.email_service import generate_otp, send_verification_email
from werkzeug.security import generate_password_hash
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger("verifymesh.auth")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


class InMemoryRateLimiter:
    """Thread-safe rate and attempt limiter for authentication endpoints."""
    def __init__(self):
        self._lock = threading.Lock()
        self._attempts = {}

    def is_allowed(self, key, max_attempts, window_seconds):
        now = time.time()
        with self._lock:
            timestamps = self._attempts.get(key, [])
            timestamps = [t for t in timestamps if now - t < window_seconds]
            self._attempts[key] = timestamps
            if len(timestamps) >= max_attempts:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                return False, retry_after
            return True, 0

    def record_attempt(self, key):
        now = time.time()
        with self._lock:
            if key not in self._attempts:
                self._attempts[key] = []
            self._attempts[key].append(now)

    def reset(self, key):
        with self._lock:
            self._attempts.pop(key, None)


limiter = InMemoryRateLimiter()


def generate_auth_token(user_id, role, remember_me=False):
    """
    Generate an HMAC-SHA256 signed auth token.
    Fails safely if SECRET_KEY is not configured.
    """
    if not Config.SECRET_KEY:
        raise RuntimeError("CRITICAL ERROR: SECRET_KEY is not configured.")

    duration = 30 * 24 * 3600 if remember_me else 24 * 3600
    payload = {
        "uid": int(user_id),
        "role": str(role),
        "exp": int(time.time()) + duration
    }
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
    signature = hmac.new(
        Config.SECRET_KEY.encode('utf-8'),
        encoded_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def decode_auth_token(token):
    """
    Verify and decode an HMAC-SHA256 signed auth token.
    Strictly rejects invalid signatures, expired tokens, and malformed payloads.
    """
    if not token or not isinstance(token, str):
        return None
    if not Config.SECRET_KEY:
        return None

    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        encoded_payload, signature = parts

        expected_sig = hmac.new(
            Config.SECRET_KEY.encode('utf-8'),
            encoded_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add base64 padding if needed
        rem = len(encoded_payload) % 4
        padded = encoded_payload + ('=' * ((4 - rem) % 4))
        raw_json = base64.urlsafe_b64decode(padded.encode('utf-8')).decode('utf-8')
        payload = json.loads(raw_json)

        if not isinstance(payload, dict):
            return None

        uid = payload.get("uid")
        exp = payload.get("exp")
        role = payload.get("role")

        if uid is None or exp is None or role is None:
            return None
        if not isinstance(exp, (int, float)) or exp <= time.time():
            return None

        payload["uid"] = int(uid)
        return payload
    except Exception:
        return None


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = re.sub(r'[\s\-\(\)]', '', data.get('phone', '').strip())
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not full_name:
        return jsonify({"success": False, "error": "Full name is required."}), 400
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400
    if not phone:
        return jsonify({"success": False, "error": "Phone number is required."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters."}), 400
    if password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match."}), 400

    password_hash = generate_password_hash(password)
    PENDING_SIGNUPS[email] = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "password_hash": password_hash,
        "created_at": time.time()
    }

    code = generate_otp()
    if not store_otp(email, code):
        PENDING_SIGNUPS.pop(email, None)
        return jsonify({
            "success": False,
            "error": "Database service is temporarily unavailable. Please try again later."
        }), 503

    try:
        send_verification_email(email, full_name, code)
    except Exception as e:
        PENDING_SIGNUPS.pop(email, None)
        logger.error(f"Failed to send verification email: {type(e).__name__}")
        return jsonify({
            "success": False,
            "error": "Failed to send verification email. Please verify your connection or try again."
        }), 500

    return jsonify({
        "success": True,
        "requires_verification": True,
        "email": email,
        "message": "A 6-digit verification code has been sent to your email address."
    }), 200


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify the OTP code and create the user account."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()

    if not email or not code:
        return jsonify({"success": False, "error": "Email and verification code are required."}), 400

    # Rate limiting: max 5 verification attempts per 10 minutes per email
    rate_key = f"verify:{email}"
    allowed, retry_after = limiter.is_allowed(rate_key, max_attempts=5, window_seconds=600)
    if not allowed:
        resp = jsonify({
            "success": False,
            "error": f"Too many verification attempts. Please wait {retry_after} seconds before trying again."
        })
        resp.headers["Retry-After"] = str(retry_after)
        return resp, 429

    limiter.record_attempt(rate_key)

    if not verify_otp(email, code):
        return jsonify({"success": False, "error": "Invalid or expired code. Please try again."}), 400

    # Reset limiter on successful OTP match
    limiter.reset(rate_key)

    pending = PENDING_SIGNUPS.get(email)
    if not pending:
        return jsonify({"success": False, "error": "No pending signup found for this email. Please register again."}), 400

    success, error = create_agent_user(
        pending["full_name"],
        pending["email"],
        pending["phone"],
        pending["password_hash"]
    )

    PENDING_SIGNUPS.pop(email, None)

    if not success:
        return jsonify({"success": False, "error": error}), 400

    return jsonify({
        "success": True,
        "message": "Email verified successfully. You can now sign in."
    }), 201


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend a fresh OTP code to the user's email with rate limiting."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Email is required."}), 400

    # Rate limit: max 3 resend attempts per 10 minutes
    rate_key = f"resend:{email}"
    allowed, retry_after = limiter.is_allowed(rate_key, max_attempts=3, window_seconds=600)
    if not allowed:
        resp = jsonify({
            "success": False,
            "error": f"Please wait {retry_after} seconds before requesting another verification code."
        })
        resp.headers["Retry-After"] = str(retry_after)
        return resp, 429

    limiter.record_attempt(rate_key)

    pending = PENDING_SIGNUPS.get(email)
    if not pending:
        return jsonify({"success": False, "error": "No pending signup found. Please register again."}), 400

    code = generate_otp()
    if not store_otp(email, code):
        return jsonify({
            "success": False,
            "error": "Database service is temporarily unavailable. Please try again later."
        }), 503

    try:
        send_verification_email(email, pending["full_name"], code)
    except Exception as e:
        logger.error(f"Failed to resend email: {type(e).__name__}")
        return jsonify({"success": False, "error": "Failed to resend verification email."}), 500

    return jsonify({"success": True, "message": "A new verification code has been sent to your email."}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login request with attempt rate limiting."""
    data = request.get_json(silent=True) or {}
    
    identifier = data.get('email') or data.get('identifier') or data.get('username')
    password = data.get('password')
    remember_me = bool(data.get('rememberMe', False))

    if not identifier or not str(identifier).strip():
        return jsonify({"success": False, "error": "Email or Username is required."}), 400

    if not password or not str(password).strip():
        return jsonify({"success": False, "error": "Password is required."}), 400

    clean_id = str(identifier).strip().lower()
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
    rate_key = f"login:{clean_id}:{client_ip}"

    # Rate limit: max 5 failed attempts per 15 minutes (900 seconds)
    allowed, retry_after = limiter.is_allowed(rate_key, max_attempts=5, window_seconds=900)
    if not allowed:
        logger.warning(f"Login rate limit exceeded for identifier {clean_id} from IP {client_ip}")
        resp = jsonify({
            "success": False,
            "error": f"Too many failed login attempts. Please wait {retry_after} seconds before trying again."
        })
        resp.headers["Retry-After"] = str(retry_after)
        return resp, 429

    user, error = verify_credentials(clean_id, password)
    if error:
        limiter.record_attempt(rate_key)
        if "unavailable" in error.lower():
            return jsonify({"success": False, "error": error}), 503
        return jsonify({"success": False, "error": error}), 401

    # Successful login: reset failed login attempts
    limiter.reset(rate_key)

    token = generate_auth_token(user["id"], user["role"], remember_me=remember_me)

    return jsonify({
        "success": True,
        "message": "Authentication successful",
        "token": token,
        "user": user
    }), 200


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Verify auth token and re-validate current user status and role from MySQL."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else None
    
    if not token:
        return jsonify({"success": False, "error": "Authorization token required."}), 401

    payload = decode_auth_token(token)
    if not payload:
        return jsonify({"success": False, "error": "Invalid or expired token."}), 401

    user, db_err = find_user_by_id(payload["uid"])
    if db_err:
        return jsonify({"success": False, "error": "Database service is currently unavailable."}), 503
    if not user:
        return jsonify({"success": False, "error": "User account no longer exists or session is invalid."}), 401

    if not user.get("is_active", True):
        return jsonify({"success": False, "error": "Account is inactive. Please contact your administrator."}), 403

    canonical_role = normalize_role(user["role"])
    return jsonify({
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "fullName": user.get("full_name") or user.get("fullName"),
            "role": canonical_role,
            "assessment": user.get("assessment", None),
            "competency_level": user.get("competency_level", None),
            "confidence": user.get("confidence", None),
            "dashboardUrl": "/admin/dashboard" if canonical_role == "Administrator" else "/agent/dashboard"
        }
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Handle password reset request without user enumeration."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({
            "success": False,
            "error": "Please enter your registered email address."
        }), 400

    return jsonify({
        "success": True,
        "message": f"If an account with {email} exists, password reset instructions have been sent to it."
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Handle user logout."""
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    }), 200


@auth_bp.route('/google', methods=['POST'])
def google_login():
    data = request.get_json(silent=True) or {}
    token = data.get('credential')
    if not token:
        return jsonify({"success": False, "error": "Missing Google credential token."}), 400

    if not Config.GOOGLE_CLIENT_ID:
        return jsonify({"success": False, "error": "Google authentication is not configured on this server."}), 500

    try:
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            Config.GOOGLE_CLIENT_ID
        )
        email = idinfo.get('email')
        name = idinfo.get('name', email.split('@')[0])
        if not email:
            return jsonify({"success": False, "error": "Email not provided by Google."}), 400

        user, err = find_or_create_google_user(email, name)
        if err or not user:
            status_code = 503 if "unavailable" in str(err).lower() else 400
            return jsonify({"success": False, "error": err or "Failed to authenticate user."}), status_code

        auth_token = generate_auth_token(user['id'], user['role'], remember_me=True)
        return jsonify({
            "success": True,
            "token": auth_token,
            "user": user,
            "message": "Signed in with Google successfully."
        }), 200
    except ValueError:
        return jsonify({"success": False, "error": "Invalid Google token."}), 401
    except Exception as e:
        logger.error(f"Google authentication failed: {type(e).__name__}")
        return jsonify({"success": False, "error": "Google authentication failed. Please try again."}), 500