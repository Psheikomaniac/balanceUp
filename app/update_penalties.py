# update_penalties_by_user_id.py

import sqlite3
from datetime import datetime
from services.user_utils import display_user_ids, validate_user_id


def update_penalties(db_path, user_id):
    """
    Update all unpaid penalties for the given user ID.

    :param db_path: Path to the SQLite database file.
    :param user_id: The ID of the user.
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

    user_name = user_name[0]

    # Update all unpaid penalties for the user
    update_query = """
    UPDATE penalties
    SET penalty_paid_date = ?
    WHERE user_id = ? AND penalty_paid_date IS NULL
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(update_query, (current_date, user_id))
    conn.commit()

    print(f"Updated all unpaid penalties for user '{user_name}' (ID: {user_id}).")
    conn.close()


if __name__ == "__main__":
    db_path = 'database/penalties.db'

    # Display user IDs with their names sorted alphabetically by name
    display_user_ids(db_path)

    while True:
        user_id_input = input("Please enter the user ID: ")

        try:
            user_id = int(user_id_input)
            if validate_user_id(db_path, user_id):
                confirmation = input(f"Do you want to update unpaid penalties for user ID '{user_id}'? (yes/no): ")
                if confirmation.lower() == 'yes':
                    # Update unpaid penalties for the given user ID
                    update_penalties(db_path, user_id)
                    break
                elif confirmation.lower() == 'no':
                    print("Update canceled. Exiting script.")
                    break
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
            else:
                print(f"Invalid user ID: {user_id}")
        except ValueError:
            print("Invalid input. Please enter a valid user ID (integer).")
