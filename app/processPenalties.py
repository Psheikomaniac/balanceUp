import sqlite3

db_path = 'database/penalties.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

query = """
SELECT `p`.`user_id`, `u`.`user_name`, `p`.`penalty_amount`, `p`.`penalty_reason`
FROM `penalties` AS `p`
JOIN `users` AS `u` ON `p`.`user_id` = `u`.`user_id`
WHERE `p`.`penalty_archived` = ? AND `p`.`penalty_paid_date` IS NULL
"""
cursor.execute(query, ('NO',))
rows = cursor.fetchall()

user_penalties = {}
for row in rows:
    user_id, user_name, penalty_amount, penalty_reason = row
    if user_id not in user_penalties:
        user_penalties[user_id] = {'user_name': user_name, 'amount': 0}
    if penalty_reason == 'Guthaben':
        user_penalties[user_id]['amount'] -= penalty_amount
    else:
        user_penalties[user_id]['amount'] += penalty_amount

filtered_users = {user_id: data for user_id, data in user_penalties.items() if data['amount'] >= 0}
sorted_users = sorted(filtered_users.values(), key=lambda x: x['amount'], reverse=True)

for user in sorted_users:
    print(f'{user["user_name"]}: {user["amount"]}')

conn.close()
