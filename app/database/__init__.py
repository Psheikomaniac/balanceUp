import sqlite3
import logging
import os
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass

engine = None
SessionLocal = None

def get_engine():
    """Get or create SQLAlchemy engine"""
    global engine
    if engine is None:
        from app.config.settings import get_settings
        settings = get_settings()
        
        # Ensure database directory exists for SQLite
        if not settings.DATABASE_URL.startswith("sqlite:///:memory:"):
            db_dir = os.path.dirname(settings.DATABASE_URL.replace('sqlite:///', ''))
            os.makedirs(db_dir, exist_ok=True)
        
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    return engine

def get_session():
    """Get SQLAlchemy session maker"""
    global SessionLocal
    if SessionLocal is None:
        engine = get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

def get_db():
    """Get database session"""
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import these after Base is defined to avoid circular imports
from app.database.models import User, Penalty, Transaction, AuditLog
from app.database.crud import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database(db_path: str):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            team_id INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS penalties (
            penalty_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            penalty_created TEXT NOT NULL,
            penalty_reason TEXT NOT NULL,
            penalty_archived TEXT NOT NULL,
            penalty_amount REAL NOT NULL,
            penalty_currency TEXT NOT NULL,
            penalty_subject TEXT,
            search_params TEXT,
            penalty_paid_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_timestamp TEXT,
            log_action TEXT,
            log_details TEXT,
            user_id INTEGER
        )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database created successfully at {db_path}")
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    except Exception as e:
        logger.error(f"Error creating database: {e}")
