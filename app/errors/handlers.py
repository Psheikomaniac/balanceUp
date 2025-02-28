import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from .exceptions import BaseAPIException, ValidationError, AuthenticationError, NotFoundError, RateLimitError

logger = logging.getLogger(__name__)

async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Handle all API exceptions with proper logging"""
    logger.error(
        "API error occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "client_ip": request.client.host if request.client else None,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors"""
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "detail": exc.detail,
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": exc.detail}
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions"""
    logger.error(
        "Unhandled error occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )