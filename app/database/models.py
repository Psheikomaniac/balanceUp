import sqlite3
import os
from datetime import datetime

def get_db_connection():
    """
    Get a connection to the SQLite database with proper configuration.
    - Enables foreign key constraints
    - Sets row factory to sqlite3.Row for dict-like row access
    - Creates database directory if it doesn't exist
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'penalties.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    """
    Initialize the database schema with tables and constraints.
    Tables:
    - teams: Stores team information
    - users: Stores user information with team association
    - punishments: Stores punishment records (formerly penalties)
    - dues: Stores dues records
    - transactions: Stores transaction records
    - logs: Stores application activity logs
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            team_name TEXT NOT NULL CHECK(length(team_name) <= 100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL CHECK(length(user_name) <= 100),
            team_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        )
    ''')

    # Handle the rename of penalties to punishments if needed
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='penalties'")
    if cursor.fetchone() is not None:
        # Penalties table exists, rename it to punishments
        cursor.execute('ALTER TABLE penalties RENAME TO punishments')
    else:
        # Create punishments table if neither exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS punishments (
                penalty_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                penalty_created DATE NOT NULL,
                penalty_reason TEXT NOT NULL CHECK(length(penalty_reason) <= 500),
                penalty_archived INTEGER DEFAULT 0 CHECK(penalty_archived IN (0, 1)),
                penalty_amount REAL NOT NULL CHECK(penalty_amount >= 0),
                penalty_currency TEXT NOT NULL DEFAULT 'EUR' CHECK(length(penalty_currency) = 3),
                penalty_subject TEXT CHECK(penalty_subject IS NULL OR length(penalty_subject) <= 200),
                search_params TEXT CHECK(search_params IS NULL OR length(search_params) <= 500),
                penalty_paid_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                CHECK(penalty_paid_date IS NULL OR penalty_paid_date >= penalty_created)
            )
        ''')

    # Create dues table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dues (
            due_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            due_created DATE NOT NULL,
            due_reason TEXT NOT NULL CHECK(length(due_reason) <= 500),
            due_archived INTEGER DEFAULT 0 CHECK(due_archived IN (0, 1)),
            due_amount REAL NOT NULL CHECK(due_amount >= 0),
            due_currency TEXT NOT NULL DEFAULT 'EUR' CHECK(length(due_currency) = 3),
            due_subject TEXT CHECK(due_subject IS NULL OR length(due_subject) <= 200),
            search_params TEXT CHECK(search_params IS NULL OR length(search_params) <= 500),
            due_paid_date DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (team_id) REFERENCES teams (team_id),
            CHECK(due_paid_date IS NULL OR due_paid_date >= due_created)
        )
    ''')

    # Add user_paid column to dues table if it doesn't exist
    cursor.execute("""
        PRAGMA table_info(dues)
    """)
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_paid' not in columns:
        cursor.execute("""
            ALTER TABLE dues
            ADD COLUMN user_paid TEXT CHECK(user_paid IN ('STATUS_PAID', 'STATUS_UNPAID', 'STATUS_EXEMPT') OR user_paid IS NULL)
        """)

    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            transaction_created DATE NOT NULL,
            transaction_reason TEXT NOT NULL CHECK(length(transaction_reason) <= 500),
            transaction_amount REAL NOT NULL,
            transaction_currency TEXT NOT NULL DEFAULT 'EUR' CHECK(length(transaction_currency) = 3),
            transaction_subject TEXT CHECK(transaction_subject IS NULL OR length(transaction_subject) <= 200),
            search_params TEXT CHECK(search_params IS NULL OR length(search_params) <= 500),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (team_id) REFERENCES teams (team_id)
        )
    ''')

    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_timestamp DATETIME NOT NULL,
            log_action TEXT NOT NULL CHECK(length(log_action) <= 50),
            log_details TEXT CHECK(log_details IS NULL OR length(log_details) <= 500),
            user_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Create trigger to update updated_at timestamp for teams
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_team_timestamp 
        AFTER UPDATE ON teams
        BEGIN
            UPDATE teams SET updated_at = CURRENT_TIMESTAMP 
            WHERE team_id = NEW.team_id;
        END;
    ''')

    # Create trigger to update updated_at timestamp for users
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_user_timestamp 
        AFTER UPDATE ON users
        BEGIN
            UPDATE users SET updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = NEW.user_id;
        END;
    ''')

    # Create trigger to update updated_at timestamp for punishments
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_punishment_timestamp 
        AFTER UPDATE ON punishments
        BEGIN
            UPDATE punishments SET updated_at = CURRENT_TIMESTAMP 
            WHERE penalty_id = NEW.penalty_id;
        END;
    ''')

    # Create trigger to update updated_at timestamp for dues
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_dues_timestamp 
        AFTER UPDATE ON dues
        BEGIN
            UPDATE dues SET updated_at = CURRENT_TIMESTAMP 
            WHERE due_id = NEW.due_id;
        END;
    ''')

    # Create trigger to update updated_at timestamp for transactions
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_transactions_timestamp 
        AFTER UPDATE ON transactions
        BEGIN
            UPDATE transactions SET updated_at = CURRENT_TIMESTAMP 
            WHERE transaction_id = NEW.transaction_id;
        END;
    ''')

    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_punishments_user_id ON punishments(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_punishments_team_id ON punishments(team_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_punishments_paid_date ON punishments(penalty_paid_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_punishments_created ON punishments(penalty_created)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(team_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(log_timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dues_user_id ON dues(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dues_team_id ON dues(team_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dues_paid_date ON dues(due_paid_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dues_created ON dues(due_created)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_team_id ON transactions(team_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(transaction_created)')

    conn.commit()
    conn.close()

# Initialize the database when this module is imported
init_db()
