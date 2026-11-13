"""
Migration 012: Configure dedicated Workforce Officer (Robert Otieno) and Platform Admin (John Nyabuto)
"""

import os
import sys
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.db import get_mysql_connection

def run_migration():
    conn = get_mysql_connection()
    if not conn:
        print("[FAIL] Cannot connect to MySQL.")
        sys.exit(1)

    password_hash = generate_password_hash("password123")

    try:
        with conn.cursor() as cur:
            # 1. Update user 2 to be Robert Otieno (Workforce Officer)
            print("[RUN] Updating User 2 to Robert Otieno (Workforce Officer)...")
            cur.execute("""
                UPDATE users 
                SET full_name = 'Robert Otieno',
                    email = 'robert.otieno@verifymesh.io',
                    role = 'WORKFORCE_OFFICER',
                    password_hash = %s,
                    is_active = 1,
                    email_verified = 1
                WHERE user_id = 2
            """, (password_hash,))

            # 2. Check if John Nyabuto (Platform Admin) exists
            cur.execute("SELECT user_id FROM users WHERE email = 'john.nyabuto@verifymesh.io'")
            john = cur.fetchone()
            if not john:
                print("[RUN] Creating John Nyabuto (Platform Admin)...")
                cur.execute("""
                    INSERT INTO users (full_name, email, password_hash, role, is_active, email_verified, created_at)
                    VALUES ('John Nyabuto', 'john.nyabuto@verifymesh.io', %s, 'PLATFORM_ADMIN', 1, 1, NOW())
                """, (password_hash,))
                john_id = cur.lastrowid
                print(f"[SUCCESS] John Nyabuto created with user_id {john_id}")
            else:
                print(f"[RUN] Updating existing John Nyabuto (user_id {john['user_id']}) to PLATFORM_ADMIN...")
                cur.execute("""
                    UPDATE users 
                    SET full_name = 'John Nyabuto',
                        role = 'PLATFORM_ADMIN',
                        password_hash = %s,
                        is_active = 1,
                        email_verified = 1
                    WHERE user_id = %s
                """, (password_hash, john["user_id"]))

            # Record migration
            cur.execute("""
                INSERT INTO schema_migrations (migration_name, applied_at)
                VALUES ('012_workforce_and_platform_admin_accounts', NOW())
                ON DUPLICATE KEY UPDATE applied_at = NOW()
            """)
            conn.commit()
            print("[SUCCESS] Migration 012 applied successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()

