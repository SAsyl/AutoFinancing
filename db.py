import sqlite3
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

db_expenses = os.getenv("db_expenses")
db_incomes = os.getenv("db_incomes")
db_users = os.getenv("db_users")


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if db_path == db_expenses:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                subcategory TEXT,
                amount REAL,
                description TEXT,
                store TEXT,
                date TEXT
            )
        """)
    elif db_path == db_incomes:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                subcategory TEXT,
                amount REAL,
                description TEXT,
                date TEXT
            )
        """)
    elif db_path == db_users:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_fullname TEXT,
                register_date TEXT
            )
        """)

    conn.commit()
    conn.close()

    print("DB initialized!")

def add_expense(user_id, category, subcategory, amount, description, store, date=None):
    if date is None or date == '':
        date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        date = date + ''

    if user_id.lower() == 'asyl':
        user_id = os.getenv("admin_user_id")
    else:
        user_id = os.getenv("ghost_user_id")

    conn = sqlite3.connect(db_expenses)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (user_id, category, subcategory, amount, description, store, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, category, subcategory, amount, description, store, date))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # init_db(db_incomes)
    pass
