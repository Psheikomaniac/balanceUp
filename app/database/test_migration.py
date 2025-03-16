import os
import sys
import pytest
import uuid
from datetime import datetime
import shutil
import tempfile
import logging

# Set up path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from app.config.settings import get_settings
from app.database.models import User, Penalty, Transaction, AuditLog
from app.database import get_db
from app.database.migrate_db import migrate_db
from app.utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

def test_migration() -> bool:
    """
    Test the database migration in a temporary environment.
    
    Returns:
        bool: True if the test migration was successful, False otherwise
    """
    settings = get_settings()
    original_db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Create a copy of the database in the temp directory
            temp_db_path = os.path.join(temp_dir, 'test_penalties.db')
            if os.path.exists(original_db_path):
                shutil.copy2(original_db_path, temp_db_path)
            
            # Temporarily override the database path
            settings.DATABASE_URL = f"sqlite:///{temp_db_path}"
            
            # Run the migration
            logger.info("Starting test migration...")
            migrate_db()
            
            # Verify the migrated database
            success = verify_migration(temp_db_path)
            if success:
                logger.info("Test migration completed successfully")
            else:
                logger.error("Test migration verification failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during test migration: {str(e)}")
            return False
        finally:
            # Restore the original database path
            settings.DATABASE_URL = f"sqlite:///{original_db_path}"

def verify_migration(db_path: str) -> bool:
    """
    Verify that the migrated database has the correct schema and data integrity.
    
    Args:
        db_path: Path to the migrated database
        
    Returns:
        bool: True if verification passes, False otherwise
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        required_tables = [
            'users',
            'penalties',
            'transactions',
            'audit_logs',
            'schema_version'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table not in existing_tables:
                logger.error(f"Required table '{table}' not found in migrated database")
                return False
        
        # Verify schema version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]
        if version < 3:  # Our latest version
            logger.error(f"Database schema version {version} is lower than expected (3)")
            return False
        
        # Check table schemas
        schema_checks = {
            'users': [
                'id TEXT PRIMARY KEY',
                'name TEXT NOT NULL',
                'email TEXT UNIQUE',
                'phone TEXT',
                'created_at TIMESTAMP',
                'updated_at TIMESTAMP'
            ],
            'penalties': [
                'penalty_id TEXT PRIMARY KEY',
                'user_id TEXT NOT NULL',
                'amount REAL NOT NULL',
                'reason TEXT',
                'date TIMESTAMP',
                'paid BOOLEAN',
                'paid_at TIMESTAMP',
                'created_at TIMESTAMP',
                'updated_at TIMESTAMP'
            ],
            'transactions': [
                'transaction_id TEXT PRIMARY KEY',
                'user_id TEXT NOT NULL',
                'amount REAL NOT NULL',
                'transaction_date TIMESTAMP',
                'description TEXT',
                'created_at TIMESTAMP'
            ],
            'audit_logs': [
                'log_id TEXT PRIMARY KEY',
                'action TEXT NOT NULL',
                'entity_type TEXT NOT NULL',
                'entity_id TEXT',
                'user_id TEXT',
                'details TEXT',
                'timestamp TIMESTAMP'
            ]
        }
        
        for table, required_columns in schema_checks.items():
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            column_defs = [f"{col[1]} {col[2]}" + (" PRIMARY KEY" if col[5] == 1 else "") for col in columns]
            
            for req_col in required_columns:
                if not any(col.upper().startswith(req_col.upper()) for col in column_defs):
                    logger.error(f"Required column '{req_col}' not found in table '{table}'")
                    return False
        
        # Verify foreign key constraints
        cursor.execute("PRAGMA foreign_key_list(penalties)")
        fks = cursor.fetchall()
        if not any(fk[3] == 'user_id' and fk[2] == 'users' for fk in fks):
            logger.error("Foreign key constraint missing for penalties.user_id")
            return False
        
        cursor.execute("PRAGMA foreign_key_list(transactions)")
        fks = cursor.fetchall()
        if not any(fk[3] == 'user_id' and fk[2] == 'users' for fk in fks):
            logger.error("Foreign key constraint missing for transactions.user_id")
            return False
        
        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        required_indexes = [
            'idx_penalties_user_id',
            'idx_penalties_paid',
            'idx_users_name',
            'idx_transactions_user_id',
            'idx_audit_logs_entity_id'
        ]
        
        for idx in required_indexes:
            if idx not in indexes:
                logger.error(f"Required index '{idx}' not found")
                return False
        
        logger.info("All database schema checks passed")
        return True
        
    except Exception as e:
        logger.error(f"Error during migration verification: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = test_migration()
    if success:
        print("Database migration test successful!")
        sys.exit(0)
    else:
        print("Database migration test failed!")
        sys.exit(1)