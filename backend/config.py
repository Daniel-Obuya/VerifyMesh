import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'verifymesh-secure-auth-secret-key-2026')
    
    # MySQL Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '@Kangaro254')
    DB_NAME = os.getenv('DB_NAME', 'verifymesh_db')
    
    # Allowed CORS Origins
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000').split(',')

    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '261701138674-e0srjqjh5qob3i8iartestj48dpjoe7b.apps.googleusercontent.com')
    
    # SMTP Mail Server Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    
    # Sender Credentials
    MAIL_SENDER_EMAIL = os.getenv('MAIL_SENDER_EMAIL', 'danielobuya833@gmail.com')
    MAIL_SENDER_PASSWORD = os.getenv('MAIL_SENDER_PASSWORD', 'oxyk nalq wead ffun')
    MAIL_SENDER_NAME = os.getenv('MAIL_SENDER_NAME', 'VerifyMesh')