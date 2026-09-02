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
    return verify_supabase_jwt(
        token=token,
        secret=settings.SUPABASE_JWT_SECRET,
        verify_aud=False if settings.APP_ENV == "testing" else True,
    )
