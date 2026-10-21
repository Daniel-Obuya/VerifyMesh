"""
Migration Runner: 004_binary_eligibility_alignment
Extends ml_predictions and task_requirements to support binary classification (ELIGIBLE / NOT_ELIGIBLE).
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
    print("RUNNING MIGRATION: 004_binary_eligibility_alignment")
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
            # 1. Read and execute 004_binary_eligibility_alignment.sql
            sql_file = os.path.join(os.path.dirname(__file__), "004_binary_eligibility_alignment.sql")
            with open(sql_file, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            clean_lines = [line for line in raw_sql.splitlines() if not line.strip().startswith("--")]
            clean_sql = "\n".join(clean_lines)

            for cmd in clean_sql.split(";"):
                cmd = cmd.strip()
                if not cmd:
                    continue
                print(f"Executing: {cmd[:60]}...")
                cursor.execute(cmd)

            # 2. Record migration in schema_migrations if not already recorded
            cursor.execute("SELECT migration_id FROM schema_migrations WHERE migration_name = %s LIMIT 1",
                           ("004_binary_eligibility_alignment",))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO schema_migrations (migration_name, applied_at)
                    VALUES (%s, NOW())
                """, ("004_binary_eligibility_alignment",))
                print("Recorded 004_binary_eligibility_alignment in schema_migrations.")
            else:
                print("Migration 004 already recorded.")

        conn.commit()
        print("=" * 60)
        print("MIGRATION 004 COMPLETED SUCCESSFULLY")
        print("=" * 60)
        return True

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
