import os
import sqlite3
import logging
from app.config.settings import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()

def get_db_connection():
    """
    Get a connection to the SQLite database with proper error handling.
    
    Returns:
        sqlite3.Connection: Database connection object
        
    Raises:
        sqlite3.Error: If connection fails
    """
    try:
        # Extract database path from settings
        db_url = settings.DATABASE_URL
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            # Ensure path is absolute
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        else:
            logger.warning(f"Unsupported database URL format: {db_url}, using default path")
            db_path = os.path.join(os.getcwd(), 'database', 'penalties.db')
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def process_penalties():
    """
    Process and summarize penalties by user with proper security practices.
    
    Returns:
        dict: Dictionary of user penalties with summary
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Using parameterized query to prevent SQL injection
        query = """
        SELECT p.user_id, u.user_name, p.penalty_amount, p.penalty_reason
        FROM penalties AS p
        JOIN users AS u ON p.user_id = u.user_id
        WHERE p.penalty_archived = ? AND p.penalty_paid_date IS NULL
        """

        cursor.execute(query, ('NO',))
        rows = cursor.fetchall()

        user_penalties = {}
        for row in rows:
            user_id, user_name, penalty_amount, penalty_reason = row
            if user_id not in user_penalties:
                user_penalties[user_id] = {'user_name': user_name, 'amount': 0}
            
            # Apply logic based on penalty reason
            if penalty_reason == 'Guthaben':
                user_penalties[user_id]['amount'] -= penalty_amount
            else:
                user_penalties[user_id]['amount'] += penalty_amount

        # Print summary of user penalties
        print("\n=== Unpaid Penalties Summary ===")
        for user_id, data in sorted(user_penalties.items(), key=lambda x: x[1]['amount'], reverse=True):
            if data['amount'] > 0:  # Only show users with positive balance
                print(f"{data['user_name']}: {data['amount']:.2f} EUR")
        print("==============================\n")

        # Return the data for further processing if needed
        return user_penalties
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {}
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    process_penalties()
