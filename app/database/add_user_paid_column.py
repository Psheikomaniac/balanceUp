import sqlite3
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def add_user_paid_column():
    """Add user_paid column to dues table and populate it based on due_paid_date"""
    db_path = os.path.join('database', 'penalties.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute("BEGIN")
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(dues)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_paid' not in columns:
            # Add the column
            cursor.execute("""
                ALTER TABLE dues
                ADD COLUMN user_paid TEXT 
                CHECK(user_paid IN ('STATUS_PAID', 'STATUS_UNPAID', 'STATUS_EXEMPT') OR user_paid IS NULL)
            """)
            
            # Update existing records
            cursor.execute("""
                UPDATE dues
                SET user_paid = CASE 
                    WHEN due_paid_date IS NOT NULL THEN 'STATUS_PAID'
                    ELSE 'STATUS_UNPAID'
                END
            """)
        
        conn.commit()
        print("Added user_paid column to dues table")
        
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_user_paid_column()