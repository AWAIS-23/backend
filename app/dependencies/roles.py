from typing import Callable
from fastapi import Depends, Request
from app.core.constants import OrgRole, UserRole
from app.core.exceptions import PermissionDeniedException
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user


def require_role(allowed_roles: list[UserRole]) -> Callable[..., AuthenticatedUser]:
    """
    Dependency factory enforcing platform-level role authorization.
    Example: Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN]))
    """
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedException(
                f"Action requires one of the following roles: {[r.value for r in allowed_roles]}."
            )
        return current_user

    return role_checker


def require_org_role(
    allowed_roles: list[OrgRole],
    org_id_field: str = "org_id",
) -> Callable[..., AuthenticatedUser]:
    """
    Dependency factory enforcing organization-level role authorization.
    Checks if current_user has the required OrgRole in the target organization.
    """
    async def org_role_checker(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        # Platform admins bypass organization role checks
        if current_user.role == UserRole.ADMIN:
            return current_user

        org_id = request.path_params.get(org_id_field)
        if not org_id:
            raise PermissionDeniedException(f"Missing '{org_id_field}' parameter in route.")

        user_org_role = current_user.org_roles.get(str(org_id))
        if not user_org_role or user_org_role not in allowed_roles:
            raise PermissionDeniedException(
                f"User lacks required organization permission in org '{org_id}'."
            )
        return current_user

    return org_role_checker
