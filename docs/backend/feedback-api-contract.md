# Rising Skills — Feedback API Contract

## Domain: Structured Employer Feedback & Evaluation

---

## 1. Endpoints Overview

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/experiences/{experience_id}/feedback` | Submit structured rubric review for an experience | Employer / Admin |
| `GET` | `/api/v1/experiences/{experience_id}/feedback` | List feedback reviews for an experience | Owner / Employer / Admin |

---

## 2. Request & Response Schemas

### `POST /api/v1/experiences/{experience_id}/feedback`

**Headers:**
`Authorization: Bearer <employer_jwt>`

**Request Body (`ExperienceFeedbackCreate`):**
```json
{
  "overall_rating": 4,
  "strengths": "Exceptional Python fundamentals and clean database migrations.",
  "areas_for_improvement": "Could improve test assertion specificity in edge cases.",
  "communication_rating": 4,
  "technical_rating": 5,
  "problem_solving_rating": 4,
  "teamwork_rating": 4,
  "professionalism_rating": 5,
  "recommendation": "Highly recommend for full-time backend positions."
}
```

**Response Body (`ExperienceFeedbackPublic`):**
```json
{
  "id": "22222222-3333-4444-5555-666666666666",
  "experience_id": "11111111-2222-3333-4444-555555555555",
  "profile_id": "11111111-1111-1111-1111-111111111111",
  "organization_id": "77777777-1111-2222-3333-444444444444",
  "reviewer_id": "22222222-2222-2222-2222-222222222222",
  "overall_rating": 4,
  "strengths": "Exceptional Python fundamentals and clean database migrations.",
  "areas_for_improvement": "Could improve test assertion specificity in edge cases.",
  "communication_rating": 4,
  "technical_rating": 5,
  "problem_solving_rating": 4,
  "teamwork_rating": 4,
  "professionalism_rating": 5,
  "recommendation": "Highly recommend for full-time backend positions.",
  "created_at": "2026-08-30T17:45:00Z"
}
```

---

## 3. Security & Integrity Invariants

1. **Unique Feedback Constraint**:
   - `UniqueConstraint("experience_id", "reviewer_id")` enforces at both database and application level that a reviewer can only review an experience once.
   - Subsequent submissions return HTTP `409 Conflict` (`DUPLICATE_FEEDBACK`).
2. **Reviewer Identity Immutability**:
   - `reviewer_id` is derived strictly from cryptographic JWT claims (`AuthenticatedUser.id`).
3. **Organization Isolation**:
   - Only authorized employers (`OrgRole.OWNER`, `OrgRole.ADMIN`, `OrgRole.RECRUITER`, `OrgRole.EVALUATOR`) of the experience's hosting organization can submit feedback.
4. **Rating Bounds**:
   - Ratings are strictly bounded between $1$ and $5$. Out-of-bounds ratings are rejected with HTTP `422 Unprocessable Entity`.
5. **Feedback $\ne$ Verified Evidence**:
   - Employer feedback provides qualitative signal and growth guidance, but does not automatically bypass the evidence verification pipeline.
