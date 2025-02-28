#!/usr/bin/env python3
import os
import sys
import sqlite3
from collections import defaultdict
from typing import Dict, List, Tuple, Set

# Add the project root to Python path to access app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the database connection function from app.database.models
from app.database.models import get_db_connection

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

def display_user_summary():
    """Display a summary of unpaid penalties per user, sorted from highest to lowest amount."""
    user_penalties = get_unpaid_penalties()
    
    if not user_penalties:
        print("\nNo users with unpaid penalties found.")
        return
    
    print("\nUnpaid Penalties Summary Per User:")
    print("=" * 80)
    
    total_sum = 0
    for user_name, amount, reasons in user_penalties:
        print(f"\nUser: {user_name}")
        print(f"Total Amount: {amount:.2f} EUR")
        
        # Print reasons with their counts
        print("Reasons:")
        for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                print(f"  - {reason} ({count}x)")
            else:
                print(f"  - {reason}")
        
        print("-" * 40)
        total_sum += amount
    
    print("\n" + "=" * 80)
    print(f"TOTAL UNPAID AMOUNT: {total_sum:.2f} EUR")
    print("=" * 80)

def get_unpaid_items_detailed():
    """Get all unpaid punishments and dues - detailed view (not used by default)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get unpaid punishments
        cursor.execute('''
            SELECT 
                'punishment' as type,
                u.user_name, 
                t.team_name,
                p.penalty_created as created_date,
                p.penalty_reason as reason,
                p.penalty_amount as amount,
                p.penalty_currency as currency
            FROM punishments p
            JOIN users u ON p.user_id = u.user_id
            JOIN teams t ON p.team_id = t.team_id
            WHERE p.penalty_paid_date IS NULL
            AND p.penalty_archived = 0
        ''')
        unpaid_punishments = cursor.fetchall()

        # Get unpaid dues
        cursor.execute('''
            SELECT 
                'due' as type,
                u.user_name, 
                t.team_name,
                d.due_created as created_date,
                d.due_reason as reason,
                d.due_amount as amount,
                d.due_currency as currency
            FROM dues d
            JOIN users u ON d.user_id = u.user_id
            JOIN teams t ON d.team_id = t.team_id
            WHERE d.due_paid_date IS NULL
            AND d.due_archived = 0
        ''')
        unpaid_dues = cursor.fetchall()

        # Combine and sort all unpaid items by date
        all_unpaid = []
        for row in unpaid_punishments + unpaid_dues:
            all_unpaid.append({
                'type': row[0],
                'user_name': row[1],
                'team_name': row[2],
                'created_date': row[3],
                'reason': row[4],
                'amount': row[5],
                'currency': row[6]
            })

        # Sort by date, newest first
        all_unpaid.sort(key=lambda x: x['created_date'], reverse=True)

        # Print summary
        if all_unpaid:
            print("\nUnpaid Items Summary (Detailed):")
            print("=" * 80)
            total_amount = 0
            for item in all_unpaid:
                print(f"\nType: {item['type'].upper()}")
                print(f"User: {item['user_name']}")
                print(f"Team: {item['team_name']}")
                print(f"Created: {item['created_date']}")
                print(f"Reason: {item['reason']}")
                print(f"Amount: {item['amount']} {item['currency']}")
                print("-" * 40)
                if item['currency'] == 'EUR':
                    total_amount += float(item['amount'])

            print(f"\nTotal unpaid amount: {total_amount:.2f} EUR")
        else:
            print("\nNo unpaid items found.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Use the summarized version by default
    display_user_summary()
    
    # Uncomment the line below to see the detailed view (not the default behavior)
    # get_unpaid_items_detailed()