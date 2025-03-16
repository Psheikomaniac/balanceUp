# logging_utils.py

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.database import crud, schemas
import sqlite3


def log_action(conn: sqlite3.Connection, log_action: str, log_details: str, user_id: int):
    """
    Log an action to the logs table.

    :param conn: SQLite database connection.
    :param log_action: The action performed (e.g., 'QUERY', 'UPDATE', 'INSERT').
    :param log_details: Details about the action.
    :param user_id: The ID of the user performing the action.
    """
    cursor = conn.cursor()

    log_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
    INSERT INTO logs (log_timestamp, log_action, log_details, user_id)
    VALUES (?, ?, ?, ?)
    ''', (log_timestamp, log_action, log_details, user_id))
    conn.commit()


class AuditLogger:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an auditable action to both database and log file
        """
        timestamp = datetime.utcnow()
        
        # Create database audit log
        audit_log = crud.create_audit_log(
            self.db,
            schemas.AuditLogCreate(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                details=details,
                metadata=metadata
            )
        )

        # Also log to file for redundancy
        log_message = (
            f"AUDIT: {action} | "
            f"Type: {entity_type} | "
            f"ID: {entity_id} | "
            f"User: {user_id or 'system'} | "
            f"Details: {details or 'N/A'}"
        )
        self.logger.info(log_message)

    def log_financial_action(
        self,
        action: str,
        amount: float,
        user_id: str,
        transaction_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """
        Specialized method for logging financial actions
        """
        metadata = {
            "amount": amount,
            "transaction_id": transaction_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.log_action(
            action=action,
            entity_type="financial",
            entity_id=transaction_id or user_id,
            user_id=user_id,
            details=details,
            metadata=metadata
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> None:
        """
        Log error events
        """
        self.log_action(
            action="error",
            entity_type=error_type,
            entity_id=entity_id or "system",
            user_id=user_id,
            details=error_message
        )
        self.logger.error(f"Error: {error_type} - {error_message}")

def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the application
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
