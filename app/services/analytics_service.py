import uuid
import logging
from app.core.constants import OrgRole, UserRole
from app.core.exceptions import PermissionDeniedException
from app.core.security import AuthenticatedUser
from app.repositories.analytics_repo import AnalyticsRepository
from app.schemas.analytics import OrganizationAnalytics

logger = logging.getLogger("rising_skills.services.analytics")


class AnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepository):
        self.analytics_repo = analytics_repo

    async def get_organization_analytics(
        self,
        organization_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> OrganizationAnalytics:
        if current_user.role != UserRole.ADMIN:
            org_role = current_user.org_roles.get(str(organization_id))
            if current_user.role != UserRole.EMPLOYER or org_role not in [OrgRole.OWNER, OrgRole.ADMIN, OrgRole.RECRUITER, OrgRole.EVALUATOR]:
                raise PermissionDeniedException("You lack authorization to access analytics for this organization.")

        metrics = await self.analytics_repo.get_organization_metrics(organization_id)
        logger.info(f"Analytics generated for organization '{organization_id}' by user '{current_user.id}'.")
        return metrics
