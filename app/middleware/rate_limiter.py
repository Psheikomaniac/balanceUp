from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config.settings import get_settings

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app):
    """Configure rate limiting for the FastAPI application"""
    app.state.limiter = limiter
    app.add_exception_handler(Exception, limiter.error_handler)

def rate_limit():
    """Decorator for rate limiting endpoints"""
    return limiter.limit(
        f"{settings.RATE_LIMIT_MAX_REQUESTS}/{settings.RATE_LIMIT_WINDOW}s"
    )