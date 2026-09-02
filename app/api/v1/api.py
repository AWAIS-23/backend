from fastapi import APIRouter
from app.api.v1.routes import (
    analytics,
    applications,
    assessments,
    attempts,
    challenges,
    evidence,
    experiences,
    health,
    matches,
    notifications,
    opportunities,
    organizations,
    profiles,
    roles,
    skills,
    submissions,
    verifications,
)

api_router = APIRouter()

# Register v1 routes
api_router.include_router(health.router)
api_router.include_router(profiles.router)
api_router.include_router(organizations.router)
api_router.include_router(skills.router)
api_router.include_router(roles.router)
api_router.include_router(assessments.router)
api_router.include_router(attempts.router)
api_router.include_router(challenges.router)
api_router.include_router(submissions.router)
api_router.include_router(evidence.router)
api_router.include_router(verifications.router)
api_router.include_router(opportunities.router)
api_router.include_router(applications.router)
api_router.include_router(matches.router)
api_router.include_router(experiences.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
