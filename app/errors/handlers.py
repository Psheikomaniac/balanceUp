"""
Error handlers for FastAPI application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from .exceptions import (
    FileValidationError,
    InputValidationError,
    SecurityError,
    RateLimitExceededError
)

logger = logging.getLogger(__name__)

def register_error_handlers(app: FastAPI) -> None:
    """Register security-related error handlers"""
    
    @app.exception_handler(FileValidationError)
    async def file_validation_error_handler(request: Request, exc: FileValidationError):
        """Handle file validation errors"""
        logger.error(f"File validation error: {exc.message}",
                    extra={"path": request.url.path, "details": exc.details})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "File validation error",
                "message": exc.message,
                "details": exc.details
            }
        )

    @app.exception_handler(InputValidationError)
    async def input_validation_error_handler(request: Request, exc: InputValidationError):
        """Handle input validation errors"""
        logger.error(f"Input validation error: {exc.message}",
                    extra={"path": request.url.path, "details": exc.details})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Input validation error",
                "message": exc.message,
                "details": exc.details
            }
        )

    @app.exception_handler(SecurityError)
    async def security_error_handler(request: Request, exc: SecurityError):
        """Handle security-related errors"""
        logger.error(f"Security error: {exc.message}",
                    extra={"path": request.url.path, "details": exc.details})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Security error",
                "message": exc.message
            }
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError):
        """Handle rate limit exceeded errors"""
        logger.warning(f"Rate limit exceeded: {exc.message}",
                     extra={"path": request.url.path, "details": exc.details})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Rate limit exceeded",
                "message": exc.message,
                "retry_after": exc.details.get("retry_after") if exc.details else None
            }
        )