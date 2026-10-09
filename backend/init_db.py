"""
VerifyMesh Database Initialization Script

Sets up the MySQL database, creates tables from schema.sql,
and seeds development/test accounts with securely hashed passwords.

Authentication is email-based:
    - AGENT
    - ADMIN

The script is designed to work with the current VerifyMesh schema.
"""

import os
import sys

# Allow imports from the project root
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

import pymysql
from werkzeug.security import generate_password_hash

from backend.config import Config


def execute_schema(conn):
    """Execute the SQL schema file."""
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "schema.sql"
    )

    if not os.path.exists(schema_path):
        raise FileNotFoundError(
            f"Schema file not found: {schema_path}"
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        sql_commands = f.read().split(";")

    with conn.cursor() as cursor:
        for command in sql_commands:
            command = command.strip()

            # Ignore empty commands and SQL comment-only lines
            if not command:
                continue

            if command.startswith("--"):
                continue

            cursor.execute(command)

    print("Schema executed successfully.")


def seed_users(conn):
    """
    Seed development accounts.

    Authentication uses:
        email
        password_hash
        role

    No username column is used.
    """

    with conn.cursor() as cursor:

        # ---------------------------------------------------------
        # Check whether users already exist
        # ---------------------------------------------------------
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count > 0:
            print(
                f"Users table already contains {user_count} account(s). "
                "Skipping user seed."
            )
            return

        print("Seeding initial users...")

        # ---------------------------------------------------------
        # Passwords are hashed before being stored.
        # ---------------------------------------------------------
        agent_password_hash = generate_password_hash(
            "password123"
        )

        admin_password_hash = generate_password_hash(
            "password123"
        )

        # ---------------------------------------------------------
        # Create Agent account
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                password_hash,
                role,
                is_active,
                email_verified
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "Alex Morgan",
                "alex.morgan@university.edu",
                agent_password_hash,
                "AGENT",
                True,
                True
            )
        )

        agent_user_id = cursor.lastrowid

        # ---------------------------------------------------------
        # Create the Agent-specific profile
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO agents (
                user_id,
                phone,
                education,
                experience_months,
                availability_status,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                agent_user_id,
                "+254700000000",
                "BSc Informatics and Computer Science",
                12,
                "AVAILABLE",
                "ACTIVE"
            )
        )

        # ---------------------------------------------------------
        # Create Admin account
        # ---------------------------------------------------------
        cursor.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                password_hash,
                role,
                is_active,
                email_verified
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "System Administrator",
                "admin@verifymesh.io",
                admin_password_hash,
                "ADMIN",
                True,
                True
            )
        )

        conn.commit()

        print("Successfully seeded development accounts:")
        print("  Agent: alex.morgan@university.edu")
        print("  Admin: admin@verifymesh.io")
        print("  Development password: password123")


def init_mysql_database():
    """Create the database, execute the schema, and seed accounts."""

    print(
        f"Connecting to MySQL at "
        f"{Config.DB_HOST}:{Config.DB_PORT} "
        f"as {Config.DB_USER}..."
    )

    conn = None

    try:
        # =========================================================
        # 1. Connect to MySQL without selecting a database
        # =========================================================
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset="utf8mb4"
        )

        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}`
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )

        conn.commit()
        conn.close()
        conn = None

        print(f"Database `{Config.DB_NAME}` ensured.")

        # =========================================================
        # 2. Connect to the VerifyMesh database
        # =========================================================
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            autocommit=False
        )

        # =========================================================
        # 3. Execute schema.sql
        # =========================================================
        execute_schema(conn)

        # =========================================================
        # 4. Seed development accounts
        # =========================================================
        seed_users(conn)

        print("MySQL initialization completed successfully.")
        return True

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

        print(f"Could not connect or initialize MySQL: {e}")
        print(
            "MySQL initialization failed. "
            "The application should not silently switch to a "
            "fallback authentication store."
        )

        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    success = init_mysql_database()

    if not success:
        sys.exit(1)

