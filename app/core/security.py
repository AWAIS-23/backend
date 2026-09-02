import jwt
from typing import Any
from pydantic import BaseModel, Field
from app.core.constants import UserRole, OrgRole
from app.core.exceptions import InvalidTokenException


class AuthenticatedUser(BaseModel):
    """Immutable identity representation derived strictly from verified Supabase JWT claims."""
    id: str = Field(..., description="Supabase auth UUID (sub claim)")
    email: str | None = None
    role: UserRole = Field(default=UserRole.LEARNER, description="Global platform role")
    org_roles: dict[str, OrgRole] = Field(
        default_factory=dict,
        description="Mapping of organization_id to OrgRole"
    )
    raw_claims: dict[str, Any] = Field(default_factory=dict)


def verify_supabase_jwt(
    token: str,
    secret: str,
    algorithms: list[str] | None = None,
    verify_aud: bool = True,
) -> AuthenticatedUser:
    """
    Decodes and validates a Supabase JWT.
    
    Security:
    - Enforces signature verification against SUPABASE_JWT_SECRET.
    - Rejects expired tokens.
    - Never trusts arbitrary client claims without cryptographic verification.
    """
    if not token or not secret:
        raise InvalidTokenException("Missing authentication token or verification secret.")

    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=algorithms,
            audience="authenticated" if verify_aud else None,
            options={"verify_aud": verify_aud},
        )
    except jwt.ExpiredSignatureError:
        raise InvalidTokenException("Authentication token has expired.")
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenException(f"Invalid authentication token: {str(exc)}")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException("Token payload is missing subject claim ('sub').")

    # Extract role from Supabase metadata if present
    app_metadata = payload.get("app_metadata", {})
    user_metadata = payload.get("user_metadata", {})

    raw_role = app_metadata.get("role") or user_metadata.get("role") or payload.get("role")
    role = UserRole.LEARNER
    if raw_role:
        try:
            role = UserRole(raw_role)
        except ValueError:
            role = UserRole.LEARNER

    # Extract organization roles if embedded in claims
    raw_org_roles = app_metadata.get("org_roles", {})
    org_roles: dict[str, OrgRole] = {}
    if isinstance(raw_org_roles, dict):
        for org_id, org_role_str in raw_org_roles.items():
            try:
                org_roles[org_id] = OrgRole(org_role_str)
            except ValueError:
                pass

    return AuthenticatedUser(
        id=user_id,
        email=payload.get("email") or user_metadata.get("email"),
        role=role,
        org_roles=org_roles,
        raw_claims=payload,
    )
