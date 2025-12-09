import sqlite3

conn = sqlite3.connect('example.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER
)
''')

cursor.execute('INSERT INTO users (name, age) VALUES (?, ?)', ('test', 30))
cursor.execute('INSERT INTO users (name, age) VALUES (?, ?)', ('asd', 25))
conn.commit()

cursor.execute('SELECT * FROM users')
rows = cursor.fetchall()
for row in rows:
    print(row)

cursor.execute('UPDATE users SET age = ? WHERE name = ?', (31, 'asd'))
conn.commit()

cursor.execute('DELETE FROM users WHERE name = ?', ('test',))
conn.commit()

conn.close()
