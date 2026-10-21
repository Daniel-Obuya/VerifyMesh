import os
import sys
import time
import json
import base64
import hmac
import hashlib
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.auth_routes import (
    generate_auth_token,
    decode_auth_token,
    limiter
)
from backend.email_service import generate_otp
from backend.db import (
    verify_credentials,
    find_user_by_credential,
    find_user_by_id,
    store_otp,
    verify_otp
)
from backend.app import create_app


class TestConfigSecurity(unittest.TestCase):
    """Test configuration validation, fail-safe defaults, and CORS origin rules."""

    def test_missing_secret_key_fails_validation(self):
        class BadConfig(Config):
            SECRET_KEY = None
            TESTING = False

        with self.assertRaises(ValueError) as ctx:
            BadConfig.validate()
        self.assertIn("SECRET_KEY environment variable is missing", str(ctx.exception))

    def test_insecure_default_secret_key_fails_in_production(self):
        class InsecureConfig(Config):
            SECRET_KEY = 'verifymesh-secure-auth-secret-key-2026'
            FLASK_ENV = 'production'
            DEBUG = False
            TESTING = False

        with self.assertRaises(ValueError) as ctx:
            InsecureConfig.validate()
        self.assertIn("insecure or known default SECRET_KEY", str(ctx.exception))

    def test_cors_wildcard_stripped_when_credentials_enabled(self):
        class CorsConfig(Config):
            TESTING = True
            SECRET_KEY = "test-secret-key-with-sufficient-entropy-12345"
            CORS_ORIGINS = ["*", "http://localhost:5173"]

        app = create_app(config_class=CorsConfig)
        client = app.test_client()

        # Origin header matching trusted origin
        res = client.get('/api/health', headers={'Origin': 'http://localhost:5173'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), 'http://localhost:5173')

        # Origin header matching untrusted origin
        res_untrusted = client.get('/api/health', headers={'Origin': 'http://evil-attacker.com'})
        self.assertNotEqual(res_untrusted.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertNotEqual(res_untrusted.headers.get('Access-Control-Allow-Origin'), 'http://evil-attacker.com')


class TestTokenSecurity(unittest.TestCase):
    """Test token generation, tampering, signature forgery, expiration, and malformed inputs."""

    def setUp(self):
        self.test_secret = "test-very-secure-random-secret-key-32bytes-12345"
        Config.SECRET_KEY = self.test_secret

    def test_valid_token_decodes_successfully(self):
        token = generate_auth_token(user_id=42, role="Agent")
        payload = decode_auth_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["uid"], 42)
        self.assertEqual(payload["role"], "Agent")
        self.assertGreater(payload["exp"], time.time())

    def test_tampered_signature_rejected(self):
        token = generate_auth_token(user_id=1, role="Agent")
        parts = token.split(".")
        # Tamper with signature
        forged_sig = parts[1][:-4] + "ffff"
        bad_token = f"{parts[0]}.{forged_sig}"
        self.assertIsNone(decode_auth_token(bad_token))

    def test_forged_payload_rejected(self):
        token = generate_auth_token(user_id=1, role="Agent")
        parts = token.split(".")
        # Tamper payload to elevate role to Administrator
        malicious_payload = {"uid": 1, "role": "Administrator", "exp": int(time.time()) + 3600}
        b64_payload = base64.urlsafe_b64encode(json.dumps(malicious_payload).encode()).decode().rstrip("=")
        forged_token = f"{b64_payload}.{parts[1]}"
        self.assertIsNone(decode_auth_token(forged_token))

    def test_token_signed_with_different_secret_rejected(self):
        # Generate token using a different secret key
        diff_secret = "attacker-secret-key-which-is-different-12345"
        payload = {"uid": 1, "role": "Administrator", "exp": int(time.time()) + 3600}
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig = hmac.new(diff_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        forged_token = f"{encoded}.{sig}"
        self.assertIsNone(decode_auth_token(forged_token))

    def test_expired_token_rejected(self):
        # Create an expired payload
        expired_payload = {"uid": 1, "role": "Agent", "exp": int(time.time()) - 100}
        raw = json.dumps(expired_payload).encode()
        encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        sig = hmac.new(self.test_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        expired_token = f"{encoded}.{sig}"
        self.assertIsNone(decode_auth_token(expired_token))

    def test_malformed_tokens_rejected(self):
        malformed_cases = [
            "",
            None,
            "not-a-token",
            "part1.part2.part3",
            "badbase64!@#.signature",
            f"{base64.urlsafe_b64encode(b'not-json').decode()}.fakesig",
            f"{base64.urlsafe_b64encode(b'[]').decode()}.fakesig",
            f"{base64.urlsafe_b64encode(json.dumps({'uid': 'not-an-int', 'role': 'Agent', 'exp': 9999999999}).encode()).decode()}.fakesig",
            f"{base64.urlsafe_b64encode(json.dumps({'role': 'Agent', 'exp': 9999999999}).encode()).decode()}.fakesig",
        ]
        for bad in malformed_cases:
            self.assertIsNone(decode_auth_token(bad), f"Failed to reject malformed token: {bad}")


class TestDatabaseFallbackRemoval(unittest.TestCase):
    """Test that database unavailability produces clean 503 service errors and never authenticates from fallback."""

    def setUp(self):
        Config.SECRET_KEY = "test-secret-key-with-sufficient-entropy-12345"
        Config.TESTING = True
        self.app = create_app(config_class=Config)
        self.client = self.app.test_client()

    @patch("backend.db.get_mysql_connection", return_value=None)
    def test_login_when_database_down_returns_503_not_fallback(self, mock_conn):
        # Try to authenticate with the old fallback admin credentials
        res = self.client.post("/api/auth/login", json={
            "identifier": "admin@verifymesh.io",
            "password": "password123"
        })
        self.assertEqual(res.status_code, 503)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("unavailable", data["error"].lower())
        self.assertNotIn("token", data)

    @patch("backend.db.get_mysql_connection", return_value=None)
    def test_otp_storage_fails_safely_when_db_down(self, mock_conn):
        result = store_otp("user@example.com", "123456")
        self.assertFalse(result)

    @patch("backend.db.get_mysql_connection", return_value=None)
    def test_otp_verification_fails_safely_when_db_down(self, mock_conn):
        result = verify_otp("user@example.com", "123456")
        self.assertFalse(result)

    @patch("backend.admin_routes.find_user_by_id", return_value=(None, "DB_UNAVAILABLE"))
    def test_admin_route_when_db_down_returns_503(self, mock_find_user):
        token = generate_auth_token(user_id=2, role="Administrator")
        res = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 503)
        data = res.get_json()
        self.assertIn("unavailable", data["error"].lower())

    @patch("backend.competency_routes.find_user_by_id", return_value=(None, "DB_UNAVAILABLE"))
    def test_agent_route_when_db_down_returns_503(self, mock_find_user):
        token = generate_auth_token(user_id=1, role="Agent")
        res = self.client.get("/api/competency/agent-status", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 503)
        data = res.get_json()
        self.assertIn("unavailable", data["error"].lower())


class TestAuthorizationAndRoleVerification(unittest.TestCase):
    """Test server-side live database re-verification of roles and active status."""

    def setUp(self):
        Config.SECRET_KEY = "test-secret-key-with-sufficient-entropy-12345"
        Config.TESTING = True
        self.app = create_app(config_class=Config)
        self.client = self.app.test_client()

    @patch("backend.admin_routes.find_user_by_id")
    def test_token_claims_admin_but_db_role_demoted_to_agent_is_forbidden(self, mock_find_user):
        # In MySQL, user 2 was demoted to AGENT
        mock_find_user.return_value = ({
            "id": 2,
            "email": "user2@verifymesh.io",
            "role": "AGENT",
            "is_active": True
        }, None)
        # Token still has role="Administrator"
        token = generate_auth_token(user_id=2, role="Administrator")
        res = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Administrator role required", data["error"])

    @patch("backend.admin_routes.find_user_by_id")
    def test_inactive_admin_account_is_blocked(self, mock_find_user):
        # Admin account deactivated/suspended in MySQL
        mock_find_user.return_value = ({
            "id": 2,
            "email": "admin@verifymesh.io",
            "role": "ADMIN",
            "is_active": False
        }, None)
        token = generate_auth_token(user_id=2, role="Administrator")
        res = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("inactive or suspended", data["error"].lower())

    @patch("backend.competency_routes.find_user_by_id")
    def test_inactive_agent_account_is_blocked(self, mock_find_user):
        # Agent account deactivated
        mock_find_user.return_value = ({
            "id": 1,
            "email": "agent@verifymesh.io",
            "role": "AGENT",
            "is_active": False
        }, None)
        token = generate_auth_token(user_id=1, role="Agent")
        res = self.client.get("/api/competency/agent-status", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("inactive or suspended", data["error"].lower())

    def test_unauthenticated_admin_request_rejected(self):
        res = self.client.get("/api/admin/overview")
        self.assertEqual(res.status_code, 401)

    @patch("backend.admin_routes.find_user_by_id")
    def test_agent_accessing_admin_endpoint_forbidden(self, mock_find_user):
        mock_find_user.return_value = ({
            "id": 1,
            "email": "alex.morgan@university.edu",
            "role": "AGENT",
            "is_active": True
        }, None)
        token = generate_auth_token(user_id=1, role="Agent")
        res = self.client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Administrator role required", res.get_json()["error"])


class TestRateLimitingAndSecurityHelpers(unittest.TestCase):
    """Test attempt rate limiting and CSPRNG OTP generation."""

    def setUp(self):
        Config.SECRET_KEY = "test-secret-key-with-sufficient-entropy-12345"
        Config.TESTING = True
        self.app = create_app(config_class=Config)
        self.client = self.app.test_client()

    def test_login_attempt_rate_limiting(self):
        test_email = "brute_force_target@test.com"
        with patch("backend.auth_routes.verify_credentials", return_value=(None, "Invalid email/username or password.")):
            # 5 allowed failed attempts
            for i in range(5):
                res = self.client.post("/api/auth/login", json={
                    "identifier": test_email,
                    "password": f"wrongpass{i}"
                })
                self.assertEqual(res.status_code, 401)

            # 6th attempt must be rate-limited (429)
            res_blocked = self.client.post("/api/auth/login", json={
                "identifier": test_email,
                "password": "wrongpass_again"
            })
            self.assertEqual(res_blocked.status_code, 429)
            data = res_blocked.get_json()
            self.assertIn("Too many failed login attempts", data["error"])
            self.assertIn("Retry-After", res_blocked.headers)

    def test_csprng_otp_format_and_entropy(self):
        otps = set()
        for _ in range(100):
            otp = generate_otp()
            self.assertEqual(len(otp), 6)
            self.assertTrue(otp.isdigit())
            val = int(otp)
            self.assertGreaterEqual(val, 100000)
            self.assertLessEqual(val, 999999)
            otps.add(otp)
        # In 100 samples from 900,000 choices, almost all should be distinct
        self.assertGreater(len(otps), 95)


if __name__ == "__main__":
    unittest.main()
