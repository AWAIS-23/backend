# Rising Skills — Experience API Contract

## Domain: Practical Work Experiences & Engagements

---

## 1. Endpoints Overview

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/experiences/me` | List learner's experiences (paginated, filterable by status) | Learner / Admin |
| `GET` | `/api/v1/experiences/{experience_id}` | Retrieve experience details with relations | Owner / Employer / Admin |
| `POST` | `/api/v1/experiences` | Create self-reported or employer-created experience | Learner / Employer / Admin |
| `POST` | `/api/v1/experiences/from-application/{application_id}` | Instantiate experience from an accepted application | Employer / Admin |
| `POST` | `/api/v1/experiences/{experience_id}/complete` | Transition experience to completed status | Owner / Employer / Admin |

---

## 2. Request & Response Schemas

### `POST /api/v1/experiences/from-application/{application_id}`

**Headers:**
`Authorization: Bearer <employer_jwt>`

**Status Code:** `201 Created`

**Response (`ExperiencePublic`):**
```json
{
  "id": "11111111-2222-3333-4444-555555555555",
  "profile_id": "11111111-1111-1111-1111-111111111111",
  "organization_id": "77777777-1111-2222-3333-444444444444",
  "opportunity_id": "aaaaaaaa-7777-8888-9999-000000000000",
  "application_id": "cccccccc-1111-2222-3333-444444444444",
  "title": "Backend Engineer Intern",
  "description": "Build APIs for Rising Skills.",
  "experience_type": "internship",
  "started_at": "2026-08-30T17:40:00Z",
  "ended_at": null,
  "status": "active",
  "verification_status": "verified",
  "created_at": "2026-08-30T17:40:00Z",
  "updated_at": "2026-08-30T17:40:00Z"
}
```

---

## 3. Invariants & Business Logic

1. **Application Gate**:
   - Creating an experience from an application strictly requires `application.status == "accepted"`.
   - Any attempt on `submitted`, `reviewing`, `shortlisted`, `rejected`, or `withdrawn` returns HTTP `400 Bad Request` (`APPLICATION_NOT_ACCEPTED`).
2. **Lifecycle Transitions**:
   - `active` $\to$ `completed` (sets `ended_at` timestamp).
   - Re-completing an already completed experience returns HTTP `400 Bad Request` (`EXPERIENCE_ALREADY_COMPLETED`).
3. **Notification Triggering**:
   - Activation and completion automatically dispatch in-app notifications to the learner.
