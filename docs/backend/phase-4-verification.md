# Rising Skills — Backend Phase 4 Verification Report

## Opportunity Publishing, Deterministic Matching & Applications

---

## 1. Executive Summary

| Metric | Target | Result | Status |
|---|---|---|---|
| **Total Test Suite** | All Passing | **67 / 67** | ✅ 100% |
| **New Phase 4 Tests** | Complete Coverage | **+11 tests** | ✅ Complete |
| **Overall Code Coverage** | $\ge 85\%$ | **87%** | ✅ Exceeds Goal |
| **Zero Warnings / Failures** | 0 | **0** | ✅ Clean |
| **OpenAPI Schema Generation** | Valid v3.1 | **Valid** | ✅ |

---

## 2. Architecture & Data Flow

Phase 4 connects verified practical/theoretical skill evidence to real employer opportunities:

```
Employer Organization
        │
        ▼
1. Create Draft Opportunity (POST /api/v1/opportunities)
        │
        ▼
2. Attach Required Skills with Weights (PUT /api/v1/opportunities/{id}/skills)
        │  - Python: 0.50, FastAPI: 0.30, PostgreSQL: 0.20
        ▼
3. Publish Opportunity (POST /api/v1/opportunities/{id}/publish)
        │
        ▼
4. Deterministic Matching Engine
        │  - Computes: 0.60 * Skill Score + 0.30 * Evidence Score + 0.10 * Experience Score
        │  - Unverified evidence produces 0.0 coverage
        │  - Generates transparent, explainable skill breakdown
        ▼
5. Candidate Discovers & Applies (POST /api/v1/opportunities/{id}/apply)
        │  - Duplicate application prevention (409)
        │  - Instant match score computed
        ▼
6. Employer Review & Decision (PATCH /api/v1/applications/{id}/status)
        │  - Reviewing → Shortlisted → Accepted / Rejected
        ▼
Opportunity Fulfilled
```

---

## 3. Database Schema & Migration

Migration Revision: `004_phase4` (Parent: `003_phase3`)

### 3.1 Tables Added

1. **`opportunities`**:
   - `id`: UUID (Primary Key)
   - `organization_id`: FK to `organizations.id` (RESTRICT)
   - `title`: String(255), Indexed
   - `description`: Text
   - `opportunity_type`: Enum (`job`, `internship`, `apprenticeship`, `project`)
   - `status`: Enum (`draft`, `published`, `closed`, `archived`)
   - `location`: String(255)
   - `is_remote`: Boolean
   - `deadline`: DateTime(timezone=True)
   - `created_by`: FK to `profiles.id` (SET NULL)
   - `published_at`: DateTime(timezone=True)
   - `created_at`, `updated_at`

2. **`opportunity_skills`**:
   - `id`: UUID (Primary Key)
   - `opportunity_id`: FK to `opportunities.id` (CASCADE)
   - `skill_id`: FK to `skills.id` (RESTRICT)
   - `importance_weight`: Float ($0.0 \le \text{weight} \le 1.0$)
   - Unique Constraint: `(opportunity_id, skill_id)`

3. **`applications`**:
   - `id`: UUID (Primary Key)
   - `opportunity_id`: FK to `opportunities.id` (RESTRICT)
   - `profile_id`: FK to `profiles.id` (CASCADE)
   - `status`: Enum (`submitted`, `reviewing`, `shortlisted`, `rejected`, `accepted`, `withdrawn`)
   - `cover_note`: Text
   - `applied_at`: DateTime(timezone=True)
   - `reviewed_at`: DateTime(timezone=True)
   - `reviewed_by`: FK to `profiles.id` (SET NULL)
   - `created_at`, `updated_at`
   - Unique Constraint: `(opportunity_id, profile_id)`

4. **`matches`**:
   - `id`: UUID (Primary Key)
   - `opportunity_id`: FK to `opportunities.id` (CASCADE)
   - `profile_id`: FK to `profiles.id` (CASCADE)
   - `overall_score`: Float ($0.0 \le \text{score} \le 100.0$)
   - `skill_score`: Float
   - `evidence_score`: Float
   - `experience_score`: Float
   - `breakdown`: JSON (Explainable matching details)
   - `created_at`, `updated_at`
   - Unique Constraint: `(opportunity_id, profile_id)`

---

## 4. Deterministic Matching Formula

$$\text{overall\_score} = 0.60 \times \text{skill\_score} + 0.30 \times \text{evidence\_score} + 0.10 \times \text{experience\_score}$$

1. **`skill\_score`**:
   $$\text{skill\_score} = \frac{\sum (w_i \times c_i)}{\sum w_i}$$
   where $c_i = \text{score}$ if verified evidence exists for skill $i$, else $c_i = 0.0$.
2. **`evidence\_score`**:
   $$\text{evidence\_score} = \frac{\text{count(verified\_required\_skills)}}{\text{count(required\_skills)}} \times 100.0$$
3. **`experience\_score`**:
   - $\ge 2$ verified practical challenges: $100.0$
   - $1$ verified practical challenge: $70.0$
   - $0$ verified challenges: $0.0$

---

## 5. Security & Isolation Controls

1. **Zero Client Trust on Identity & Scores**:
   - `profile_id` and reviewer identity are derived strictly from verified JWT tokens.
   - Match scores cannot be submitted or overridden by clients; they are computed server-side.
2. **Organization Boundary Isolation**:
   - Employers can only manage, publish, review applications for, or view matches for opportunities belonging to their own organization.
3. **Learner Application Isolation**:
   - Learners can only view and withdraw their own applications.
4. **Duplicate Prevention**:
   - DB and service guards prevent multiple applications by the same learner to the same opportunity.
