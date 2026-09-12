import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        # SQLite database path
        db_path = os.getenv("DB_PATH", "krishibondhu.db")
        
        connection = sqlite3.connect(db_path)
        # Enable foreign keys
        connection.execute("PRAGMA foreign_keys = ON")
        print(f"Connected to SQLite database: {db_path}")
        return connection
    except Exception as e:
        print(f"Connection Error: {e}")
        return None