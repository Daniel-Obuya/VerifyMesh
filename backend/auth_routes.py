import base64
import hmac
import hashlib
import json
import time
from flask import Blueprint, request, jsonify
from backend.config import Config
from backend.db import (
    verify_credentials, find_user_by_id, check_mysql_status,
    create_agent_user, normalize_role, find_or_create_google_user,
    store_otp, verify_otp, PENDING_SIGNUPS
)
from backend.email_service import generate_otp, send_verification_email
from werkzeug.security import generate_password_hash
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

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
        "password_hash": password_hash
    }

    code = generate_otp()
    store_otp(email, code)

    try:
        send_verification_email(email, full_name, code)
    except Exception as e:
        # Clean up pending signup memory if email fails
        PENDING_SIGNUPS.pop(email, None)
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

    if not verify_otp(email, code):
        return jsonify({"success": False, "error": "Invalid or expired code. Please try again."}), 400

    pending = PENDING_SIGNUPS.get(email)
    if not pending:
        return jsonify({"success": False, "error": "No pending signup found for this email. Please register again."}), 400

    success, error = create_agent_user(
        pending["full_name"],
        pending["email"],
        pending["phone"],
        pending["password_hash"]
    )

    # Clean up pending signup data regardless of outcome
    PENDING_SIGNUPS.pop(email, None)

    if not success:
        return jsonify({"success": False, "error": error}), 400

    return jsonify({
        "success": True,
        "message": "Email verified successfully. You can now sign in."
    }), 201


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend a fresh OTP code to the user's email."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Email is required."}), 400

    pending = PENDING_SIGNUPS.get(email)
    if not pending:
        return jsonify({"success": False, "error": "No pending signup found. Please register again."}), 400

    code = generate_otp()
    store_otp(email, code)

    try:
        send_verification_email(email, pending["full_name"], code)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to resend code: {str(e)}"}), 500

    return jsonify({"success": True, "message": "A new verification code has been sent to your email."}), 200

def generate_auth_token(user_id, role, remember_me=False):
    """Generate a signed auth token."""
    duration = 30 * 24 * 3600 if remember_me else 24 * 3600
    payload = {
        "uid": user_id,
        "role": role,
        "exp": int(time.time()) + duration
    }
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(Config.SECRET_KEY.encode(), encoded_payload.encode(), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"

def decode_auth_token(token):
    """Verify and decode a signed auth token."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        encoded_payload, signature = parts
        expected_sig = hmac.new(Config.SECRET_KEY.encode(), encoded_payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login request."""
    data = request.get_json(silent=True) or {}
    
    # Support both identifier or email/username keys
    identifier = data.get('email') or data.get('identifier') or data.get('username')
    password = data.get('password')
    remember_me = bool(data.get('rememberMe', False))

    if not identifier or not str(identifier).strip():
        return jsonify({
            "success": False,
            "error": "Email or Username is required."
        }), 400

    if not password or not str(password).strip():
        return jsonify({
            "success": False,
            "error": "Password is required."
        }), 400

    user, error = verify_credentials(identifier.strip(), password)
    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 401

    token = generate_auth_token(user["id"], user["role"], remember_me=remember_me)

    return jsonify({
        "success": True,
        "message": "Authentication successful",
        "token": token,
        "user": user
    }), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Verify auth token and return the current user's profile."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip() if auth_header.startswith('Bearer ') else None
    
    if not token:
        return jsonify({"success": False, "error": "Authorization token required."}), 401

    payload = decode_auth_token(token)
    if not payload:
        return jsonify({"success": False, "error": "Invalid or expired token."}), 401

    user = find_user_by_id(payload["uid"])
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

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
    """Handle password reset request."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({
            "success": False,
            "error": "Please enter your registered email address."
        }), 400

    # In production, this generates a token and sends an email via SMTP.
    # Return standard generic confirmation to prevent user enumeration
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
    try:
        # Verify the token against Google servers
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
            return jsonify({"success": False, "error": err or "Failed to authenticate user."}), 400
        auth_token = generate_auth_token(user['id'], user['role'], remember_me=True)
        return jsonify({
            "success": True,
            "token": auth_token,
            "user": user,
            "message": "Signed in with Google successfully."
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": "Invalid Google token."}), 401
    except Exception as e:
        return jsonify({"success": False, "error": f"Google authentication failed: {str(e)}"}), 500