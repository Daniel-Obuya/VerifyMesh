"""
Migration 011: Expand users.role ENUM to explicitly include WORKFORCE_OFFICER and PLATFORM_ADMIN
Non-destructive: preserves existing AGENT and ADMIN rows intact.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.db import get_mysql_connection

def run_migration():
    conn = get_mysql_connection()
    if not conn:
        print("[FAIL] Cannot connect to MySQL.")
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            # Check if migration already recorded
            cur.execute("SELECT migration_id FROM schema_migrations WHERE migration_name = '011_platform_admin_and_workforce_roles'")
            if cur.fetchone():
                print("[SKIP] Migration 011 already applied.")
                return

            print("[RUN] Expanding users.role ENUM...")
            cur.execute("""
                ALTER TABLE users 
                MODIFY COLUMN role ENUM('AGENT', 'ADMIN', 'WORKFORCE_OFFICER', 'PLATFORM_ADMIN') NOT NULL DEFAULT 'AGENT'
            """)

            cur.execute("""
                INSERT INTO schema_migrations (migration_name, applied_at)
                VALUES ('011_platform_admin_and_workforce_roles', NOW())
            """)
            conn.commit()
            print("[SUCCESS] Migration 011 applied successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()

