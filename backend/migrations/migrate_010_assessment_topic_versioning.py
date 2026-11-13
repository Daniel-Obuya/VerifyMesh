"""
Migration Runner: 010_assessment_topic_versioning
Adds version to assessment_topics and topic_version to assessment_attempts.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 010_assessment_topic_versioning")
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
            # 1. Add version to assessment_topics
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_topics' AND COLUMN_NAME = 'version'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `version` column to `assessment_topics`...")
                cursor.execute("ALTER TABLE `assessment_topics` ADD COLUMN `version` INT UNSIGNED NOT NULL DEFAULT 1 AFTER `status`")
                print("Added `version` column.")
            else:
                print("Column `version` already exists in `assessment_topics`.")

            # 2. Add topic_version to assessment_attempts
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'topic_version'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `topic_version` column to `assessment_attempts`...")
                cursor.execute("ALTER TABLE `assessment_attempts` ADD COLUMN `topic_version` INT UNSIGNED NOT NULL DEFAULT 1 AFTER `closure_reason`")
                print("Added `topic_version` column.")
            else:
                print("Column `topic_version` already exists in `assessment_attempts`.")

            # Record migration in schema_migrations
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'schema_migrations'
            """)
            if cursor.fetchone()["cnt"] > 0:
                cursor.execute("""
                    INSERT IGNORE INTO schema_migrations (migration_name, applied_at)
                    VALUES ('010_assessment_topic_versioning', NOW())
                """)

        conn.commit()
        print("MIGRATION 010 COMPLETED SUCCESSFULLY.")
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

