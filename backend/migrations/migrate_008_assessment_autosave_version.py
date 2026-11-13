"""
Migration Runner: 008_assessment_autosave_version
Adds answers_version and last_saved_at to assessment_attempts table.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 008_assessment_autosave_version")
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
            # 1. Add answers_version to assessment_attempts
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'answers_version'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `answers_version` column to `assessment_attempts`...")
                cursor.execute("ALTER TABLE `assessment_attempts` ADD COLUMN `answers_version` int unsigned NOT NULL DEFAULT 0 AFTER `answers_json`")
                print("Added `answers_version` column.")
            else:
                print("Column `answers_version` already exists in `assessment_attempts`.")

            # 2. Add last_saved_at to assessment_attempts
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'last_saved_at'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `last_saved_at` column to `assessment_attempts`...")
                cursor.execute("ALTER TABLE `assessment_attempts` ADD COLUMN `last_saved_at` datetime NULL DEFAULT NULL AFTER `answers_version`")
                print("Added `last_saved_at` column.")
            else:
                print("Column `last_saved_at` already exists in `assessment_attempts`.")

            # Record migration in schema_migrations if table exists
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations'
            """)
            if cursor.fetchone()["cnt"] > 0:
                cursor.execute("""
                    INSERT IGNORE INTO schema_migrations (migration_name, applied_at)
                    VALUES ('008_assessment_autosave_version', NOW())
                """)

        conn.commit()
        print("MIGRATION 008 COMPLETED SUCCESSFULLY.")
        print("=" * 60)
        return True
    except Exception as e:
        conn.rollback()
        print(f"MIGRATION FAILED: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
