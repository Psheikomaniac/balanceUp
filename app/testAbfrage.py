import os
import sqlite3
import logging
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

def query_penalties(limit=None, where_clause=None, params=None):
    """
    Query penalties from the database with optional filtering.
    
    Args:
        limit (int, optional): Maximum number of records to return
        where_clause (str, optional): SQL WHERE clause to filter results
        params (tuple, optional): Parameters for the where clause
        
    Returns:
        list: List of penalty records
        
    Raises:
        sqlite3.Error: If database operations fail
    """
    conn = None
    try:
        # Get database path from settings
        db_path = get_db_path()
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with proper parameterization
        query = "SELECT * FROM penalties"
        
        # Add where clause if provided
        if where_clause:
            query += f" WHERE {where_clause}"
            
        # Add limit if provided
        if limit is not None:
            query += " LIMIT ?"
            # Add limit to params
            if params:
                params = params + (limit,)
            else:
                params = (limit,)
        
        # Execute with parameters
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        results = cursor.fetchall()
        
        # Print results
        for row in results:
            print(dict(row))
            
        return results
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Example usage with safe parameterization
    try:
        query_penalties(limit=10)
        
        # Example with where clause and parameters
        # query_penalties(
        #     where_clause="user_id = ?", 
        #     params=(1,),
        #     limit=5
        # )
    except Exception as e:
        logger.error(f"Error querying penalties: {str(e)}")
        print(f"An error occurred: {str(e)}")