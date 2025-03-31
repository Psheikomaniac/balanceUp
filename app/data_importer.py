import csv
import re
import sqlite3
import os
from datetime import datetime
from app.services.logging_utils import log_action
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define our own database connection functions to avoid import issues
def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join('database', 'penalties.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database if needed"""
    db_path = os.path.join('database', 'penalties.db')
    logger.info(f"Checking database connection at {db_path}")
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
        logger.info(f"Created database directory: {os.path.dirname(db_path)}")
    
    # Just verify we can connect
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def truncate_table(cursor, table_name):
    """Truncate the specified table"""
    try:
        if table_name not in ['dues', 'punishments', 'transactions']:
            raise ValueError(f"Invalid table name: {table_name}")
        cursor.execute(f"DELETE FROM {table_name}")
        logger.info(f"Truncated table: {table_name}")
    except sqlite3.Error as e:
        logger.error(f"Error truncating table {table_name}: {e}")
        raise

def get_files_to_import(directory):
    """Get all CSV files that match our naming pattern"""
    pattern = re.compile(r'^cashbox-(dues|punishments|transactions)-\d{2}-\d{2}-\d{4}-\d{6}\.csv$')
    for filename in os.listdir(directory):
        if pattern.match(filename):
            file_type = filename.split('-')[1]  # dues, punishments, or transactions
            yield (os.path.join(directory, filename), file_type)

def detect_file_type(file_path):
    """Detect file type by examining the CSV headers"""
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')
            headers = reader.fieldnames
            if headers:
                # Fix for punishments with misspelled headers
                if any(h.startswith('penatly_') for h in headers):
                    return 'punishments'
                elif any(h.startswith('penalty_') for h in headers):
                    return 'punishments'
                elif any(h.startswith('due_') for h in headers):
                    return 'dues'
                elif any(h.startswith('transaction_') for h in headers):
                    return 'transactions'
    except Exception as e:
        logger.error(f"Error detecting file type: {e}")
    return None

def convert_payment_status(status, paid_date):
    """Convert payment status from CSV to database format"""
    if status == "STATUS_EXEMPT":
        # For exempt status, we set paid_date but preserve the status
        return paid_date if paid_date else datetime.now().strftime('%Y-%m-%d')
    elif status == "STATUS_PAID" and paid_date:
        return paid_date
    return None

def extract_user_from_subject(subject):
    """Extract username from transaction subject if possible"""
    if ': ' in subject:
        parts = subject.split(': ')
        if len(parts) > 1:
            user_part = parts[1]
            if ' (' in user_part:
                return user_part.split(' (')[0]
    return None

def process_batch(cursor, batch_data, query):
    """Process a batch of data with a single execute many statement"""
    if batch_data:
        cursor.executemany(query, batch_data)
        batch_size = len(batch_data)
        logger.info(f"Processed batch of {batch_size} records")
        return batch_size
    return 0

def import_data(file_path=None):
    """Import data from CSV files in the cashbox directory"""
    init_db()
    cashbox_dir = os.path.join(os.path.dirname(__file__), 'cashbox')
    
    # If specific file is provided, only process that file
    if file_path:
        file_type = None
        pattern = re.compile(r'^cashbox-(dues|punishments|transactions)-')
        filename = os.path.basename(file_path)
        if pattern.match(filename):
            file_type = pattern.match(filename).group(1)  # dues, punishments, or transactions
        if not file_type:
            # Try to detect file type from content for non-standard filenames
            file_type = detect_file_type(file_path)
            if not file_type:
                logger.error(f"Could not determine file type for {file_path}")
                return
        files_to_process = [(file_path, file_type)]
    else:
        files_to_process = get_files_to_import(cashbox_dir)

    # Fix column names based on file type
    column_mapping = {
        'punishments': {
            'penalty_created': 'created',
            'penatly_created': 'created',  # Handle both spellings
            'penalty_user': 'user',
            'penatly_user': 'user',
            'username': 'user',  # Map username to user
            'penalty_reason': 'reason',
            'penatly_reason': 'reason',
            'penalty_name': 'reason',  # Map penalty_name to reason
            'penalty_archived': 'archived',
            'penatly_archived': 'archived',
            'penalty_paid': 'paid_date',
            'penatly_paid': 'paid_date',
            'user_payment_date': 'paid_date',  # Add mapping for user_payment_date
            'penalty_amount': 'amount',
            'penatly_amount': 'amount',
            'penalty_currency': 'currency',
            'penatly_currency': 'currency',
            'penalty_subject': 'subject',
            'penatly_subject': 'subject'
        },
        'dues': {
            'due_created': 'created',
            'due_user': 'user',
            'username': 'user',  # Map username to user
            'due_reason': 'reason',
            'due_name': 'reason',  # Map due_name to reason
            'due_archived': 'archived',
            'due_paid': 'paid_date',
            'user_payment_date': 'paid_date',  # Add mapping for user_payment_date
            'due_amount': 'amount',
            'due_currency': 'currency',
            'due_subject': 'subject'
        },
        'transactions': {
            'transaction_created': 'created',
            'transaction_user': 'user',
            'username': 'user',  # Map username to user
            'transaction_reason': 'reason',
            'transaction_name': 'reason',  # Map transaction_name to reason
            'transaction_amount': 'amount',
            'transaction_currency': 'currency',
            'transaction_subject': 'subject'
        }
    }

    # Prepare queries for batch operations
    due_query = '''
        INSERT INTO dues (
            user_id, team_id, due_created, due_reason,
            due_archived, due_amount, due_currency, 
            due_subject, search_params, due_paid_date, user_paid
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    punishment_query = '''
        INSERT INTO punishments (
            user_id, team_id, penalty_created, penalty_reason,
            penalty_archived, penalty_amount, penalty_currency, 
            penalty_subject, search_params, penalty_paid_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    transaction_query = '''
        INSERT INTO transactions (
            user_id, team_id, transaction_created, transaction_reason,
            transaction_amount, transaction_currency, transaction_subject,
            search_params
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''

    # Use a single connection for the entire import process
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA cache_size = 10000")  # Increase cache size for performance
        cursor.execute("BEGIN TRANSACTION")
        
        # Cache users to avoid repeated lookups
        users_cache = {}
        cursor.execute('SELECT user_id, user_name FROM users')
        for user_id, user_name in cursor.fetchall():
            users_cache[user_name] = user_id
        
        # Cache teams
        teams_map = {}
        cursor.execute('SELECT team_id, team_name FROM teams')
        for team_id, team_name in cursor.fetchall():
            teams_map[team_id] = team_name
        
        total_processed = 0
        
        for file_path, file_type in files_to_process:
            try:
                # Truncate the corresponding table before importing new data
                truncate_table(cursor, file_type)
                
                with open(file_path, mode='r', encoding='utf-8-sig') as file:
                    reader = csv.DictReader(file, delimiter=';')
                    mapping = column_mapping[file_type]
                    
                    # Prepare batches for bulk inserts
                    batch_data = []
                    batch_size = 1000  # Process 1000 rows at a time
                    
                    # Keep track of processed rows for logging
                    processed_rows = 0
                    paid_items = 0
                    
                    for row in reader:
                        try:
                            fixed_row = {}
                            for key, value in row.items():
                                fixed_key = mapping.get(key, key)
                                fixed_row[fixed_key] = value
                            
                            team_id = int(fixed_row['team_id'])
                            team_name = fixed_row['team_name']
                            
                            # Special handling for transactions which don't have a direct user field
                            if file_type == 'transactions':
                                subject = fixed_row.get('transaction_subject', '')
                                user_name = extract_user_from_subject(subject)
                                if not user_name:
                                    # If we can't extract a user, use a placeholder
                                    user_name = "SYSTEM"
                                created_date = datetime.strptime(fixed_row['transaction_date'], '%d-%m-%Y').strftime('%Y-%m-%d')
                                # For transactions, use subject as reason if no specific reason field exists
                                reason = fixed_row.get('transaction_reason', subject)
                            else:
                                user_name = fixed_row['user']
                                created_date = datetime.strptime(fixed_row['created'], '%d-%m-%Y').strftime('%Y-%m-%d')
                                reason = fixed_row.get('reason', '')
                                
                            # Handle amount conversion
                            try:
                                amount = float(fixed_row.get('amount', fixed_row.get('transaction_amount', '0'))) / 100
                            except ValueError:
                                amount = 0.0
                                
                            currency = fixed_row.get('currency', fixed_row.get('transaction_currency', 'EUR'))
                            subject = fixed_row.get('subject', fixed_row.get('transaction_subject', ''))
                            search_params = fixed_row.get('search_params', '')
                            
                            # Handle paid_date and status for dues and punishments
                            paid_date = None
                            if file_type in ['dues', 'punishments']:
                                # For punishments, check if penatly_paid or penalty_paid contains a date
                                if file_type == 'punishments':
                                    # Get any field with "paid" in its name
                                    paid_date_str = None
                                    
                                    # Check both penatly_paid and penalty_paid fields
                                    if 'penatly_paid' in row and row['penatly_paid'] and row['penatly_paid'].strip():
                                        paid_date_str = row['penatly_paid']
                                    elif 'penalty_paid' in row and row['penalty_paid'] and row['penalty_paid'].strip():
                                        paid_date_str = row['penalty_paid']
                                        
                                    # Process the paid date if we have one
                                    if paid_date_str:
                                        try:
                                            paid_date = datetime.strptime(paid_date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
                                            paid_items += 1
                                        except ValueError:
                                            logger.warning(f"Invalid date format for paid_date: {paid_date_str}")
                                            paid_date = None
                                else:
                                    # For dues, use the payment_date and status logic
                                    status = fixed_row.get('user_paid', '')
                                    payment_date = fixed_row.get('user_payment_date', '')
                                    
                                    if payment_date:
                                        try:
                                            paid_date = datetime.strptime(payment_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                                        except ValueError:
                                            paid_date = None
                                    
                                    paid_date = convert_payment_status(status, paid_date)
                                    
                            # Handle archived field for dues and punishments
                            archived = None
                            if file_type in ['dues', 'punishments']:
                                archived_value = fixed_row.get('archived', '')
                                archived = 1 if archived_value and archived_value.upper() == 'YES' else 0
                                
                            # Ensure team exists
                            if team_id not in teams_map:
                                cursor.execute('INSERT OR IGNORE INTO teams (team_id, team_name) VALUES (?, ?)', 
                                             (team_id, team_name))
                                teams_map[team_id] = team_id
                            
                            # Handle user creation/lookup more efficiently using the cache
                            if user_name in users_cache:
                                user_id = users_cache[user_name]
                            else:
                                # User not in cache, look up in database
                                cursor.execute('SELECT user_id FROM users WHERE user_name = ?', (user_name,))
                                existing_user = cursor.fetchone()
                                
                                if existing_user:
                                    user_id = existing_user[0]
                                    users_cache[user_name] = user_id  # Update cache
                                else:
                                    # Create user with auto-generated ID
                                    cursor.execute('INSERT INTO users (user_name, team_id) VALUES (?, ?)', 
                                                (user_name, team_id))
                                    user_id = cursor.lastrowid
                                    users_cache[user_name] = user_id
                            
                            # Prepare data for batch insert based on file type
                            if file_type == 'dues':
                                batch_data.append((
                                    user_id, team_id, created_date, reason,
                                    archived, amount, currency, subject,
                                    search_params, paid_date, fixed_row.get('user_paid', 'STATUS_UNPAID')
                                ))
                            elif file_type == 'punishments':
                                batch_data.append((
                                    user_id, team_id, created_date, reason,
                                    archived, amount, currency, subject,
                                    search_params, paid_date
                                ))
                            else:  # transactions
                                batch_data.append((
                                    user_id, team_id, created_date, reason,
                                    amount, currency, subject, search_params
                                ))
                            
                            processed_rows += 1
                            
                            # Process in batches for better performance
                            if len(batch_data) >= batch_size:
                                if file_type == 'dues':
                                    process_batch(cursor, batch_data, due_query)
                                elif file_type == 'punishments':
                                    process_batch(cursor, batch_data, punishment_query)
                                else:  # transactions
                                    process_batch(cursor, batch_data, transaction_query)
                                batch_data = []
                                
                        except Exception as e:
                            logger.error(f"Error importing row: {row}. Error: {e}")
                            raise  # Re-raise to trigger rollback
                    
                    # Process any remaining rows in the batch
                    if batch_data:
                        if file_type == 'dues':
                            process_batch(cursor, batch_data, due_query)
                        elif file_type == 'punishments':
                            process_batch(cursor, batch_data, punishment_query)
                        else:  # transactions
                            process_batch(cursor, batch_data, transaction_query)
                    
                    logger.info(f"Processed {processed_rows} rows from {file_path}")
                    logger.info(f"Found {paid_items} paid items in {file_path}")
                    total_processed += processed_rows
                
                # After successful import, rename the file using current date
                basename = os.path.basename(file_path)
                
                # Use current date for the new filename
                current_date = datetime.now().strftime('%Y%m%d')
                new_filename = f"{current_date}_{file_type}.csv"
                new_filepath = os.path.join(os.path.dirname(file_path), new_filename)
                
                # Check if target file already exists
                if os.path.exists(new_filepath):
                    # Add timestamp to make it unique
                    timestamp = datetime.now().strftime('%H%M%S')
                    new_filename = f"{current_date}_{timestamp}_{file_type}.csv"
                    new_filepath = os.path.join(os.path.dirname(file_path), new_filename)
                
                if file_path != new_filepath:
                    os.rename(file_path, new_filepath)
                    logger.info(f"Renamed {basename} to {new_filename}")

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                conn.rollback()
                raise
        
        # Commit the entire transaction after all files are processed
        conn.commit()
        logger.info(f"Successfully imported {total_processed} records in total")
        
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()