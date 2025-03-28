"""
Middleware configuration utilities
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.input_validation import InputValidationMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware

def configure_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Add CORS middleware first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add security middleware
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)