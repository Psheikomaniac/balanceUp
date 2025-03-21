#!/usr/bin/env python3
import os
import sys
import sqlite3
from datetime import datetime

def summarize_unpaid_penalties():
    """Display a summary of unpaid penalties for all users with detailed reasons."""
    try:
        # Use absolute path to the database
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'penalties.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get users with unpaid penalties and their total amounts
        query = """
        SELECT 
            u.user_name, 
            u.user_id,
            SUM(CASE WHEN p.penalty_reason = 'Guthaben' THEN -p.penalty_amount ELSE p.penalty_amount END) as total_amount
        FROM users u
        INNER JOIN punishments p ON u.user_id = p.user_id
        WHERE p.penalty_paid_date IS NULL
        AND p.penalty_archived = 0
        GROUP BY u.user_id, u.user_name
        HAVING total_amount > 0
        ORDER BY total_amount DESC
        """
        
        cursor.execute(query)
        users_with_penalties = cursor.fetchall()

        for user_name, user_id, total_amount in users_with_penalties:
            print("\n" + "=" * 60)
            print(f"User: {user_name}")
            print(f"Total Amount: {total_amount:.2f} EUR")
            print("Reasons:")
            
            # Get individual penalties for this user with more details
            penalty_query = """
            SELECT penalty_reason, penalty_amount, penalty_created, penalty_currency
            FROM punishments
            WHERE user_id = ?
            AND penalty_paid_date IS NULL
            AND penalty_archived = 0
            AND (penalty_reason != 'Guthaben' OR (penalty_reason = 'Guthaben' AND penalty_amount < 0))
            ORDER BY penalty_created DESC
            """
            
            cursor.execute(penalty_query, (user_id,))
            penalties = cursor.fetchall()

            # Group penalties by reason
            reason_dict = {}
            for reason, amount, created_date, currency in penalties:
                if reason not in reason_dict:
                    reason_dict[reason] = []
                
                # Parse the date if it exists
                date_str = ""
                if created_date:
                    try:
                        date_obj = datetime.strptime(created_date, '%Y-%m-%d')
                        date_str = date_obj.strftime('%d.%m.%Y')
                    except ValueError:
                        date_str = created_date
                
                reason_dict[reason].append((amount, date_str, currency))
            
            # Print grouped reasons
            for reason, entries in reason_dict.items():
                total_for_reason = sum(amount for amount, _, _ in entries)
                
                # Format the output
                if len(entries) > 1:
                    # Multiple entries for this reason
                    print(f"    - {reason} (Total: {total_for_reason:.2f} {entries[0][2]})")
                    for amount, date_str, currency in entries:
                        # Check if it might be a note (very small amount)
                        if amount < 0.01 and amount > 0:
                            print(f"        • {date_str} ({reason})")
                        else:
                            print(f"        • {date_str}: {amount:.2f} {currency}")
                else:
                    # Just one entry for this reason
                    amount, date_str, currency = entries[0]
                    # Check if it might be a note/special case (very small amount)
                    if amount < 0.01 and amount > 0:
                        print(f"    - {reason} (Kasten)")
                    else:
                        if date_str:
                            print(f"    - {reason}: {amount:.2f} {currency} ({date_str})")
                        else:
                            print(f"    - {reason}: {amount:.2f} {currency}")
            
            print("-" * 60)

        print(f"\nTotal unpaid amount across all users: {sum(u[2] for u in users_with_penalties):.2f} EUR")
        print(f"Total users with unpaid penalties: {len(users_with_penalties)}")

        conn.close()

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    summarize_unpaid_penalties()