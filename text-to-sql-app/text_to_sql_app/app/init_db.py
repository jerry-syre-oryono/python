# app/init_db.py
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///app/database.db")

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            country TEXT,
            signup_date TEXT
        );
    """))
    conn.execute(text("""
        INSERT INTO customers (name, country, signup_date)
        VALUES
        ('Alice', 'USA', '2024-06-10'),
        ('Bob', 'Kenya', '2024-06-12'),
        ('Clara', 'Uganda', '2024-07-01')
    """))
    conn.commit()
print("Database initialized ✅")
