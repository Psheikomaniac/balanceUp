# logging_utils.py

from datetime import datetime
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
