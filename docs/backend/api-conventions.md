# API Design Conventions & Error Contract

## 1. RESTful Conventions

- **Version Prefix**: All domain endpoints must use `/api/v1/`.
- **Plural Nouns**: Resource collections use plural naming (e.g. `/api/v1/assessments`, `/api/v1/skills`, `/api/v1/opportunities`).
- **Standard HTTP Methods**:
  - `GET`: Safe, idempotent read operations.
  - `POST`: Resource creation, state transition triggers (e.g., `/attempts/{id}/submit`).
  - `PATCH`: Partial resource updates.
  - `DELETE`: Resource removal / soft deactivation.

---

## 2. Centralized Error Contract (RFC 7807 Compliant)

All error responses return a standardized, machine-readable JSON structure:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Assessment with id '550e8400-e29b-41d4-a716-446655440000' not found.",
    "details": {},
    "timestamp": "2026-08-30T11:40:00Z"
  }
}
```

### Standard Error Codes
- `VALIDATION_ERROR` (422)
- `AUTHENTICATION_REQUIRED` (401)
- `INVALID_TOKEN` (401)
- `PERMISSION_DENIED` (403)
- `RESOURCE_NOT_FOUND` (404)
- `RESOURCE_CONFLICT` (409)
- `ATTEMPT_EXPIRED` (400)
- `ATTEMPT_ALREADY_COMPLETED` (400)
- `INTERNAL_SERVER_ERROR` (500)

---

## 3. Standard Pagination & Filtering

Query parameters for collection endpoints:
- `page`: integer $\ge 1$ (default: 1)
- `page_size`: integer between 1 and 100 (default: 20)

Paginated response wrapper:
```json
{
  "items": [...],
  "total": 120,
  "page": 1,
  "page_size": 20,
  "pages": 6
}
```
