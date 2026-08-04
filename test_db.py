from db_connect import get_connection

def test_connection():
    conn = get_connection()
    if conn is None:
        return
    
    cursor = conn.cursor()
    cursor.execute("SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') FROM DUAL")
    result = cursor.fetchone()
    
    print(f"Oracle is alive! Database time is: {result[0]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_connection()
