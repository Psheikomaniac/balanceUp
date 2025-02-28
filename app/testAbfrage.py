import sqlite3

conn = sqlite3.connect('/Users/private/PycharmProjects/scripts/balanceUp/database/penalties.db')
cursor = conn.cursor()

query = "SELECT * FROM penalties;"
cursor.execute(query)

results = cursor.fetchall()
for row in results:
    print(row)

conn.close()