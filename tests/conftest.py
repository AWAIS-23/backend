import os
import time
from typing import AsyncGenerator
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import Settings, get_settings
from app.core.constants import OrgRole, UserRole
from app.db.base import Base
from app.dependencies.database import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

TEST_DB_FILE = "./test_app.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

os.environ["APP_ENV"] = "testing"
os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret-1234567890-test-secret-32bytes"
os.environ["DATABASE_URL"] = TEST_DB_URL

TEST_ENGINE = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    future=True,
)
TestingSessionLocal = async_sessionmaker(
    bind=TEST_ENGINE,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Create database tables once for the entire test session."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await TEST_ENGINE.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture(autouse=True)
async def clean_database():
    """Wipes table rows between individual test executions for clean isolation."""
    yield
    async with TEST_ENGINE.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-jwt-secret-1234567890-test-secret-32bytes",
        DATABASE_URL=TEST_DB_URL,
    )


@pytest.fixture(autouse=True)
async def override_dependencies(test_settings: Settings):
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    fastapi_app.dependency_overrides[get_settings] = lambda: test_settings
    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield
    fastapi_app.dependency_overrides.pop(get_settings, None)
    fastapi_app.dependency_overrides.pop(get_db, None)


def create_mock_jwt(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    email: str = "learner@example.com",
    role: UserRole = UserRole.LEARNER,
    org_roles: dict[str, str] | None = None,
    secret: str = "test-jwt-secret-1234567890-test-secret-32bytes",
    expires_in_seconds: int = 3600,
) -> str:
    """Helper to generate signed test JWTs mimicking Supabase Auth."""
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
        "app_metadata": {
            "role": role.value,
            "org_roles": org_roles or {},
        },
        "user_metadata": {
            "email": email,
            "role": role.value,
        },
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def learner_token() -> str:
    return create_mock_jwt(
        user_id="11111111-1111-1111-1111-111111111111",
        email="learner@risingskills.com",
        role=UserRole.LEARNER,
    )


@pytest.fixture
def learner_token_2() -> str:
    return create_mock_jwt(
        user_id="44444444-4444-4444-4444-444444444444",
        email="learner2@risingskills.com",
        role=UserRole.LEARNER,
    )


@pytest.fixture
def employer_token() -> str:
    return create_mock_jwt(
        user_id="22222222-2222-2222-2222-222222222222",
        email="employer@company.com",
        role=UserRole.EMPLOYER,
        org_roles={"org-100": OrgRole.ADMIN.value},
    )


@pytest.fixture
def admin_token() -> str:
    return create_mock_jwt(
        user_id="33333333-3333-3333-3333-333333333333",
        email="admin@risingskills.com",
        role=UserRole.ADMIN,
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
