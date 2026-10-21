"""
Migration Runner: 002_assessment_integrity
Creates assessment_attempts table and ensures attempt_id references are present.
Records execution in schema_migrations table.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 002_assessment_integrity")
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
            # 1. Read and execute 002_assessment_integrity.sql
            sql_file = os.path.join(os.path.dirname(__file__), "002_assessment_integrity.sql")
            with open(sql_file, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            clean_lines = [line for line in raw_sql.splitlines() if not line.strip().startswith("--")]
            clean_sql = "\n".join(clean_lines)

            for cmd in clean_sql.split(";"):
                cmd = cmd.strip()
                if not cmd:
                    continue
                cursor.execute(cmd)

            # 2. Add attempt_id to exam_results if not present
            cursor.execute("DESCRIBE exam_results")
            er_cols = [r["Field"] for r in cursor.fetchall()]
            if "attempt_id" not in er_cols:
                print("Adding attempt_id column to exam_results...")
                cursor.execute("""
                    ALTER TABLE exam_results 
                    ADD COLUMN attempt_id INT UNSIGNED NULL AFTER exam_result_id,
                    ADD KEY idx_exam_results_attempt (attempt_id)
                """)

            # 3. Record migration completion
            cursor.execute("""
                INSERT INTO schema_migrations (migration_name) 
                VALUES (%s) 
                ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP
            """, ("002_assessment_integrity",))

            conn.commit()
            print("Migration 002_assessment_integrity verified and applied successfully.")
            return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
