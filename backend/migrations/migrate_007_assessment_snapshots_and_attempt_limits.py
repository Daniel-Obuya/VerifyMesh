"""
Migration Runner: 007_assessment_snapshots_and_attempt_limits
Adds max_attempts to assessment_topics, question_snapshot_json to assessment_attempts,
and status to exam_questions.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 007_assessment_snapshots_and_attempt_limits")
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
            # 1. Add max_attempts to assessment_topics
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_topics' AND COLUMN_NAME = 'max_attempts'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `max_attempts` column to `assessment_topics`...")
                cursor.execute("ALTER TABLE `assessment_topics` ADD COLUMN `max_attempts` int unsigned NOT NULL DEFAULT 3 AFTER `estimated_minutes`")
                print("Added `max_attempts` column.")
            else:
                print("Column `max_attempts` already exists in `assessment_topics`.")

            # 2. Add question_snapshot_json to assessment_attempts
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_attempts' AND COLUMN_NAME = 'question_snapshot_json'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `question_snapshot_json` column to `assessment_attempts`...")
                cursor.execute("ALTER TABLE `assessment_attempts` ADD COLUMN `question_snapshot_json` json NULL DEFAULT NULL AFTER `subscores_json`")
                print("Added `question_snapshot_json` column.")
            else:
                print("Column `question_snapshot_json` already exists in `assessment_attempts`.")

            # 3. Add status to exam_questions
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'exam_questions' AND COLUMN_NAME = 'status'
            """)
            if cursor.fetchone()["cnt"] == 0:
                print("Adding `status` column to `exam_questions`...")
                cursor.execute("ALTER TABLE `exam_questions` ADD COLUMN `status` enum('ACTIVE','INACTIVE','DRAFT') NOT NULL DEFAULT 'ACTIVE' AFTER `options_json`")
                print("Added `status` column.")
            else:
                print("Column `status` already exists in `exam_questions`.")

            # 4. Record migration in schema_migrations if it exists
            cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
            if cursor.fetchone():
                cursor.execute("""
                    INSERT IGNORE INTO `schema_migrations` (`migration_name`, `applied_at`)
                    VALUES ('007_assessment_snapshots_and_attempt_limits', NOW())
                """)

            conn.commit()
            print("Migration 007 completed successfully!")
            return True
    except Exception as e:
        conn.rollback()
        print(f"Migration 007 failed: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

