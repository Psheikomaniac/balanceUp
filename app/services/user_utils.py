# services/user_utils.py

from typing import List, Dict, Any, Optional
import uuid
import sqlite3
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.errors.exceptions import ResourceNotFoundException

logger = get_logger(__name__)

def display_user_ids(db_path: str) -> List[tuple]:
    """
    Display and return a list of user IDs with their names sorted alphabetically.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        List of tuples containing (user_id, user_name)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'SELECT user_id, user_name FROM users ORDER BY user_name'
    cursor.execute(query)
    users = cursor.fetchall()

    conn.close()
    return users

def validate_user_id(db_path: str, user_id: int) -> bool:
    """
    Validate if a user ID exists in the database.
    
    Args:
        db_path: Path to the SQLite database file
        user_id: The ID of the user to validate
        
    Returns:
        Boolean indicating whether the user ID exists
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'SELECT COUNT(*) FROM users WHERE user_id = ?'
    cursor.execute(query, (user_id,))
    count = cursor.fetchone()[0]

    conn.close()
    return count > 0

class UserUtils:
    """Service for handling user-related operations"""
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str):
        """
        Get a user by ID
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        from app.database.models import User
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found with ID: {user_id}")
                return None
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_name(db: Session, name: str):
        """
        Get a user by name
        
        Args:
            db: Database session
            name: User name
            
        Returns:
            User object or None if not found
        """
        from app.database.models import User
        
        try:
            user = db.query(User).filter(User.name == name).first()
            if not user:
                logger.warning(f"User not found with name: {name}")
                return None
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by name {name}: {str(e)}")
            return None
    
    @staticmethod
    def create_user(db: Session, user_data: Dict[str, Any]):
        """
        Create a new user
        
        Args:
            db: Database session
            user_data: User data dictionary
            
        Returns:
            Created user object
        """
        from app.database.models import User
        
        try:
            # Check if user already exists
            if 'name' in user_data:
                existing_user = UserUtils.get_user_by_name(db, user_data['name'])
                if existing_user:
                    logger.info(f"User already exists with name: {user_data['name']}")
                    return existing_user
            
            # Create new user
            user = User(
                id=user_data.get('id') or str(uuid.uuid4()),
                name=user_data.get('name', ''),
                email=user_data.get('email'),
                phone=user_data.get('phone')
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Created new user: {user.name} (ID: {user.id})")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    @staticmethod
    def update_user(db: Session, user_id: str, user_data: Dict[str, Any]):
        """
        Update an existing user
        
        Args:
            db: Database session
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Updated user object
        """
        from app.database.models import User
        
        try:
            user = UserUtils.get_user_by_id(db, user_id)
            if not user:
                raise ResourceNotFoundException("User", user_id)
            
            # Update user attributes
            for key, value in user_data.items():
                if hasattr(user, key) and key != 'id':  # Don't update ID
                    setattr(user, key, value)
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"Updated user: {user.name} (ID: {user.id})")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_user(db: Session, user_id: str):
        """
        Delete a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Boolean indicating success
        """
        from app.database.models import User
        
        try:
            user = UserUtils.get_user_by_id(db, user_id)
            if not user:
                raise ResourceNotFoundException("User", user_id)
            
            db.delete(user)
            db.commit()
            
            logger.info(f"Deleted user: {user.name} (ID: {user.id})")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_penalties(db: Session, user_id: str, include_paid: bool = True):
        """
        Get penalties for a user
        
        Args:
            db: Database session
            user_id: User ID
            include_paid: Whether to include paid penalties
            
        Returns:
            List of penalties for the user
        """
        from app.database.models import Penalty, User
        
        try:
            # Check if user exists
            user = UserUtils.get_user_by_id(db, user_id)
            if not user:
                raise ResourceNotFoundException("User", user_id)
            
            # Get penalties
            query = db.query(Penalty).filter(Penalty.user_id == user_id)
            if not include_paid:
                query = query.filter(Penalty.paid == False)
            
            penalties = query.all()
            logger.info(f"Retrieved {len(penalties)} penalties for user: {user.name}")
            
            return penalties
        except Exception as e:
            logger.error(f"Error getting penalties for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_balance(db: Session, user_id: str):
        """
        Calculate the balance for a user (sum of unpaid penalties)
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User balance as float
        """
        try:
            # Get unpaid penalties
            penalties = UserUtils.get_user_penalties(db, user_id, include_paid=False)
            
            # Calculate total
            balance = sum(p.amount for p in penalties)
            
            return balance
        except Exception as e:
            logger.error(f"Error calculating balance for user {user_id}: {str(e)}")
            raise
