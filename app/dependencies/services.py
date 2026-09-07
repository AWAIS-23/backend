from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.dependencies.database import get_db
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.application_repo import ApplicationRepository
from app.repositories.assessment_answer_repo import AssessmentAnswerRepository
from app.repositories.assessment_attempt_repo import AssessmentAttemptRepository
from app.repositories.assessment_repo import AssessmentRepository
from app.repositories.assessment_result_repo import AssessmentResultRepository
from app.repositories.challenge_repo import ChallengeRepository
from app.repositories.evaluation_repo import EvaluationRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.education_repo import EducationRepository
from app.repositories.experience_repo import ExperienceRepository
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.matching_repo import MatchingRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.opportunity_repo import OpportunityRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.skill_repo import SkillRepository
from app.repositories.submission_repo import SubmissionRepository
from app.repositories.verification_repo import VerificationRepository
from app.services.analytics_service import AnalyticsService
from app.services.application_service import ApplicationService
from app.services.assessment_attempt_service import AssessmentAttemptService
from app.services.assessment_evaluation_service import AssessmentEvaluationService
from app.services.assessment_service import AssessmentService
from app.services.challenge_service import ChallengeService
from app.services.evaluation_service import EvaluationService
from app.services.evidence_service import EvidenceService
from app.services.education_service import EducationService
from app.services.experience_service import ExperienceService
from app.services.feedback_service import FeedbackService
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.services.opportunity_service import OpportunityService
from app.services.organization_service import OrganizationService
from app.services.profile_service import ProfileService
from app.services.role_service import RoleService
from app.services.skill_service import SkillService
from app.services.submission_service import SubmissionService
from app.services.verification_service import VerificationService


def get_ai_service(
    settings: Settings = Depends(get_settings),
):
    """
    Construct the AIService with the configured AI provider.

    Returns None when AI is disabled or not configured, allowing dependent
    services to degrade gracefully while still serving deterministic data.

    Returns None when:
    - AI_ENABLED is False (feature disabled)
    - GROQ_API_KEY is missing (provider not configured)
    """
    from app.ai.groq_client import GroqProvider
    from app.ai.service import AIService

    if not settings.AI_ENABLED:
        return None

    try:
        provider = GroqProvider(settings)
    except Exception:
        return None

    return AIService(provider)


def get_profile_service(session: AsyncSession = Depends(get_db)) -> ProfileService:
    repo = ProfileRepository(session)
    return ProfileService(repo)


def get_organization_service(session: AsyncSession = Depends(get_db)) -> OrganizationService:
    org_repo = OrganizationRepository(session)
    profile_repo = ProfileRepository(session)
    return OrganizationService(org_repo, profile_repo)


def get_skill_service(session: AsyncSession = Depends(get_db)) -> SkillService:
    repo = SkillRepository(session)
    return SkillService(repo)


def get_role_service(session: AsyncSession = Depends(get_db)) -> RoleService:
    role_repo = RoleRepository(session)
    skill_repo = SkillRepository(session)
    return RoleService(role_repo, skill_repo)


def get_assessment_service(session: AsyncSession = Depends(get_db)) -> AssessmentService:
    repo = AssessmentRepository(session)
    return AssessmentService(repo)


def get_assessment_attempt_service(session: AsyncSession = Depends(get_db)) -> AssessmentAttemptService:
    attempt_repo = AssessmentAttemptRepository(session)
    assessment_repo = AssessmentRepository(session)
    answer_repo = AssessmentAnswerRepository(session)
    return AssessmentAttemptService(attempt_repo, assessment_repo, answer_repo)


def get_assessment_evaluation_service(session: AsyncSession = Depends(get_db)) -> AssessmentEvaluationService:
    attempt_repo = AssessmentAttemptRepository(session)
    result_repo = AssessmentResultRepository(session)
    return AssessmentEvaluationService(attempt_repo, result_repo)


def get_challenge_service(session: AsyncSession = Depends(get_db)) -> ChallengeService:
    repo = ChallengeRepository(session)
    return ChallengeService(repo)


def get_submission_service(session: AsyncSession = Depends(get_db)) -> SubmissionService:
    submission_repo = SubmissionRepository(session)
    challenge_repo = ChallengeRepository(session)
    return SubmissionService(submission_repo, challenge_repo)


def get_evaluation_service(session: AsyncSession = Depends(get_db)) -> EvaluationService:
    eval_repo = EvaluationRepository(session)
    sub_repo = SubmissionRepository(session)
    evi_repo = EvidenceRepository(session)
    return EvaluationService(eval_repo, sub_repo, evi_repo)


def get_evidence_service(session: AsyncSession = Depends(get_db)) -> EvidenceService:
    repo = EvidenceRepository(session)
    return EvidenceService(repo)


def get_education_service(session: AsyncSession = Depends(get_db)) -> EducationService:
    repo = EducationRepository(session)
    return EducationService(repo)


def get_verification_service(session: AsyncSession = Depends(get_db)) -> VerificationService:
    ver_repo = VerificationRepository(session)
    evi_repo = EvidenceRepository(session)
    return VerificationService(ver_repo, evi_repo)


def get_opportunity_service(session: AsyncSession = Depends(get_db)) -> OpportunityService:
    repo = OpportunityRepository(session)
    organization_repo = OrganizationRepository(session)
    return OpportunityService(repo, organization_repo)


def get_matching_service(session: AsyncSession = Depends(get_db)) -> MatchingService:
    matching_repo = MatchingRepository(session)
    opportunity_repo = OpportunityRepository(session)
    evidence_repo = EvidenceRepository(session)
    submission_repo = SubmissionRepository(session)
    return MatchingService(matching_repo, opportunity_repo, evidence_repo, submission_repo)


def get_application_service(session: AsyncSession = Depends(get_db)) -> ApplicationService:
    application_repo = ApplicationRepository(session)
    opportunity_repo = OpportunityRepository(session)
    matching_repo = MatchingRepository(session)
    evidence_repo = EvidenceRepository(session)
    submission_repo = SubmissionRepository(session)
    matching_service = MatchingService(matching_repo, opportunity_repo, evidence_repo, submission_repo)
    return ApplicationService(application_repo, opportunity_repo, matching_service)


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    repo = NotificationRepository(session)
    return NotificationService(repo)


def get_experience_service(session: AsyncSession = Depends(get_db)) -> ExperienceService:
    exp_repo = ExperienceRepository(session)
    app_repo = ApplicationRepository(session)
    notif_repo = NotificationRepository(session)
    notif_service = NotificationService(notif_repo)
    return ExperienceService(exp_repo, app_repo, notif_service)


def get_feedback_service(session: AsyncSession = Depends(get_db)) -> FeedbackService:
    fb_repo = FeedbackRepository(session)
    exp_repo = ExperienceRepository(session)
    notif_repo = NotificationRepository(session)
    notif_service = NotificationService(notif_repo)
    return FeedbackService(fb_repo, exp_repo, notif_service)


def get_analytics_service(session: AsyncSession = Depends(get_db)) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    return AnalyticsService(repo)


def get_skill_gap_service(
    session: AsyncSession = Depends(get_db),
    ai_service=Depends(get_ai_service),
):
    """Construct SkillGapService with matching repository and optional AI service.

    When ai_service is None (AI disabled or misconfigured), SkillGapService
    still serves deterministic match data with ai_explanation=null.
    """
    from app.services.skill_gap_service import SkillGapService

    matching_repo = MatchingRepository(session)
    return SkillGapService(matching_repo, ai_service)


def get_ai_insight_service(
    session: AsyncSession = Depends(get_db),
    ai_service=Depends(get_ai_service),
):
    """Construct AIInsightService with repositories and optional AI service."""
    from app.services.ai_insight_service import AIInsightService

    challenge_repo = ChallengeRepository(session)
    evidence_repo = EvidenceRepository(session)
    skill_repo = SkillRepository(session)
    return AIInsightService(challenge_repo, evidence_repo, skill_repo, ai_service)
