import pymysql
from backend.db import get_mysql_connection

def run_migration():
    conn = get_mysql_connection()
    if not conn:
        print("Failed to connect to MySQL")
        return False

    cursor = conn.cursor()
    try:
        # 1. Check existing columns in tasks
        cursor.execute("DESCRIBE tasks")
        existing_cols = {r["Field"] for r in cursor.fetchall()}

        new_cols = [
            ("work_arrangement", "ENUM('Remote', 'Hybrid', 'On-site') NOT NULL DEFAULT 'Remote'"),
            ("location", "VARCHAR(150) NULL"),
            ("deliverables", "TEXT NULL"),
            ("required_skills", "TEXT NULL"),
            ("payment_type", "ENUM('Hourly', 'Fixed Budget') NOT NULL DEFAULT 'Fixed Budget'"),
            ("currency", "VARCHAR(10) NOT NULL DEFAULT 'KES'"),
            ("hourly_rate_min", "DECIMAL(10,2) NULL"),
            ("hourly_rate_max", "DECIMAL(10,2) NULL"),
            ("fixed_budget", "DECIMAL(10,2) NULL"),
            ("positions_count", "INT UNSIGNED NOT NULL DEFAULT 1"),
            ("application_deadline", "DATE NULL"),
            ("expected_duration", "VARCHAR(100) NULL"),
            ("exam_id", "INT UNSIGNED NULL"),
        ]

        for col_name, col_def in new_cols:
            if col_name not in existing_cols:
                sql = f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}"
                print(f"Adding column: {col_name}...")
                cursor.execute(sql)

        # 2. Add foreign key if not exists
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tasks' AND CONSTRAINT_NAME = 'fk_tasks_exams'
        """)
        if not cursor.fetchone():
            try:
                cursor.execute("""
                    ALTER TABLE tasks 
                    ADD CONSTRAINT fk_tasks_exams 
                    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE SET NULL
                """)
                print("Added foreign key fk_tasks_exams")
            except Exception as e:
                print(f"Notice regarding fk_tasks_exams: {e}")

        # 3. Populate existing tasks with realistic compensation & arrangement
        cursor.execute("""
            UPDATE tasks 
            SET 
                work_arrangement = COALESCE(work_arrangement, 'Remote'),
                location = COALESCE(location, 'Nairobi, Kenya (Hybrid/Remote)'),
                currency = COALESCE(currency, 'KES'),
                payment_type = CASE WHEN task_id IN (3, 4) THEN 'Hourly' ELSE 'Fixed Budget' END,
                hourly_rate_min = CASE WHEN task_id IN (3, 4) THEN 2500.00 ELSE NULL END,
                hourly_rate_max = CASE WHEN task_id IN (3, 4) THEN 4500.00 ELSE NULL END,
                fixed_budget = CASE WHEN task_id NOT IN (3, 4) THEN 120000.00 ELSE NULL END,
                positions_count = COALESCE(positions_count, 2),
                application_deadline = DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY),
                expected_duration = '3 months',
                deliverables = 'Deliver assigned weekly tickets, maintain SLA compliance, and provide de-escalation reports.',
                required_skills = 'Customer Communication, Technical Troubleshooting, SLA Adherence'
            WHERE location IS NULL OR deliverables IS NULL
        """)

        # 4. Ensure exams exist for both Category 1 and Category 2
        cursor.execute("SELECT exam_id FROM exams WHERE category_id = 2 LIMIT 1")
        cat2_exam = cursor.fetchone()
        if not cat2_exam:
            cursor.execute("""
                INSERT INTO exams (category_id, exam_name, description, passing_score, status)
                VALUES (2, 'Customer Support Diagnostic Assessment', 
                        'Evaluates customer de-escalation, diagnostic methodology, ticket communication, and enterprise SLA compliance.',
                        75.00, 'ACTIVE')
            """)
            cat2_exam_id = cursor.lastrowid
            print(f"Created Exam ID {cat2_exam_id} for Category 2 (Customer Support)")
        else:
            cat2_exam_id = cat2_exam["exam_id"]

        # 5. Populate exam_questions if empty
        cursor.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id = 1")
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute("""
                INSERT INTO exam_questions (exam_id, question_text, question_type, points, correct_answer, options_json, question_order)
                VALUES 
                (1, 'In VerifyMesh architecture, what is the role of Google Colab versus the Flask backend?', 'MULTIPLE_CHOICE', 25.00, 'A',
                 '["Colab trains and exports the ML model; Flask serves inference and runs business rules.", "Colab runs live API requests for every client click.", "Flask retrains the Random Forest model on each request.", "Colab directly manages MySQL database tables."]', 1),
                (1, 'When counseling an enterprise client hesitant about platform ROI, what is the best approach?', 'MULTIPLE_CHOICE', 25.00, 'A',
                 '["Analyze monthly volume and demonstrate dispute reduction savings.", "Immediately cut pricing by 50%% without data.", "Direct them to generic documentation links.", "Suggest they look for a different service."]', 2),
                (1, 'How should multi-tier competency thresholds be explained to prospective team leads?', 'MULTIPLE_CHOICE', 25.00, 'B',
                 '["Eligibility guarantees task assignment regardless of availability.", "Competency is a baseline prerequisite evaluated per task against verified criteria.", "Tiers are assigned manually without ML prediction.", "All agents share the same static tier."]', 3),
                (1, 'Which metric indicates high consultative sales proficiency in workforce management?', 'MULTIPLE_CHOICE', 25.00, 'C',
                 '["Closing contracts without verifying agent requirements.", "Sending repetitive uncustomized proposals.", "Accurately matching talent competency tiers to task complexity.", "Ignoring customer support history."]', 4)
            """)
            print("Seeded exam_questions for Exam 1")

        cursor.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id = %s", (cat2_exam_id,))
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute("""
                INSERT INTO exam_questions (exam_id, question_text, question_type, points, correct_answer, options_json, question_order)
                VALUES 
                (%s, 'A client reports an urgent task delivery delay with high emotional escalation. What is your initial action?', 'MULTIPLE_CHOICE', 25.00, 'A',
                 '["Acknowledge immediately, validate frustration, explain concrete recovery steps with an updated ETA.", "Ignore until the issue resolves itself.", "Blame the engineering team for server slowness.", "Issue a generic refund without investigating."]', 1),
                (%s, 'When troubleshooting recurring agent qualification mismatches, where should you investigate first?', 'MULTIPLE_CHOICE', 25.00, 'B',
                 '["Clear browser local storage on the client side.", "Verify audit logs, certification validity, and task requirement thresholds.", "Drop and recreate the agents table.", "Retrain the machine learning model immediately."]', 2),
                (%s, 'Under what condition does mandatory certification block an agent from applying for a task?', 'MULTIPLE_CHOICE', 25.00, 'A',
                 '["Whenever the task requires a certification that the agent does not actively hold, regardless of competency tier.", "Only if the agent is marked Ineligible.", "Only when the agent has zero months of experience.", "Certification never blocks application if score is above 80%%."]', 3),
                (%s, 'What is the required workflow when an agent application is submitted for a high-tier task?', 'MULTIPLE_CHOICE', 25.00, 'C',
                 '["Auto-assign task immediately upon submission.", "Delete earlier application records.", "Move status to Application Submitted or Under Review pending administrative action.", "Immediately mark as Rejected."]', 4)
            """, (cat2_exam_id, cat2_exam_id, cat2_exam_id, cat2_exam_id))
            print(f"Seeded exam_questions for Exam {cat2_exam_id}")

        # Link tasks that require exam to an exam_id
        cursor.execute("""
            UPDATE tasks t
            JOIN task_requirements tr ON t.task_id = tr.task_id
            SET t.exam_id = CASE WHEN t.category_id = 1 THEN 1 ELSE %s END
            WHERE tr.exam_required = 1 AND t.exam_id IS NULL
        """, (cat2_exam_id,))

        conn.commit()
        print("Migration and data setup completed successfully!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
