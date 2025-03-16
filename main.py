import os
import sys
import logging
from app.utils.logging_config import setup_logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from app.routers import penalties, users
from app.database.models import init_db
from app.config.settings import get_settings
from app.utils.logging_config import setup_logging
from app.middleware.rate_limiter import setup_rate_limiting
from app.errors.handlers import (
    api_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.errors.exceptions import BaseAPIException, ValidationError

# Initialize settings and logging
settings = get_settings()
from app.utils.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing penalties and users.",
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Set up rate limiting
setup_rate_limiting(app)

# Register exception handlers
app.add_exception_handler(BaseAPIException, api_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # Handle FastAPI validation errors
app.add_exception_handler(HTTPException, api_exception_handler)  # Handle 404 and other HTTP errors
app.add_exception_handler(Exception, unhandled_exception_handler)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up API service")
    init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down API service")

# Include routers
app.include_router(penalties.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
