import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        # Read Instant Client path from .env
        instant_client_path = os.getenv("INSTANT_CLIENT_PATH")
        
        if instant_client_path:
            oracledb.init_oracle_client(lib_dir=instant_client_path)
        else:
            print("Warning: INSTANT_CLIENT_PATH not found in .env")
            print("Trying to connect without Oracle Client...")

        # CONNECTION FIX: Simple, fresh connection
        connection = oracledb.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dsn=os.getenv("DB_DSN")
        )
        
        # CRITICAL FIX: Force the session to recognize new tables
        cursor = connection.cursor()
        cursor.execute("ALTER SESSION SET CURRENT_SCHEMA = " + os.getenv("DB_USER").upper())
        cursor.close()
        
        print("Connected to Oracle successfully!")
        return connection
    except Exception as e:
        print(f"Connection Error: {e}")
        return None