# Security Model & Access Control Specification

## 1. Identity & Authentication Architecture

Rising Skills delegates credential management and identity issuance to **Supabase Auth (GoTrue)**. The backend acts as a zero-trust mediator.

```
Client (Next.js) ──► Authorization: Bearer <Supabase_JWT> ──► FastAPI Security Dependency
                                                                         │
                                                                         ▼
                                                                Extract & Validate JWT
                                                                (Signature, exp, iss)
                                                                         │
                                                                         ▼
                                                              Build AuthenticatedUser DTO
                                                              (id, email, role, org_ids)
```

---

## 2. Platform & Organization Roles

### Platform Roles (Assigned at Profile Level)
- `learner`: Candidates taking assessments, submitting challenges, logging experiences, building evidence, and applying to opportunities.
- `employer`: Corporate users creating opportunities, reviewing applications, sponsoring challenges, evaluating submissions, and verifying skills.
- `admin`: System administrators managing platform taxonomies, compliance, and dispute resolution.

### Organization Roles (Assigned at `organization_members` Level)
- `owner`: Full control over organization settings, billing, opportunities, and membership.
- `admin`: Manages opportunities, members, challenges, and evaluations.
- `recruiter`: Reviews applications, evaluates candidates, manages matches.
- `evaluator`: Grades practical submissions and provides employer feedback.
- `member`: Standard organization view permissions.

---

## 3. Defense-in-Depth Security Rules

1. **Zero Trust from Request Body**: Any request modifying profile-owned resources ignores any `profile_id` provided in JSON bodies. The identity is strictly taken from `current_user.id` resolved by FastAPI dependency injection.
2. **Assessment Answer Masking**: Questions delivered via `GET /api/v1/assessments/{id}` or during attempts must strip `correct_answer`, `options.is_correct`, and `explanation` at the serialization layer.
3. **Immutability of Finalized Records**: Completed assessment attempts, finalized evaluations, verified evidence records, and audit logs are append-only / immutable.
4. **Append-Only Audit Trail**: Every sensitive operation (role change, verification status transition, manual evaluation override) writes to `audit_logs`.
