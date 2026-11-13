# VERIFYMESH — QUESTION RANDOMISATION AND FAIRNESS POLICY

**Document Version:** 1.0.0  
**Status:** Architecture Specification (Phase 1A Deliverable)  
**Author:** Senior Software Architect, Backend Security Engineer & Assessment Systems Specialist  
**Scope:** Cryptographic Question Selection, Option Permutation, Attempt Immutability, and Assessment Equity  

---

## 1. Executive Overview

Static assessment questions and fixed option arrangements introduce critical vulnerabilities: candidate collusion, answer key harvesting, and memorization of letter sequences (`A, B, A, B, A`). 

This policy establishes an assessment engine that guarantees:
- **Dynamic Variety:** Every assessment attempt receives a unique question sequence and independent option permutations.
- **Strict Psychometric Fairness:** Every candidate is measured against an identical blueprint of competencies, point values, and difficulty distributions.
- **Refresh & Resumption Immutability:** Once an attempt is created, its question selection and option mappings are frozen into an authoritative server snapshot. Page reloads and multi-tab resumption never regenerate the assessment.
- **Zero Information Leakage:** Answer keys remain strictly confined to backend memory during server-side evaluation.

---

## 2. Assessment Blueprint Specification

An assessment attempt is governed by an **Assessment Blueprint** defining the exact sampling criteria from the question bank.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASSESSMENT BLUEPRINT MODEL                          │
└─────────────────────────────────────────────────────────────────────────────┘

 [ Topic Question Bank ] ────► N Total Active Questions in Database (Pool >= 10)
           │
           ▼
 [ Blueprint Filter ] ───────► Target Question Count: K (e.g., 5 Questions)
           │                 ► Difficulty Distribution (e.g. 2 Beginner, 3 Intermediate)
           │                 ► Mandatory Competency Sub-Domains
           │
           ▼
 [ Cryptographic Sampling ] ─► CSPRNG (secrets.SystemRandom)
           │
           ▼
 [ Immutable Attempt ] ──────► Frozen Snapshot: Ordered Questions & Permuted Options
```

### Blueprint Schema & Configuration

For each topic assessment sitting:

| Parameter | Specification | Rule & Validation |
| :--- | :--- | :--- |
| **Topic Identifier** | `topic_id` (e.g., Topic 3: Customer Communication) | Must exist in `assessment_topics` with `status = 'ACTIVE'`. |
| **Required Question Count** | $K = 5$ questions | Number of distinct questions delivered to the candidate. |
| **Minimum Pool Size** | $N \ge 10$ active questions | Pool must be $\ge 2 \times K$ to ensure meaningful variation. |
| **Points per Question** | 1.00 point per question | Uniform question weighting. Total maximum score: $5.00$ points. |
| **Passing Score** | Configured on `assessment_topics` | Typically $70.00\%$ or $75.00\%$. |
| **Difficulty Balancing** | Standardized across attempts | Uniform proportion of scenario complexity across candidates. |

---

## 3. Cryptographically Secure Sampling Engine

### Backend Selection Algorithm
When `start_topic_attempt` or `create_assessment_attempt` is invoked:

1. **Verify Question Bank Sufficiency:**
   Query active questions for the requested topic:
   ```sql
   SELECT question_id, points, correct_answer, options_json
   FROM exam_questions
   WHERE topic_id = %s AND (status = 'ACTIVE' OR status IS NULL)
   ```
   If active questions count $< K$, attempt creation is aborted with `HTTP 500 Internal Server Error`:  
   *"Insufficient questions in question bank for topic {topic_id}. Minimum required: {K}, available: {count}."*  
   **Under no circumstances will the system silently reduce question counts or substitute questions from an unrelated topic.**

2. **Cryptographic Random Sampling:**
   Use Python's `secrets.SystemRandom()` (backed by OS entropy `/dev/urandom` / `CryptGenRandom`) to select $K$ distinct question IDs without replacement:
   ```python
   import secrets
   rng = secrets.SystemRandom()
   selected_questions = rng.sample(active_questions, k=REQUIRED_COUNT)
   rng.shuffle(selected_questions)  # Randomize question presentation order
   ```

3. **Independent Option Permutation:**
   For each selected question, parse its choices from `options_json`.  
   Permute the display options independently using `rng.shuffle()`.  
   Map the shuffled options to presentation keys `A`, `B`, `C`, `D`:
   ```python
   shuffled_options = list(raw_options)
   rng.shuffle(shuffled_options)
   # Map each display letter A..D to the underlying original option identifier
   ```

4. **Persist the Immutable Attempt Snapshot:**
   Before returning question presentation data to the client, write the frozen snapshot to `assessment_attempts.question_snapshot_json` in the same database transaction:
   ```json
   {
     "version": 1,
     "topic_id": 3,
     "question_order": [15, 13, 17, 14, 16],
     "option_mappings": {
       "15": {
         "display_to_original": {"A": "opt_2", "B": "opt_4", "C": "opt_1", "D": "opt_3"},
         "display_options": [
           {"option_id": "A", "text": "Listen to the customer..."},
           {"option_id": "B", "text": "Advise them that non-technical..."},
           {"option_id": "C", "text": "Post transparent status..."},
           {"option_id": "D", "text": "Tell them to inspect devtools..."}
         ]
       }
     }
   }
   ```

---

## 4. Immutable Resumption & Anti-Replay Guarantees

### Refresh & Multi-Tab Behavior
- When an agent reloads `/agent/assessment/:taskId` or opens the assessment in a second tab:
  1. The server identifies the existing `IN_PROGRESS` attempt.
  2. The server loads the frozen `question_snapshot_json` from the database.
  3. The exact same questions, in the exact same sequence, with the exact same option letters are returned.
- **Never Regenerate on Refresh:** The question set is created **once and only once** per attempt. Refreshing never generates a new question set.
- **Anti-Collusion:** Two different agents taking the same assessment simultaneously receive different question sequences and different option letters for the same question.

### Grading Reconciliation Engine
When the candidate submits their answers (`{"15": "B", "13": "A", ...}`):
1. The server loads the attempt's `question_snapshot_json`.
2. For each submitted question:
   - Identify the candidate's selected display letter (e.g. `"B"`).
   - Look up the underlying option in `display_to_original["B"]`.
   - Compare the candidate's selection against the database `correct_answer`.
3. If an agent submits an option letter not present in the attempt's snapshot, the submission is rejected with `HTTP 400 Bad Request`.

---

## 5. Fairness & Psychometric Quality Rules

1. **Equivalence of Difficulty:** All candidates face equal cognitive demands. No candidate receives an all-easy or all-hard set.
2. **Anti-Duplication Invariant:** No question may appear more than once within the same attempt ($|Q| = K \text{ distinct questions}$).
3. **Draft & Retired Isolation:** Questions marked `DRAFT`, `INACTIVE`, or `RETIRED` are excluded from the sampling pool.
4. **Answer Key Integrity Pre-Flight:** Any question whose `correct_answer` is null, empty, or not found among its options is quarantined and excluded from sampling.
5. **No Blind Substitutions:** If an assessment requires *Sales Techniques*, it cannot substitute questions from *Customer Support* to make up numbers.

---

## 6. Security Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY FIREWALL BOUNDARY                         │
└─────────────────────────────────────────────────────────────────────────────┘

 [ BROWSER / CLIENT ]                        [ BACKEND SERVER & DATABASE ]
 ────────────────────                        ─────────────────────────────
 Receives:                                   Stores Exclusively:
 • Question IDs                              • Database Answer Key (correct_answer)
 • Question Text                             • Internal Option Database Identifiers
 • Shuffled Option Text                      • Topic Scoring & Weighting Formulas
 • Display Option Letters (A, B, C, D)       • Integrity Checksums & Snapshots
 • Time Remaining (Countdown)                • Monotonic Answer Version Ledger
 
 Strictly Forbidden:                         Enforces:
 ✗ Correct Answer Identifiers                 ✓ Server-Side Option De-obfuscation
 ✗ Answer Keys in Hidden Form Fields          ✓ Exact Point Calculation
 ✗ Client-Side Score Calculations             ✓ Database-Level Attempt Locking
```

---

**Status:** Phase 1A Randomisation & Fairness Specification Complete. Zero schema or code modifications executed.  
**Action Required:** STOP and review the Randomisation & Fairness Policy for approval.

