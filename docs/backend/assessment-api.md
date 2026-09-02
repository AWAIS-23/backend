# Knowledge Assessment Engine — API & Integration Contract

## 1. Assessment Lifecycle & Data Flow

The assessment engine evaluates theoretical, foundational, and domain knowledge through server-authoritative scoring.

```
Learner Browses Assessments (GET /api/v1/assessments)
                      │
                      ▼
Select Assessment & Start Attempt (POST /api/v1/assessments/{id}/attempts)
                      │  Server calculates started_at and expires_at
                      ▼
Receive Safe Questions (Questions returned with NO answer keys or explanations)
                      │
                      ▼
Submit Answers (POST /api/v1/attempts/{id}/answers)
                      │  Answer recorded; NO correctness feedback leaked
                      ▼
Finalize & Submit (POST /api/v1/attempts/{id}/submit)
                      │  Server-side deterministic score calculation
                      ▼
Receive Immutable Outcome (GET /api/v1/attempts/{id}/result)
```

---

## 2. Critical Security & Anti-Leakage Invariants

1. **Answer Masking**: `correct_answer`, `is_correct`, and `explanation` fields are never exposed in learner-facing responses before submission.
2. **Server-Authoritative Clock**: The client cannot supply `started_at`, `expires_at`, or remaining duration. Expiration is strictly calculated on the server (`started_at + duration_seconds`).
3. **Immutability of Submitted Attempts**: Once an attempt is finalized, its status transitions to `submitted`. Subsequent answer submissions are rejected, and repeat `/submit` calls idempotently return the existing result without recalculating or mutating scores.
4. **IDOR Prevention**: All attempt operations verify that the authenticated token subject matches `attempt.profile_id`.

---

## 3. API Endpoints Specification

### 3.1 List Assessments
- **Endpoint**: `GET /api/v1/assessments`
- **Auth**: Optional / Public (Learners view `published` assessments only).
- **Query Params**: `skill_id`, `role_id`, `search`, `page`, `page_size`.
- **Response**: `PaginatedResponse[AssessmentPublic]`.

### 3.2 Get Assessment Details
- **Endpoint**: `GET /api/v1/assessments/{assessment_id}`
- **Auth**: Optional / Public.
- **Response**: `AssessmentDetailPublic` with list of `AssessmentQuestionPublic` (Options included, correct answers stripped).

### 3.3 Start Assessment Attempt
- **Endpoint**: `POST /api/v1/assessments/{assessment_id}/attempts`
- **Auth**: `Bearer <token>` (Required).
- **Response**: `AttemptStartResponse` (Contains `id`, `started_at`, `expires_at`, `questions`).

### 3.4 Record Answer
- **Endpoint**: `POST /api/v1/attempts/{attempt_id}/answers`
- **Auth**: `Bearer <token>` (Must be owner of attempt).
- **Request Body**:
  ```json
  {
    "question_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "selected_option": "b"
  }
  ```
- **Response**: `AnswerSubmitResponse` (`id`, `attempt_id`, `question_id`, `answered_at`).

### 3.5 Submit & Evaluate Attempt
- **Endpoint**: `POST /api/v1/attempts/{attempt_id}/submit`
- **Auth**: `Bearer <token>` (Must be owner of attempt).
- **Response**: `AssessmentResultResponse`:
  ```json
  {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "attempt_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "assessment_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "assessment_title": "Python & FastAPI Fundamentals",
    "total_questions": 10,
    "answered_questions": 10,
    "correct_answers": 8,
    "total_points": 100,
    "earned_points": 80,
    "score_percentage": 80.0,
    "passed": true,
    "passing_score": 70,
    "evaluated_at": "2026-08-30T21:40:00Z",
    "breakdown": {
      "skill_id": "...",
      "passing_score": 70,
      "score_percentage": 80.0,
      "passed": true
    }
  }
  ```

### 3.6 Get Finalized Result Report
- **Endpoint**: `GET /api/v1/attempts/{attempt_id}/result`
- **Auth**: `Bearer <token>` (Attempt owner or platform admin).
- **Response**: `AssessmentResultResponse`.
