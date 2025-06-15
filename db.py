import sqlite3
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

db_data = os.getenv("db_data")
admin_user_id = os.getenv("admin_user_id")


def init_db(path):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_fullname TEXT,
            register_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EXPENSES (
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS INCOMES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            subcategory TEXT,
            amount REAL,
            description TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()

    print("DB initialized!")

def delete_all_previous_incomes(user_id):
    conn = sqlite3.connect(db_data)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM INCOMES WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_all_previous_expenses(user_id):
    conn = sqlite3.connect(db_data)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM EXPENSES WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def migrate_table(source_db, table_name, target_conn):
    src_conn = sqlite3.connect(source_db)
    src_cursor = src_conn.cursor()
    tgt_cursor = target_conn.cursor()
    table_name = table_name.upper()

    rows = src_cursor.execute(f"SELECT * FROM {table_name}").fetchall()
    columns = [col[0] for col in src_cursor.description]
    placeholders = ", ".join(["?"] * len(columns))
    insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

    tgt_cursor.executemany(insert_query, rows)
    print(f"[✓] Migrated {len(rows)} rows from {source_db} → {table_name}")

    src_conn.close()


if __name__ == "__main__":
    # init_db(db_path)
    # delete_all_previous_incomes(admin_user_id)
    # delete_all_previous_expenses(admin_user_id)

    # main_conn = sqlite3.connect(db_data)
    # migrate_table(db_users, 'users', main_conn)
    # migrate_table(db_expenses, 'expenses', main_conn)
    # migrate_table(db_incomes, 'incomes', main_conn)
    # main_conn.commit()
    # main_conn.close()

    pass
