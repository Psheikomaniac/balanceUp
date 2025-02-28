#!/usr/bin/env python3
import os
import csv
import sqlite3
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join('database', 'penalties.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def update_punishment_payments(csv_file_path):
    """
    Update penalty_paid_date in punishments table for records that have
    a payment date in the CSV file but not in the database.
    
    Args:
        csv_file_path: Path to the punishments CSV file
    """
    # Check if file exists
    if not os.path.isfile(csv_file_path):
        logger.error(f"File not found: {csv_file_path}")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        cursor.execute("BEGIN")
        
        # Store payment information from CSV
        payment_info = {}  # {(user_name, date, reason): payment_date}
        updated_records = 0
        
        # Read CSV file and extract payment data
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                user_name = row.get('penatly_user') or row.get('penalty_user', '')
                created_str = row.get('penatly_created') or row.get('penalty_created', '')
                reason = row.get('penatly_reason') or row.get('penalty_reason', '')
                paid_str = row.get('penatly_paid') or row.get('penalty_paid', '')
                
                # Skip if no payment date
                if not paid_str or not paid_str.strip():
                    continue
                
                try:
                    # Convert date format
                    created_date = datetime.strptime(created_str, '%d-%m-%Y').strftime('%Y-%m-%d')
                    paid_date = datetime.strptime(paid_str, '%d-%m-%Y').strftime('%Y-%m-%d')
                    
                    # Store payment info
                    key = (user_name, created_date, reason)
                    payment_info[key] = paid_date
                    logger.debug(f"Found payment: {user_name} - {created_date} - {reason} - paid on {paid_date}")
                except ValueError:
                    logger.warning(f"Invalid date format: created={created_str}, paid={paid_str}")
                    continue
        
        # Get user IDs for each user name
        user_ids = {}
        cursor.execute("SELECT user_id, user_name FROM users")
        for row in cursor.fetchall():
            user_ids[row['user_name']] = row['user_id']
            
        # Get punishments that don't have a payment date in DB
        cursor.execute("""
            SELECT 
                penalty_id, 
                u.user_name, 
                penalty_created, 
                penalty_reason, 
                penalty_paid_date
            FROM punishments p
            JOIN users u ON p.user_id = u.user_id
            WHERE penalty_paid_date IS NULL
        """)
        
        # Match and update records
        for record in cursor.fetchall():
            penalty_id = record['penalty_id']
            user_name = record['user_name']
            created_date = record['penalty_created']
            reason = record['penalty_reason']
            
            key = (user_name, created_date, reason)
            if key in payment_info:
                paid_date = payment_info[key]
                logger.info(f"Updating payment for: {user_name} - {created_date} - {reason} - now paid on {paid_date}")
                
                # Update the record
                cursor.execute("""
                    UPDATE punishments 
                    SET penalty_paid_date = ? 
                    WHERE penalty_id = ?
                """, (paid_date, penalty_id))
                
                updated_records += 1
        
        # Commit changes
        conn.commit()
        logger.info(f"Updated {updated_records} punishment records with correct payment dates")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating punishment payments: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    csv_file_path = os.path.join('app', 'cashbox', '20250228_punishments.csv')
    update_punishment_payments(csv_file_path)
    print(f"Finished updating punishment payment records.")