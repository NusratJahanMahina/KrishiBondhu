import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        # Point to the NEW Instant Client folder
        oracledb.init_oracle_client(lib_dir=r"C:\Users\Mahina\Downloads\instantclient-basic-windows.x64-23.26.3.0.0\instantclient_23_26")

        connection = oracledb.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dsn=os.getenv("DB_DSN")
        )
        print("Connected to Oracle successfully!")
        return connection
    except Exception as e:
        print(f"Connection Error: {e}")
        return None