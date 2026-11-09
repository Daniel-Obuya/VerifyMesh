"""
Migration Runner: 006_task_multi_certifications
Creates task_certifications table and backfills existing task certifications.
"""

import os
import sys
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 006_task_multi_certifications")
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
            # 1. Create task_certifications table
            print("Ensuring `task_certifications` table exists...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `task_certifications` (
                  `task_id` int unsigned NOT NULL,
                  `certification_id` int unsigned NOT NULL,
                  `is_mandatory` tinyint(1) NOT NULL DEFAULT '1',
                  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`task_id`, `certification_id`),
                  KEY `idx_tc_task` (`task_id`),
                  KEY `idx_tc_certification` (`certification_id`),
                  CONSTRAINT `fk_tc_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`task_id`) ON DELETE CASCADE ON UPDATE CASCADE,
                  CONSTRAINT `fk_tc_certification` FOREIGN KEY (`certification_id`) REFERENCES `certifications` (`certification_id`) ON DELETE RESTRICT ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # 2. Backfill existing task requirements
            print("Backfilling existing certifications from `task_requirements`...")
            cursor.execute("""
                INSERT IGNORE INTO `task_certifications` (`task_id`, `certification_id`, `is_mandatory`)
                SELECT `task_id`, `required_certification_id`, 1
                FROM `task_requirements`
                WHERE `required_certification_id` IS NOT NULL;
            """)
            backfilled = cursor.rowcount
            print(f"Backfilled {backfilled} task certification link(s).")

            # 3. Record migration in schema_migrations if table exists
            cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
            if cursor.fetchone():
                cursor.execute("""
                    INSERT IGNORE INTO `schema_migrations` (`migration_name`)
                    VALUES ('006_task_multi_certifications')
                """)

            conn.commit()
            print("Migration 006 completed successfully!")
            return True
    except Exception as e:
        conn.rollback()
        print(f"Migration 006 failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

