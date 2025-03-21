from datetime import datetime
import logging
import sqlite3
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.models import Base
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

MIGRATIONS = [
    # Version 1: Initial schema
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS penalties (
        penalty_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        reason TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid BOOLEAN DEFAULT FALSE,
        paid_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_penalties_user_id ON penalties(user_id);
    CREATE INDEX IF NOT EXISTS idx_penalties_paid ON penalties(paid);
    CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
    """,
    
    # Version 2: Add transactions table
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
    """,
    
    # Version 3: Add audit logging
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        user_id TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    
    CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_id ON audit_logs(entity_id);
    """,
    
    # Version 4: Add new indexes and constraints
    """
    -- Add composite indexes for improved query performance
    CREATE INDEX IF NOT EXISTS idx_user_search 
    ON users(name, email);
    
    CREATE INDEX IF NOT EXISTS idx_penalty_status 
    ON penalties(user_id, paid);
    
    CREATE INDEX IF NOT EXISTS idx_penalty_date 
    ON penalties(user_id, date);
    
    CREATE INDEX IF NOT EXISTS idx_transaction_date 
    ON transactions(user_id, transaction_date);
    
    CREATE INDEX IF NOT EXISTS idx_audit_search 
    ON audit_logs(action, entity_type, timestamp);
    
    -- Add cascade delete constraints
    DROP TRIGGER IF EXISTS cascade_delete_penalties;
    CREATE TRIGGER cascade_delete_penalties
    AFTER DELETE ON users
    FOR EACH ROW
    BEGIN
        DELETE FROM penalties WHERE user_id = OLD.id;
        DELETE FROM transactions WHERE user_id = OLD.id;
    END;
    
    -- Add trigger to update timestamps
    DROP TRIGGER IF EXISTS update_user_timestamp;
    CREATE TRIGGER update_user_timestamp
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users 
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.id;
    END;
    
    DROP TRIGGER IF EXISTS update_penalty_timestamp;
    CREATE TRIGGER update_penalty_timestamp
    AFTER UPDATE ON penalties
    FOR EACH ROW
    BEGIN
        UPDATE penalties 
        SET updated_at = CURRENT_TIMESTAMP
        WHERE penalty_id = NEW.penalty_id;
    END;
    """
]

def get_current_version(db: Session) -> int:
    """Get the current database schema version"""
    try:
        result = db.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        return result or 0
    except Exception:
        return 0

def record_migration(db: Session, version: int):
    """Record that a migration has been applied"""
    db.execute(
        text("INSERT INTO schema_version (version, applied_at) VALUES (:version, :applied_at)"),
        {"version": version, "applied_at": datetime.utcnow()}
    )
    db.commit()

def migrate_db(db: Session, target_version: Optional[int] = None) -> None:
    """
    Apply database migrations
    
    Args:
        db: The database session
        target_version: Optional specific version to migrate to
    """
    current_version = get_current_version(db)
    if target_version is None:
        target_version = len(MIGRATIONS)
    
    if current_version >= target_version:
        logger.info(f"Database is already at version {current_version}")
        return
    
    logger.info(f"Current database version: {current_version}")
    logger.info(f"Target database version: {target_version}")
    
    for version, migration in enumerate(MIGRATIONS[current_version:target_version], start=current_version + 1):
        logger.info(f"Applying migration version {version}...")
        try:
            # Split migration into individual statements
            statements = [s.strip() for s in migration.split(';') if s.strip()]
            for statement in statements:
                db.execute(text(statement))
            
            record_migration(db, version)
            db.commit()
            logger.info(f"Successfully applied migration version {version}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error applying migration version {version}: {str(e)}")
            raise

def init_db():
    """Initialize database and run migrations"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run migrations
    with Session(engine) as session:
        migrate_db(session)
    
    return engine

def verify_database_integrity(db: Session) -> bool:
    """
    Verify the integrity of the database schema and constraints.
    
    Returns:
        bool: True if all checks pass, False otherwise
    """
    try:
        # Check table existence and basic structure
        tables = [
            'users',
            'penalties',
            'transactions',
            'audit_logs',
            'schema_version'
        ]
        
        for table in tables:
            result = db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            result.fetchall()  # Just to verify the query succeeds
        
        # Verify foreign key constraints
        db.execute(text("PRAGMA foreign_key_check"))
        
        # Check indexes
        required_indexes = [
            'idx_penalties_user_id',
            'idx_penalties_paid',
            'idx_users_name',
            'idx_transactions_user_id',
            'idx_audit_logs_entity_id'
        ]
        
        for index in required_indexes:
            result = db.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='index' AND name=:index"),
                {"index": index}
            )
            if not result.fetchone():
                logger.error(f"Required index {index} is missing")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Database integrity check failed: {str(e)}")
        return False

if __name__ == "__main__":
    init_db()