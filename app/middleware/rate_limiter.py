from fastapi import FastAPI, Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config.settings import get_settings
from app.utils.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW}seconds"]
)

def setup_rate_limiting(app: FastAPI):
    """Configure rate limiting for the FastAPI application"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        response = await call_next(request)
        return response
        
    logger.info("Rate limiting middleware configured")

def rate_limit(limit_value: str = None):
    """Decorator for rate limiting endpoints"""
    if limit_value is None:
        limit_value = f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW}seconds"
    
    return limiter.limit(limit_value)