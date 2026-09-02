from enum import StrEnum


class UserRole(StrEnum):
    LEARNER = "learner"
    EMPLOYER = "employer"
    ADMIN = "admin"


class OrgRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    EVALUATOR = "evaluator"
    MEMBER = "member"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class ExperienceType(StrEnum):
    EMPLOYER_PROJECT = "employer_project"
    INTERNSHIP = "internship"
    APPRENTICESHIP = "apprenticeship"
    FREELANCE = "freelance"
    PRACTICAL_CHALLENGE = "practical_challenge"


class ExperienceStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    VERIFIED = "verified"
    CANCELLED = "cancelled"


class NotificationType(StrEnum):
    APPLICATION_STATUS = "application_status"
    EXPERIENCE_CREATED = "experience_created"
    EXPERIENCE_COMPLETED = "experience_completed"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    EVIDENCE_VERIFIED = "evidence_verified"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    EVALUATED = "evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ChallengeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EvidenceStatus(StrEnum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class EvidenceSourceType(StrEnum):
    ASSESSMENT = "assessment"
    CHALLENGE_SUBMISSION = "challenge_submission"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TRUE_FALSE = "true_false"


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class OpportunityType(StrEnum):
    JOB = "job"
    INTERNSHIP = "internship"
    APPRENTICESHIP = "apprenticeship"
    PROJECT = "project"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    # Assessment
    ATTEMPT_EXPIRED = "ATTEMPT_EXPIRED"
    ATTEMPT_ALREADY_COMPLETED = "ATTEMPT_ALREADY_COMPLETED"
    ATTEMPT_NOT_IN_PROGRESS = "ATTEMPT_NOT_IN_PROGRESS"
    INVALID_QUESTION_FOR_ASSESSMENT = "INVALID_QUESTION_FOR_ASSESSMENT"
    INVALID_OPTION_SELECTED = "INVALID_OPTION_SELECTED"
    SUBMISSION_NOT_ALLOWED = "SUBMISSION_NOT_ALLOWED"
    # Phase 3 — Challenges & Submissions
    SUBMISSION_DEADLINE_PASSED = "SUBMISSION_DEADLINE_PASSED"
    DUPLICATE_SUBMISSION = "DUPLICATE_SUBMISSION"
    INVALID_SUBMISSION_STATE = "INVALID_SUBMISSION_STATE"
    # Phase 3 — Evaluations
    EVALUATION_FORBIDDEN = "EVALUATION_FORBIDDEN"
    RUBRIC_VALIDATION_ERROR = "RUBRIC_VALIDATION_ERROR"
    SELF_EVALUATION_FORBIDDEN = "SELF_EVALUATION_FORBIDDEN"
    # Phase 3 — Evidence & Verification
    EVIDENCE_ALREADY_VERIFIED = "EVIDENCE_ALREADY_VERIFIED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    VERIFICATION_FORBIDDEN = "VERIFICATION_FORBIDDEN"
    SELF_VERIFICATION_FORBIDDEN = "SELF_VERIFICATION_FORBIDDEN"
    # Phase 4 — Opportunities, Matching & Applications
    OPPORTUNITY_NOT_PUBLISHED = "OPPORTUNITY_NOT_PUBLISHED"
    OPPORTUNITY_CLOSED = "OPPORTUNITY_CLOSED"
    INVALID_OPPORTUNITY_STATE = "INVALID_OPPORTUNITY_STATE"
    DUPLICATE_APPLICATION = "DUPLICATE_APPLICATION"
    INVALID_APPLICATION_STATUS = "INVALID_APPLICATION_STATUS"
    APPLICATION_DEADLINE_PASSED = "APPLICATION_DEADLINE_PASSED"
    # Phase 5 — Experience, Feedback & Analytics
    EXPERIENCE_NOT_ACTIVE = "EXPERIENCE_NOT_ACTIVE"
    EXPERIENCE_ALREADY_COMPLETED = "EXPERIENCE_ALREADY_COMPLETED"
    APPLICATION_NOT_ACCEPTED = "APPLICATION_NOT_ACCEPTED"
    DUPLICATE_FEEDBACK = "DUPLICATE_FEEDBACK"
    FEEDBACK_FORBIDDEN = "FEEDBACK_FORBIDDEN"
    # General
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
