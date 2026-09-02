import pytest
from app.core.config import Settings


def test_settings_default_values():
    settings = Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-secret",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )
    assert settings.APP_NAME == "Rising Skills Backend"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.GROQ_MODEL == "llama-3.3-70b-versatile"
    assert settings.GROQ_TEMPERATURE == 0.2
    assert settings.GROQ_MAX_TOKENS == 2048
    assert settings.GROQ_TIMEOUT_SECONDS == 30
    assert settings.MATCH_WEIGHT_SKILL_FIT == 0.50
    assert settings.MATCH_WEIGHT_EVIDENCE_STRENGTH == 0.30
    assert settings.MATCH_WEIGHT_EXPERIENCE == 0.20
    assert settings.MATCH_WEIGHT_SKILL_FIT + settings.MATCH_WEIGHT_EVIDENCE_STRENGTH + settings.MATCH_WEIGHT_EXPERIENCE == 1.0


def test_cors_origins_parsing():
    settings = Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-secret",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        CORS_ORIGINS=["https://app.risingskills.com", "https://admin.risingskills.com"],
    )
    assert len(settings.CORS_ORIGINS) == 2
    assert "https://app.risingskills.com" in settings.CORS_ORIGINS
