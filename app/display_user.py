# display_user_penalties_by_id.py
import os
import sys
# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime
from app.services.user_utils import display_user_ids, validate_user_id


def display_user_penalties(db_path, user_id):
    """
    Display all unpaid items (penalties, dues) for the given user ID and return them as lists.
    Only show STATUS_UNPAID items, treat STATUS_EXEMPT as paid.

    :param db_path: Path to the SQLite database file.
    :param user_id: The ID of the user.
    :return: Tuple of (punishments, dues) where each is a list of records
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch user name
    cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
    user_name = cursor.fetchone()

    if not user_name:
        print(f"User with ID '{user_id}' does not exist.")
        conn.close()
        return [], []

    user_name = user_name[0]
    total_amount = 0

    print(f"\nItems for user '{user_name}' (ID: {user_id}):")
    print("-" * 50)

    # Fetch unpaid punishments (those without a paid date)
    query_punishments = """
    SELECT penalty_id, penalty_created, penalty_amount, penalty_reason, penalty_currency
    FROM punishments
    WHERE user_id = ? AND penalty_paid_date IS NULL
    ORDER BY penalty_created DESC
    """
    cursor.execute(query_punishments, (user_id,))
    punishments = cursor.fetchall()

    if punishments:
        print("\nUnpaid punishments:")
        for i, (pid, created, amount, reason, currency) in enumerate(punishments, 1):
            formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
            print(f"{i}. {formatted_date} {reason} ({amount} {currency})")
            total_amount += amount

    # Fetch unpaid dues (only STATUS_UNPAID)
    query_dues = """
    SELECT due_id, due_created, due_amount, due_reason, due_currency
    FROM dues
    WHERE user_id = ? 
    AND (
        (due_paid_date IS NULL AND user_paid = 'STATUS_UNPAID')
        OR (due_paid_date IS NULL AND user_paid IS NULL)
    )
    ORDER BY due_created DESC
    """
    cursor.execute(query_dues, (user_id,))
    dues = cursor.fetchall()

    if dues:
        print("\nUnpaid dues:")
        punishment_count = len(punishments)
        for i, (did, created, amount, reason, currency) in enumerate(dues, punishment_count + 1):
            formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
            print(f"{i}. {formatted_date} {reason} ({amount} {currency})")
            total_amount += amount

    # Show recent transactions separately (for information only)
    query_transactions = """
    SELECT transaction_created, transaction_amount, transaction_reason, transaction_currency
    FROM transactions
    WHERE user_id = ?
    ORDER BY transaction_created DESC
    LIMIT 5
    """
    cursor.execute(query_transactions, (user_id,))
    transactions = cursor.fetchall()

    if transactions:
        print("\nRecent transactions (last 5, for reference only):")
        for created, amount, reason, currency in transactions:
            formatted_date = datetime.strptime(created, '%Y-%m-%d').strftime('%d.%m.%Y')
            print(f"{formatted_date} {reason} ({amount} {currency})")

    if total_amount > 0:
        print(f"\nTotal unpaid amount: {total_amount} €")
    else:
        print("\nNo unpaid items found.")
    print("-" * 50)

    conn.close()
    return punishments, dues


def update_selected_penalties(db_path, user_id, selected_items, punishments, dues):
    """
    Update only the selected unpaid items for the given user ID.

    :param db_path: Path to the SQLite database file.
    :param user_id: The ID of the user.
    :param selected_items: List of selected item numbers
    :param punishments: List of punishment records
    :param dues: List of dues records
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the user exists
    cursor.execute('SELECT user_name FROM users WHERE user_id = ?', (user_id,))
    user_name = cursor.fetchone()

    if not user_name:
        print(f"User with ID '{user_id}' does not exist.")
        conn.close()
        return

    current_date = datetime.now().strftime('%Y-%m-%d')
    punishment_count = len(punishments)

    for item_num in selected_items:
        if 1 <= item_num <= punishment_count:
            # It's a punishment
            penalty_id = punishments[item_num - 1][0]
            cursor.execute("""
                UPDATE punishments
                SET penalty_paid_date = ?
                WHERE penalty_id = ? AND user_id = ?
            """, (current_date, penalty_id, user_id))
        else:
            # It's a due
            due_index = item_num - punishment_count - 1
            if due_index < len(dues):
                due_id = dues[due_index][0]
                cursor.execute("""
                    UPDATE dues
                    SET due_paid_date = ?, user_paid = 'STATUS_PAID'
                    WHERE due_id = ? AND user_id = ?
                """, (current_date, due_id, user_id))

    conn.commit()
    print(f"Updated selected items for user '{user_name[0]}' (ID: {user_id}).")
    conn.close()


if __name__ == "__main__":
    db_path = ('database/penalties.db')

    # Display user IDs with their names sorted alphabetically by name
    print("\nAvailable users:")
    print("-" * 30)
    users = display_user_ids(db_path)
    for user_id, user_name in users:
        print(f"ID: {user_id:2d} | {user_name}")
    print("-" * 30 + "\n")

    while True:
        user_id_input = input("Please enter the user ID: ")

        try:
            user_id = int(user_id_input)
            if validate_user_id(db_path, user_id):
                # Display unpaid penalties for the given user ID
                punishments, dues = display_user_penalties(db_path, user_id)

                if punishments or dues:
                    print("\nEnter the numbers of the items you want to mark as paid (comma-separated)")
                    print("Example: 1,3,4 or 'all' for all items")
                    selection = input("Your selection (or press Enter to cancel): ").strip()

                    if selection.lower() == '':
                        print("Update canceled. Exiting script.")
                        break
                    elif selection.lower() == 'all':
                        selected_items = list(range(1, len(punishments) + len(dues) + 1))
                    else:
                        try:
                            selected_items = [int(x.strip()) for x in selection.split(',')]
                            max_allowed = len(punishments) + len(dues)
                            if not all(1 <= x <= max_allowed for x in selected_items):
                                print(f"Invalid selection. Please enter numbers between 1 and {max_allowed}")
                                continue
                        except ValueError:
                            print("Invalid input. Please enter numbers separated by commas.")
                            continue

                    # Update selected penalties
                    update_selected_penalties(db_path, user_id, selected_items, punishments, dues)
                    break
                else:
                    break
            else:
                print(f"Invalid user ID: {user_id}")
        except ValueError:
            print("Invalid input. Please enter a valid user ID (integer).")
