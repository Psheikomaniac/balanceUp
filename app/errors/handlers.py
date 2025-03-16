from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.utils.logging_config import get_logger
from app.errors.exceptions import (
    ResourceNotFoundException, 
    DuplicateResourceException,
    UnauthorizedException
)

logger = get_logger(__name__)

def setup_exception_handlers(app: FastAPI):
    """Configure exception handlers for the FastAPI application"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors in API requests"""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body,
                "message": "Validation error in request data"
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle SQLAlchemy errors"""
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Database error occurred", "detail": str(exc)}
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """Handle database integrity errors"""
        logger.error(f"Database integrity error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": "Database integrity error occurred", "detail": str(exc)}
        )
    
    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
        """Handle resource not found errors"""
        logger.warning(f"Resource not found: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": str(exc)}
        )
    
    @app.exception_handler(DuplicateResourceException)
    async def duplicate_resource_handler(request: Request, exc: DuplicateResourceException):
        """Handle duplicate resource errors"""
        logger.warning(f"Duplicate resource: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": str(exc)}
        )
    
    @app.exception_handler(UnauthorizedException)
    async def unauthorized_handler(request: Request, exc: UnauthorizedException):
        """Handle unauthorized access errors"""
        logger.warning(f"Unauthorized access: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": str(exc)}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle any unhandled exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "An unexpected error occurred"}
        )
    
    logger.info("Exception handlers configured")