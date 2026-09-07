from fastapi import Depends, Header
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationRequiredException, InvalidTokenException
from app.core.security import AuthenticatedUser, verify_supabase_jwt


async def get_current_user(
    authorization: str | None = Header(default=None, description="Bearer token from Supabase Auth"),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """
    Extracts and validates the Supabase JWT from the Authorization header.
    
    Returns:
        AuthenticatedUser with trusted claims.
        
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
    return verify_supabase_jwt(
        token=token,
        secret=settings.SUPABASE_JWT_SECRET,
        verify_aud=False if settings.APP_ENV == "testing" else True,
        jwks_url=jwks_url,
    )


async def get_optional_current_user(
    authorization: str | None = Header(default=None, description="Optional bearer token"),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser | None:
    """Authenticate when a token is supplied, while allowing public requests."""
    if not authorization:
        return None
    return await get_current_user(authorization=authorization, settings=settings)
