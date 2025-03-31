"""
Error handlers for FastAPI application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.errors.exceptions import (
    BaseError,
    DatabaseError,
    ResourceNotFoundException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    BusinessLogicError,
    PaymentError,
    InsufficientFundsError,
    DuplicateResourceError,
    DataIntegrityError,
    ConfigurationError
)
from app.database.schemas import ErrorResponse
from app.utils.logging_config import get_logger

logger = logging.getLogger(__name__)

async def base_error_handler(request: Request, exc: BaseError) -> JSONResponse:
    """Base error handler for all custom exceptions"""
    logger.error(f"Error processing request: {exc.message}", 
                extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=exc.message,
            details=exc.details
        ).dict()
    )

async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handler for database-related errors"""
    logger.error(f"Database error: {exc.message}", 
                extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Database operation failed",
            details=exc.details
        ).dict()
    )

async def not_found_handler(request: Request, exc: ResourceNotFoundException) -> JSONResponse:
    """Handler for resource not found errors"""
    logger.warning(f"Resource not found: {exc.message}",
                  extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error=exc.message,
            details=exc.details
        ).dict()
    )

async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handler for validation errors"""
    logger.warning(f"Validation error: {exc.message}",
                  extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation error",
            details=exc.details
        ).dict()
    )

async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Handler for authentication errors"""
    logger.warning(f"Authentication error: {exc.message}",
                  extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            error="Authentication failed",
            details=exc.details
        ).dict()
    )

async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Handler for authorization errors"""
    logger.warning(f"Authorization error: {exc.message}",
                  extra={"path": request.url.path, "user": request.state.user if hasattr(request.state, 'user') else None})
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            error="Permission denied",
            details=exc.details
        ).dict()
    )

async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    """Handler for rate limit exceeded errors"""
    logger.warning(f"Rate limit exceeded: {exc.message}",
                  extra={"path": request.url.path, "client_ip": request.client.host})
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            error="Too many requests",
            details=exc.details
        ).dict()
    )

async def business_logic_error_handler(request: Request, exc: BusinessLogicError) -> JSONResponse:
    """Handler for business logic violations"""
    logger.error(f"Business rule violation: {exc.message}",
                extra={"path": request.url.path, "rule": exc.rule, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=exc.message,
            details={"rule": exc.rule, **exc.details}
        ).dict()
    )

async def payment_error_handler(request: Request, exc: PaymentError) -> JSONResponse:
    """Handler for payment-related errors"""
    logger.error(f"Payment error: {exc.message}",
                extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Payment operation failed",
            details=exc.details
        ).dict()
    )

async def insufficient_funds_handler(request: Request, exc: InsufficientFundsError) -> JSONResponse:
    """Handler for insufficient funds errors"""
    logger.warning(f"Insufficient funds: {exc.message}",
                  extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Insufficient funds",
            details=exc.details
        ).dict()
    )

async def duplicate_resource_handler(request: Request, exc: DuplicateResourceError) -> JSONResponse:
    """Handler for duplicate resource errors"""
    logger.warning(f"Duplicate resource: {exc.message}",
                  extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            error="Resource already exists",
            details=exc.details
        ).dict()
    )

async def data_integrity_error_handler(request: Request, exc: DataIntegrityError) -> JSONResponse:
    """Handler for data integrity violations"""
    logger.error(f"Data integrity error: {exc.message}",
                extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="Data integrity violation",
            details=exc.details
        ).dict()
    )

async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handler for configuration errors"""
    logger.error(f"Configuration error: {exc.message}",
                extra={"path": request.url.path, "details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Configuration error",
            details=exc.details
        ).dict()
    )

def register_error_handlers(app):
    """Register all error handlers with the FastAPI application"""
    app.add_exception_handler(BaseError, base_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(ResourceNotFoundException, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthenticationError, auth_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_error_handler)
    app.add_exception_handler(BusinessLogicError, business_logic_error_handler)
    app.add_exception_handler(PaymentError, payment_error_handler)
    app.add_exception_handler(InsufficientFundsError, insufficient_funds_handler)
    app.add_exception_handler(DuplicateResourceError, duplicate_resource_handler)
    app.add_exception_handler(DataIntegrityError, data_integrity_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)