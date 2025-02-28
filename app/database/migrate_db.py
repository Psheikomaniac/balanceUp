import sqlite3
import os
from models import get_db_connection
from datetime import datetime

def migrate_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Start transaction
    cursor.execute('BEGIN TRANSACTION')
    
    try:
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')

        # Backup existing tables
        cursor.execute('CREATE TABLE penalties_backup AS SELECT * FROM penalties')
        cursor.execute('CREATE TABLE users_backup AS SELECT * FROM users')
        cursor.execute('CREATE TABLE teams_backup AS SELECT * FROM teams')
        
        # Drop existing tables in reverse order of dependencies
        cursor.execute('DROP TABLE penalties')
        cursor.execute('DROP TABLE users')
        cursor.execute('DROP TABLE teams')
        
        # Create new teams table with updated schema
        cursor.execute('''
            CREATE TABLE teams (
                team_id INTEGER PRIMARY KEY,
                team_name TEXT NOT NULL CHECK(length(team_name) <= 100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create new users table with updated schema
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL CHECK(length(user_name) <= 100),
                team_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (team_id)
            )
        ''')

        # Create new penalties table with updated schema
        cursor.execute('''
            CREATE TABLE penalties (
                penalty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                penalty_created DATE NOT NULL,
                penalty_reason TEXT NOT NULL CHECK(length(penalty_reason) <= 500),
                penalty_archived INTEGER DEFAULT 0 CHECK(penalty_archived IN (0, 1)),
                penalty_amount REAL NOT NULL CHECK(penalty_amount >= 0),
                penalty_currency TEXT NOT NULL DEFAULT 'EUR' CHECK(length(penalty_currency) = 3),
                penalty_subject TEXT CHECK(penalty_subject IS NULL OR length(penalty_subject) <= 200),
                penalty_paid_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                CHECK(penalty_paid_date IS NULL OR penalty_paid_date >= penalty_created)
            )
        ''')

        # Create triggers for updated_at
        cursor.execute('''
            CREATE TRIGGER update_team_timestamp 
            AFTER UPDATE ON teams
            BEGIN
                UPDATE teams SET updated_at = CURRENT_TIMESTAMP 
                WHERE team_id = NEW.team_id;
            END;
        ''')

        cursor.execute('''
            CREATE TRIGGER update_user_timestamp 
            AFTER UPDATE ON users
            BEGIN
                UPDATE users SET updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = NEW.user_id;
            END;
        ''')

        cursor.execute('''
            CREATE TRIGGER update_penalty_timestamp 
            AFTER UPDATE ON penalties
            BEGIN
                UPDATE penalties SET updated_at = CURRENT_TIMESTAMP 
                WHERE penalty_id = NEW.penalty_id;
            END;
        ''')

        # Migrate data from backup tables
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Migrate teams data
        cursor.execute('''
            INSERT INTO teams (team_id, team_name, created_at, updated_at)
            SELECT 
                team_id, 
                substr(team_name, 1, 100),  -- Enforce length limit
                ?, 
                ?
            FROM teams_backup
        ''', (current_timestamp, current_timestamp))

        # Migrate users data
        cursor.execute('''
            INSERT INTO users (user_id, user_name, team_id, created_at, updated_at)
            SELECT 
                user_id, 
                substr(user_name, 1, 100),  -- Enforce length limit
                team_id,
                ?, 
                ?
            FROM users_backup
        ''', (current_timestamp, current_timestamp))

        # Migrate penalties data
        cursor.execute('''
            INSERT INTO penalties (
                user_id, team_id, penalty_created, penalty_reason,
                penalty_archived, penalty_amount, penalty_currency,
                penalty_subject, penalty_paid_date, created_at, updated_at
            )
            SELECT 
                user_id, 
                team_id, 
                penalty_created,
                substr(penalty_reason, 1, 500),  -- Enforce length limit
                CASE 
                    WHEN penalty_archived = 'true' THEN 1
                    WHEN penalty_archived = 'false' THEN 0
                    ELSE 0
                END,
                ABS(penalty_amount),  -- Ensure non-negative
                COALESCE(penalty_currency, 'EUR'),
                CASE 
                    WHEN penalty_subject IS NULL THEN NULL
                    ELSE substr(penalty_subject, 1, 200)  -- Enforce length limit
                END,
                penalty_paid_date,
                ?,
                ?
            FROM penalties_backup
            WHERE penalty_amount >= 0  -- Skip invalid amounts
        ''', (current_timestamp, current_timestamp))
        
        # Create new indexes
        cursor.execute('CREATE INDEX idx_penalties_user_id ON penalties(user_id)')
        cursor.execute('CREATE INDEX idx_penalties_team_id ON penalties(team_id)')
        cursor.execute('CREATE INDEX idx_penalties_paid_date ON penalties(penalty_paid_date)')
        cursor.execute('CREATE INDEX idx_penalties_created ON penalties(penalty_created)')
        cursor.execute('CREATE INDEX idx_users_team_id ON users(team_id)')
        cursor.execute('CREATE INDEX idx_teams_name ON teams(team_name)')
        
        # Drop backup tables
        cursor.execute('DROP TABLE penalties_backup')
        cursor.execute('DROP TABLE users_backup')
        cursor.execute('DROP TABLE teams_backup')
        
        # Commit transaction
        conn.commit()
        print("Migration completed successfully with the following improvements:")
        print("- Added CHECK constraints for data validation")
        print("- Added audit fields (created_at, updated_at)")
        print("- Added automatic timestamp updates via triggers")
        print("- Added text field length limits")
        print("- Added additional indexes for better performance")
        print("- Enforced non-negative penalty amounts")
        print("- Enforced valid penalty_archived values (0 or 1)")
        print("- Enforced valid currency format")
        print("- Added validation for penalty_paid_date")
        
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()