from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

from app.config.settings import get_settings
from app.utils.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=settings.is_development,
    pool_pre_ping=True
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

@contextmanager
def get_db():
    """
    Dependency for database session, to be used with FastAPI's Depends()
    or as a context manager.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

def create_database(db_path: str):
    """
    Create database if it doesn't exist
    
    Args:
        db_path: Path to the SQLite database file
    """
    try:
        if db_path and not os.path.exists(db_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Import models to ensure tables are created
            from app.database.models import Base
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            logger.info(f"Created database at {db_path}")
        else:
            logger.info(f"Database already exists at {db_path}")
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise

def get_engine():
    """
    Get the SQLAlchemy engine
    
    Returns:
        Engine: SQLAlchemy engine
    """
    return engine
