#!/usr/bin/env python3
import os
import sys
import sqlite3
from collections import defaultdict
from typing import Dict, List, Tuple, Set

# Add the project root to Python path to access app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define our own db connection function instead of importing it
def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join('database', 'penalties.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_unpaid_penalties() -> List[Tuple[str, float, Dict[str, int]]]:
    """
    Summarize unpaid penalties for each user, subtracting 'Guthaben' and 'Guthaben Rest' amounts.
    Returns a list of (user_name, total_amount, reason_counts) sorted by total_amount in descending order.
    Only includes users with a positive total amount.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all users and their unpaid penalties with user info
    cursor.execute('''
        SELECT 
            u.user_name,
            p.penalty_amount,
            p.penalty_reason,
            p.penalty_archived
        FROM punishments p 
        JOIN users u ON p.user_id = u.user_id
        WHERE p.penalty_paid_date IS NULL
        ORDER BY u.user_name
    ''')
    
    punishment_rows = cursor.fetchall()
    
    # Get unpaid dues as well
    cursor.execute('''
        SELECT 
            u.user_name,
            d.due_amount,
            d.due_reason,
            d.due_archived
        FROM dues d
        JOIN users u ON d.user_id = u.user_id
        WHERE d.due_paid_date IS NULL
        ORDER BY u.user_name
    ''')
    
    dues_rows = cursor.fetchall()
    conn.close()
    
    # Calculate the sum for each user, subtracting "Guthaben" and "Guthaben Rest" entries
    user_totals = defaultdict(float)  # {user_name: total_amount}
    user_reasons = defaultdict(lambda: defaultdict(int))  # {user_name: {reason: count}}
    
    # Process punishments
    for row in punishment_rows:
        user_name = row['user_name']
        amount = row['penalty_amount']
        reason = row['penalty_reason'].strip() if row['penalty_reason'] else ""
        
        # Check for credit keywords in more varied forms
        is_credit = any(keyword in reason.lower() for keyword in ['guthaben', 'gutschrift', 'credit', 'erstattung', 'rückzahlung'])
        
        if is_credit:
            user_totals[user_name] -= amount
        else:
            user_totals[user_name] += amount
            if reason:  # Only count non-empty reasons
                user_reasons[user_name][reason] += 1
    
    # Process dues
    for row in dues_rows:
        user_name = row['user_name']
        amount = row['due_amount']
        reason = row['due_reason'].strip() if row['due_reason'] else ""
        
        # Check for credit keywords in more varied forms
        is_credit = any(keyword in reason.lower() for keyword in ['guthaben', 'gutschrift', 'credit', 'erstattung', 'rückzahlung'])
        
        if is_credit:
            user_totals[user_name] -= amount
        else:
            user_totals[user_name] += amount
            if reason:  # Only count non-empty reasons
                user_reasons[user_name][reason] += 1
    
    # Filter out users with non-positive balances and sort by amount (descending)
    result = [(user, total, user_reasons[user]) for user, total in user_totals.items() if total > 0]
    result.sort(key=lambda x: x[1], reverse=True)
    
    return result