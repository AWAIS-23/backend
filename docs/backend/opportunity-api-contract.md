# Opportunity API Integration Contract

## 1. Endpoints Specification

### 1.1 List Opportunities
- **Method**: `GET /api/v1/opportunities`
- **Auth**: Optional / Public (Learners view `published` opportunities only).
- **Query Params**: `organization_id`, `search`, `opportunity_type`, `page`, `page_size`.
- **Response**: `PaginatedResponse[OpportunityPublic]`.

### 1.2 Create Opportunity Draft
- **Method**: `POST /api/v1/opportunities`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in organization or `UserRole.ADMIN`).
- **Request Body**:
  ```json
  {
    "organization_id": "99999999-0000-1111-2222-333333333333",
    "title": "Backend Software Engineer",
    "description": "Design async FastAPI services.",
    "opportunity_type": "job",
    "location": "San Francisco, CA",
    "is_remote": true,
    "deadline": "2026-09-30T23:59:59Z",
    "skills": [
      {
        "skill_id": "11110000-1111-2222-3333-444455556666",
        "importance_weight": 0.6
      },
      {
        "skill_id": "22220000-1111-2222-3333-444455556666",
        "importance_weight": 0.4
      }
    ]
  }
  ```
- **Response**: `OpportunityPublic` (status: `draft`).

### 1.3 Get Opportunity Detail
- **Method**: `GET /api/v1/opportunities/{opportunity_id}`
- **Auth**: Optional / Public.
- **Response**: `OpportunityDetailPublic` (includes list of required skills and weights).

### 1.4 Publish Opportunity
- **Method**: `POST /api/v1/opportunities/{opportunity_id}/publish`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in organization or `UserRole.ADMIN`).
- **Response**: `OpportunityPublic` (status: `published`).

### 1.5 Close Opportunity
- **Method**: `POST /api/v1/opportunities/{opportunity_id}/close`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in organization or `UserRole.ADMIN`).
- **Response**: `OpportunityPublic` (status: `closed`).

### 1.6 Set/Update Required Skills
- **Method**: `PUT /api/v1/opportunities/{opportunity_id}/skills`
- **Auth**: `Bearer <token>` (`UserRole.EMPLOYER` in organization or `UserRole.ADMIN`).
- **Request Body**: `list[OpportunitySkillItem]`.
- **Response**: `OpportunityDetailPublic`.
