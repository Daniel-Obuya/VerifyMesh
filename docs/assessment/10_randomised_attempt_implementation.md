# Phase 2A — Question Randomisation & Attempt Integrity Implementation

**Document ID:** `docs/assessment/10_randomised_attempt_implementation.md`  
**Status:** Completed  
**Version:** 1.0.0  
**Date:** 2026-11-11  

---

## 1. Overview & Policy Directives

Phase 2A delivers cryptographic question randomisation, option shuffling, attempt quota enforcement, and tamper-resistant attempt snapshots in accordance with approved policy directives:

1. **3-Attempt Limit:** Candidates may attempt each competency topic a maximum of 3 times (`assessment_topics.max_attempts = 3`). When 3 non-passing attempts are exhausted, the topic locks with `AttemptLimitReachedError` (HTTP 403), requiring Workforce Officer review.
2. **Cryptographic Randomisation:** Each new attempt generates an isolated question selection and option permutation using Python's `secrets.SystemRandom()`.
3. **Attempt Snapshots:** The selected questions and shuffled option mappings are frozen in `assessment_attempts.question_snapshot_json` at generation time. Resuming an active attempt reconstructs the identical presentation.
4. **Mark Incomplete on Expiry:** Attempts that exceed their time limit (`expires_at < NOW()`) are finalized as `status = 'EXPIRED', score = NULL, passed = 0`. They count against the 3-attempt quota to deter item harvesting, but do not skew candidate competency averages with artificial zero scores.

---

## 2. Database Schema Migration 007

Migration `007_assessment_snapshots_and_attempt_limits.sql` applied non-destructive DDL additions:

```sql
-- 1. Attempt limit configuration per competency topic
ALTER TABLE assessment_topics
  ADD COLUMN max_attempts INT NOT NULL DEFAULT 3;

-- 2. Immutable question & option snapshot per candidate attempt
ALTER TABLE assessment_attempts
  ADD COLUMN question_snapshot_json MEDIUMTEXT NULL;

-- 3. Question status flag for content lifecycle management
ALTER TABLE exam_questions
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE';
```

---

## 3. Cryptographic Randomisation & Snapshot Engine

When an agent initiates an attempt via `create_assessment_attempt(agent_id, exam_id, topic_id)`:

1. **Quota Check:**
   - Counts past attempts with `status IN ('SUBMITTED', 'EXPIRED')`.
   - If `att_count >= max_attempts` and topic is not already passed, raises `AttemptLimitReachedError`.
2. **Active Attempt Resumption:**
   - If an `IN_PROGRESS` attempt exists and has not expired, it returns immediately without re-randomising.
   - If expired, it transitions to `status = 'EXPIRED', score = NULL, passed = 0`.
3. **Random Sampling & Option Shuffling:**
   ```python
   rng = secrets.SystemRandom()
   # Questions shuffled cryptographically
   selected_questions = questions[:]
   rng.shuffle(selected_questions)

   for q in selected_questions:
       raw_options = json.loads(q["options_json"])
       # Keys: ['A', 'B', 'C', 'D']
       keys = list(raw_options.keys())
       rng.shuffle(keys)
       
       # Map new display letters to original content
       shuffled_options = {}
       display_to_original = {}
       for idx, k in enumerate(['A', 'B', 'C', 'D'][:len(keys)]):
           original_key = keys[idx]
           shuffled_options[k] = raw_options[original_key]
           display_to_original[k] = original_key
   ```
4. **Snapshot Storage:**
   - Stored in `assessment_attempts.question_snapshot_json`.
   - Contains `display_questions` (stripped of `correct_answer`) and `display_to_original_maps` for grading.

---

## 4. Grading & Re-mapping Workflow

When the agent submits answers via `/topics/<id>/submit`:

1. **Option Re-mapping:**
   - The agent submits choices according to their display letters (e.g. `Q10: 'B'`).
   - The grading algorithm retrieves `display_to_original_maps` from the attempt's snapshot.
   - Converts display choice `'B'` $\rightarrow$ original answer key `'D'`.
   - Compares the mapped key against `correct_answer` stored in the authoritative database row.
2. **Zero Client Trust:**
   - Correct answers are NEVER returned in question payloads or API responses.
   - The client never grades or calculates points; all scoring is strictly backend-evaluated.
3. **Idempotent Submission Recovery:**
   - If a duplicate submission arrives due to network retries, the server safely returns the already-calculated score and attempt record with HTTP 200 rather than throwing a duplicate conflict.

---

## 5. Attempt Limit & Hard-Prerequisites Integration

If an agent reaches 3 attempts without passing:
- Backend `get_agent_tasks_with_eligibility()` sets `state = 'Attempt Limit Reached'`.
- The task card alerts: `"Maximum assessment attempts (3) reached for mandatory qualification topic. Contact workforce officer."`
- The `Take Assessment` button is disabled, safeguarding system integrity and test fairness.

---

## 6. Phase 2A Delivery Sign-off

- Migration 007 verified: `max_attempts`, `question_snapshot_json`, `status` active in MySQL.
- Randomization verified: Cryptographically isolated questions and option shuffling across attempts.
- Frontend build verified: `npm run build --prefix frontend` (0 errors, 3.96s).

