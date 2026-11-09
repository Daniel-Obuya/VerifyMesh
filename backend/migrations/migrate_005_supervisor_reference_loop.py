"""
Migration Runner: 005_supervisor_reference_loop
Adds supervisor contact and verification token columns to agent_experience.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 005_supervisor_reference_loop")
    print("=" * 60)

    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

    try:
        with conn.cursor() as cursor:
            # Check existing columns on agent_experience
            cursor.execute("DESCRIBE agent_experience")
            cols = [r["Field"] for r in cursor.fetchall()]

            columns_to_add = [
                ("supervisor_name", "VARCHAR(150) NULL AFTER `description`"),
                ("supervisor_email", "VARCHAR(150) NULL AFTER `supervisor_name`"),
                ("supervisor_phone", "VARCHAR(50) NULL AFTER `supervisor_email`"),
                ("verification_token", "VARCHAR(64) NULL AFTER `rejection_reason`"),
                ("token_expires_at", "DATETIME NULL AFTER `verification_token`"),
                ("verified_via", "ENUM('ADMIN','SUPERVISOR_REFERENCE','SYSTEM') DEFAULT NULL AFTER `token_expires_at`"),
                ("supervisor_feedback", "TEXT NULL AFTER `verified_via`"),
            ]

            for col_name, col_def in columns_to_add:
                if col_name not in cols:
                    print(f"Adding column '{col_name}' to agent_experience...")
                    cursor.execute(f"ALTER TABLE `agent_experience` ADD COLUMN `{col_name}` {col_def}")
                else:
                    print(f"Column '{col_name}' already exists.")

            # Add index on verification_token if not present
            cursor.execute("SHOW INDEX FROM agent_experience WHERE Key_name = 'idx_exp_verification_token'")
            if not cursor.fetchone():
                print("Adding index 'idx_exp_verification_token'...")
                cursor.execute("ALTER TABLE `agent_experience` ADD KEY `idx_exp_verification_token` (`verification_token`)")

            # Record migration in schema_migrations if table exists
            cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
            if cursor.fetchone():
                cursor.execute("""
                    INSERT INTO schema_migrations (migration_name, applied_at)
                    VALUES ('005_supervisor_reference_loop', NOW())
                    ON DUPLICATE KEY UPDATE applied_at = NOW()
                """)

            conn.commit()
            print("MIGRATION 005 COMPLETED SUCCESSFULLY!")
    except Exception as e:
        conn.rollback()
        print(f"ERROR RUNNING MIGRATION 005: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
