import logging
import uuid
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.core.constants import UserRole
from app.core.exceptions import AuthenticationRequiredException, InvalidTokenException
from app.core.security import AuthenticatedUser, verify_supabase_jwt
from app.dependencies.database import get_db
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.profile_repo import ProfileRepository

logger = logging.getLogger("rising_skills.auth")


async def get_current_user(
    authorization: str | None = Header(default=None, description="Bearer token from Supabase Auth"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """
    Extracts and validates the Supabase JWT from the Authorization header,
    then resolves organization memberships directly from the database based on profile ID.
    
    Returns:
        AuthenticatedUser with trusted claims and database-backed org roles.
        
    Raises:
        AuthenticationRequiredException (401) if header is missing or malformed.
        InvalidTokenException (401) if token signature or expiry fails.
    """
    if not authorization:
        raise AuthenticationRequiredException("Authorization header is missing.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationRequiredException(
            "Authorization header must follow format: 'Bearer <token>'."
        )

    token = parts[1]
    jwks_url = settings.SUPABASE_JWKS_URL
    if not jwks_url:
        base = settings.SUPABASE_URL.rstrip("/")
        jwks_url = f"{base}/auth/v1/.well-known/jwks.json"
    user = verify_supabase_jwt(
        token=token,
        secret=settings.SUPABASE_JWT_SECRET,
        verify_aud=False if settings.APP_ENV == "testing" else True,
        jwks_url=jwks_url,
    )

    # Fetch user's organizations from the database based on their profile ID
    try:
        profile_uuid = uuid.UUID(user.id)
        org_repo = OrganizationRepository(session)
        db_org_roles = await org_repo.get_org_roles_for_profile(profile_uuid)
        if db_org_roles:
            user.org_roles = {**user.org_roles, **db_org_roles}

        # Synchronize role if profile exists in DB or user belongs to an organization
        profile_repo = ProfileRepository(session)
        profile = await profile_repo.get_by_id(profile_uuid)
        if profile and profile.role in (UserRole.EMPLOYER, UserRole.ADMIN) and user.role == UserRole.LEARNER:
            user.role = profile.role
        elif db_org_roles and user.role == UserRole.LEARNER:
            user.role = UserRole.EMPLOYER
    except Exception as exc:
        logger.warning(f"Failed to fetch organization roles for user {user.id}: {exc}")

    return user


async def get_optional_current_user(
    authorization: str | None = Header(default=None, description="Optional bearer token"),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedUser | None:
    """Authenticate when a token is supplied, while allowing public requests."""
    if not authorization:
        return None
    return await get_current_user(authorization=authorization, settings=settings, session=session)
