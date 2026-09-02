from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.schemas.common import HealthResponse

logger = logging.getLogger("rising_skills.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and graceful shutdown lifecycle."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG)
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode.")
    
    yield
    
    # Graceful shutdown: clean up DB engines if initialized
    from app.db.session import _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed gracefully.")


def create_app() -> FastAPI:
    """Application factory creating the configured FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Production-grade API for Rising Skills - Skills-to-Opportunity Platform",
        docs_url="/docs" if settings.DEBUG or settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.DEBUG or settings.APP_ENV != "production" else None,
        openapi_url="/openapi.json" if settings.DEBUG or settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # 1. CORS Middleware Configuration
    # Defensively restrict origins to configured whitelist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. Centralized Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 3. Root Level Health Check (for cloud load balancers)
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def root_health(settings: Settings = Depends(get_settings)):
        return HealthResponse(
            status="ok",
            service="rising-skills-backend",
            environment=settings.APP_ENV,
        )

    # 4. Mount API v1 Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
