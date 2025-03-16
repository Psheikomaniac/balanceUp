import sqlite3
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import get_settings
from app.database.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
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
    conn = sqlite3.connect('database/penalties.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_database(db_path: str):
    try:
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