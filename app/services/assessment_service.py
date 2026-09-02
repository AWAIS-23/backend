import math
import uuid
import logging
from typing import Sequence
from app.core.constants import AssessmentStatus, UserRole
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.repositories.assessment_repo import AssessmentRepository
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentDetailPublic,
    AssessmentPublic,
    AssessmentQuestionPublic,
    QuestionOption,
)
from app.schemas.common import PaginatedResponse

logger = logging.getLogger("rising_skills.services.assessment")


class AssessmentService:
    def __init__(self, assessment_repo: AssessmentRepository):
        self.assessment_repo = assessment_repo

    async def list_assessments(
        self,
        skill_id: uuid.UUID | None = None,
        role_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        user_role: UserRole = UserRole.LEARNER,
    ) -> PaginatedResponse[AssessmentPublic]:
        skip = (page - 1) * page_size
        # Learners only see PUBLISHED assessments; Admins can see all
        status_filter = AssessmentStatus.PUBLISHED if user_role == UserRole.LEARNER else None

        items, total = await self.assessment_repo.list_assessments(
            skill_id=skill_id,
            role_id=role_id,
            status=status_filter,
            search=search,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[AssessmentPublic](
            items=[AssessmentPublic.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_assessment_detail(
        self,
        assessment_id: uuid.UUID,
        user_role: UserRole = UserRole.LEARNER,
    ) -> AssessmentDetailPublic:
        assessment = await self.assessment_repo.get_by_id_with_questions(assessment_id)
        if not assessment:
            raise ResourceNotFoundException(resource="Assessment", identifier=assessment_id)

        # Visibility guard for draft assessments
        if user_role == UserRole.LEARNER and assessment.status != AssessmentStatus.PUBLISHED:
            raise PermissionDeniedException("This assessment is not currently published or available.")

        # Serialize questions to learner-safe DTOs (Stripping correct_answer & explanation)
        safe_questions = []
        for q in assessment.questions:
            if not q.is_active and user_role == UserRole.LEARNER:
                continue

            raw_options = q.options if isinstance(q.options, list) else []
            parsed_options = [
                QuestionOption(id=str(opt.get("id")), text=str(opt.get("text")))
                for opt in raw_options
                if isinstance(opt, dict)
            ]

            safe_questions.append(
                AssessmentQuestionPublic(
                    id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    options=parsed_options,
                    points=q.points,
                    display_order=q.display_order,
                )
            )

        detail = AssessmentDetailPublic.model_validate(assessment)
        detail.questions = safe_questions
        return detail

    async def create_assessment(
        self,
        creator_id: uuid.UUID,
        data: AssessmentCreate,
    ) -> Assessment:
        assessment = Assessment(
            title=data.title.strip(),
            description=data.description,
            skill_id=data.skill_id,
            role_id=data.role_id,
            difficulty=data.difficulty,
            duration_seconds=data.duration_seconds,
            passing_score=data.passing_score,
            status=data.status,
            created_by=creator_id,
        )

        question_entities = []
        for q_data in data.questions:
            options_dict = [opt.model_dump() for opt in q_data.options]
            q = AssessmentQuestion(
                question_text=q_data.question_text,
                question_type=q_data.question_type,
                options=options_dict,
                correct_answer=q_data.correct_answer.strip(),
                points=q_data.points,
                display_order=q_data.display_order,
                explanation=q_data.explanation,
                is_active=True,
            )
            question_entities.append(q)

        created = await self.assessment_repo.create_with_questions(assessment, question_entities)
        logger.info(f"Assessment '{created.title}' created with {len(question_entities)} questions.")
        return created
