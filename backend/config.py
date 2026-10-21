import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically load the .env file from the project root if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class Config:
    # Environment & Debug Controls
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    TESTING = os.getenv('TESTING', 'False').lower() in ('true', '1', 't')

    # Security: Secret key loaded strictly from environment with no insecure default fallback
    SECRET_KEY = os.getenv('SECRET_KEY')

    # MySQL Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'verifymesh_db')

    # Allowed CORS Origins - parsed and sanitized into a list
    raw_cors = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000')
    CORS_ORIGINS = [origin.strip() for origin in raw_cors.split(',') if origin.strip()]

    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')

    # SMTP Mail Server Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')

    # Sender Credentials
    MAIL_SENDER_NAME = os.getenv('MAIL_SENDER_NAME', 'VerifyMesh')
    MAIL_SENDER_EMAIL = os.getenv('MAIL_SENDER_EMAIL', '')
    MAIL_SENDER_PASSWORD = os.getenv('MAIL_SENDER_PASSWORD', '')

    # Assessment Policy & Integrity Controls
    ASSESSMENT_COOLDOWN_SECONDS = int(os.getenv('ASSESSMENT_COOLDOWN_SECONDS', 300))
    ASSESSMENT_ATTEMPT_DURATION_MINUTES = int(os.getenv('ASSESSMENT_ATTEMPT_DURATION_MINUTES', 30))
    MAX_ASSESSMENT_ATTEMPTS = int(os.getenv('MAX_ASSESSMENT_ATTEMPTS', 10))

    @classmethod
    def validate(cls):
        """Validate required secrets and configuration settings."""
        if not cls.SECRET_KEY:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is missing. "
                "Set a secure, high-entropy SECRET_KEY in your environment or .env file before starting the application."
            )
        if cls.SECRET_KEY in ('verifymesh-secure-auth-secret-key-2026', 'default', 'secret', 'changeme'):
            if cls.FLASK_ENV == 'production' or not cls.DEBUG:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: An insecure or known default SECRET_KEY is being used. "
                    "Generate a cryptographically secure random key for production."
                )