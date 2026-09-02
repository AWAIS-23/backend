# Rising Skills — Backend Phase 5 Architectural Audit

## Experience, Feedback & Employer Workflow

---

## 1. Existing Reusable Components & Entity Audit

| Domain / Concept | Existing Status | Phase 5 Reuse Plan |
|---|---|---|
| **Profiles** (`app/models/profile.py`) | Completed in Phase 1 | `Experience.profile_id`, `ExperienceFeedback.profile_id`, `Notification.profile_id` |
| **Organizations** (`app/models/organization.py`) | Completed in Phase 1 | `Experience.organization_id`, `ExperienceFeedback.organization_id` |
| **Organization Members** (`OrganizationMember`) | Completed in Phase 1 | Org RBAC validation for employers creating experiences and submitting feedback |
| **Opportunities** (`app/models/opportunity.py`) | Completed in Phase 4 | `Experience.opportunity_id` link |
| **Applications** (`app/models/application.py`) | Completed in Phase 4 | Gate for experience creation (`Application.status == accepted`) |
| **Evidence & Verification** (`app/models/evidence.py`) | Completed in Phase 3 | Preserves distinction: Feedback $\ne$ Verified Evidence |
| **Constants / Enums** (`app/core/constants.py`) | `ExperienceType`, `VerificationStatus` already defined | Add `ExperienceStatus`, `NotificationType`, Phase 5 ErrorCodes |
| **Auth & Security** (`app/dependencies/auth.py`, `roles.py`) | Verified JWT claims | Derive identity and org membership from JWT claims |
| **Base Repository & Session** | `BaseRepository[T]`, `TimestampMixin` | Clean async repositories & transactions |

---

## 2. Phase 5 Entity Design (No Duplication)

1. **`Experience`** (`app/models/experience.py`):
   - Practical work engagement performed by a candidate.
   - Tied to `profile_id`, optional `organization_id`, `opportunity_id`, `application_id`.
   - Lifecycle: `draft` $\to$ `active` $\to$ `completed` $\to$ `verified`.
2. **`ExperienceFeedback`** (`app/models/experience_feedback.py`):
   - Structured employer feedback evaluating a candidate's performance across standard dimensions (communication, technical, problem solving, teamwork, professionalism, strengths, areas for improvement).
   - Unique per `(experience_id, reviewer_id)`.
3. **`Notification`** (`app/models/notification.py`):
   - In-app notification foundation recording lifecycle events (`application_status`, `experience_created`, `feedback_submitted`, `evidence_verified`).

---

## 3. Key Architectural & Security Invariants

1. **Gate on Application Acceptance**:
   - An employer can only instantiate an `Experience` from an application if `application.status == ApplicationStatus.ACCEPTED`.
2. **Strict Identity Derivation**:
   - `profile_id` for learners and `reviewer_id` for employers are derived strictly from cryptographically verified Supabase JWT claims (`AuthenticatedUser.id`).
3. **Organization Isolation**:
   - Employer of Org A cannot create experiences, view applications, or submit feedback for Org B.
4. **Feedback $\ne$ Verified Evidence**:
   - Subjective employer feedback is tracked for candidate growth and analytics, but does not automatically bypass the evidence verification state machine.
5. **Zero AI in Core Workflow**:
   - Verification and status transitions are governed purely by authorized human actions.

---

## 4. Planned Migration

- Alembic revision: `005_phase5_experience_feedback_notifications`
- Parent revision: `004_phase4`
