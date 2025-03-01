# services/user_utils.py

import sqlite3
import os

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join('database', 'penalties.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def display_user_ids(db_path: str):
    """
    Display all user IDs with their names sorted alphabetically by name.

    :param db_path: Path to the SQLite database file.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all user IDs with their names sorted alphabetically by name
    cursor.execute('SELECT user_id, user_name FROM users ORDER BY user_name')
    users = cursor.fetchall()

    conn.close()

    return users


def validate_user_id(db_path: str, user_id: int) -> bool:
    """
    Validate the user ID.

    :param db_path: Path to the SQLite database file.
    :param user_id: The ID of the user.
    :return: True if the user ID is valid, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the user exists
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    existing_user_id = cursor.fetchone()

    conn.close()

    return existing_user_id is not None
