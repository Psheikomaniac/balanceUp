# update_penalties_by_user_id.py
import os
import sys
import sqlite3
import logging
from datetime import datetime
from app.services.user_utils import display_user_ids, validate_user_id
from app.config.settings import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()

def get_db_path():
    """
    Extract the database path from settings.
    
    Returns:
        str: Path to the SQLite database
    """
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        # Ensure path is absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        return db_path
    else:
        logger.warning(f"Unsupported database URL format: {db_url}, using default path")
        return os.path.join(os.getcwd(), 'database', 'penalties.db')

def update_penalties(db_path, user_id):
    """
    Update all unpaid penalties for the given user ID.
    
    Args:
        db_path: Path to the SQLite database file.
        user_id: The ID of the user.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the user exists
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_name = cursor.fetchone()
        
        if not user_name:
            logger.warning(f"User with ID '{user_id}' does not exist.")
            print(f"User with ID '{user_id}' does not exist.")
            return
            
        user_name = user_name[0]
        
        # Update all unpaid penalties for the user
        update_query = """
        UPDATE penalties
        SET penalty_paid_date = ?
        WHERE user_id = ? AND penalty_paid_date IS NULL
        """
        current_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(update_query, (current_date, user_id))
        
        # Get count of updated records
        rows_affected = cursor.rowcount
        
        conn.commit()
        logger.info(f"Updated {rows_affected} unpaid penalties for user '{user_name}' (ID: {user_id}).")
        print(f"Updated {rows_affected} unpaid penalties for user '{user_name}' (ID: {user_id}).")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        print(f"Error updating penalties: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        # Get database path from settings
        db_path = get_db_path()
        
        # Display user IDs with their names sorted alphabetically by name
        display_user_ids(db_path)
        
        while True:
            user_id_input = input("Please enter the user ID: ")
            
            try:
                user_id = int(user_id_input)
                if validate_user_id(db_path, user_id):
                    confirmation = input(f"Do you want to update unpaid penalties for user ID '{user_id}'? (yes/no): ")
                    
                    if confirmation.lower() == 'yes':
                        # Update unpaid penalties for the given user ID
                        update_penalties(db_path, user_id)
                        break
                    elif confirmation.lower() == 'no':
                        print("Update canceled. Exiting script.")
                        break
                    else:
                        print("Invalid input. Please enter 'yes' or 'no'.")
                else:
                    print(f"Invalid user ID: {user_id}")
            except ValueError:
                print("Invalid input. Please enter a valid user ID (integer).")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"An error occurred: {str(e)}")
        sys.exit(1)
