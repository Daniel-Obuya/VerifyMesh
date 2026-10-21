import pymysql
from backend.config import Config

def migrate_profile_schema():
    print("============================================================")
    print("RUNNING AGENT PROFILE & VERIFICATION SCHEMA MIGRATION")
    print("============================================================")

    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

    try:
        with conn.cursor() as cursor:
            # 1. Update agents table: add bio and location
            cursor.execute("DESCRIBE agents")
            agent_cols = [r["Field"] for r in cursor.fetchall()]
            
            if "bio" not in agent_cols:
                print("Adding 'bio' column to agents table...")
                cursor.execute("ALTER TABLE agents ADD COLUMN bio TEXT NULL AFTER education")
            
            if "location" not in agent_cols:
                print("Adding 'location' column to agents table...")
                cursor.execute("ALTER TABLE agents ADD COLUMN location VARCHAR(150) NULL AFTER bio")

            # 2. Update agent_certifications table: expand status enum and add verification tracking
            cursor.execute("DESCRIBE agent_certifications")
            cert_cols = [r["Field"] for r in cursor.fetchall()]

            print("Updating 'status' ENUM in agent_certifications...")
            cursor.execute("""
                ALTER TABLE agent_certifications 
                MODIFY COLUMN status ENUM('PENDING', 'VERIFIED', 'REJECTED', 'EXPIRED', 'ACTIVE', 'REVOKED') 
                NOT NULL DEFAULT 'PENDING'
            """)

            if "issuing_organization" not in cert_cols:
                print("Adding 'issuing_organization' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN issuing_organization VARCHAR(150) NULL AFTER certificate_number")

            if "credential_url" not in cert_cols:
                print("Adding 'credential_url' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN credential_url VARCHAR(255) NULL AFTER issuing_organization")

            if "rejection_reason" not in cert_cols:
                print("Adding 'rejection_reason' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN rejection_reason TEXT NULL AFTER status")

            if "reviewed_by" not in cert_cols:
                print("Adding 'reviewed_by' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN reviewed_by INT UNSIGNED NULL AFTER rejection_reason")

            if "reviewed_at" not in cert_cols:
                print("Adding 'reviewed_at' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN reviewed_at DATETIME NULL AFTER reviewed_by")

            if "updated_at" not in cert_cols:
                print("Adding 'updated_at' column to agent_certifications...")
                cursor.execute("ALTER TABLE agent_certifications ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at")

            # 3. Create agent_experience table
            cursor.execute("SHOW TABLES LIKE 'agent_experience'")
            if not cursor.fetchone():
                print("Creating 'agent_experience' table...")
                cursor.execute("""
                    CREATE TABLE agent_experience (
                        experience_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        agent_id INT UNSIGNED NOT NULL,
                        job_title VARCHAR(150) NOT NULL,
                        company VARCHAR(150) NOT NULL,
                        work_category ENUM('Sales', 'Customer Service', 'Other') NOT NULL DEFAULT 'Other',
                        description TEXT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE NULL,
                        is_current TINYINT(1) NOT NULL DEFAULT 0,
                        verification_status ENUM('PENDING', 'VERIFIED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
                        rejection_reason TEXT NULL,
                        reviewed_by INT UNSIGNED NULL,
                        reviewed_at DATETIME NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_agent_exp (agent_id),
                        INDEX idx_agent_exp_status (agent_id, verification_status),
                        CONSTRAINT fk_agent_experience_agent FOREIGN KEY (agent_id) 
                            REFERENCES agents (agent_id) ON DELETE CASCADE,
                        CONSTRAINT fk_agent_experience_reviewer FOREIGN KEY (reviewed_by) 
                            REFERENCES users (user_id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

            # 4. Seed verified baseline work experience for Agent 1 (Alex Morgan)
            cursor.execute("SELECT agent_id FROM agents WHERE user_id = 1")
            agent1 = cursor.fetchone()
            if agent1:
                agent1_id = agent1["agent_id"]
                # Update bio and location if empty
                cursor.execute("""
                    UPDATE agents 
                    SET bio = 'Senior Customer Operations & Technical Support Specialist with over 2 years of experience managing escalations, onboarding, and enterprise client relations.',
                        location = 'Nairobi, Kenya',
                        phone = '+254 700 123456'
                    WHERE agent_id = %s AND (bio IS NULL OR bio = '')
                """, (agent1_id,))

                # Check if Agent 1 has experience records
                cursor.execute("SELECT COUNT(*) AS cnt FROM agent_experience WHERE agent_id = %s", (agent1_id,))
                if cursor.fetchone()["cnt"] == 0:
                    print("Seeding verified baseline work experience for Agent 1 (Alex Morgan)...")
                    # Experience 1: Sales & Client Onboarding Specialist (18 months: 2024-01-01 to 2025-06-30)
                    cursor.execute("""
                        INSERT INTO agent_experience 
                        (agent_id, job_title, company, work_category, description, start_date, end_date, is_current, verification_status, reviewed_by, reviewed_at)
                        VALUES 
                        (%s, 'Sales & Client Onboarding Specialist', 'CloudCommerce Ltd', 'Sales', 
                         'Managed high-velocity client acquisition, enterprise solution walkthroughs, and onboarding pipeline.', 
                         '2024-01-01', '2025-06-30', 0, 'VERIFIED', 2, NOW())
                    """, (agent1_id,))
                    
                    # Experience 2: Customer Support Lead (12 months: 2025-07-01 to 2026-06-30)
                    cursor.execute("""
                        INSERT INTO agent_experience 
                        (agent_id, job_title, company, work_category, description, start_date, end_date, is_current, verification_status, reviewed_by, reviewed_at)
                        VALUES 
                        (%s, 'Customer Support Lead', 'Nexus Digital', 'Customer Service', 
                         'Spearheaded Tier 2 SaaS customer issue resolution, incident reporting, and satisfaction metrics.', 
                         '2025-07-01', '2026-06-30', 0, 'VERIFIED', 2, NOW())
                    """, (agent1_id,))

                # Check if Agent 1 has active certification
                cursor.execute("SELECT COUNT(*) AS cnt FROM agent_certifications WHERE agent_id = %s", (agent1_id,))
                if cursor.fetchone()["cnt"] == 0:
                    print("Seeding verified certification for Agent 1...")
                    cursor.execute("""
                        INSERT INTO agent_certifications 
                        (agent_id, certification_id, certificate_number, issuing_organization, credential_url, issue_date, expiry_date, status, reviewed_by, reviewed_at)
                        VALUES 
                        (%s, 1, 'VM-CERT-2025-001', 'VerifyMesh Professional Academy', 'https://verifymesh.io/verify/VM-CERT-2025-001', '2025-01-15', '2027-01-15', 'VERIFIED', 2, NOW())
                    """, (agent1_id,))

            conn.commit()
            print("============================================================")
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("============================================================")

    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_profile_schema()
