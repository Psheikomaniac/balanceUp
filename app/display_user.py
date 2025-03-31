#!/usr/bin/env python3
import os
import sys
# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def get_db_connection(db_path=None):
    """
    Get a connection to the SQLite database with proper error handling.
    
    Args:
        db_path (str, optional): Path to the SQLite database file. If None, uses the path from settings.
        
    Returns:
        sqlite3.Connection: Database connection object
        
    Raises:
        sqlite3.Error: If connection fails
    """
    try:
        if db_path is None:
            # Extract database path from settings
            db_url = settings.DATABASE_URL
            if db_url.startswith('sqlite:///'):
                db_path = db_url.replace('sqlite:///', '')
                # Ensure path is absolute
                if not os.path.isabs(db_path):
                    db_path = os.path.join(os.getcwd(), db_path)
            else:
                raise ValueError(f"Unsupported database URL format: {db_url}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def display_user_penalties(db_path=None, user_id=None):
    """
    Display all unpaid items (penalties, dues) for the given user ID and return them as lists.
    Only show STATUS_UNPAID items, treat STATUS_EXEMPT as paid.
    
    Args:
        db_path (str, optional): Path to the SQLite database file. If None, uses the path from settings.
        user_id (int): The ID of the user
        
    Returns:
        tuple: (punishments, dues) where each is a list of records
        
    Raises:
        sqlite3.Error: If database operations fail
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Fetch user name with parameterized query
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_name = cursor.fetchone()
        
        if not user_name:
            logger.warning(f"User with ID '{user_id}' does not exist.")
            return [], []
            
        user_name = user_name[0]
        total_amount = 0
        
        print(f"\nItems for user '{user_name}' (ID: {user_id}):")
        print("-" * 50)
        
        # Fetch unpaid punishments (those without a paid date) - parameterized query
        query_punishments = """
        SELECT penalty_id, penalty_created, penalty_amount, penalty_reason, penalty_currency
        FROM punishments
        WHERE user_id = ? AND penalty_paid_date IS NULL
        ORDER BY penalty_created DESC
        """
        cursor.execute(query_punishments, (user_id,))
        punishments = cursor.fetchall()

        if punishments:
            print("\nUnpaid punishments:")
            for i, (pid, created, amount, reason, currency) in enumerate(punishments, 1):
                try:
                    formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
                except ValueError:
                    formatted_date = created or "Unknown date"
                print(f"{i}. {formatted_date} {reason} ({amount} {currency})")
                total_amount += amount

        # Fetch unpaid dues (only STATUS_UNPAID) - parameterized query
        query_dues = """
        SELECT due_id, due_created, due_amount, due_reason, due_currency
        FROM dues
        WHERE user_id = ? 
        AND (
            (due_paid_date IS NULL AND user_paid = ?)
            OR (due_paid_date IS NULL AND user_paid IS NULL)
        )
        ORDER BY due_created DESC
        """
        cursor.execute(query_dues, (user_id, 'STATUS_UNPAID'))
        dues = cursor.fetchall()

        if dues:
            print("\nUnpaid dues:")
            punishment_count = len(punishments)
            for i, (did, created, amount, reason, currency) in enumerate(dues, punishment_count + 1):
                try:
                    formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
                except ValueError:
                    formatted_date = created or "Unknown date"
                print(f"{i}. {formatted_date} {reason} ({amount} {currency})")
                total_amount += amount

        # Show recent transactions separately (for information only) - parameterized query
        query_transactions = """
        SELECT transaction_created, transaction_amount, transaction_reason, transaction_currency
        FROM transactions
        WHERE user_id = ?
        ORDER BY transaction_created DESC
        LIMIT ?
        """
        cursor.execute(query_transactions, (user_id, 5))
        transactions = cursor.fetchall()

        if transactions:
            print("\nRecent transactions (last 5, for reference only):")
            for created, amount, reason, currency in transactions:
                try:
                    formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
                except ValueError:
                    formatted_date = created or "Unknown date"
                print(f"{formatted_date} {reason} ({amount} {currency})")

        if total_amount > 0:
            print(f"\nTotal unpaid amount: {total_amount} €")
        else:
            print("\nNo unpaid items found.")
        print("-" * 50)

        return punishments, dues
        
    except sqlite3.Error as e:
        logger.error(f"Database error in display_user_penalties: {str(e)}")
        return [], []
    finally:
        if conn:
            conn.close()

def update_selected_penalties(db_path=None, user_id=None, selected_items=None, punishments=None, dues=None):
    """
    Update only the selected unpaid items for the given user ID.
    
    Args:
        db_path (str, optional): Path to the SQLite database file. If None, uses the path from settings.
        user_id (int): The ID of the user
        selected_items (list): List of selected item numbers
        punishments (list): List of punishment records
        dues (list): List of dues records
        
    Raises:
        sqlite3.Error: If database operations fail
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Check if the user exists - parameterized query
        cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
        user_name = cursor.fetchone()
        
        if not user_name:
            logger.warning(f"User with ID '{user_id}' does not exist.")
            return
            
        current_date = datetime.now().strftime('%Y-%m-%d')
        punishment_count = len(punishments)
        
        for item_num in selected_items:
            if 1 <= item_num <= punishment_count:
                # It's a punishment - parameterized query
                penalty_id = punishments[item_num - 1][0]
                cursor.execute("""
                    UPDATE punishments
                    SET penalty_paid_date = ?
                    WHERE penalty_id = ? AND user_id = ?
                """, (current_date, penalty_id, user_id))
            else:
                # It's a due - parameterized query
                due_index = item_num - punishment_count - 1
                if due_index < len(dues):
                    due_id = dues[due_index][0]
                    cursor.execute("""
                        UPDATE dues
                        SET due_paid_date = ?, user_paid = ?
                        WHERE due_id = ? AND user_id = ?
                    """, (current_date, 'STATUS_PAID', due_id, user_id))

        conn.commit()
        logger.info(f"Updated selected items for user '{user_name[0]}' (ID: {user_id}).")
        print(f"Updated selected items for user '{user_name[0]}' (ID: {user_id}).")
        
    except sqlite3.Error as e:
        logger.error(f"Database error in update_selected_penalties: {str(e)}")
        if conn:
            conn.rollback()
        print(f"Error updating items: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Get database path from settings
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        # Ensure path is absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
    else:
        db_path = os.path.join(os.getcwd(), 'database', 'penalties.db')
        logger.warning(f"Unsupported database URL format: {db_url}, using default path")

    try:
        # Display user IDs with their names sorted alphabetically by name
        print("\nAvailable users:")
        print("-" * 30)
        users = display_user_ids(db_path)
        for user_id, user_name in users:
            print(f"ID: {user_id:2d} | {user_name}")
        print("-" * 30 + "\n")

        while True:
            user_id_input = input("Please enter the user ID: ")
            
            try:
                user_id = int(user_id_input)
                if validate_user_id(db_path, user_id):
                    # Display unpaid penalties for the given user ID
                    punishments, dues = display_user_penalties(db_path, user_id)
                    
                    if punishments or dues:
                        print("\nEnter the numbers of the items you want to mark as paid (comma-separated)")
                        print("Example: 1,3,4 or 'all' for all items")
                        selection = input("Your selection (or press Enter to cancel): ").strip()
                        
                        if selection.lower() == '':
                            print("Update canceled. Exiting script.")
                            break
                        elif selection.lower() == 'all':
                            selected_items = list(range(1, len(punishments) + len(dues) + 1))
                        else:
                            try:
                                selected_items = [int(x.strip()) for x in selection.split(',')]
                                max_allowed = len(punishments) + len(dues)
                                
                                if not all(1 <= x <= max_allowed for x in selected_items):
                                    print(f"Invalid selection. Please enter numbers between 1 and {max_allowed}")
                                    continue
                            except ValueError:
                                print("Invalid input. Please enter numbers separated by commas.")
                                continue
                                
                        # Update selected penalties
                        update_selected_penalties(db_path, user_id, selected_items, punishments, dues)
                        break
                    else:
                        break
                else:
                    print(f"Invalid user ID: {user_id}")
            except ValueError:
                print("Invalid input. Please enter a valid user ID (integer).")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"An error occurred: {str(e)}")
        sys.exit(1)
