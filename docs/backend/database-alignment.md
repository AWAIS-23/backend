# Database Architecture & Entity Alignment

## 1. Domain Entities & Alignment Overview

To support the complete product loop, the database architecture is categorized into 8 core domain groups totaling 26 tables (including explicit additions of `applications` and `experiences`).

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Profiles & Organizations: profiles, organizations, organization_members,│
│                          roles                                          │
│ Taxonomy & Skills:       skills, role_skills                            │
│ Assessments:             assessments, assessment_questions,             │
│                          assessment_attempts, assessment_answers,       │
│                          assessment_results                             │
│ Practical Challenges:    challenges, challenge_skills, submissions,     │
│                          evaluations                                    │
│ Evidence & Verification: evidence, verifications                        │
│ Opportunities:           opportunities, opportunity_skills, matches,    │
│                          applications [ADDED]                           │
│ Experiences:             experiences [ADDED]                            │
│ Feedback, AI & Audit:    feedback, ai_generations, notifications,       │
│                          audit_logs                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architectural Additions & Rationales

### 2.1 `applications` Entity (Added)
- **Domain Purpose**: Tracks the application lifecycle when a learner applies to a published opportunity.
- **Why Needed**: Enables the `OPPORTUNITY` $\to$ `APPLICATION` $\to$ `SELECTION` workflow.
- **Key Fields**:
  - `id`: UUID (Primary Key)
  - `opportunity_id`: UUID (FK $\to$ `opportunities.id`, ON DELETE RESTRICT)
  - `profile_id`: UUID (FK $\to$ `profiles.id`, ON DELETE CASCADE)
  - `status`: Enum (`submitted`, `reviewing`, `shortlisted`, `rejected`, `accepted`, `withdrawn`)
  - `application_note`: Text (Nullable)
  - `applied_at`: Timestamptz (Default now())
  - `updated_at`: Timestamptz (Default now())
- **Constraint**: Unique constraint on `(opportunity_id, profile_id)` to prevent duplicate active applications.

### 2.2 `experiences` Entity (Added)
- **Domain Purpose**: Records real-world work, internships, employer challenges, and practical projects completed by learners.
- **Why Needed**: Enables the core `EXPERIENCE` phase of the product loop.
- **Key Fields**:
  - `id`: UUID (Primary Key)
  - `profile_id`: UUID (FK $\to$ `profiles.id`, ON DELETE CASCADE)
  - `organization_id`: UUID (Nullable, FK $\to$ `organizations.id`, ON DELETE SET NULL)
  - `opportunity_id`: UUID (Nullable, FK $\to$ `opportunities.id`, ON DELETE SET NULL)
  - `title`: Varchar(255)
  - `description`: Text
  - `experience_type`: Enum (`employer_project`, `internship`, `apprenticeship`, `freelance`, `practical_challenge`)
  - `started_at`: Timestamptz
  - `ended_at`: Timestamptz (Nullable)
  - `verification_status`: Enum (`unverified`, `pending`, `verified`, `rejected`)
  - `created_at`: Timestamptz
  - `updated_at`: Timestamptz

---

## 3. Critical Domain Invariants & Rules

### 3.1 Result vs. Evidence vs. Verification
- **Assessment Result / Challenge Evaluation**: Raw measurement of performance.
- **Evidence**: Canonical platform record connecting a learner to a specific skill with an achieved score and source origin.
- **Verification**: Explicit state machine transition (`pending` $\to$ `verified` / `rejected` / `revoked`) performed by authorized human verifiers, employers, or trusted automated gates. **AI cannot independently verify evidence.**

### 3.2 Evidence Source Linkage
The `evidence` entity supports foreign keys to its originating artifact:
- `assessment_result_id` (Nullable FK $\to$ `assessment_results.id`)
- `evaluation_id` (Nullable FK $\to$ `evaluations.id`)
- `experience_id` (Nullable FK $\to$ `experiences.id`)

Check constraint ensures valid source provenance.
