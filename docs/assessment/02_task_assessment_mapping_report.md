# Phase 2 — Task Assessment Mapping & Deterministic Eligibility Report

**Document ID:** `docs/assessment/02_task_assessment_mapping_report.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Executive Summary

Phase 2 resolves the architectural coupling between legacy monolithic exams, task-specific competencies, and deterministic eligibility rules in VerifyMesh. 

Prior to Phase 2:
1. Tasks evaluated assessment status (`Assessment Needed`) before hard prerequisites like minimum experience, displaying an active `Take Assessment ->` CTA to agents who were fundamentally disqualified by experience.
2. The legacy `exam_id` association caused candidate scores from unrelated tasks to leak across competencies (e.g., Alex Morgan's legacy 20% Product Knowledge score contaminating Customer Communication on Task 4).
3. The Agent Dashboard exposed a demo reset feature (`Reset to Unassessed (Demo)`) directly in the production navigation dropdown.

Phase 2 implements strict **Hard-Prerequisites First** evaluation, isolates topic evaluations per task via `task_assessment_topics`, removes client demo reset mechanisms, and enforces authoritative server-side prerequisite gating.

---

## 2. Hard-Prerequisites First Evaluation Precedence

The deterministic evaluation engine in `backend/db.py` (`get_agent_tasks_with_eligibility`) and application submission validator (`apply_for_task`) enforces the following immutable evaluation hierarchy:

```
[1. Assigned]
      │ (not assigned)
      ▼
[2. Application Submitted / Active Status]
      │ (not applied)
      ▼
[3. Certification Required] ─── Missing mandatory verified certs
      │ (certs verified)
      ▼
[4. Verification Pending] ───── Agent suspended or cert pending review
      │ (active & in good standing)
      ▼
[5. Requires X Months Exp] ──── Verified experience < min_experience_months
      │ (experience verified >= required)
      ▼
[6. Attempt Limit Reached] ──── Maximum 3 attempts exhausted on required topic
      │ (< 3 attempts or passing)
      ▼
[7. Assessment Needed] ──────── Missing passing score on mandatory topic
      │ (all mandatory topics passed)
      ▼
[8. Ready to Apply] ─────────── Eligible to submit application
```

### Business Impact:
- If a task requires 24 months of experience and the agent possesses 0 or 23 months, the status evaluates immediately to `Requires 24 Months Exp`.
- The task card renders an informational amber warning: `Agent has X months verified experience; task requires 24 months`.
- The primary action button switches to `View details →`. The agent is never urged or permitted to `Take Assessment`.

---

## 3. Removal of "Reset to Unassessed (Demo)"

The user menu dropdown on the Agent Dashboard previously contained a debug toggle:
- `Reset to Unassessed (Demo)` (icon: `RotateCcw`, text styled in yellow).

### Modifications:
1. **Frontend Removal (`frontend/src/pages/AgentDashboard.jsx`):**
   - Removed `handleResetAssessment` handler and `RotateCcw` import.
   - Removed the button element from the header user menu dropdown.
   - Menu now strictly contains: `Dashboard`, `My Profile`, `Retake Assessment` / `Complete Assessment`, `Help & Documentation`, `Sign Out`.
2. **API Isolation:**
   - The reset endpoint remains restricted and is never invoked by legitimate agent UI workflows.

---

## 4. Multi-Topic Qualification Assessment Mapping

### Database Relationship Model:
```
tasks (task_id)
  └── task_assessment_topics (task_id, topic_id, is_mandatory)
        └── assessment_topics (topic_id, passing_score, max_attempts)
              └── exam_questions (question_id, topic_id)
```

### Key Rules:
1. **Task-to-Topic Gating:**
   - Each task explicitly declares which topics are mandatory via `task_assessment_topics`.
   - Topics from other tasks are flagged as `COMPETENCY_STATE_NOT_REQUIRED` and strictly excluded from weakest-link deficits, feature vectors, and eligibility decisions.
2. **Latest Attempt Integrity:**
   - Topic completion is determined exclusively by the agent's latest submitted attempt for that specific topic.
   - Passing requires `score >= passing_score`.
3. **Multi-Topic Aggregation:**
   - For multi-topic tasks (e.g. Task 2 requiring Topics 1, 3, and 4), all mandatory topics must independently achieve passing scores before `Ready to Apply` is awarded.

---

## 5. Verification Matrix

| Test Case | Scenario | Expected Behavior | Outcome |
| :--- | :--- | :--- | :--- |
| **Prerequisite Precedence** | Agent with 0 mo exp views Task 2 (req 24 mo) | State is `Requires 24 Months Exp`, button is `View details →` | **PASS** |
| **UI Menu Cleanliness** | Agent opens profile dropdown | "Reset to Unassessed" is completely absent | **PASS** |
| **Topic Isolation** | Alex Morgan (Task 4, Topic 3) | Topic 1 (Product Knowledge 20%) is `NOT_REQUIRED`, score is not penalized | **PASS** |
| **Multi-Topic Evaluation** | Task 2 (Topics 1, 3, 4) | 0/3 Passed shows `Needed (≥70%)`, `Needed (≥75%)` | **PASS** |
| **Server-Side Enforcement** | Direct POST to `/tasks/apply` with unmet exp | HTTP 403 / 400: Experience prerequisite unmet | **PASS** |

---

## 6. Conclusion

Phase 2 establishes bulletproof server-side determinism for task eligibility, eliminates misleading UI prompts for unqualified candidates, and purges demo testing artifacts from the production agent interface.

