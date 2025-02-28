from .models import get_db_connection
from .schemas import Penalty, User
from typing import List, Optional

def get_user(user_id: int) -> Optional[User]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(**row)
    return None

def get_penalties(user_id: int) -> List[Penalty]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM penalties WHERE user_id = ? AND penalty_paid_date IS NULL', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [Penalty(**row) for row in rows]

def update_penalties(user_id: int, penalty_paid_date: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE penalties
        SET penalty_paid_date = ?
        WHERE user_id = ? AND penalty_paid_date IS NULL
    ''', (penalty_paid_date, user_id))
    conn.commit()
    conn.close()

def list_users() -> List[User]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY user_name')
    rows = cursor.fetchall()
    conn.close()
    return [User(**row) for row in rows]
