import sqlite3
import os
import sys
# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def merge_duplicate_users(db_path):
    """Merge users with the same name, keeping the one with the larger user_id"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute("BEGIN")
        
        # Find duplicate usernames
        cursor.execute("""
            SELECT user_name, GROUP_CONCAT(user_id) as user_ids, COUNT(*) as count
            FROM users 
            GROUP BY user_name 
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        
        for user_name, user_ids, count in duplicates:
            ids = [int(id) for id in user_ids.split(',')]
            keep_id = max(ids)  # Keep the larger ID
            remove_ids = [id for id in ids if id != keep_id]
            
            print(f"Merging {user_name}: keeping ID {keep_id}, removing IDs {remove_ids}")
            
            # Update references in all tables
            for table in ['punishments', 'dues', 'transactions']:
                cursor.execute(f"""
                    UPDATE {table}
                    SET user_id = ?
                    WHERE user_id IN ({','.join('?' for _ in remove_ids)})
                """, [keep_id] + remove_ids)
            
            # Delete duplicate user entries
            cursor.execute(f"""
                DELETE FROM users
                WHERE user_name = ? AND user_id != ?
            """, (user_name, keep_id))
        
        # Commit changes
        conn.commit()
        print("Duplicate users merged successfully")
        
    except Exception as e:
        print(f"Error merging users: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = os.path.join('database', 'penalties.db')
    merge_duplicate_users(db_path)