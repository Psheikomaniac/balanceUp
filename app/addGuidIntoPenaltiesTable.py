import os
import configparser
import sqlite3
import uuid

config = configparser.ConfigParser()
config_path = os.path.join('config', 'config.ini')
config.read(config_path)
db_path = config['Database']['db_path']

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT rowid FROM penalties')
rows = cursor.fetchall()

for row in rows:
    penalty_id = str(uuid.uuid4())
    cursor.execute('UPDATE penalties SET penalty_id = ? WHERE rowid = ?', (penalty_id, row[0]))

conn.commit()
conn.close()

print("Die Spalte 'penalty_id' wurde erfolgreich hinzugefügt und mit GUIDs gefüllt.")