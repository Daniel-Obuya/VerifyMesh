"""
Migration Runner: 003_assessment_topics_framework
Creates assessment_topics, task_assessment_topics, and agent_topic_results tables.
Adds topic_id to exam_questions and assessment_attempts.
Populates standard 4 competency topics, task-topic associations, and 20 scenario questions (5 per topic).
Records execution in schema_migrations table.
"""

import os
import sys
import json
import pymysql

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.config import Config


TOPICS_DATA = [
    {
        "topic_id": 1,
        "topic_name": "Product Knowledge",
        "category_id": 1,
        "description": "Evaluates foundational understanding of platform capabilities, cloud architecture, system workflows, and operational configurations.",
        "passing_score": 70.00,
        "estimated_minutes": 10
    },
    {
        "topic_id": 2,
        "topic_name": "Sales Techniques and Objection Handling",
        "category_id": 1,
        "description": "Assesses consultative discovery, commercial value framing, enterprise objection management, and post-call diligence.",
        "passing_score": 70.00,
        "estimated_minutes": 10
    },
    {
        "topic_id": 3,
        "topic_name": "Customer Communication",
        "category_id": 2,
        "description": "Evaluates clarity, empathy, de-escalation tone, professional written correspondence, and stakeholder messaging.",
        "passing_score": 75.00,
        "estimated_minutes": 10
    },
    {
        "topic_id": 4,
        "topic_name": "Customer Relationship Management",
        "category_id": 2,
        "description": "Assesses SLA triage, multi-tier escalation protocols, client retention risk handling, and account relationship management.",
        "passing_score": 75.00,
        "estimated_minutes": 10
    }
]

TASK_TOPIC_MAPPINGS = [
    # Task 2: Enterprise Onboarding Lead
    {"task_id": 2, "topic_id": 1, "is_mandatory": 1},
    {"task_id": 2, "topic_id": 3, "is_mandatory": 1},
    {"task_id": 2, "topic_id": 4, "is_mandatory": 1},
    # Task 3: Customer Support Specialist
    {"task_id": 3, "topic_id": 3, "is_mandatory": 1},
    {"task_id": 3, "topic_id": 4, "is_mandatory": 1},
    # Task 4: Technical Support Agent
    {"task_id": 4, "topic_id": 1, "is_mandatory": 1},
    {"task_id": 4, "topic_id": 3, "is_mandatory": 1},
    # Task 5: Product Consultant
    {"task_id": 5, "topic_id": 1, "is_mandatory": 1},
    {"task_id": 5, "topic_id": 2, "is_mandatory": 1},
    {"task_id": 5, "topic_id": 3, "is_mandatory": 1},
    # Task 6: Enterprise Escalation Lead
    {"task_id": 6, "topic_id": 3, "is_mandatory": 1},
    {"task_id": 6, "topic_id": 4, "is_mandatory": 1},
    # Task 10: Tier 2 Technical Support Agent
    {"task_id": 10, "topic_id": 1, "is_mandatory": 1},
    {"task_id": 10, "topic_id": 4, "is_mandatory": 1},
]

TOPIC_QUESTIONS = [
    # ==========================================
    # Topic 1: Product Knowledge (5 Questions, Exam 2)
    # ==========================================
    {
        "topic_id": 1,
        "exam_id": 2,
        "question_order": 1,
        "question_text": "A remote enterprise user reports: 'I was editing a critical report, and when I clicked Save, the screen flashed an Error 401 Unauthorized, and my changes failed to persist.' What is the most accurate diagnosis and immediate corrective action?",
        "options": [
            {"option_id": "A", "text": "The session token expired while drafting; open a secondary tab to re-authenticate, then retry the submission or preserve the payload in a local scratch buffer."},
            {"option_id": "B", "text": "The database dropped the table write lock; restart the local browser and advise clearing cookies completely."},
            {"option_id": "C", "text": "The client network firewall blocked outgoing port 443; switch immediately to an unsecured public hotspot."},
            {"option_id": "D", "text": "The API server ran out of disk space; ask the user to wait 24 hours for system maintenance."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 1,
        "exam_id": 2,
        "question_order": 2,
        "question_text": "While inspecting browser developer tools for an onboarding partner, you observe: POST /api/v1/sync 403 Forbidden - Response: {'error': 'insufficient_role_permissions', 'user_id': 884}. The user insists they should have full administrative rights. What should you verify first?",
        "options": [
            {"option_id": "A", "text": "Ask the user to disable their ad-blocker and browser hardware acceleration."},
            {"option_id": "B", "text": "Verify whether the user's role mapping in the enterprise directory matches the required admin role in the platform database."},
            {"option_id": "C", "text": "Tell the user to change their account password three times in succession."},
            {"option_id": "D", "text": "Immediately delete and re-create the user's entire organizational workspace."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 1,
        "exam_id": 2,
        "question_order": 3,
        "question_text": "In a distributed platform architecture, how does the system ensure data consistency between an asynchronous worker queue and the primary relational database?",
        "options": [
            {"option_id": "A", "text": "By executing background worker jobs without database transactions to maximize throughput."},
            {"option_id": "B", "text": "By using transactional outbox patterns, idempotent task execution keys, and atomic commits on job completion."},
            {"option_id": "C", "text": "By storing all financial records exclusively in local browser localStorage caches."},
            {"option_id": "D", "text": "By running database migrations on live production clusters during peak midday hours."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 1,
        "exam_id": 2,
        "question_order": 4,
        "question_text": "An enterprise client deploys a system update, but end users report seeing stale configuration metadata on their dashboards. Which architectural mechanism is most likely responsible?",
        "options": [
            {"option_id": "A", "text": "A CDN edge cache or browser service worker caching layer that requires a versioned cache invalidation or purge."},
            {"option_id": "B", "text": "The database primary server running out of available CPU threads."},
            {"option_id": "C", "text": "The client operating system having its system clock out of synchronization by 2 seconds."},
            {"option_id": "D", "text": "The domain DNS server rejecting DNSSEC cryptographic signatures."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 1,
        "exam_id": 2,
        "question_order": 5,
        "question_text": "When configuring an outbound webhook integration to notify third-party ERP systems of verified task completions, what is the mandatory security best practice?",
        "options": [
            {"option_id": "A", "text": "Sign each webhook payload using an HMAC secret key transmitted via HTTP header and include a timestamp to prevent replay attacks."},
            {"option_id": "B", "text": "Embed the database root password in the URL query string for faster authentication."},
            {"option_id": "C", "text": "Disable TLS certificate validation so firewalls do not block webhook traffic."},
            {"option_id": "D", "text": "Send raw unencrypted database query dumps directly over plain HTTP port 80."}
        ],
        "correct_answer": "A"
    },

    # =================================================================
    # Topic 2: Sales Techniques and Objection Handling (5 Questions, Exam 1)
    # =================================================================
    {
        "topic_id": 2,
        "exam_id": 1,
        "question_order": 1,
        "question_text": "An enterprise client managing 150 gig-workers is evaluating VerifyMesh. They want to ensure work eligibility compliance without adding manual spreadsheet tracking. Which approach represents best consultative sales discovery?",
        "options": [
            {"option_id": "A", "text": "Immediately offer a 30% discount if they commit to a 3-year enterprise contract before end-of-quarter."},
            {"option_id": "B", "text": "Ask diagnostic questions to map their current audit cycle, human error rates, and compliance exposure costs before proposing a tailored automated workflow."},
            {"option_id": "C", "text": "Tell them spreadsheets are obsolete and refuse to discuss their existing workflow until they review product slides."},
            {"option_id": "D", "text": "Transfer the prospect immediately to legal without conducting preliminary discovery."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 2,
        "exam_id": 1,
        "question_order": 2,
        "question_text": "A prospective partner says: 'We already have an internal team doing manual checks; why should we pay for an automated competency verification platform?' What is the strongest value-oriented response?",
        "options": [
            {"option_id": "A", "text": "Highlight how automated verification reduces time-to-onboard from 5 days to 2 minutes, eliminates fraud liability, and lets their team focus on higher-value workforce retention."},
            {"option_id": "B", "text": "Warn them that their existing team will make costly mistakes and will likely fail an audit soon."},
            {"option_id": "C", "text": "Argue that software is always cheaper than human employees and advise them to downsize immediately."},
            {"option_id": "D", "text": "Offer free swag and ask them to reconsider after seeing competitors switch."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 2,
        "exam_id": 1,
        "question_order": 3,
        "question_text": "When a prospective business client expresses concern about platform implementation complexity and IT burden, how should you structure your response?",
        "options": [
            {"option_id": "A", "text": "Dismiss their concerns as exaggerated and state that modern APIs require zero technical knowledge."},
            {"option_id": "B", "text": "Tell them implementation takes months and they must hire an external systems integrator."},
            {"option_id": "C", "text": "Acknowledge the valid concern, walk through the pre-built connectors and turnkey sandbox deployment, and offer a guided 14-day proof of concept with dedicated onboarding support."},
            {"option_id": "D", "text": "Direct them to a 300-page API documentation manual and ask them to return when finished reading."}
        ],
        "correct_answer": "C"
    },
    {
        "topic_id": 2,
        "exam_id": 1,
        "question_order": 4,
        "question_text": "Which metric provides the strongest quantitative proof of platform ROI to a skeptical enterprise Chief Financial Officer (CFO)?",
        "options": [
            {"option_id": "A", "text": "Total number of followers on the platform's social media announcement channel."},
            {"option_id": "B", "text": "Documented reduction in cost-per-verified-agent, 82% lower compliance infraction risk, and payback period within 90 days."},
            {"option_id": "C", "text": "The aesthetic design and color scheme of the agent dashboard interface."},
            {"option_id": "D", "text": "The number of lines of source code written by the backend development team."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 2,
        "exam_id": 1,
        "question_order": 5,
        "question_text": "In professional sales communication, what is the required practice after completing an initial enterprise discovery call?",
        "options": [
            {"option_id": "A", "text": "Send a structured summary within 24 hours confirming agreed pain points, quantified business impact, mutual next action items, and clear ownership deadlines."},
            {"option_id": "B", "text": "Wait at least two weeks before reaching out to avoid seeming overeager."},
            {"option_id": "C", "text": "Send an unrequested invoice with standard annual license fees attached."},
            {"option_id": "D", "text": "Post the prospect's internal requirements on a public community forum for feedback."}
        ],
        "correct_answer": "A"
    },

    # =================================================================
    # Topic 3: Customer Communication (5 Questions, Exam 3)
    # =================================================================
    {
        "topic_id": 3,
        "exam_id": 3,
        "question_order": 1,
        "question_text": "A high-tier client submits an urgent ticket in all caps: 'YOUR SYSTEM FAILED AGAIN IN THE MIDDLE OF OUR SHIFT! WE ARE LOSING THOUSANDS PER HOUR! FIX THIS IMMEDIATELY OR WE ARE CANCELING OUR CONTRACT TODAY!' What is the most effective initial de-escalation response?",
        "options": [
            {"option_id": "A", "text": "Acknowledge the severe operational impact immediately, validate their urgency with calm empathy, provide a direct point of contact, and state the exact investigation steps currently underway with a commitment to update within 15 minutes."},
            {"option_id": "B", "text": "Remind the client that typing in all capital letters violates platform community terms of service."},
            {"option_id": "C", "text": "Reply that outages are covered under the standard SLA disclaimer section 14.2 and close the ticket."},
            {"option_id": "D", "text": "Wait until the root cause is 100% resolved several hours later before replying to avoid giving incomplete answers."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 3,
        "exam_id": 3,
        "question_order": 2,
        "question_text": "When writing instructions to help a non-technical department manager resolve a browser caching mismatch, which response demonstrates the highest standard of customer communication?",
        "options": [
            {"option_id": "A", "text": "Tell them to 'inspect the service worker cache storage via devtools and invalidate the stale ETags'."},
            {"option_id": "B", "text": "Provide clear, numbered steps with plain-language directions, keyboard shortcuts, screenshots or visual landmarks, and a reassurance that their saved data is secure."},
            {"option_id": "C", "text": "Ask them to surrender their workstation credentials over plain text email so you can fix it."},
            {"option_id": "D", "text": "Advise them that non-technical users should not attempt to access cloud web applications."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 3,
        "exam_id": 3,
        "question_order": 3,
        "question_text": "During an unexpected service disruption affecting agent verification processing, how should customer communications be handled?",
        "options": [
            {"option_id": "A", "text": "Post transparent status updates on the platform incident dashboard, explaining what happened, current mitigation progress, and expected resolution ETA without technical evasion."},
            {"option_id": "B", "text": "Deny that any issue exists and tell individual inquiring users that the problem is unique to their local internet service provider."},
            {"option_id": "C", "text": "Disable the customer support inbox until all systems return to full health."},
            {"option_id": "D", "text": "Blame a third-party cloud provider by name in public angry messages."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 3,
        "exam_id": 3,
        "question_order": 4,
        "question_text": "When preparing a Root Cause Analysis (RCA) summary for an enterprise client after an outage, what tone and structure should be adopted?",
        "options": [
            {"option_id": "A", "text": "A defensive tone explaining that platform uptime is statistically higher than industry averages."},
            {"option_id": "B", "text": "An objective, professional post-mortem covering incident timeline, root cause mechanism, blast radius, immediate containment, and permanent engineering remediations to prevent recurrence."},
            {"option_id": "C", "text": "A brief message stating the issue has been resolved and no further discussion is necessary."},
            {"option_id": "D", "text": "An internal technical code review diff without business context or executive summary."}
        ],
        "correct_answer": "B"
    },
    {
        "topic_id": 3,
        "exam_id": 3,
        "question_order": 5,
        "question_text": "A customer requests a custom product feature that your engineering roadmap does not plan to support. How should you communicate this decision?",
        "options": [
            {"option_id": "A", "text": "Listen to the underlying business problem they are trying to solve, clarify why the specific request is not on the immediate roadmap, and present viable alternative workflows within existing platform features."},
            {"option_id": "B", "text": "Promise them that the feature will be released next week to keep them happy in the short term."},
            {"option_id": "C", "text": "Ignore the ticket until the customer forgets about the request."},
            {"option_id": "D", "text": "Inform them that their feature idea lacks commercial merit and close the conversation."}
        ],
        "correct_answer": "A"
    },

    # =====================================================================
    # Topic 4: Customer Relationship Management (5 Questions, Exam 4)
    # =====================================================================
    {
        "topic_id": 4,
        "exam_id": 4,
        "question_order": 1,
        "question_text": "You arrive at your shift and find 4 tickets waiting in your queue. Under standard service level agreements (SLAs), which ticket must you triage and investigate FIRST?",
        "options": [
            {"option_id": "A", "text": "Ticket #104 (P1 Critical): 'Live production payment gateway connection failing; 400+ gig workers cannot receive shift payouts.'"},
            {"option_id": "B", "text": "Ticket #101 (P3 Normal): 'Can we change our company logo background from light grey to dark blue?'"},
            {"option_id": "C", "text": "Ticket #102 (P4 Minor): 'Typo found in FAQ section paragraph 3 on onboarding page.'"},
            {"option_id": "D", "text": "Ticket #103 (P3 Normal): 'Requesting monthly CSV export of active workers for accounting audit next month.'"}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 4,
        "exam_id": 4,
        "question_order": 2,
        "question_text": "An account manager notes that an enterprise customer's weekly active verifications dropped by 45% over the past month. What proactive CRM action is most appropriate?",
        "options": [
            {"option_id": "A", "text": "Schedule a proactive health-check meeting with the key account stakeholder to review utilization, identify workflow blockers, and re-engage training if needed."},
            {"option_id": "B", "text": "Send an automated cancellation fee warning to their billing department."},
            {"option_id": "C", "text": "Do nothing until their renewal contract date arrives in 8 months."},
            {"option_id": "D", "text": "Throttle their remaining account API rate limits to save infrastructure costs."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 4,
        "exam_id": 4,
        "question_order": 3,
        "question_text": "When a customer issue requires escalation from Tier 1 Support to Core Engineering, what information must the agent document to ensure seamless cross-functional resolution?",
        "options": [
            {"option_id": "A", "text": "A complete reproduction path, affected tenant and user IDs, timestamps, browser/environment details, request/response payloads, and expected vs actual behavior."},
            {"option_id": "B", "text": "Only the single sentence: 'Client says it does not work; please fix.'"},
            {"option_id": "C", "text": "A screenshot of the customer's email signature."},
            {"option_id": "D", "text": "A copy of the client's commercial contract and billing address."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 4,
        "exam_id": 4,
        "question_order": 4,
        "question_text": "Which factor is the most reliable leading indicator of customer churn risk in an enterprise SaaS relationship?",
        "options": [
            {"option_id": "A", "text": "A sharp decline in key stakeholder login frequency combined with unresolved critical support tickets and low product adoption."},
            {"option_id": "B", "text": "The client requesting their invoice in PDF format rather than HTML."},
            {"option_id": "C", "text": "The client adding 5 new team members to their organization account."},
            {"option_id": "D", "text": "The client submitting a feature request to customize their notification preferences."}
        ],
        "correct_answer": "A"
    },
    {
        "topic_id": 4,
        "exam_id": 4,
        "question_order": 5,
        "question_text": "Following a major incident resolution, what is the best practice for concluding the customer relationship interaction?",
        "options": [
            {"option_id": "A", "text": "Follow up directly with the customer to confirm their operations are running smoothly, verify that all affected data is reconciled, and ask for their feedback on support responsiveness."},
            {"option_id": "B", "text": "Immediately mark the ticket 'Closed - Do Not Reopen' and block future replies."},
            {"option_id": "C", "text": "Instruct the client to submit a public 5-star review before you confirm system recovery."},
            {"option_id": "D", "text": "Ask the client to reimburse the support team for overtime hours spent investigating."}
        ],
        "correct_answer": "A"
    }
]


def run_migration():
    print("=" * 60)
    print("RUNNING MIGRATION: 003_assessment_topics_framework")
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
            # 1. Execute DDL from 003_assessment_topics_framework.sql
            sql_file = os.path.join(os.path.dirname(__file__), "003_assessment_topics_framework.sql")
            with open(sql_file, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            clean_lines = [line for line in raw_sql.splitlines() if not line.strip().startswith("--")]
            clean_sql = "\n".join(clean_lines)

            for cmd in clean_sql.split(";"):
                cmd = cmd.strip()
                if not cmd:
                    continue
                cursor.execute(cmd)

            # 2. Add topic_id to exam_questions if not present
            cursor.execute("DESCRIBE exam_questions")
            eq_cols = [r["Field"] for r in cursor.fetchall()]
            if "topic_id" not in eq_cols:
                print("Adding topic_id column to exam_questions...")
                cursor.execute("""
                    ALTER TABLE exam_questions
                    ADD COLUMN topic_id INT UNSIGNED NULL AFTER exam_id,
                    ADD KEY idx_exam_questions_topic (topic_id),
                    ADD CONSTRAINT fk_exam_questions_topic FOREIGN KEY (topic_id) REFERENCES assessment_topics(topic_id) ON DELETE SET NULL
                """)

            # 3. Add topic_id to assessment_attempts if not present
            cursor.execute("DESCRIBE assessment_attempts")
            att_cols = [r["Field"] for r in cursor.fetchall()]
            if "topic_id" not in att_cols:
                print("Adding topic_id column to assessment_attempts...")
                cursor.execute("""
                    ALTER TABLE assessment_attempts
                    ADD COLUMN topic_id INT UNSIGNED NULL AFTER exam_id,
                    ADD KEY idx_attempts_topic (topic_id),
                    ADD CONSTRAINT fk_attempts_topic FOREIGN KEY (topic_id) REFERENCES assessment_topics(topic_id) ON DELETE SET NULL
                """)

            # 3b. Drop old uq_exam_question_order constraint if present and replace with uq_topic_question_order
            cursor.execute("SHOW INDEX FROM exam_questions WHERE Key_name = 'uq_exam_question_order'")
            if cursor.fetchone():
                print("Dropping old uq_exam_question_order constraint...")
                cursor.execute("ALTER TABLE exam_questions DROP INDEX uq_exam_question_order")

            # 3c. Ensure exams 2 and 4 exist for topics 1 and 4
            cursor.execute("""
                INSERT INTO exams (exam_id, category_id, exam_name, description, passing_score, status)
                VALUES (2, 1, 'Product Knowledge Assessment', 'Evaluates cloud architecture, system workflows, error handling, and platform configurations.', 70.00, 'ACTIVE')
                ON DUPLICATE KEY UPDATE
                    exam_name = VALUES(exam_name),
                    description = VALUES(description),
                    passing_score = VALUES(passing_score),
                    status = 'ACTIVE'
            """)
            cursor.execute("""
                INSERT INTO exams (exam_id, category_id, exam_name, description, passing_score, status)
                VALUES (4, 2, 'Customer Relationship Management Assessment', 'Assesses SLA triage, escalation protocols, customer retention, and account management.', 75.00, 'ACTIVE')
                ON DUPLICATE KEY UPDATE
                    exam_name = VALUES(exam_name),
                    description = VALUES(description),
                    passing_score = VALUES(passing_score),
                    status = 'ACTIVE'
            """)

            # 4. Upsert Assessment Topics
            print("Seeding standard assessment topics...")
            for top in TOPICS_DATA:
                cursor.execute("""
                    INSERT INTO assessment_topics (topic_id, topic_name, category_id, description, passing_score, estimated_minutes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE')
                    ON DUPLICATE KEY UPDATE
                        topic_name = VALUES(topic_name),
                        category_id = VALUES(category_id),
                        description = VALUES(description),
                        passing_score = VALUES(passing_score),
                        estimated_minutes = VALUES(estimated_minutes),
                        status = 'ACTIVE'
                """, (
                    top["topic_id"],
                    top["topic_name"],
                    top["category_id"],
                    top["description"],
                    top["passing_score"],
                    top["estimated_minutes"]
                ))

            # 5. Upsert Task-Topic Requirements
            print("Mapping task-to-topic requirements...")
            for mapping in TASK_TOPIC_MAPPINGS:
                cursor.execute("""
                    INSERT INTO task_assessment_topics (task_id, topic_id, is_mandatory)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        is_mandatory = VALUES(is_mandatory)
                """, (
                    mapping["task_id"],
                    mapping["topic_id"],
                    mapping["is_mandatory"]
                ))

            # 6. Seed 20 authoritative workplace scenario questions (5 per topic)
            print("Seeding question bank (5 questions per topic, 20 total)...")
            for q in TOPIC_QUESTIONS:
                options_str = json.dumps(q["options"])
                # First check by topic_id and question_order
                cursor.execute("""
                    SELECT question_id FROM exam_questions
                    WHERE topic_id = %s AND question_order = %s
                    LIMIT 1
                """, (q["topic_id"], q["question_order"]))
                existing_q = cursor.fetchone()

                # If not found by topic_id, check if there's an unassigned question with this exam_id and order
                if not existing_q:
                    cursor.execute("""
                        SELECT question_id FROM exam_questions
                        WHERE exam_id = %s AND question_order = %s AND (topic_id IS NULL OR topic_id = %s)
                        LIMIT 1
                    """, (q["exam_id"], q["question_order"], q["topic_id"]))
                    existing_q = cursor.fetchone()

                if existing_q:
                    cursor.execute("""
                        UPDATE exam_questions
                        SET question_text = %s,
                            options_json = %s,
                            correct_answer = %s,
                            exam_id = %s,
                            topic_id = %s,
                            points = 1.00
                        WHERE question_id = %s
                    """, (
                        q["question_text"],
                        options_str,
                        q["correct_answer"],
                        q["exam_id"],
                        q["topic_id"],
                        existing_q["question_id"]
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO exam_questions (exam_id, topic_id, question_text, question_type, points, correct_answer, options_json, question_order)
                        VALUES (%s, %s, %s, 'MULTIPLE_CHOICE', 1.00, %s, %s, %s)
                    """, (
                        q["exam_id"],
                        q["topic_id"],
                        q["question_text"],
                        q["correct_answer"],
                        options_str,
                        q["question_order"]
                    ))

            # Add uq_topic_question_order constraint if not present
            cursor.execute("SHOW INDEX FROM exam_questions WHERE Key_name = 'uq_topic_question_order'")
            if not cursor.fetchone():
                print("Adding uq_topic_question_order constraint...")
                cursor.execute("ALTER TABLE exam_questions ADD UNIQUE KEY uq_topic_question_order (topic_id, question_order)")

            # 7. Migrate existing passed exam results into agent_topic_results
            print("Backfilling existing valid exam results to agent_topic_results...")
            cursor.execute("""
                SELECT er.exam_result_id, er.agent_id, er.exam_id, er.assessment_score, er.passed, er.completed_at
                FROM exam_results er
                WHERE er.passed = 1
            """)
            passed_exams = cursor.fetchall()

            for pe in passed_exams:
                # If exam_id == 3 (Customer Support), it maps to topic 3 & 4
                # If exam_id == 1 (Sales/Competency), it maps to topic 1 & 2
                mapped_topic_ids = [3, 4] if pe["exam_id"] == 3 else [1, 2]
                for tid in mapped_topic_ids:
                    cursor.execute("""
                        SELECT result_id FROM agent_topic_results
                        WHERE agent_id = %s AND topic_id = %s AND passed = 1
                        LIMIT 1
                    """, (pe["agent_id"], tid))
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO agent_topic_results (agent_id, topic_id, score, passed, completed_at)
                            VALUES (%s, %s, %s, 1, %s)
                        """, (pe["agent_id"], tid, pe["assessment_score"], pe["completed_at"]))

            # 8. Record migration in schema_migrations
            cursor.execute("""
                INSERT INTO schema_migrations (migration_name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP
            """, ("003_assessment_topics_framework",))

            conn.commit()
            print("Migration 003_assessment_topics_framework completed successfully.")
            return True

    except Exception as e:
        conn.rollback()
        print(f"Migration 003 failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
