# Rising Skills — Backend Phase 3 Verification Report

## Practical Challenges, Submissions, Evaluations, Evidence & Verification

---

## 1. Executive Summary

| Metric | Target | Result | Status |
|---|---|---|---|
| **Total Test Suite** | All Passing | **56 / 56** | ✅ 100% |
| **New Phase 3 Tests** | Complete Coverage | **+13 tests** | ✅ |
| **Overall Code Coverage** | $\ge 85\%$ | **89%** | ✅ Exceeds Goal |
| **Zero Warnings / Failures** | 0 | **0** | ✅ Clean |
| **OpenAPI Schema Generation** | Valid v3.1 | **Valid** | ✅ |

---

## 2. Architecture & Data Flow

Phase 3 builds the practical demonstration, evaluation, and proof layer:

```
                  ┌────────────────────────────────────────┐
                  │ Practical Challenge                    │
                  │ (Platform-wide or Employer-linked)     │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ Learner Submission                     │
                  │ (Repo URL, Deployment URL, Notes)      │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ Structured Rubric Evaluation           │
                  │ (Server-Calculated Score 0-100%)       │
                  └──────────────────┬─────────────────────┘
                                     │ (Atomic Creation)
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ Skill Evidence Record                  │
                  │ (Status: UNVERIFIED / PENDING)         │
                  └──────────────────┬─────────────────────┘
                                     │ (Human Verifier Decision)
                                     ▼
                  ┌────────────────────────────────────────┐
                  │ Verification Audit Trail               │
                  │ (Status: VERIFIED / REJECTED)          │
                  └──────────────────┬─────────────────────┘
                                     │
                                     ▼
                          Trusted Skill Signal
```

---

## 3. Database Entities & Migration

Migration Revision: `003_phase3` (Parent: `002_phase2`)

### 3.1 Tables Added

1. **`challenges`**:
   - `id`: UUID (Primary Key)
   - `title`: String(255), Indexed
   - `description`: Text
   - `instructions`: Text
   - `difficulty`: Enum (`beginner`, `intermediate`, `advanced`)
   - `status`: Enum (`draft`, `published`, `archived`)
   - `created_by`: FK to `profiles.id` (SET NULL)
   - `organization_id`: FK to `organizations.id` (SET NULL)
   - `role_id`: FK to `roles.id` (SET NULL)
   - `time_limit_seconds`: Integer (Check: `> 0`)
   - `submission_deadline`: DateTime(timezone=True)
   - Timestamps: `created_at`, `updated_at`

2. **`challenge_skills`**:
   - `id`: UUID (Primary Key)
   - `challenge_id`: FK to `challenges.id` (CASCADE)
   - `skill_id`: FK to `skills.id` (RESTRICT)
   - `importance_weight`: Float (Check: `0.0 <= weight <= 1.0`)
   - Unique Constraint: `(challenge_id, skill_id)`

3. **`submissions`**:
   - `id`: UUID (Primary Key)
   - `challenge_id`: FK to `challenges.id` (RESTRICT)
   - `profile_id`: FK to `profiles.id` (CASCADE)
   - `repository_url`: String(2048)
   - `deployment_url`: String(2048)
   - `description`: Text
   - `status`: Enum (`draft`, `submitted`, `under_review`, `evaluated`, `accepted`, `rejected`, `withdrawn`)
   - `submitted_at`: DateTime(timezone=True)
   - Timestamps: `created_at`, `updated_at`

4. **`evaluations`**:
   - `id`: UUID (Primary Key)
   - `submission_id`: FK to `submissions.id` (RESTRICT)
   - `evaluator_id`: FK to `profiles.id` (RESTRICT)
   - `rubric`: JSON (List of criterion objects with `max_points` and `awarded_points`)
   - `score`: Float (Check: `0.0 <= score <= 100.0`, Calculated server-side)
   - `feedback`: Text
   - `status`: String(50)
   - Timestamps: `created_at`, `updated_at`

5. **`evidence`**:
   - `id`: UUID (Primary Key)
   - `profile_id`: FK to `profiles.id` (CASCADE)
   - `skill_id`: FK to `skills.id` (RESTRICT)
   - `source_type`: Enum (`assessment`, `challenge_submission`)
   - `source_id`: UUID (FK to originating evaluation or assessment result)
   - `score`: Float (Check: `0.0 <= score <= 100.0`)
   - `evidence_data`: JSON (Provenance snapshot)
   - `status`: Enum (`unverified`, `pending`, `verified`, `rejected`)
   - Timestamps: `created_at`, `updated_at`

6. **`verifications`**:
   - `id`: UUID (Primary Key)
   - `evidence_id`: FK to `evidence.id` (CASCADE)
   - `verifier_id`: FK to `profiles.id` (RESTRICT)
   - `from_status`: String(50)
   - `to_status`: String(50)
   - `notes`: Text
   - Timestamps: `created_at`, `updated_at`

---

## 4. Security & Business Rules Enforced

### 4.1 Anti-Tamper & IDOR Protection
- **Never trust client-supplied IDs**: `profile_id` and `evaluator_id` are extracted strictly from cryptographic JWT claims (`AuthenticatedUser.id`).
- **Cross-user isolation**: Learners cannot edit other learners' submissions, view unshared work, or tamper with foreign evidence records.

### 4.2 Deterministic Server-Side Scoring
- The client cannot supply a final score in `POST /evaluations`.
- The backend parses the rubric, verifies `0 <= awarded_points <= max_points`, and calculates:
  $$\text{score} = \frac{\sum \text{awarded\_points}}{\sum \text{max\_points}} \times 100$$

### 4.3 Self-Evaluation & Self-Verification Prevention
- A learner is strictly forbidden from evaluating their own submission (`SELF_EVALUATION_FORBIDDEN`).
- A candidate cannot verify their own evidence (`SELF_VERIFICATION_FORBIDDEN`).

### 4.4 The Critical AI Boundary
- **AI MUST NOT GRANT VERIFIED STATUS**: AI models may generate suggestions, summarize code, or assist evaluators, but the transition `status = "verified"` can only be executed by an authorized human verifier or approved deterministic test pipeline.

### 4.5 Controlled Verification State Machine
- `unverified` $\to$ `pending`
- `pending` $\to$ `verified`
- `pending` $\to$ `rejected`
- **Immutable Once Verified**: Verified evidence cannot be reverted to unverified or mutated directly by learners.

---

## 5. API Reference Summary

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/challenges` | Public | List published challenges |
| `POST` | `/api/v1/challenges` | Employer/Admin | Create new practical challenge |
| `GET` | `/api/v1/challenges/{id}` | Public | Get challenge details and mapped skills |
| `POST` | `/api/v1/challenges/{id}/submissions` | Bearer (Learner) | Submit practical work |
| `GET` | `/api/v1/challenges/{id}/submissions` | Employer/Admin | List all submissions for challenge |
| `GET` | `/api/v1/submissions/{id}` | Bearer (Owner/Admin) | Get submission details |
| `PATCH` | `/api/v1/submissions/{id}` | Bearer (Owner) | Update submission before evaluation |
| `POST` | `/api/v1/submissions/{id}/evaluations` | Employer/Admin | Record rubric evaluation & create evidence |
| `GET` | `/api/v1/submissions/{id}/evaluations` | Bearer (Owner/Admin) | List evaluations for submission |
| `GET` | `/api/v1/evidence` | Bearer | List learner's skill evidence records |
| `GET` | `/api/v1/evidence/{id}` | Bearer | Get evidence details with provenance |
| `POST` | `/api/v1/verifications` | Employer/Admin | Approve or reject evidence |
| `GET` | `/api/v1/verifications/evidence/{id}` | Bearer | View verification audit history |

---

## 6. Phase 4 Boundary

Phase 3 is complete and fully verified. In Phase 4, we will introduce **Opportunity Publishing & Matching Engine** to match verified skill evidence against real career opportunities.
