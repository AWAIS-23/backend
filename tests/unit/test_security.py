import pytest
import time
import jwt
from app.core.constants import UserRole, OrgRole
from app.core.exceptions import InvalidTokenException
from app.core.security import verify_supabase_jwt
from tests.conftest import create_mock_jwt

SECRET = "test-jwt-secret-1234567890-test-secret-32bytes"


def test_verify_valid_jwt():
    token = create_mock_jwt(
        user_id="usr-123",
        email="test@user.com",
        role=UserRole.LEARNER,
        secret=SECRET,
    )
    user = verify_supabase_jwt(token, SECRET, verify_aud=False)
    assert user.id == "usr-123"
    assert user.email == "test@user.com"
    assert user.role == UserRole.LEARNER


def test_verify_expired_jwt():
    token = create_mock_jwt(
        user_id="usr-123",
        secret=SECRET,
        expires_in_seconds=-10,  # Already expired
    )
    with pytest.raises(InvalidTokenException) as exc_info:
        verify_supabase_jwt(token, SECRET, verify_aud=False)
    assert "expired" in str(exc_info.value).lower()


def test_verify_invalid_signature():
    token = create_mock_jwt(user_id="usr-123", secret="wrong-secret-that-is-32-bytes-long")
    with pytest.raises(InvalidTokenException):
        verify_supabase_jwt(token, SECRET, verify_aud=False)


def test_verify_org_roles_parsing():
    token = create_mock_jwt(
        user_id="usr-employer",
        role=UserRole.EMPLOYER,
        org_roles={"org-abc": "owner", "org-def": "evaluator"},
        secret=SECRET,
    )
    user = verify_supabase_jwt(token, SECRET, verify_aud=False)
    assert user.role == UserRole.EMPLOYER
    assert user.org_roles.get("org-abc") == OrgRole.OWNER
    assert user.org_roles.get("org-def") == OrgRole.EVALUATOR
