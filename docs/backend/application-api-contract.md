# Application & Matching API Integration Contract

## 1. Endpoints Specification

### 1.1 Apply to Opportunity
- **Method**: `POST /api/v1/opportunities/{opportunity_id}/apply`
- **Auth**: `Bearer <token>` (Authenticated Learner).
- **Request Body**:
  ```json
  {
    "cover_note": "I have completed verified practical challenges in FastAPI and Python."
  }
  ```
- **Response**: `ApplicationPublic` (status: `submitted`).
- **Errors**:
  - `400 OPPORTUNITY_NOT_PUBLISHED` (if draft/closed)
  - `400 APPLICATION_DEADLINE_PASSED` (if past deadline)
  - `409 DUPLICATE_APPLICATION` (if already applied)

### 1.2 List Learner's Applications
- **Method**: `GET /api/v1/applications`
- **Auth**: `Bearer <token>` (Learner).
- **Query Params**: `status`, `page`, `page_size`.
- **Response**: `PaginatedResponse[ApplicationPublic]`.

### 1.3 Withdraw Application
- **Method**: `PATCH /api/v1/applications/{application_id}/withdraw`
- **Auth**: `Bearer <token>` (Applicant).
- **Response**: `ApplicationPublic` (status: `withdrawn`).

### 1.4 Review Candidate Application
- **Method**: `PATCH /api/v1/applications/{application_id}/status`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in opportunity's organization or `UserRole.ADMIN`).
- **Request Body**:
  ```json
  {
    "status": "shortlisted"
  }
  ```
- **Response**: `ApplicationPublic`.

### 1.5 List Matched Opportunities for Learner
- **Method**: `GET /api/v1/matches/opportunities`
- **Auth**: `Bearer <token>` (Learner).
- **Query Params**: `min_score`, `page`, `page_size`.
- **Response**: `PaginatedResponse[MatchPublic]`.

### 1.6 List Candidate Matches for Opportunity
- **Method**: `GET /api/v1/opportunities/{opportunity_id}/matches`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in organization or `UserRole.ADMIN`).
- **Query Params**: `min_score`, `page`, `page_size`.
- **Response**: `PaginatedResponse[MatchPublic]`.
