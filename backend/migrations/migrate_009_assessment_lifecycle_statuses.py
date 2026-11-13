"""
Migration Runner: 009_assessment_lifecycle_statuses
Expands assessment_attempts status enum to include ABANDONED and CANCELLED,
and adds closure_reason column.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 009_assessment_lifecycle_statuses")
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
            # 1. Modify status column on assessment_attempts
            print("Expanding `status` ENUM on `assessment_attempts`...")
            cursor.execute("""
                ALTER TABLE assessment_attempts
                MODIFY COLUMN status ENUM('IN_PROGRESS','SUBMITTED','EXPIRED','CLOSED','ABANDONED','CANCELLED')
                COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'IN_PROGRESS'
            """)
            print("`status` ENUM updated.")

            # 2. Add closure_reason to assessment_attempts
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'closure_reason'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `closure_reason` column to `assessment_attempts`...")
                cursor.execute("ALTER TABLE `assessment_attempts` ADD COLUMN `closure_reason` VARCHAR(255) NULL DEFAULT NULL AFTER `last_saved_at`")
                print("Added `closure_reason` column.")
            else:
                print("Column `closure_reason` already exists in `assessment_attempts`.")

            # Record migration in schema_migrations if table exists
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations'
            """)
            if cursor.fetchone()["cnt"] > 0:
                cursor.execute("""
                    INSERT IGNORE INTO schema_migrations (migration_name, applied_at)
                    VALUES ('009_assessment_lifecycle_statuses', NOW())
                """)

        conn.commit()
        print("MIGRATION 009 COMPLETED SUCCESSFULLY.")
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

