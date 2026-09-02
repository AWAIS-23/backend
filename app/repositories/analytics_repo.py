import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import ApplicationStatus, ExperienceStatus, OpportunityStatus
from app.models.application import Application
from app.models.experience import Experience
from app.models.experience_feedback import ExperienceFeedback
from app.models.match import Match
from app.models.opportunity import Opportunity
from app.schemas.analytics import OrganizationAnalytics


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_organization_metrics(self, organization_id: uuid.UUID) -> OrganizationAnalytics:
        # 1. Opportunities counts
        opp_total_stmt = select(func.count()).select_from(Opportunity).where(
            Opportunity.organization_id == organization_id
        )
        total_opportunities = (await self.session.execute(opp_total_stmt)).scalar() or 0

        opp_pub_stmt = select(func.count()).select_from(Opportunity).where(
            Opportunity.organization_id == organization_id,
            Opportunity.status == OpportunityStatus.PUBLISHED,
        )
        published_opportunities = (await self.session.execute(opp_pub_stmt)).scalar() or 0

        # 2. Applications counts
        app_base = select(Application).join(Opportunity).where(
            Opportunity.organization_id == organization_id
        )
        app_total_stmt = select(func.count()).select_from(app_base.subquery())
        total_applications = (await self.session.execute(app_total_stmt)).scalar() or 0

        app_short_stmt = select(func.count()).select_from(
            select(Application).join(Opportunity).where(
                Opportunity.organization_id == organization_id,
                Application.status == ApplicationStatus.SHORTLISTED,
            ).subquery()
        )
        shortlisted_applications = (await self.session.execute(app_short_stmt)).scalar() or 0

        app_acc_stmt = select(func.count()).select_from(
            select(Application).join(Opportunity).where(
                Opportunity.organization_id == organization_id,
                Application.status == ApplicationStatus.ACCEPTED,
            ).subquery()
        )
        accepted_applications = (await self.session.execute(app_acc_stmt)).scalar() or 0

        # 3. Experiences counts
        active_exp_stmt = select(func.count()).select_from(Experience).where(
            Experience.organization_id == organization_id,
            Experience.status == ExperienceStatus.ACTIVE,
        )
        active_experiences = (await self.session.execute(active_exp_stmt)).scalar() or 0

        comp_exp_stmt = select(func.count()).select_from(Experience).where(
            Experience.organization_id == organization_id,
            Experience.status == ExperienceStatus.COMPLETED,
        )
        completed_experiences = (await self.session.execute(comp_exp_stmt)).scalar() or 0

        ver_exp_stmt = select(func.count()).select_from(Experience).where(
            Experience.organization_id == organization_id,
            Experience.status == ExperienceStatus.VERIFIED,
        )
        verified_experiences = (await self.session.execute(ver_exp_stmt)).scalar() or 0

        # 4. Average match score
        avg_match_stmt = select(func.avg(Match.overall_score)).join(Opportunity).where(
            Opportunity.organization_id == organization_id
        )
        avg_match = (await self.session.execute(avg_match_stmt)).scalar()
        average_match_score = round(float(avg_match), 2) if avg_match is not None else 0.0

        # 5. Average feedback rating
        avg_fb_stmt = select(func.avg(ExperienceFeedback.overall_rating)).where(
            ExperienceFeedback.organization_id == organization_id
        )
        avg_fb = (await self.session.execute(avg_fb_stmt)).scalar()
        average_feedback_rating = round(float(avg_fb), 2) if avg_fb is not None else 0.0

        return OrganizationAnalytics(
            organization_id=organization_id,
            total_opportunities=total_opportunities,
            published_opportunities=published_opportunities,
            total_applications=total_applications,
            shortlisted_applications=shortlisted_applications,
            accepted_applications=accepted_applications,
            active_experiences=active_experiences,
            completed_experiences=completed_experiences,
            verified_experiences=verified_experiences,
            average_match_score=average_match_score,
            average_feedback_rating=average_feedback_rating,
        )
