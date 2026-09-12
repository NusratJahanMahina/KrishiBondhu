from db_connect import get_connection

conn = get_connection()
cur = conn.cursor()

# Hardcoded values - no binds, no TRIM, nothing fancy
print("=== TEST 1: hardcoded center_code, no binds ===")
cur.execute("""
    SELECT l.loan_no, l.loan_state
    FROM LOAN l
    JOIN FARMER f ON l.farmer_code = f.farmer_code
    WHERE f.center_code = 'C-001'
    AND l.loan_state = 'PENDING'
""")
rows = cur.fetchall()
print(f"  Got {len(rows)} rows")
for r in rows:
    print(f"    {r}")

# Same query with ONE bind
print("\n=== TEST 2: one bind for center_code ===")
cur.execute("""
    SELECT l.loan_no, l.loan_state
    FROM LOAN l
    JOIN FARMER f ON l.farmer_code = f.farmer_code
    WHERE f.center_code = :1
    AND l.loan_state = 'PENDING'
""", ('C-001',))
rows = cur.fetchall()
print(f"  Got {len(rows)} rows")
for r in rows:
    print(f"    {r}")

# Same query with TWO binds (like our function)
print("\n=== TEST 3: two binds (:1 and :2) ===")
cur.execute("""
    SELECT l.loan_no
    FROM LOAN l
    JOIN FARMER f ON l.farmer_code = f.farmer_code
    WHERE f.center_code = :1
    AND l.loan_state = 'PENDING'
    AND (:2 = :2)
""", ('C-001', 'AG-001'))
rows = cur.fetchall()
print(f"  Got {len(rows)} rows")

# Check what get_center_code returns
print("\n=== TEST 4: what does get_center_code return? ===")
from agent_queries import get_center_code
cc = get_center_code(cur, 1001)
print(f"  center_code = {cc!r}, type={type(cc).__name__}, len={len(cc) if cc else 0}")

# Check its hex bytes
if cc:
    print(f"  bytes = {cc.encode('utf-8').hex()}")

conn.close()