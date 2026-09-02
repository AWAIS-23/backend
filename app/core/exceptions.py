import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.constants import ErrorCode

logger = logging.getLogger("rising_skills.exceptions")


class AppException(Exception):
    """Base application exception with machine-readable error codes."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        message: str = "An application error occurred.",
        details: dict[str, Any] | list[Any] | None = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationRequiredException(AppException):
    def __init__(self, message: str = "Authentication credentials were not provided."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            message=message,
        )


class InvalidTokenException(AppException):
    def __init__(self, message: str = "Provided authentication token is invalid or expired."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_TOKEN,
            message=message,
        )


class PermissionDeniedException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.PERMISSION_DENIED,
            message=message,
        )


class ResourceNotFoundException(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource} with identifier '{identifier}' was not found.",
            details={"resource": resource, "identifier": str(identifier)},
        )


class ResourceConflictException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            details=details,
        )


class AttemptExpiredException(AppException):
    def __init__(self, message: str = "The assessment attempt time limit has expired."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.ATTEMPT_EXPIRED,
            message=message,
        )


class AttemptAlreadyCompletedException(AppException):
    def __init__(self, message: str = "This assessment attempt has already been finalized."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.ATTEMPT_ALREADY_COMPLETED,
            message=message,
        )


def format_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Standard RFC-7807 compliant error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details if details is not None else {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return format_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code.value if hasattr(exc.error_code, "value") else str(exc.error_code),
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(item) for item in err.get("loc", []) if item != "body"])
        errors.append({
            "field": loc or "body",
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed.",
        details=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on path {request.url.path}: {str(exc)}")
    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        message="An unexpected internal server error occurred. Please contact support.",
        details={},
    )
