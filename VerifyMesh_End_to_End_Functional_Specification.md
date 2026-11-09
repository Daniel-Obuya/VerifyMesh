# VERIFYMESH — SYSTEM FUNCTIONAL AND TECHNICAL SPECIFICATION

**Document Type:** Authoritative Product, Functional and Technical Requirements  
**Project:** VerifyMesh  
**Document Status:** Updated System Specification and Development Baseline  
**Primary Application Roles:** Agent and Administrator  
**Technology Baseline:** React, Flask/Python, MySQL  
**ML Component:** Experimental task-specific agent suitability model  
**Intended Audience:** Developers, Antigravity AI Agent, Software Testers, Project Supervisors and Capstone Evaluators  
**Purpose:** Define the intended functionality, business rules, system architecture, data relationships, security requirements, assessment workflow, eligibility logic, ML integration and acceptance criteria for VerifyMesh.

---

# PART I — PROJECT DEFINITION AND DEVELOPMENT RULES

## 1. PURPOSE OF THIS DOCUMENT

This document is the authoritative functional and technical reference for VerifyMesh.

It defines how the system should operate from agent registration and professional profile creation through evidence verification, competency assessments, task discovery, eligibility evaluation, application submission, administrative review and final assignment.

It also defines the responsibilities of the deterministic eligibility engine and the machine-learning component.

The document is intended to ensure that:

- The development team implements one consistent business workflow.
- Antigravity's AI agent does not invent functionality or architectural decisions.
- Assessment functionality is integrated properly with the task and eligibility workflows.
- Previously completed assessments can be reused where appropriate.
- Task requirements are configured by the Administrator rather than assumed by the system.
- Mandatory eligibility requirements cannot be bypassed by an ML prediction.
- Important decisions are made and validated on the backend.
- Existing working functionality is preserved unless it conflicts with this specification.
- All important information is persisted in MySQL.
- The system remains within the approved capstone scope.

### 1.1 Mandatory instructions for Antigravity's AI agent

Whenever working on the VerifyMesh codebase, the AI agent MUST:

1. Read this document fully before making changes.
2. Treat it as the authoritative reference for the intended business workflow and system behaviour.
3. Inspect the current repository, active Git branch, uncommitted changes, frontend, backend, database schema, migrations, API routes, tests, ML artifacts and configuration.
4. Establish what is already implemented before proposing or implementing changes.
5. Distinguish between:
   - Functionality that already works.
   - Functionality that is partially implemented.
   - Functionality that is broken.
   - Functionality that is not implemented.
   - Functionality described in this document but not yet verified in the repository.
6. Reuse existing components, database structures, services and endpoints wherever appropriate.
7. Avoid unnecessary rewrites, duplicate functionality and incompatible architectural changes.
8. Never invent database tables, columns, endpoints, model features, assessment results, task requirements or successful test outcomes.
9. Never introduce mock data, hardcoded responses, in-memory fallbacks or arbitrary default scores as substitutes for missing backend functionality.
10. Never assume that a frontend screen proves that its underlying functionality works.
11. Never change the ML model, its preprocessing pipeline, feature order, target classes, inference threshold or training assumptions without inspecting the actual artifact and its metadata.
12. Never allow the ML model to override mandatory eligibility requirements.
13. Never expose assessment answer keys, passwords, authentication tokens, secrets or other sensitive information to the frontend.
14. Preserve existing working functionality unless it directly conflicts with this specification or the project owner explicitly authorises a change.
15. Implement changes incrementally and test each important workflow.
16. If the current repository contradicts this specification, report the contradiction and recommend the smallest safe correction before implementing substantial changes.
17. If a requirement cannot be implemented because necessary data, configuration or functionality is missing, explain the limitation rather than fabricating a solution.
18. After every substantial implementation task, report:
    - Files inspected.
    - Files changed.
    - Requirements addressed.
    - Database changes or migrations.
    - API changes.
    - Tests executed.
    - Actual test results.
    - Remaining issues.
    - Known limitations.

**This specification defines intended behaviour. It does not establish that all described functionality is already implemented.**

### 1.2 Priority when making development decisions

Use the following priority order:

1. Security and data integrity.
2. Correct business rules and eligibility decisions.
3. Correct assessment and evidence verification workflows.
4. Backend persistence and API consistency.
5. ML integration and its limitations.
6. Frontend functionality and usability.
7. Visual refinements.

Do not prioritise visual improvements over broken eligibility, assessment, authentication or persistence functionality.

---

## 2. PROJECT PURPOSE

### 2.1 What VerifyMesh is

VerifyMesh is an AI-assisted competency verification and task-eligibility system designed to help administrators assess whether independent agents possess the verified qualifications, relevant experience and demonstrated competencies required for particular work opportunities.

The system is inspired by real-world recruitment and workforce qualification screening.

In a real recruitment process:

- Candidates create professional profiles.
- Candidates submit qualifications and employment histories.
- Employers review supporting evidence.
- Candidates may demonstrate their skills through assessments.
- Employers define the qualifications and competencies required for particular positions.
- Previously obtained qualifications and assessment results may be reused where relevant.
- Additional assessments may be required for particular positions.
- Employers evaluate applicants and make the final selection.

VerifyMesh should reproduce this process in a simplified, focused technical environment.

It combines:

1. Agent registration and professional profile management.
2. Submission and administrative verification of qualifications and work experience.
3. An independent competency assessment catalogue.
4. Voluntary agent-initiated assessments.
5. Reusable, server-graded assessment results.
6. Administrator-defined task requirements.
7. Task-specific eligibility evaluation.
8. An experimental ML-based task suitability signal.
9. Application management.
10. Human administrative review and assignment.

### 2.2 The central design principle

**Agents demonstrate what they can do. Administrators determine what a particular task requires. VerifyMesh checks whether the agent's verified evidence satisfies those requirements.**

The system must not assume that every agent has to complete every available assessment.

Likewise, the system must not assume that passing one assessment makes an agent eligible for every task.

An agent may have demonstrated Product Knowledge, Sales Techniques and Customer Communication competencies. However, an Administrator may create a task requiring only Product Knowledge and Customer Communication.

VerifyMesh must evaluate the agent against those specific requirements.

### 2.3 Core evaluation unit

The central unit of eligibility and suitability evaluation is an:

**Agent–Task Pair**

The system must evaluate an individual agent against an individual task.

An agent can be:

- Eligible for one task.
- Ineligible for another task.
- Eligible for a third task but have a lower experimental ML suitability score.
- Awaiting verification or additional assessment for another task.

Do not assign a permanent, universal eligibility status to an agent that automatically applies to all tasks.

### 2.4 What VerifyMesh is not

VerifyMesh is not intended to become a complete HR platform, recruitment marketplace or workforce-management system.

Unless explicitly approved, do not implement:

- Payroll processing.
- Salary management.
- Contract generation and signing.
- Payment processing.
- External government identity verification.
- Full background-check integrations.
- Automated hiring.
- Automated task assignment without administrator approval.
- Client-side recruitment accounts.
- A third Workforce Manager, HR Officer or Supervisor application role.
- Real-time work tracking.
- Time sheets.
- Deliverable management.
- Customer communication and messaging infrastructure.
- Full task execution or performance monitoring.

The system ends at the point where an Administrator makes and records an assignment decision.

An assignment record does not prove that the agent has completed the work.

---

# PART II — USERS AND PERMISSIONS

## 3. SYSTEM ROLES

VerifyMesh has two primary application roles:

1. Agent.
2. Administrator.

Do not introduce additional roles without explicit approval.

### 3.1 Agent

An Agent represents an independent worker or candidate who wants to demonstrate their competencies and apply for available tasks.

An Agent can:

- Register and authenticate.
- Verify their email address.
- Create and update their permitted professional profile information.
- Submit education and qualification information where supported.
- Submit work experience records.
- Upload supporting documents.
- Submit professional certification claims.
- View verification statuses.
- Browse the published competency assessment catalogue.
- Voluntarily take available assessments.
- View their assessment attempts and results.
- Retake assessments where permitted.
- Browse available tasks.
- View task requirements.
- See which requirements they satisfy.
- Identify missing or incomplete requirements.
- Complete additional assessments when required by a task.
- Reuse valid assessment results where compatible.
- Apply for eligible tasks.
- Track application statuses.
- View tasks assigned to them.

An Agent must not be able to:

- Verify their own experience.
- Approve their own certifications.
- Change an assessment score.
- Change an assessment pass/fail status.
- Modify a model prediction.
- Override an eligibility decision.
- Modify a task's requirements.
- Publish or close tasks.
- View another agent's private profile, evidence, assessment results or applications.
- Access administrator functionality by manipulating frontend URLs or API requests.
- Mark an application as shortlisted or assigned.
- Treat an application submission as a confirmed assignment.

### 3.2 Administrator

The Administrator manages the system's verification, competency assessment configuration, task requirements and applicant-selection process.

An Administrator can:

- Authenticate through the protected administrator access flow.
- View the administrative dashboard.
- View agent profiles.
- Review experience claims and supporting evidence.
- Verify, reject or request corrections to submitted experience.
- Review certifications and qualification documents.
- Verify, reject or request corrections to submitted credentials.
- Manage the competency assessment catalogue where supported.
- Create and manage assessment topics and question banks where supported.
- Configure assessment validity and attempt policies.
- Review assessment results.
- Create and manage tasks.
- Select competencies required for a task.
- Configure required assessment topics and minimum pass marks.
- Configure mandatory certification requirements.
- Configure minimum relevant experience.
- Publish, close or cancel tasks according to the supported state model.
- Review task-specific eligibility results.
- Review submitted applications.
- Inspect the evidence supporting each applicant's eligibility.
- View the experimental ML suitability output where available.
- Shortlist or reject applicants where supported.
- Assign an eligible applicant to a task.
- Review audit information.

An Administrator must not be able to silently bypass mandatory eligibility requirements.

For the MVP, the Administrator cannot simply use a high ML score or manually change an agent's status to eligible when a mandatory requirement has failed.

If an exceptional override policy is ever required, it must be explicitly approved, documented, authorised and auditable. It must not be introduced as an undocumented shortcut.

---

# PART III — CORE SYSTEM CONCEPTS

## 4. IMPORTANT DISTINCTIONS

The following concepts must remain separate throughout the application.

### 4.1 Profile information

Profile information consists of information submitted by an Agent.

Examples:

- Name and contact information.
- Education.
- Skills.
- Work history.
- Areas of interest.
- Professional qualifications.

Information submitted by an Agent is not automatically verified.

### 4.2 Verification

Verification is the administrative review of submitted evidence.

For example, an Agent may claim to have six months of sales experience.

That claim does not become verified experience until the required review process is completed.

Use the repository's existing status conventions where appropriate. The intended statuses include:

- `Pending`
- `Verified`
- `Rejected`
- `Changes Requested`
- `Expired`, where applicable

Verification must be persisted and auditable.

### 4.3 Professional certification

A professional certification is a qualification issued by an external organisation or institution.

Examples include an industry certification or professional training certificate.

An internally administered VerifyMesh assessment must not automatically be represented as an externally issued professional certification.

These are separate forms of evidence.

### 4.4 Competency assessment

A competency assessment is an internally administered, server-graded evaluation designed to establish whether an Agent has demonstrated knowledge or competency in a particular subject.

Examples:

- Product Knowledge.
- Sales Techniques.
- Customer Communication.
- CRM Skills.

Passing an internal assessment creates an internal competency result.

It does not automatically award an external professional certification.

### 4.5 Assessment topic

An assessment topic is a reusable competency category in the assessment catalogue.

For example:

`Product Knowledge`

A topic may contain a question bank, assessment instructions, scoring configuration and validity policy.

Multiple tasks may reference the same topic.

### 4.6 Assessment attempt

An assessment attempt is one specific instance in which an Agent takes an assessment.

It records the questions presented, submitted answers, score, outcome, timestamp and relevant metadata.

### 4.7 Assessment result

An assessment result is the officially recorded outcome of an assessment attempt.

It must be generated by the backend, not supplied by the frontend.

### 4.8 Task requirement

A task requirement is a condition configured by an Administrator for a particular task.

Examples:

- A specific verified certification.
- Six months of relevant verified experience.
- Product Knowledge assessment at 70%.
- Customer Communication assessment at 75%.

### 4.9 Eligibility

Eligibility is the deterministic decision that establishes whether an Agent meets all mandatory requirements for a particular task.

Eligibility is not the same as an ML prediction.

### 4.10 ML suitability prediction

The ML component estimates task-specific suitability using the features supported by the actual trained model.

It is an experimental decision-support signal.

It is not proof of real-world performance, qualification validity or eligibility.

### 4.11 Application

An application is the Agent's request to be considered for a particular task.

It does not mean that the Agent has been selected.

### 4.12 Assignment

An assignment is an explicit administrative decision that links an eligible Agent to a task.

Only a successfully persisted assignment should be represented as confirmed.

---

# PART IV — END-TO-END BUSINESS WORKFLOW

## 5. OVERALL SYSTEM WORKFLOW

The intended workflow is:

1. Administrator configures the competency assessment catalogue and manages available assessment topics.
2. Administrator creates tasks and defines the requirements for each task.
3. Agent registers and verifies their email.
4. Agent creates a professional profile.
5. Agent submits qualifications, certifications and work experience.
6. Administrator reviews submitted evidence.
7. Agent browses the competency assessment catalogue.
8. Agent voluntarily completes assessments for competencies they want to demonstrate.
9. VerifyMesh records the Agent's server-graded assessment results.
10. Agent browses published tasks.
11. VerifyMesh displays the requirements for each task.
12. VerifyMesh checks whether existing assessment results and verified evidence satisfy those requirements.
13. Agent completes missing or insufficient assessments where necessary.
14. VerifyMesh evaluates all mandatory eligibility requirements.
15. If eligible, the Agent can submit an application.
16. The backend rechecks eligibility when the application is submitted.
17. Administrator reviews applicants and their supporting evidence.
18. Administrator considers the experimental ML suitability output where available.
19. Administrator makes the final selection and assignment decision.
20. Agent sees the persisted application or assignment outcome.

The Agent does not need to complete every assessment before browsing tasks.

The Agent may browse tasks before becoming eligible.

However, applying must be restricted by the task's mandatory requirements.

---

# PART V — AGENT FUNCTIONAL REQUIREMENTS

## 6. REGISTRATION AND AUTHENTICATION

### 6.1 Registration

The Agent opens the registration page and provides the required registration information.

The backend must:

- Validate submitted information.
- Check for duplicate accounts.
- Hash passwords securely where password authentication is used.
- Create the account using the existing authentication architecture.
- Trigger the configured email verification process.
- Return an accurate response.

### 6.2 Email verification

The configured email verification mechanism must:

- Generate a secure verification code or link.
- Enforce expiry.
- Prevent token reuse.
- Limit repeated requests and attempts.
- Avoid exposing secrets in logs or responses.

The Agent must not be treated as successfully verified if verification fails.

Do not introduce a new authentication provider without approval.

---

## 7. PROFESSIONAL PROFILE MANAGEMENT

After registration, the Agent completes their professional profile.

Profile fields should use the existing schema and may include:

- Personal and contact information.
- Education and qualifications.
- Skills and areas of interest.
- Professional experience.
- Certifications.
- Supporting documents.

Rules:

1. Agents may edit only their permitted information.
2. The backend must identify the Agent using the authenticated session or token.
3. Submitted information must be distinguished from verified information.
4. An Agent must not be able to approve their own evidence.
5. Missing profile fields must not be filled with invented information.
6. Do not collect unnecessary personal information.

The profile should communicate which information is complete, pending review or requires correction.

---

## 8. WORK EXPERIENCE SUBMISSION AND VERIFICATION

### 8.1 Agent submission

The Agent submits work experience information using the existing experience-management workflow.

Where supported, an experience entry may include:

- Organisation or work context.
- Role or position.
- Work category.
- Relevant skills.
- Start date.
- End date or current employment indicator.
- Description of responsibilities.
- Supporting documents or evidence.

### 8.2 Verification

New experience records remain pending until reviewed.

The Administrator can:

- Verify the record.
- Reject it with a reason.
- Request corrections.

The system must record the review decision and reviewer information where supported.

### 8.3 Experience calculation

Only verified experience contributes to eligibility calculations.

Experience must be calculated carefully.

**Overlapping periods must not be double-counted.**

Example:

- Job A: January to June.
- Job B: March to August.

These records represent eight months of elapsed calendar time, not twelve months.

For task-specific experience:

1. Identify verified experience records.
2. Filter records relevant to the task category or configured competency.
3. Merge overlapping date intervals.
4. Calculate the union of the relevant intervals.
5. Compare the result with the task's minimum experience requirement.

Overall experience and category-specific experience must remain distinguishable.

Do not add overlapping sales, customer service and general experience periods together in a way that inflates total experience.

Define the handling of current employment, date boundaries and incomplete records consistently.

---

## 9. CERTIFICATION AND QUALIFICATION SUBMISSION

### 9.1 Agent submission

An Agent may submit a certification or qualification claim.

Where supported, information includes:

- Credential name.
- Issuing organisation.
- Credential identifier.
- Issue date.
- Expiry date.
- Supporting document.

### 9.2 Administrative verification

The Administrator reviews the submission and records a decision:

- Verified.
- Rejected.
- Changes Requested.

A submitted credential is not automatically valid.

### 9.3 Eligibility rules

When a task requires a certification:

1. Identify the exact required certification.
2. Locate an individually matching Agent credential.
3. Confirm that it is verified.
4. Confirm that it has not expired where expiry applies.
5. Use that credential as evidence for the requirement.

A generic certification count is not sufficient to establish that the Agent possesses a particular required credential.

Do not claim authoritative external issuer verification unless an actual integration exists. Administrator review is a human evidence-review process.

---

# PART VI — COMPETENCY ASSESSMENT SYSTEM

## 10. ASSESSMENT SYSTEM OVERVIEW

The assessment system is a central part of VerifyMesh.

It must be independent of task creation while remaining fully integrated with task eligibility.

**The assessment catalogue defines what Agents can demonstrate. Tasks define which competencies they require.**

The system must support two related concepts:

1. General competency assessments available in the assessment catalogue.
2. Task-specific assessment requirements configured by the Administrator.

These are not two separate assessment engines.

They should use the same underlying assessment topics, question banks, attempts and result records wherever technically appropriate.

### 10.1 General competency assessment catalogue

The assessment catalogue is an independent collection of competency assessments available to Agents.

Agents may browse the catalogue and voluntarily complete assessments even when they have not applied for a task.

Illustrative catalogue topics:

| Assessment topic | Competency demonstrated |
|---|---|
| Product Knowledge | Understanding products, features, benefits and specifications |
| Sales Techniques | Persuasion, negotiation and objection handling |
| Customer Communication | Professional communication and customer handling |
| CRM Skills | Customer records and relationship management |
| Customer Service | Customer support, issue resolution and service standards |

These are illustrative topics. The actual published catalogue must be based on the assessment topics and question banks configured in the system.

### 10.2 Voluntary assessment participation

An Agent can:

1. Open the Assessments section.
2. Browse available assessment topics.
3. View the assessment description and instructions.
4. See relevant information such as question count, pass mark, time limit and attempt policy where configured.
5. Select an assessment.
6. Start an attempt.
7. Answer the questions.
8. Submit answers.
9. Receive a server-generated result.
10. View the result in their competency or assessment history.

An Agent must not be forced to complete every catalogue assessment.

They should be able to choose which competencies they want to demonstrate.

### 10.3 Published and unpublished assessments

Where the system supports assessment administration, the Administrator should be able to control whether an assessment topic is available to Agents.

Intended states include:

- Draft: being configured and unavailable to Agents.
- Published/Available: Agents may take it.
- Archived/Inactive: unavailable for new attempts, while historical results remain accessible.

Do not create duplicate assessment statuses if the repository already has an equivalent state model.

Historical assessment results must not be deleted simply because a topic is archived.

### 10.4 Assessment topics and question banks

Each assessment topic should have an associated question bank.

A question bank contains questions relevant to that competency.

Each question should have, as appropriate:

- Question text.
- Answer options.
- Correct answer or scoring rubric.
- Marks or points.
- Competency/topic association.
- Difficulty level where supported.
- Active/inactive status.
- Version information where supported.

For objective multiple-choice questions, the correct answer must remain on the backend.

The frontend must receive only the question and permitted answer options.

Never expose correct answers through:

- API responses.
- Frontend source code.
- Browser storage.
- Client-side scoring logic.
- Hidden HTML fields.

### 10.5 Assessment attempt workflow

The assessment workflow must follow this process:

1. Agent selects an available assessment.
2. Frontend requests a new assessment attempt.
3. Backend validates that the assessment is published and the Agent is allowed to attempt it.
4. Backend creates or authorises the attempt.
5. Backend selects the questions according to the configured question-selection policy.
6. Backend returns questions and answer options without answer keys.
7. Agent answers the questions.
8. Agent submits answer identifiers only.
9. Backend validates the attempt and submitted answers.
10. Backend calculates the score.
11. Backend determines whether the attempt meets the applicable pass threshold.
12. Backend persists the result and attempt metadata.
13. Agent receives the recorded result.
14. The result becomes available for future task eligibility evaluation if it satisfies the relevant validity and compatibility rules.

The browser must never submit an authoritative score, pass/fail status or competency classification.

### 10.6 Server-side grading

The backend is authoritative for:

- Question selection.
- Correct answers.
- Scoring.
- Pass thresholds.
- Attempt validation.
- Attempt timing where applicable.
- Attempt limits.
- Cooldown rules.
- Final assessment outcome.
- Result persistence.

The client sends answer IDs or another approved answer representation.

The backend independently calculates the score.

Invalid, missing, duplicate or tampered answer identifiers must be handled safely.

A client-supplied `score`, `passed=true`, competency label or result status must never be accepted as authoritative.

### 10.7 Assessment scoring

Scoring must use the actual configured question marks and scoring rules.

Where percentage scoring is appropriate:

`Score = (Marks Earned / Total Available Marks) × 100`

The score must be within the valid range.

If different questions have different marks, use their actual marks rather than assuming equal weighting.

Any competency-specific scoring or weighting must be documented and applied consistently.

Do not introduce arbitrary score defaults.

For example, if an Agent has not completed Customer Communication, VerifyMesh must not substitute 75% or another pass-like value.

Missing evidence remains missing.

### 10.8 Assessment result states

The system should distinguish:

- Not Attempted.
- In Progress.
- Passed.
- Failed.
- Expired.
- Invalid, where applicable.

Use existing repository conventions if they already represent these states correctly.

A failed assessment is not a missing assessment.

An expired result is not a currently valid pass.

An incomplete attempt is not a pass.

### 10.9 Attempt limits and retakes

The system should support configurable attempt policies where implemented.

Possible policies include:

- Maximum attempts.
- Waiting period between attempts.
- Retake availability after failure.
- Assessment-specific cooldown periods.

The backend must enforce configured policies.

A failed assessment should not permanently lock an Agent out unless an explicitly approved policy requires it.

Do not invent arbitrary attempt limits.

If attempt policy is not configured, do not silently impose a different rule in the frontend.

### 10.10 Question randomisation

Where supported, questions should be selected or presented using a server-controlled randomisation policy.

The purpose is to reduce straightforward answer sharing and repeated exposure to the same questions.

The question-selection process must still preserve the assessment's intended competency coverage and scoring rules.

Do not randomise questions in a way that produces invalid or inconsistent scoring.

---

## 11. ASSESSMENT RESULT REUSE

This is one of the most important requirements of the VerifyMesh assessment architecture.

**A previously passed assessment should be reusable across multiple tasks when its topic, validity, version and score satisfy the new task's requirements.**

An Agent must not have to repeat the same assessment simply because they are applying for a different task.

### 11.1 Example of assessment reuse

An Agent completes:

`Product Knowledge`

Recorded result:

- Score: 85%.
- Outcome: Passed.
- Topic: Product Knowledge.
- Result status: Valid.

The Agent later views a task requiring Product Knowledge at 70%.

VerifyMesh should reuse the existing 85% result.

The Agent does not need to retake the assessment.

The Agent then views another task requiring Product Knowledge at 90%.

The existing 85% result does not meet the new threshold.

The Agent must complete an appropriate new assessment attempt or another approved assessment pathway.

### 11.2 Conditions for reuse

A previous assessment result may be reused only when all applicable conditions are satisfied:

1. The result belongs to the authenticated Agent.
2. The assessment topic matches the task requirement.
3. The result was officially graded and persisted by the backend.
4. The result is valid and has not expired.
5. The assessment version is accepted for the task.
6. The recorded score meets the task's configured minimum pass mark.
7. The result has not been invalidated or revoked.
8. Any additional compatibility conditions explicitly configured by the system are satisfied.

Do not reuse an assessment simply because its name appears similar.

The system should use stable topic identifiers and approved compatibility mappings where necessary.

### 11.3 Assessment validity periods

Assessment topics should support configurable validity periods where this functionality is implemented.

Examples:

- A competency may remain valid for twelve months.
- Another competency may remain valid for twenty-four months.
- Some topics may have no expiry period.

These are illustrative examples, not fixed global values.

The Administrator should be able to configure the validity policy for a topic where supported.

When a result expires:

- Preserve the historical result.
- Mark it expired for current eligibility purposes.
- Do not delete the attempt.
- Require a new valid result when a task requires that competency.

### 11.4 Assessment version compatibility

A result from an older assessment version should not automatically be accepted for every newer version.

The system should determine whether the old version is still accepted for the relevant task requirement.

If a topic has been materially revised, the Administrator may decide that earlier results are no longer compatible.

Do not automatically invalidate all historical results whenever a question is edited.

Where possible, preserve assessment version information so eligibility decisions can be traced to the exact result and assessment configuration used.

### 11.5 Multiple attempts and result selection

The system must define one consistent policy for choosing the assessment result used in eligibility evaluation.

Possible approaches include:

- Latest valid attempt.
- Best valid attempt.
- Latest passed attempt.

The policy must be explicit and consistent across the API, database queries and frontend.

Do not use one policy in the Agent dashboard and a different policy in the eligibility engine.

If a new attempt is in progress, do not automatically invalidate a previously valid result unless the configured policy requires it.

The selected result must be traceable.

### 11.6 Assessment history

Agents should be able to view their assessment history, including:

- Assessment topic.
- Attempt date.
- Score.
- Outcome.
- Validity status.
- Attempt number where supported.
- Retake availability where applicable.

Historical results should remain available even after a result expires.

---

## 12. TASK-SPECIFIC ASSESSMENT REQUIREMENTS

### 12.1 Administrator-defined requirements

When creating a task, the Administrator determines which competency assessments are mandatory for that task.

For example:

**Task:** Sales Support Agent

Required assessment topics:

| Topic | Minimum score | Mandatory |
|---|---:|---|
| Product Knowledge | 70% | Yes |
| Customer Communication | 70% | Yes |
| Sales Techniques | 65% | Yes |

The Administrator is selecting existing assessment topics from the catalogue.

The task should reference those topics and their required pass marks.

It should not create a completely separate question bank for every task.

### 12.2 Shared assessment catalogue

A single Product Knowledge topic may be referenced by:

- Sales Support Agent.
- Retail Sales Assistant.
- Product Support Representative.

Each task may specify a different minimum score.

This avoids duplicating the same questions and assessment logic across multiple tasks.

### 12.3 Additional task-specific assessments

Some tasks may require competencies that the Agent has not previously demonstrated.

When the Agent opens the task, VerifyMesh identifies the missing or insufficient assessment requirements.

The Agent can then complete the required assessment.

Where the system supports genuinely role-specific assessments, these should still use the same underlying assessment framework and must have a clearly defined topic or competency association.

Do not create an unrelated second assessment engine for task-specific testing.

### 12.4 Task requirement evaluation example

Assume the Agent has the following results:

| Assessment | Agent's result | Task requirement | Outcome |
|---|---:|---:|---|
| Product Knowledge | 85% | 70% | Satisfied |
| Customer Communication | Not attempted | 70% | Incomplete |
| Sales Techniques | 72% | 65% | Satisfied |

VerifyMesh must:

- Reuse Product Knowledge.
- Identify Customer Communication as missing.
- Reuse Sales Techniques.
- Explain that the Agent must complete Customer Communication.
- Recalculate eligibility after the new result is recorded.

The Agent should not be forced to repeat the assessments already satisfied.

### 12.5 No automatic pass

A task requirement is satisfied only when an appropriate, valid and officially recorded assessment result meets the configured threshold.

Missing results, pending attempts, failed results and expired results must never be converted into passes.

---

# PART VII — TASK MANAGEMENT AND DISCOVERY

## 13. TASK CREATION AND CONFIGURATION

The Administrator creates tasks that represent available work opportunities.

A task should use existing database fields and may contain:

- Task title.
- Description.
- Category or work type.
- Required skills or competencies.
- Minimum relevant experience.
- Required professional certifications.
- Required assessment topics.
- Minimum score for each required assessment.
- Opening and closing dates where supported.
- Task status.
- Other explicitly supported mandatory requirements.

### 13.1 Required task configuration

When creating a task, the Administrator should be able to:

1. Enter the task details.
2. Select the task category.
3. Define the minimum relevant experience, if required.
4. Select required professional certifications, if any.
5. Select required assessment topics from the assessment catalogue.
6. Set the minimum score for each required topic.
7. Identify which requirements are mandatory.
8. Save the task as a draft.
9. Publish the task when its requirements are valid.

A task with no certification requirement must not accidentally become certification-dependent.

A task with no assessment requirement must not accidentally require an assessment.

Only requirements explicitly configured for the task should be evaluated.

### 13.2 Task validation

The backend must validate:

- Required fields.
- Non-negative experience requirements.
- Valid assessment topic references.
- Valid certification references.
- Valid score thresholds.
- Consistent task states.
- Valid dates where configured.
- Mandatory versus informational requirements.

Do not publish a task with invalid or contradictory requirements.

### 13.3 Task states

The intended task states are:

- `Draft`
- `Open`
- `Closed`
- `Filled`
- `Cancelled`

Map these to existing repository statuses where possible.

Do not create duplicate state systems.

Meaning:

- Draft: visible to administrators only.
- Open: published and accepting applications.
- Closed: no longer accepting applications.
- Filled: assigned, where supported.
- Cancelled: withdrawn by the Administrator, where supported.

---

## 14. AGENT TASK DISCOVERY

Agents should be able to browse tasks that are published and available.

Each task listing should show information available from the actual database, such as:

- Task title.
- Description.
- Category.
- Relevant competencies.
- Required certifications.
- Minimum experience.
- Required assessment topics and pass marks.
- Application deadline, if configured.
- Task status.
- Agent-specific application status.

Do not invent salary, employer identity, number of openings or other information that is not stored.

Agents may view task details before they satisfy the requirements.

However, private information about other applicants must remain inaccessible.

---

## 15. TASK DETAILS AND REQUIREMENT BREAKDOWN

When an Agent opens a task, VerifyMesh should display the task requirements and the Agent's current status against each requirement.

The page should clearly distinguish:

- Requirements already satisfied.
- Requirements awaiting verification.
- Requirements not yet attempted.
- Requirements failed.
- Requirements expired.
- Requirements that need a higher assessment score.

Example:

**Sales Support Agent**

| Requirement | Agent's evidence | Status |
|---|---|---|
| Verified sales certification | Verified and current | Satisfied |
| Relevant experience | 8 verified months; 6 required | Satisfied |
| Product Knowledge | 85%; 70% required | Satisfied |
| Customer Communication | Not attempted | Incomplete |
| Sales Techniques | 72%; 65% required | Satisfied |

The page should explain the next action required.

For example:

"Complete the Customer Communication assessment to satisfy this task's assessment requirements."

If an existing assessment result is reusable, display it as satisfied.

Do not ask the Agent to repeat a compatible valid result.

---

# PART VIII — DETERMINISTIC ELIGIBILITY ENGINE

## 16. ELIGIBILITY PRINCIPLE

Eligibility is determined by explicit, explainable business rules.

**The deterministic eligibility engine is the authority for whether an Agent can apply for a task.**

The ML model is not the eligibility engine.

The model must never replace or override mandatory requirements.

### 16.1 Mandatory eligibility checks

For each Agent–Task pair, evaluate the requirements actually configured for that task.

Typical checks:

1. Task availability.
2. Agent authentication and account eligibility.
3. Required verified certifications.
4. Required competency assessments.
5. Minimum verified relevant experience.
6. Other explicitly configured mandatory requirements.

### 16.2 Task availability

The task must be open and accepting applications.

A task that is Draft, Closed, Filled or Cancelled must not accept new applications.

If a deadline is configured, it must not have passed.

### 16.3 Certification requirement

Every required certification must be individually matched to a verified and current credential record.

A pending or expired credential does not satisfy a requirement that demands a current verified credential.

### 16.4 Assessment requirement

Every required assessment topic must have an accepted result.

For each requirement:

1. Identify the correct assessment topic.
2. Retrieve the Agent's valid result.
3. Confirm result compatibility.
4. Apply the task's required threshold.
5. Record whether the requirement is satisfied.

A missing assessment result is incomplete evidence.

A failed assessment is a failed requirement.

An expired result must not satisfy a requirement that demands a current result.

### 16.5 Relevant experience requirement

Use only verified experience.

Filter by task relevance.

Merge overlapping date intervals.

Compare the resulting relevant experience against the minimum requirement.

Do not double-count.

### 16.6 Other mandatory requirements

Evaluate only requirements that are explicitly stored and supported by the backend.

Do not invent additional eligibility rules.

### 16.7 Eligibility outcomes

The system should distinguish the following outcomes:

**Eligible**

All mandatory requirements are satisfied.

**Incomplete**

The Agent has not completed one or more required steps, such as an assessment.

**Pending Review**

Required evidence has been submitted but has not yet been reviewed.

**Not Eligible**

One or more known mandatory requirements have failed.

**Unavailable / Evaluation Error**

The system cannot safely evaluate eligibility because a required data source or backend operation failed.

Use existing repository status conventions where appropriate, but preserve these distinctions in the underlying logic.

Do not label an Agent Eligible when a mandatory requirement is incomplete or pending.

### 16.8 Eligibility decision evidence

The system should be able to explain every decision.

For each Agent–Task evaluation, retain or reconstruct:

- Task identifier.
- Agent identifier.
- Requirement evaluated.
- Requirement outcome.
- Evidence record used.
- Assessment result used.
- Required threshold.
- Actual score where relevant.
- Experience calculation.
- Credential status.
- Evaluation timestamp.
- Reasons for any failure or pending state.

Use existing database structures where appropriate.

Do not introduce unnecessary duplicate eligibility tables without first inspecting the schema.

### 16.9 Eligibility recalculation

Recalculate eligibility when a relevant condition changes, including:

- Certification verified.
- Certification rejected.
- Certification expires.
- Experience verified.
- Experience rejected.
- Experience dates or category corrected.
- Assessment result recorded.
- Assessment result expires.
- Assessment result invalidated.
- Assessment version compatibility changes.
- Task requirement changes.
- Task status changes.

A previously eligible Agent may become ineligible if a required credential expires or a task requirement changes.

The backend must always recheck current eligibility when an application is submitted and before an assignment is confirmed.

---

# PART IX — MACHINE LEARNING COMPONENT

## 17. PURPOSE OF THE ML COMPONENT

VerifyMesh includes an experimental machine-learning component to provide an additional task-specific suitability signal.

The ML component is separate from:

- Professional credential verification.
- Assessment grading.
- Experience verification.
- Mandatory eligibility evaluation.
- Final administrator selection.

The intended ML evaluation unit is an Agent–Task pair.

The model is intended to provide supplementary information about how suitable an Agent's demonstrated profile may be for a particular task.

### 17.1 Correct decision architecture

The system must follow this sequence:

1. Retrieve the Agent's verified profile and evidence.
2. Retrieve the task requirements.
3. Evaluate mandatory eligibility using deterministic rules.
4. If mandatory requirements are not satisfied, preserve the relevant Incomplete, Pending Review or Not Eligible outcome.
5. If the Agent satisfies mandatory requirements and the model is available, construct the model's input using its verified feature contract.
6. Generate the task-specific ML output.
7. Present the ML output to the Administrator as supplementary decision support.
8. Allow the Administrator to review the evidence and make the final selection.

The ML model must not:

- Approve certifications.
- Verify work experience.
- Grade assessments.
- Change an assessment result.
- Override failed mandatory requirements.
- Automatically reject an otherwise eligible Agent.
- Automatically assign an Agent.
- Guarantee task success.
- Replace human review.

### 17.2 Current model artifacts

The current intended task-specific model artifacts are:

- `verifymesh_final_optimized_pipeline.joblib`
- `verifymesh_threshold_metadata.json`

The metadata file must be inspected before integration.

The actual pipeline and metadata are the authority for the model's input and inference contract.

Do not assume that an earlier model's feature list, preprocessing, class mapping or threshold remains valid.

### 17.3 Mandatory model inspection

Before integrating the model, inspect:

- Actual model file.
- Pipeline structure.
- Feature names.
- Feature order.
- Preprocessing steps.
- Expected data types.
- Missing-value handling.
- Target classes.
- Positive class definition.
- Probability output behaviour.
- Threshold metadata.
- Model training environment.
- Scikit-learn version.
- Dependency compatibility.
- Training and evaluation evidence.

The model must be loaded and tested using the actual supplied artifact.

Do not claim the model is integrated merely because the file exists in the repository.

### 17.4 Threshold handling

The current project owner has indicated that the optimized Random Forest model uses a threshold of 0.61.

This is a reported configuration, not permission to hardcode the value without verification.

Antigravity must:

1. Read the supplied threshold metadata.
2. Confirm the threshold value.
3. Confirm which class is treated as the positive class.
4. Confirm the correct probability column using the model's class labels.
5. Confirm whether the threshold is applied to `predict_proba` output.
6. Confirm the evaluation evidence supporting the chosen threshold.
7. Use the threshold consistently with the training and evaluation methodology.

Do not assume that a probability of 0.61 represents a calibrated 61% chance of real-world success.

Do not describe the output as a probability of successful task performance unless calibration and real-world outcome validation support that claim.

### 17.5 Model input features

The backend must construct the feature vector using the exact feature contract of the actual saved model.

Do not reuse an older feature list merely because it was used by a previous model.

Potential source information includes:

- Task characteristics.
- Task difficulty.
- Task minimum experience.
- Applicant's verified relevant experience.
- Relevant verified certifications.
- Server-generated assessment results.
- Competency-related profile information.
- Engineered task-agent comparison features.

However, only features explicitly supported by the actual model may be supplied.

For every feature:

1. Identify its authoritative source.
2. Confirm that the source is persisted.
3. Confirm the expected data type.
4. Apply the exact training transformation.
5. Preserve the required order.
6. Handle missing data according to the trained pipeline's documented contract.

Do not invent feature values.

Do not use unverified experience or client-supplied assessment scores.

Do not fabricate missing scores with arbitrary defaults.

If a required feature cannot be safely constructed, the model output should be unavailable for that evaluation.

### 17.6 Separation between eligibility and ML

A high model score cannot make an ineligible Agent eligible.

A low model score cannot silently make an otherwise eligible Agent ineligible.

For example:

- Agent satisfies all mandatory requirements.
- ML output indicates relatively low experimental suitability.
- Agent remains eligible to apply.
- Administrator reviews the evidence and model output before selecting an applicant.

This preserves the distinction between qualification and supplementary suitability.

### 17.7 Model failure

If model loading or inference fails:

- Deterministic eligibility must continue to work.
- Do not return a fabricated score.
- Do not block an otherwise valid application solely because the ML service is unavailable.
- Show the ML result as unavailable.
- Log the technical error safely.
- Preserve enough information for debugging.

### 17.8 Model limitations and synthetic data

The current task-specific model was developed using synthetic applicant-task data rather than a large collection of genuine historical work outcomes.

Therefore:

- Its evaluation metrics describe performance against the synthetic labels used in the experiment.
- They do not establish real-world task success prediction.
- Synthetic labels are not equivalent to independently observed employment outcomes.
- The model must be described as experimental.
- The system must not claim that its output is a validated probability of job success.

The Administrator must retain final decision authority.

### 17.9 Model metadata and reproducibility

Keep the model metadata JSON alongside the model artifact in the repository where appropriate.

It should document the verified model contract, such as:

- Model name and version.
- Training date.
- Dataset description.
- Target definition.
- Class mapping.
- Feature names and order.
- Preprocessing.
- Threshold.
- Evaluation methodology.
- Evaluation metrics.
- Python and library versions.
- Known limitations.

Do not silently modify the metadata to make it appear that the model achieved different results.

### 17.10 Legacy binary eligibility model

The previous binary eligibility classifier must not remain an active mandatory eligibility gate if the project has adopted the new architecture.

Before decommissioning it:

1. Search the entire repository for imports and references.
2. Inspect startup loading.
3. Inspect inference services.
4. Inspect API endpoints.
5. Inspect eligibility queries.
6. Inspect frontend labels and status logic.
7. Inspect model metadata and prediction persistence.
8. Identify any historical records that depend on it.

Remove active decision dependencies safely.

Preserve historical prediction records and audit information.

Do not delete historical database records merely because the old model is no longer used.

Archive the old artifact where appropriate after confirming that no active code depends on it.

### 17.11 ML output presentation

The Administrator interface should clearly identify the output as an experimental ML suitability signal.

Display relevant information where supported:

- Model suitability output.
- Model version.
- Evaluation status.
- Relevant feature or evidence context.
- Availability/error status.

Do not use misleading labels such as:

- Guaranteed success probability.
- Confirmed performance score.
- Verified competency.
- Automatic hiring recommendation.

The ML output is supplementary information, not a final decision.

---

# PART X — APPLICATION AND ADMINISTRATIVE SELECTION

## 18. APPLICATION SUBMISSION

An Agent can apply only when:

- The task is open.
- The task is accepting applications.
- Any configured deadline has not passed.
- The Agent is authenticated.
- All mandatory requirements are satisfied.
- The Agent does not already have an active application for the same task.

### 18.1 Backend validation

When an Agent submits an application:

1. Frontend submits the task identifier and necessary application information.
2. Backend derives the Agent identity from the authenticated session.
3. Backend retrieves the current task.
4. Backend confirms that the task is accepting applications.
5. Backend checks duplicate applications.
6. Backend recalculates mandatory eligibility using current persisted evidence.
7. Backend rejects the application if eligibility is incomplete or failed.
8. Backend persists the application if all checks pass.
9. Backend returns an accurate result.
10. Frontend displays the persisted application status.

Do not rely on a frontend button being disabled as the only eligibility control.

### 18.2 Duplicate applications

The backend must prevent duplicate active applications by the same Agent to the same task.

Use transaction-safe checks or suitable database constraints where appropriate.

Do not rely solely on hiding the Apply button.

### 18.3 Application statuses

The intended statuses are:

- `Submitted`
- `Shortlisted`
- `Assigned`
- `Rejected`
- `Withdrawn`, if supported

Map these to existing repository statuses.

Do not create duplicate status systems.

Every status must have a defined meaning and permitted transition.

An Agent cannot change their own application to Shortlisted or Assigned.

---

## 19. ADMINISTRATOR APPLICANT REVIEW

The Administrator should be able to inspect applicants for a particular task.

The review interface should show:

- Agent profile information relevant to the task.
- Verified work experience.
- Verified certifications.
- Required assessment results.
- Eligibility status.
- Reasons for any failed or pending requirement.
- Application status.
- Experimental ML suitability output where available.

The Administrator should be able to understand why the Agent is eligible.

Do not present a single unexplained percentage as the entire basis for a decision.

### 19.1 Shortlisting

Where supported, the Administrator may shortlist an application.

Shortlisting means the applicant has progressed to a further stage of consideration.

It does not mean the Agent has been assigned.

### 19.2 Rejection

Where supported, the Administrator may reject an application.

The reason should be recorded where the system supports it.

A rejected application must not be assigned through an unprotected API request.

### 19.3 Final assignment

Only the Administrator can make the final assignment decision.

Before assigning, the backend must recheck:

- The task is still assignable.
- The applicant has a valid application.
- The applicant still satisfies all mandatory requirements.
- Required credentials remain valid.
- Required assessment results remain valid.
- No conflicting assignment or capacity rule is violated, where such rules are implemented.

The backend must persist the assignment and associated application status.

Use a database transaction or equivalent consistency mechanism when multiple records must change together.

The Agent should then be able to see the confirmed assignment.

The system must not claim that work has been completed.

---

# PART XI — DATABASE AND TECHNICAL ARCHITECTURE

## 20. TECHNICAL ARCHITECTURE

The existing project technology baseline is:

**Frontend**
- React.
- Vite.
- Tailwind CSS.
- Existing routing and component architecture.

**Backend**
- Python.
- Flask.
- Existing route blueprints and service structure.

**Database**
- MySQL.

**Machine Learning**
- Python.
- Scikit-learn pipeline.
- Joblib model artifact.
- JSON model metadata.

Antigravity must inspect the current implementation before changing any architectural component.

Do not replace the technology stack without explicit approval.

### 20.1 Frontend responsibilities

The frontend is responsible for:

- Displaying information.
- Collecting user input.
- Presenting assessment questions.
- Sending answer identifiers.
- Displaying backend-generated results.
- Showing task requirements.
- Presenting eligibility explanations.
- Submitting applications.
- Displaying administrative review information.

The frontend must not be authoritative for:

- Assessment scoring.
- Credential verification.
- Experience verification.
- Eligibility decisions.
- ML feature construction.
- Application authorisation.
- Assignment decisions.

### 20.2 Backend responsibilities

The backend is responsible for:

- Authentication and authorisation.
- Input validation.
- Profile persistence.
- Evidence review.
- Assessment attempt creation.
- Question selection.
- Assessment grading.
- Assessment result persistence.
- Assessment validity.
- Result reuse.
- Task requirement retrieval.
- Experience calculation.
- Certification checks.
- Eligibility evaluation.
- ML inference.
- Application validation and persistence.
- Assignment validation and persistence.
- Audit logging.

### 20.3 Database responsibilities

MySQL is the authoritative persistence layer for important system records.

The database must preserve:

- Agent accounts.
- Profiles.
- Experience records.
- Certifications.
- Verification decisions.
- Assessment topics.
- Assessment questions.
- Assessment attempts.
- Assessment results.
- Assessment version information where supported.
- Task records.
- Task assessment requirements.
- Task certification requirements.
- Applications.
- Assignments.
- ML prediction metadata and records where appropriate.
- Audit events.

These are logical data concepts, not instructions to create duplicate tables.

Antigravity must inspect the existing schema and migrations before introducing or modifying database structures.

### 20.4 Database relationship principles

The intended logical relationships are:

**Agent and evidence**
- One Agent may have multiple experience records.
- One Agent may have multiple certification records.
- Each evidence record may have a verification status and review history.

**Assessment catalogue**
- One assessment topic may contain multiple questions.
- One Agent may have multiple attempts.
- Each attempt belongs to one Agent and one assessment topic/version.
- An attempt produces a server-generated result.

**Task requirements**
- One task may reference multiple assessment topics.
- One assessment topic may be referenced by multiple tasks.
- Each task-topic relationship stores the applicable minimum score and other requirement configuration.
- One task may reference multiple required certifications.

**Applications**
- One Agent may apply to multiple tasks.
- One task may receive applications from multiple Agents.
- Each application belongs to one Agent and one task.

**ML**
- One model prediction should relate to the relevant Agent–Task pair.
- The model version and prediction timestamp should be recorded where supported.

The implementation must use the actual repository schema and avoid creating unnecessary duplicate structures.

---

# PART XII — ASSESSMENT AND TASK DATA INTEGRITY

## 21. CRITICAL ASSESSMENT DATA RULES

Antigravity must pay particular attention to the following:

1. Assessment topics must be independent of individual tasks.
2. Tasks must reference existing assessment topics.
3. Task-specific pass marks must be stored and retrieved correctly.
4. Agent assessment attempts must belong to the correct Agent.
5. Assessment results must belong to the correct topic and version.
6. A result must not be reused across unrelated topics.
7. A missing result must not be assigned a default score.
8. A pending attempt must not be treated as passed.
9. A failed result must not be treated as passed.
10. An expired result must not satisfy a current requirement.
11. The backend must choose the correct reusable result according to the configured attempt policy.
12. The backend must re-evaluate eligibility after a relevant result changes.
13. Task-specific assessments must not accidentally use another task's result or topic.
14. The frontend must not determine whether a result is reusable.
15. Every eligibility decision must be traceable to the evidence used.

### 21.1 Avoiding task-assessment linkage bugs

Verify that the complete relationship works:

`Task → Required Assessment Topic → Agent Assessment Result → Eligibility Evaluation`

Do not assume that storing a general `exam_id` on a task is sufficient if the intended design supports multiple required assessment topics.

Inspect existing task assessment relationships.

If a current route requires a topic identifier, ensure the frontend supplies the correct identifier and the backend validates it.

Do not invent a new route or database structure before examining the existing implementation.

---

# PART XIII — SECURITY AND ACCESS CONTROL

## 22. SECURITY REQUIREMENTS

### 22.1 Authentication

Use the existing secure authentication architecture.

Validate authentication tokens and sessions on the backend.

Do not trust user identity supplied in request bodies.

### 22.2 Role-based access control

Every protected endpoint must enforce the appropriate role.

Agent endpoints must also enforce ownership of private records.

An Agent must not gain administrator access by changing a URL, request parameter or frontend state.

### 22.3 Assessment security

- Correct answers remain server-side.
- Scores are calculated server-side.
- Pass/fail outcomes are generated server-side.
- Attempt limits are enforced server-side.
- Submitted answers are validated.
- An Agent cannot modify historical assessment results.
- An Agent cannot access another Agent's answers or results.

### 22.4 Evidence security

Where file uploads are implemented:

- Validate file type and size.
- Store files securely.
- Restrict access to authorised users.
- Do not trust client-supplied filesystem paths.
- Avoid exposing private evidence through public URLs.

### 22.5 Data persistence

Do not use silent in-memory fallbacks for important data.

If a database write fails, return an accurate error.

Do not display a success message when persistence has failed.

### 22.6 Secrets

- Do not commit passwords, API keys or production secrets.
- Do not use a predictable default SECRET_KEY.
- Load sensitive configuration from environment variables.
- Fail safely when required secrets are absent.
- Do not expose sensitive configuration in frontend bundles or logs.

### 22.7 Audit logging

Where supported, record:

- Verification decisions.
- Assessment result changes or invalidations.
- Task creation and publication.
- Task requirement changes.
- Application status changes.
- Assignment decisions.
- Important administrator actions.

Do not log passwords, OTP values, authentication tokens or secrets.

---

# PART XIV — USER INTERFACE REQUIREMENTS

## 23. AGENT INTERFACE

The Agent interface should provide clear access to:

1. Dashboard.
2. Professional profile.
3. Experience.
4. Certifications and qualifications.
5. Verification status.
6. Assessment catalogue.
7. Assessment attempts and results.
8. Available tasks.
9. Task details and eligibility breakdown.
10. My applications.
11. My assigned tasks.

### 23.1 Agent dashboard

The dashboard should display information based on actual persisted records.

Examples include:

- Profile completion.
- Pending verification items.
- Verified experience.
- Verified certifications.
- Completed assessments.
- Available assessments.
- Open tasks.
- Applications.
- Assignments.

Do not use hardcoded statistics.

### 23.2 Assessment catalogue interface

The catalogue should allow Agents to:

- Browse published assessment topics.
- View topic descriptions.
- View assessment instructions.
- View relevant attempt information.
- Identify whether they have a valid result.
- Start an assessment where permitted.
- View previous results.

The UI should distinguish between:

- Not attempted.
- In progress.
- Passed.
- Failed.
- Expired.

### 23.3 Task eligibility interface

For each task, show:

- Mandatory requirements.
- Existing evidence.
- Reused assessment results.
- Missing assessments.
- Insufficient scores.
- Pending verification.
- Overall eligibility status.
- Next action required.

The interface should make it clear that an Agent can be eligible for one task and ineligible for another.

### 23.4 Application interface

Agents should see:

- Task applied for.
- Submission date.
- Current application status.
- Any available decision information.
- Assignment status if selected.

Do not display an application as an assignment.

---

## 24. ADMINISTRATOR INTERFACE

The Administrator interface should provide access to:

1. Dashboard.
2. Agent management.
3. Experience verification.
4. Certification verification.
5. Assessment catalogue management where supported.
6. Assessment results.
7. Task creation and management.
8. Task requirements.
9. Applicant review.
10. Eligibility evidence.
11. ML suitability information.
12. Application management.
13. Assignment decisions.
14. Audit history where available.

### 24.1 Assessment administration

The Administrator should be able to manage the assessment catalogue and its configuration to the extent supported by the existing implementation.

Potential functions include:

- Create assessment topics.
- Edit topic descriptions.
- Manage question banks.
- Configure scoring.
- Configure pass marks for catalogue assessments.
- Configure validity periods.
- Configure attempt policies.
- Publish or archive topics.

Do not introduce unsupported administration features without first inspecting the existing application and agreeing on the required scope.

### 24.2 Task creation interface

The task creation interface should allow the Administrator to select existing assessment topics and configure their minimum scores.

The task creation interface must not generate duplicate question banks for every task.

### 24.3 Applicant review interface

The Administrator should see each applicant's eligibility evidence and, where available, the ML suitability output.

The interface must distinguish:

- Eligibility status.
- Assessment results.
- Verification status.
- ML suitability output.
- Application status.
- Final assignment decision.

These are separate concepts and must not be combined into one misleading score or badge.

---

# PART XV — ERROR HANDLING AND SYSTEM RELIABILITY

## 25. ERROR HANDLING

Every important action must produce a truthful outcome.

Examples:

- Registration successful.
- Email verification failed.
- Profile saved.
- Evidence submitted for review.
- Evidence verified.
- Evidence rejected.
- Assessment attempt started.
- Assessment submitted.
- Assessment result recorded.
- Assessment attempt rejected.
- Existing result reused.
- Assessment expired.
- Eligibility requirements satisfied.
- Eligibility incomplete.
- Application submitted.
- Application blocked with reasons.
- Assignment recorded.
- Model unavailable.
- Database operation failed.

Distinguish between:

- No records found.
- Request still loading.
- Request failed.
- Evidence pending.
- Evidence incomplete.
- Access denied.

Do not silently convert backend errors into empty lists, zero scores or successful outcomes.

---

# PART XVI — TESTING AND ACCEPTANCE CRITERIA

## 26. AUTHENTICATION AND ACCESS TESTS

- [ ] Agent can register.
- [ ] Duplicate registration is rejected.
- [ ] Email verification works through the configured mechanism.
- [ ] Expired verification tokens are rejected.
- [ ] Reused tokens are rejected.
- [ ] Unauthorised users cannot access administrator endpoints.
- [ ] Agents cannot access another Agent's private information.
- [ ] Authentication survives normal navigation and reload.

## 27. PROFILE AND EVIDENCE TESTS

- [ ] Agent can submit experience records.
- [ ] Agent can submit certification records.
- [ ] New evidence remains pending until reviewed.
- [ ] Administrator can verify evidence.
- [ ] Administrator can reject evidence with a reason where supported.
- [ ] Administrator can request corrections where supported.
- [ ] Only verified experience contributes to eligibility.
- [ ] Overlapping periods are not double-counted.
- [ ] Expired credentials do not satisfy current credential requirements.

## 28. ASSESSMENT CATALOGUE TESTS

- [ ] Agent can browse published assessment topics.
- [ ] Unpublished or archived topics are not incorrectly available for new attempts.
- [ ] Agent can voluntarily start an available assessment.
- [ ] Backend authorises and records the attempt.
- [ ] Questions are served without answer keys.
- [ ] Agent can submit answer identifiers.
- [ ] Backend grades answers.
- [ ] Client-supplied scores are ignored or rejected.
- [ ] Client-supplied pass statuses are ignored or rejected.
- [ ] Invalid answer identifiers are rejected.
- [ ] Results are persisted.
- [ ] Results remain available after refresh and re-login.
- [ ] Attempt limits are enforced where configured.
- [ ] Retake rules are enforced where configured.
- [ ] Missing answers are handled consistently.
- [ ] Historical attempts remain accessible.

## 29. ASSESSMENT REUSE TESTS

- [ ] A valid passed result can be reused by another task with the same compatible topic.
- [ ] A result meeting a lower task threshold is reused without retaking.
- [ ] A result below a higher task threshold is not accepted.
- [ ] An expired result is not reused.
- [ ] An invalidated result is not reused.
- [ ] An incompatible assessment version is not reused.
- [ ] Results from unrelated topics are not reused.
- [ ] The result belongs to the correct Agent.
- [ ] The configured attempt-selection policy is applied consistently.
- [ ] A missing result is never replaced by a default score.

## 30. TASK CONFIGURATION TESTS

- [ ] Administrator can create a valid task.
- [ ] Administrator can select existing assessment topics.
- [ ] Administrator can configure pass marks.
- [ ] Invalid assessment topic references are rejected.
- [ ] Invalid score thresholds are rejected.
- [ ] Certification requirements are optional unless configured.
- [ ] Assessment requirements are optional unless configured.
- [ ] Draft tasks are not available for application.
- [ ] Closed tasks do not accept applications.
- [ ] Filled and cancelled tasks do not accept applications.

## 31. ELIGIBILITY TESTS

- [ ] Eligibility is calculated for an Agent–Task pair.
- [ ] Required certifications are checked individually.
- [ ] Expired credentials fail current credential requirements.
- [ ] Required assessment topics are checked individually.
- [ ] Existing compatible results are reused.
- [ ] Missing assessments are identified.
- [ ] Failed assessments are identified.
- [ ] Insufficient scores are identified.
- [ ] Verified relevant experience is calculated correctly.
- [ ] Overlapping experience periods are not double-counted.
- [ ] Pending evidence produces a pending outcome.
- [ ] Failed mandatory requirements produce a not-eligible outcome.
- [ ] Satisfied mandatory requirements produce an eligible outcome.
- [ ] Every failure or pending outcome has an understandable reason.
- [ ] Eligibility recalculates when evidence or task requirements change.

## 32. ML TESTS

- [ ] The correct final optimized model artifact is loaded.
- [ ] The metadata JSON is inspected and used as appropriate.
- [ ] Feature names and order match the actual pipeline.
- [ ] Preprocessing matches the training pipeline.
- [ ] The correct positive class is identified.
- [ ] The configured threshold is read and validated.
- [ ] The threshold is applied to the correct probability column where applicable.
- [ ] Missing required features do not produce fabricated values.
- [ ] Invalid model input is handled safely.
- [ ] Model failure does not break deterministic eligibility.
- [ ] ML output does not override mandatory eligibility.
- [ ] ML output does not automatically assign or reject an Agent.
- [ ] The model version is recorded where supported.
- [ ] Synthetic-data limitations are communicated accurately.

## 33. APPLICATION AND ASSIGNMENT TESTS

- [ ] Eligible Agent can apply to an open task.
- [ ] Ineligible Agent is blocked with a clear reason.
- [ ] Incomplete Agent cannot bypass mandatory requirements.
- [ ] Closed task rejects applications.
- [ ] Duplicate active applications are prevented.
- [ ] Application is persisted.
- [ ] Application status is visible after refresh.
- [ ] Only Administrator can shortlist or reject.
- [ ] Only Administrator can assign.
- [ ] Assignment rechecks eligibility.
- [ ] Assignment rechecks task status.
- [ ] Assignment is persisted.
- [ ] Agent sees the confirmed assignment.
- [ ] Application and assignment statuses cannot be forged through frontend requests.

## 34. SECURITY AND PERSISTENCE TESTS

- [ ] Important records persist in MySQL.
- [ ] Database failures are reported accurately.
- [ ] No silent in-memory fallback is used for important records.
- [ ] Agent ownership is enforced server-side.
- [ ] Administrator permissions are enforced server-side.
- [ ] Secrets are not exposed.
- [ ] Assessment answer keys are not exposed.
- [ ] Evidence files are protected where uploads are implemented.
- [ ] Important administrative actions are auditable where supported.

---

# PART XVII — END-TO-END DEMONSTRATION SCENARIO

## 35. RECOMMENDED CAPSTONE DEMONSTRATION

Use one consistent example to demonstrate the full VerifyMesh workflow.

### Scenario: Sales Support Agent

The Administrator creates a task with the following requirements:

**Task:** Sales Support Agent

Mandatory requirements:

- At least six months of verified relevant experience.
- One specified verified and current sales certification.
- Product Knowledge assessment: minimum 70%.
- Customer Communication assessment: minimum 70%.
- Sales Techniques assessment: minimum 65%.

### Stage 1 — Agent registration

Agent A registers and verifies their email.

Agent A creates a professional profile.

### Stage 2 — Evidence submission

Agent A submits:

- Sales experience.
- Sales certification.
- Supporting documents.

The Administrator reviews the evidence.

### Stage 3 — Voluntary assessment catalogue

Agent A opens the assessment catalogue.

Agent A voluntarily completes:

- Product Knowledge: 85%.
- Sales Techniques: 72%.

Both results are officially recorded by the backend.

Customer Communication has not been attempted.

### Stage 4 — Task discovery

Agent A browses available tasks and opens Sales Support Agent.

VerifyMesh evaluates the task requirements.

| Requirement | Existing evidence | Result |
|---|---|---|
| Relevant experience | 8 verified months | Satisfied |
| Sales certification | Verified and current | Satisfied |
| Product Knowledge | 85% | Satisfied |
| Customer Communication | Not attempted | Incomplete |
| Sales Techniques | 72% | Satisfied |

The system explains that Customer Communication is the only outstanding assessment.

### Stage 5 — Complete missing assessment

Agent A opens the assessment catalogue and completes Customer Communication.

Recorded score: 78%.

The backend records the result.

VerifyMesh recalculates task eligibility.

All mandatory requirements are now satisfied.

### Stage 6 — Application

Agent A submits an application.

The backend independently rechecks eligibility and task status.

The application is persisted.

### Stage 7 — Administrator review

The Administrator opens the task's applicants.

The Administrator sees:

- Agent A's verified experience.
- Verified sales certification.
- Reused Product Knowledge result.
- Reused Sales Techniques result.
- Customer Communication result.
- Eligibility outcome.
- Experimental ML suitability output, if available.

### Stage 8 — Final selection

The Administrator reviews the evidence and decides whether to assign the task to Agent A.

The backend rechecks eligibility and persists the assignment.

Agent A sees the assignment in their dashboard.

### Stage 9 — Negative scenarios

Demonstrate at least the following:

1. Agent B has a pending certification.
2. Agent C has not completed a required assessment.
3. Agent D has an assessment score below the required threshold.
4. Agent E has an expired assessment result.
5. An Agent attempts to apply to a closed task.
6. An Agent attempts to submit a duplicate application.
7. A non-administrator attempts to assign a task.
8. ML inference fails while deterministic eligibility remains operational.

All outcomes must be based on actual backend behaviour.

If any scenario is simulated, clearly identify it as a test scenario.

---

# PART XVIII — KNOWN RISKS AND IMPLEMENTATION INVESTIGATION

## 36. ITEMS ANTIGRAVITY MUST RECHECK

The following issues have been identified in earlier project reviews. They must be rechecked against the current active repository rather than assumed to remain present.

### 36.1 Task-to-assessment linkage

Previously identified concern:

- A task may reference an exam without its required assessment topic relationships being populated.
- A frontend assessment route may omit the required topic identifier.

Inspect the complete task → assessment topic → Agent result → eligibility chain.

### 36.2 Default assessment scores

A previous route was reported to substitute a default score of 75 when assessment evidence was missing.

This behaviour must not exist.

Missing assessment evidence must remain missing.

### 36.3 Assessment reuse

Verify that results can be reused across tasks using the correct topic, validity, version and score rules.

Do not force Agents to repeat valid compatible assessments.

Do not reuse incompatible results.

### 36.4 Experience double-counting

Earlier implementation reviews identified possible double-counting in experience calculations.

Recheck the experience calculation logic and ensure that verified overlapping intervals are merged before calculating relevant experience.

### 36.5 Legacy binary model dependencies

Search the entire repository for active references to the old binary eligibility model.

Ensure that it no longer determines whether an Agent can apply if the new architecture has replaced that decision path.

Preserve historical records.

### 36.6 New ML model contract

Inspect:

- `verifymesh_final_optimized_pipeline.joblib`
- `verifymesh_threshold_metadata.json`

Confirm the feature contract, class mapping, threshold, preprocessing, dependency compatibility and evaluation methodology.

Do not use assumptions from earlier model versions.

### 36.7 Schema and runtime consistency

Verify that all backend queries use actual existing tables and columns.

Check that database migrations, schema documentation, seed data and application queries are consistent.

### 36.8 Application and assignment

Confirm that application states and assignment records are persisted and consistent across the database, backend and frontend.

### 36.9 Security

Recheck:

- Exposed credentials.
- Insecure secret defaults.
- Role-based API enforcement.
- Agent record ownership.
- Assessment answer exposure.
- File access controls.

### 36.10 Tests and branches

Inspect the active branch and uncommitted changes.

Do not assume that an older test report, README or branch represents the current working code.

Run the current tests and report the actual results.

---

# PART XIX — IMPLEMENTATION ORDER

## 37. RECOMMENDED DEVELOPMENT SEQUENCE

Antigravity should not attempt to rewrite the entire system in one operation.

Use the following sequence.

### Phase 1 — Repository audit

Inspect:

- Frontend structure.
- Backend structure.
- Database schema.
- Migrations.
- Assessment routes.
- Task routes.
- Eligibility logic.
- Application routes.
- Assignment logic.
- ML integration.
- Existing tests.
- Active Git branch.

Produce an implementation gap report.

Do not change code during the initial audit.

### Phase 2 — Assessment catalogue and data model audit

Establish how assessment topics, question banks, attempts and results currently work.

Determine whether the existing architecture can support independent catalogue assessments and reusable results.

Identify the smallest safe changes needed.

### Phase 3 — Assessment workflow

Ensure Agents can:

- Browse the catalogue.
- Start assessments.
- Submit answers.
- Receive server-generated results.
- View assessment history.

Ensure assessment security and persistence.

### Phase 4 — Assessment reuse

Implement or repair:

- Topic matching.
- Validity checks.
- Version compatibility.
- Pass-mark comparison.
- Attempt-selection policy.
- Reusable result retrieval.

Test reuse across multiple tasks.

### Phase 5 — Task requirement configuration

Ensure Administrators can select existing assessment topics and configure task-specific minimum scores.

Ensure certification and experience requirements are stored and evaluated correctly.

### Phase 6 — Eligibility engine

Ensure eligibility is determined entirely by the configured mandatory requirements.

Remove any active dependency on the legacy binary model as a mandatory gate if the new architecture has replaced it.

Preserve historical data.

### Phase 7 — ML integration

Inspect and integrate the actual final optimized pipeline.

Verify its metadata, feature construction, threshold and inference behaviour.

Keep it advisory and independent of deterministic eligibility.

### Phase 8 — Applications and assignment

Ensure eligible Agents can apply.

Ensure Administrators can review applicants and make persisted assignment decisions.

### Phase 9 — End-to-end testing

Test the complete registration-to-assignment workflow, including negative and boundary scenarios.

### Phase 10 — UI refinement and documentation

Improve the interface only after the underlying workflows are correct.

Update the README and technical documentation to reflect what the system actually implements.

---

# PART XX — FINAL SYSTEM DEFINITION

## 38. FINAL SCOPE STATEMENT

VerifyMesh is an AI-assisted competency verification and task-eligibility system inspired by real-world recruitment and workforce qualification screening.

It allows Agents to create professional profiles, submit qualifications and work experience, and voluntarily demonstrate competencies through an independent assessment catalogue.

Administrators review submitted evidence and create tasks with specific mandatory requirements, including verified certifications, relevant experience and competency assessment thresholds.

Agents can browse tasks and see which requirements they satisfy. Previously passed assessments can be reused across multiple tasks when the topic, validity period, version compatibility and required pass mark permit it. Agents only need to complete additional assessments when their existing evidence is missing, invalid, expired or insufficient.

VerifyMesh evaluates eligibility using deterministic, explainable rules.

Where available, an experimental task-specific ML model provides supplementary suitability information to support the Administrator's review.

Eligible Agents may submit applications. Administrators review applicants and make the final selection and assignment decision.

**The system does not automatically hire Agents, override mandatory eligibility requirements using ML, guarantee real-world task performance or manage the complete execution and payment lifecycle.**

The fundamental principle of VerifyMesh is:

**Agents demonstrate their competencies. Administrators define task requirements. VerifyMesh verifies the evidence, evaluates eligibility and supports informed human selection.**

When implementing any feature, preserve this principle and consult this specification before making architectural or functional changes.