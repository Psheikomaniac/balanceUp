import sqlite3
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import get_settings
from app.database.models import Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings from centralized configuration
settings = get_settings()

# Create SQLAlchemy engine for ORM operations
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_connection():
    """
    Get a direct SQLite connection based on settings configuration.
    
    Returns:
        sqlite3.Connection: A connection to the database with row factory set
    """
    # Extract SQLite path from DATABASE_URL setting (sqlite:///path/to/db)
    db_url = settings.DATABASE_URL
    
    if db_url.startswith('sqlite:///'):
        # Handle relative path
        db_path = db_url.replace('sqlite:///', '')
        # Ensure the path is absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
    else:
        # Fallback to default location if URL format not recognized
        logger.warning(f"Unrecognized database URL format: {db_url}, using default location")
        db_path = os.path.join(os.getcwd(), 'database', 'penalties.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_database(db_path: str = None):
    """
    Create database tables if they don't exist.
    
    Args:
        db_path (str, optional): Path to the database file. If None, uses the path from settings.
    """
    try:
        # Use provided path or extract from settings
        if db_path is None:
            db_url = settings.DATABASE_URL
            if db_url.startswith('sqlite:///'):
                db_path = db_url.replace('sqlite:///', '')
                # Ensure the path is absolute
                if not os.path.isabs(db_path):
                    db_path = os.path.join(os.getcwd(), db_path)
            else:
                raise ValueError(f"Unsupported database URL format: {db_url}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
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
        raise
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise