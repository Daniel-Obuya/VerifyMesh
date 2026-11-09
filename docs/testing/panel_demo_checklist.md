# VerifyMesh: Academic Panel Live Demonstration Rehearsal Checklist

**Project:** VerifyMesh: Enhancing Workforce Task Allocation Through Competency Assessment and Eligibility Prediction  
**Presentation Track:** Capstone Examination & Technical Panel Defense  
**Audience:** Academic Reviewers, Examiners, Technical Committee  
**Live Target URL:** Frontend: `http://localhost:5173` | Backend API: `http://127.0.0.1:5000`

---

## 1. Pre-Demonstration Environment Setup

Execute these steps 15 minutes before the panel begins:

### Step 1: Ensure MySQL 8.0 Windows Service is Running
Open PowerShell as Administrator:
```powershell
Get-Service -Name MySQL80,MySQL96
# If not running:
Start-Service -Name MySQL80
```

### Step 2: Start the Flask API Backend Server
In the project root:
```powershell
c:\Users\DANIEL\Desktop\Verify_Mesh\.venv\Scripts\python backend/app.py
```
**Verification Indicator:** Console prints:
```
[VerifyMesh ML] Loaded model from: ...\binary_eligibility_model.pkl (Binary Gatekeeper (Eligible / Not Eligible), 15 features)
Starting VerifyMesh API server on http://127.0.0.1:5000 (debug=False)...
```

### Step 3: Verify API Health Check
Open browser or run curl:
`http://127.0.0.1:5000/api/health`
**Expected Response:**
```json
{
  "database": {"connected": true, "engine": "MySQL", "mode": "MySQL Database"},
  "machine_learning": {"active_model": "binary_eligibility_model.pkl", "model_loaded": true},
  "service": "VerifyMesh API",
  "status": "healthy",
  "version": "1.0.0"
}
```

### Step 4: Start the React Frontend Dev Server
In a separate terminal window:
```powershell
cd c:\Users\DANIEL\Desktop\Verify_Mesh\frontend
npm run dev
```
**Verification Indicator:** Vite dev server is listening at `http://localhost:5173`.

---

## 2. Test Account Credentials Reference

*(Note: For security and academic integrity, passwords adhere to standard development conventions and must not be exposed to unauthorized parties.)*

| Role | User Identifier / Email | Pre-Configured Profile State | Panel Narrative Purpose |
| :--- | :--- | :--- | :--- |
| **Primary Test Agent** | `alex.morgan@university.edu` | 40 months verified experience, 1 active certification, passed assessment | Demonstrates the **Eligible Candidate Journey**, passing assessments, meeting task prerequisites, and applying for high-tier tasks. |
| **Entry-Level Agent** | `daniel.nyabuto@strathmore.edu` | 0 months verified experience, 0 certifications, entry profile | Demonstrates **Constraint Enforcement**, showing how missing experience, missing certifications, and ML ineligibility block unqualified assignments. |
| **System Administrator** | `admin@verifymesh.io` | Full administrator privileges, oversight permissions | Demonstrates **Governance & Oversight**, verification queues, task builder, requirement authoring, and audit logging. |

---

## 3. Ordered 21-Step Panel Demonstration Script

### Act I: System Health & Candidate Onboarding (Steps 1 – 6)

- [ ] **Step 1: System Health Verification**  
  - *Action:* Navigate to `http://127.0.0.1:5000/api/health` in browser or curl.
  - *Panel Talking Point:* "VerifyMesh verifies real-time MySQL connectivity and loads the pre-trained 15-feature Random Forest Binary Gatekeeper at startup with zero in-memory fallback."
  - *Expected Result:* JSON displaying `status: "healthy"`, `connected: true`, `model_loaded: true`.

- [ ] **Step 2: Candidate Registration**  
  - *Action:* Navigate to `http://localhost:5173/register`. Fill in:
    - Full Name: `Panel Candidate`
    - Email: `candidate.demo@verifymesh.io`
    - Phone: `+254 700 123 456`
    - Password / Confirm Password: `Password2026!`
    - Click **Create Account**.
  - *Expected Result:* Modal or prompt indicates: *"A 6-digit verification code has been sent to your email address."*

- [ ] **Step 3: Safe Email OTP Verification**  
  - *Action:* Enter the 6-digit OTP code generated for this email. (In local demonstration, obtain code from `email_verifications` table or console log). Click **Verify Code**.
  - *Expected Result:* Green confirmation banner: *"Email verified successfully. You can now sign in."*

- [ ] **Step 4: Candidate Sign In**  
  - *Action:* Enter email `candidate.demo@verifymesh.io` and password `Password2026!`. Click **Sign In**.
  - *Expected Result:* Redirected to `/dashboard` with greeting *"Welcome, Panel Candidate"*.

- [ ] **Step 5: Profile & Work History Setup**  
  - *Action:* Click **Profile** tab. Click **Add Experience**.
    - Title: `Enterprise Sales Representative`
    - Company: `Apex Global Cloud`
    - Category: `Sales`
    - Start Date: `2023-01-01` | End Date: `2023-12-31`
    - Click **Submit for Verification**.
  - *Expected Result:* Entry appears in Work History with yellow badge: `PENDING REVIEW`.

- [ ] **Step 6: Logout Candidate**  
  - *Action:* Click user dropdown -> **Sign Out**. Attempt to hit `/dashboard` directly.
  - *Expected Result:* Immediately redirected to `/login` (Protected Route boundary enforced).

---

### Act II: Administrative Oversight & Task Creation (Steps 7 – 10)

- [ ] **Step 7: Administrator Login**  
  - *Action:* Log in with `admin@verifymesh.io`.
  - *Expected Result:* Directed to `/admin/dashboard`. KPI cards display Active Agents, Active Tasks, Pending Verifications, and Active Model (`binary_eligibility_model.pkl`).

- [ ] **Step 8: Verification Queue Review**  
  - *Action:* Locate **Pending Verifications** section. Find `Panel Candidate`'s experience entry at Apex Global Cloud. Click **Approve**.
  - *Panel Talking Point:* "VerifyMesh maintains human-in-the-loop auditability. Candidates cannot self-verify experience; administrative approval is required before months contribute to ML feature vectors."
  - *Expected Result:* Entry status transitions to `VERIFIED`. Agent's verified experience updates in the database.

- [ ] **Step 9: Create a Sales Task with Strict Prerequisites**  
  - *Action:* Click **Tasks** -> **Create Task** (`/admin/tasks/create`). Fill in:
    - Task Title: `Enterprise Onboarding Specialist`
    - Category: `Sales`
    - Compensation: `Hourly` -> `KES 3,000` to `KES 4,500 / hr`
    - Description: `Lead consultative client onboarding, configure enterprise workflows, and conduct platform training.` (>= 20 chars)
    - Application Deadline: Select a date 30 days in the future.
    - Minimum Experience: `12 Months`
    - Minimum Competency: `Eligible`
    - Require Assessment: `Checked` -> Select `VerifyMesh Competency Assessment` (Exam 1) or `Customer Support Diagnostic` (Exam 3).
    - Click **Publish Task**.
  - *Expected Result:* Task is saved and appears in the Active Task list.

- [ ] **Step 10: Sign Out Administrator**  
  - *Action:* Click **Sign Out**.

---

### Act III: Candidate Assessment & Server-Side Scoring (Steps 11 – 13)

- [ ] **Step 11: Candidate Views Available Task**  
  - *Action:* Sign in as `candidate.demo@verifymesh.io` or `alex.morgan@university.edu`. Navigate to **Tasks**.
  - *Expected Result:* The newly created task displays badge: `Assessment Needed`.
  - *Panel Talking Point:* "The system enforces the 8-step precedence rule. Even though the candidate has verified experience, the task requires a validated competency assessment before an application can be unlocked."

- [ ] **Step 12: Take the Competency Assessment**  
  - *Action:* Click **Take Assessment** on the task card.
  - *Panel Talking Point:* "Inspect the browser network tab. The questions payload contains only question text and options. Correct answers and point weights are withheld on the server to prevent DOM or script inspection."
  - *Action:* Answer the 5 assessment questions. Click **Submit Assessment**.

- [ ] **Step 13: Server-Side Scoring & Instant Feedback**  
  - *Expected Result:* Results page displays:
    - Authoritative Score (e.g. `100.0%` or `80.0%`).
    - Pass/Fail Badge (e.g. `Passed (Threshold: 75.0%)`).
    - Subscore breakdowns across Product Knowledge, Customer Communication, and Diagnostic Triage.
    - Result persisted in MySQL `exam_results` and `ml_predictions`.

---

### Act IV: Machine Learning Prediction & Dual-Layer Decision (Steps 14 – 16)

- [ ] **Step 14: Automated ML Inference & Eligibility Evaluation**  
  - *Action:* Click **Return to Dashboard**. Inspect the task status.
  - *Expected Result:*
    - If candidate has >=12 mo verified experience + passed assessment + ML predicts `Eligible`: Task state transitions to **`Ready to Apply`** (Apply button enabled).
    - If candidate has <12 mo verified experience (e.g. `daniel.nyabuto@strathmore.edu`): Task state displays **`Requires 12 Months Exp`** or **`Ineligible`** (Apply button disabled).
  - *Panel Talking Point:* "This demonstrates the dual-layer architecture. A high exam score alone cannot override a mandatory experience requirement. Both the hard constraints and the ML prediction must agree."

- [ ] **Step 15: Task Application Submission**  
  - *Action:* On an unlocked task (`Ready to Apply`), click **Apply Now**. Enter optional notes: *"Available immediately for enterprise onboarding."* Click **Confirm Application**.
  - *Expected Result:* Task card state updates to `Application Submitted` / `Under Review`.

- [ ] **Step 16: Demonstrate Constraint Enforcement on Ineligible Candidate**  
  - *Action:* Switch account to `daniel.nyabuto@strathmore.edu` (0 months exp, no certs). View tasks.
  - *Expected Result:* High-tier tasks display `Certification Required` or `Requires 24 Months Exp`. The candidate is completely blocked from applying.

---

### Act V: Audit Logging, Persistence & Security Defense (Steps 17 – 21)

- [ ] **Step 17: Administrative Evidence & Audit Trail**  
  - *Action:* Log in as `admin@verifymesh.io`. Go to **Overview** / **Reviews**.
  - *Expected Result:* Administrator can see the full feature vector, model confidence score, and timestamp of the candidate's evaluation in the audit log.

- [ ] **Step 18: Browser Refresh & Persistence Verification**  
  - *Action:* Hard refresh the browser (`Ctrl + F5` or `Cmd + Shift + R`).
  - *Expected Result:* All states, badges, approved verifications, and assessment scores load identically from MySQL without data loss.

- [ ] **Step 19: Security Barrier: RBAC Role Protection**  
  - *Action:* Log in as Agent `alex.morgan@university.edu`. In the browser address bar, attempt to navigate directly to `http://localhost:5173/admin/dashboard`.
  - *Expected Result:* The frontend ProtectedRoute immediately intercepts the route and bounces the agent back to `/dashboard`.
  - *API Check:* Attempting `curl -H "Authorization: Bearer <agent_token>" http://127.0.0.1:5000/api/admin/overview` returns HTTP 403 Forbidden.

- [ ] **Step 20: Security Barrier: Anti-Tampering on Assessment Scoring**  
  - *Panel Talking Point:* "If a malicious candidate attempts to modify the HTTP request to submit their own passing score or claim pass status directly, the backend immediately detects the forbidden fields and rejects the request with HTTP 400."

- [ ] **Step 21: Conclusion & Clean State Reset**  
  - *Action:* Log in as candidate, navigate to Profile or click **Reset Assessment for Demonstration** if retrying.
  - *Expected Result:* The non-destructive reset clears the active attempt and retake cooldown while maintaining historical audit records in MySQL.

---

## 4. Emergency Recovery Procedures

| Potential Issue | Symptoms | Immediate Recovery Action |
| :--- | :--- | :--- |
| **MySQL Service Stopped** | API health returns `status: degraded`, connection refused | Run `Start-Service MySQL80` in PowerShell. Re-check `http://127.0.0.1:5000/api/health`. |
| **Port 5000 Already in Use** | Backend fails to bind port 5000 | Run `netstat -ano \| findstr :5000`. Kill the stale PID with `taskkill /F /PID <pid>`. |
| **Frontend Stale Cache** | UI displays old text or cached errors | Press `Ctrl + Shift + R` to hard-refresh browser without cache. |
| **Candidate in Cooldown** | Assessment says "cooldown active" | Call `/api/competency/reset-assessment` with agent's auth token or restart backend with `ASSESSMENT_COOLDOWN_SECONDS=0`. |
