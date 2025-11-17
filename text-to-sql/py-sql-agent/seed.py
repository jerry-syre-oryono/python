# seed.py
import sqlite3

conn = sqlite3.connect("users.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    email TEXT,
    department TEXT
)
""")

cur.executemany("""
INSERT INTO users (name, age, email, department) VALUES (?, ?, ?, ?)
""", [
    ("Alice Johnson", 28, "alice@example.com", "Engineering"),
    ("Bob Smith", 35, "bob@example.com", "Sales"),
    ("Charlie Brown", 42, "charlie@example.com", "HR"),
    ("Dana White", 29, "dana@example.com", "Engineering"),
    ("Eli Green", 50, "eli@example.com", "Management")
])

conn.commit()
print("✅ DB seeded with 5 users.")
conn.close()
