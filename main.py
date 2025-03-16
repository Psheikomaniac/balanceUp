import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.utils.logging_config import setup_logging
from app.middleware.rate_limiter import RateLimitMiddleware
from app.database import get_engine
from app.errors.handlers import register_error_handlers
from app.database.models import init_db
from app.routers import users_router, penalties_router, transactions_router

# Initialize settings and logging
settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# Register error handlers
register_error_handlers(app)

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
app.include_router(users_router)
app.include_router(penalties_router)
app.include_router(transactions_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
