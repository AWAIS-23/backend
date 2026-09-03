import jwt
from typing import Any
from pydantic import BaseModel, Field
from app.core.constants import UserRole, OrgRole
from app.core.exceptions import InvalidTokenException

# Algorithms supported for Supabase JWT verification.
# - HS256: legacy symmetric tokens (signed with SUPABASE_JWT_SECRET)
# - ES256: current asymmetric tokens (signed with ECDSA, verified via JWKS)
SUPPORTED_ALGORITHMS = ["HS256", "ES256"]


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
    jwks_url: str | None = None,
) -> AuthenticatedUser:
    """
    Decodes and validates a Supabase JWT.

    Supports two signing regimes:
    - **ES256** (current): asymmetric ECDSA tokens. The public key is fetched
      from Supabase's JWKS endpoint (``jwks_url``) and selected via the token's
      ``kid`` header. This is what Supabase Auth issues by default now.
    - **HS256** (legacy): symmetric HMAC tokens signed with ``secret``
      (``SUPABASE_JWT_SECRET``). Retained for backward compatibility and tests.

    Security:
    - Enforces signature verification (never decodes without it).
    - Rejects expired tokens.
    - Never trusts arbitrary client claims without cryptographic verification.
    """
    if not token:
        raise InvalidTokenException("Missing authentication token or verification secret.")

    if algorithms is None:
        algorithms = SUPPORTED_ALGORITHMS

    # Peek at the header (unverified) to pick the right verification strategy.
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenException(f"Invalid authentication token: {str(exc)}")

    token_alg = unverified_header.get("alg")

    if token_alg == "ES256":
        # Asymmetric verification via JWKS public key.
        if not jwks_url:
            raise InvalidTokenException(
                "ES256 token received but JWKS URL is not configured. "
                "Set SUPABASE_URL or SUPABASE_JWKS_URL."
            )
        try:
            from jwt import PyJWKClient

            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated" if verify_aud else None,
                options={"verify_aud": verify_aud},
            )
        except jwt.ExpiredSignatureError:
            raise InvalidTokenException("Authentication token has expired.")
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenException(f"Invalid authentication token: {str(exc)}")
    else:
        # Symmetric (HS256) verification with the JWT secret.
        if not secret:
            raise InvalidTokenException("Missing verification secret for HS256 token.")
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
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
