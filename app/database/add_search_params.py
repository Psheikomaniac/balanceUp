"""
This script adds the search_params column to the penalties table
if it doesn't already exist.
"""
import sqlite3
import os
from app.database.models import get_db_connection

def migrate_db():
    """Add search_params column to penalties table if it doesn't exist."""
    print("Starting database migration...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if search_params column exists
        cursor.execute("PRAGMA table_info(penalties)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'search_params' not in columns:
            print("Adding search_params column to penalties table...")
            cursor.execute('''
                ALTER TABLE penalties
                ADD COLUMN search_params TEXT CHECK(search_params IS NULL OR length(search_params) <= 500)
            ''')
            conn.commit()
            print("Column added successfully!")
        else:
            print("search_params column already exists. No changes made.")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        conn.rollback()
    finally:
        conn.close()
        
if __name__ == "__main__":
    migrate_db()