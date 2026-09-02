# ============================================
# ADMIN QUERIES – now using unqualified table
# names because the session schema is set
# to KRISHIBANDHU via ALTER SESSION.
# ============================================

def get_admin_info(cursor, person_id):
    cursor.execute("""
        SELECT 
            a.admin_code,
            a.assigned_center_code,
            c.center_name,
            a.access_level,
            a.supervisor_id,
            p.first_name || ' ' || p.last_name AS supervisor_name
        FROM ADMIN a
        LEFT JOIN IFARMER_CENTER c ON a.assigned_center_code = c.center_code
        LEFT JOIN PERSON p ON a.supervisor_id = p.person_id
        WHERE a.person_id = :1
    """, (person_id,))
    return cursor.fetchone()

def get_pending_loans(cursor, center_code=None, is_super=False):
    if is_super:
        cursor.execute("""
            SELECT 
                l.loan_no,
                f.farmer_code,
                p.first_name || ' ' || p.last_name AS farmer_name,
                l.amount,
                l.purpose,
                TO_CHAR(l.application_date, 'DD-Mon-YYYY') AS app_date,
                cs.score AS credit_score,
                c.center_name
            FROM LOAN l
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            JOIN CREDIT_SCORE cs ON f.farmer_code = cs.farmer_code
            JOIN IFARMER_CENTER c ON f.center_code = c.center_code
            WHERE l.loan_state = 'PENDING'
            ORDER BY l.application_date ASC
        """)
    else:
        cursor.execute("""
            SELECT 
                l.loan_no,
                f.farmer_code,
                p.first_name || ' ' || p.last_name AS farmer_name,
                l.amount,
                l.purpose,
                TO_CHAR(l.application_date, 'DD-Mon-YYYY') AS app_date,
                cs.score AS credit_score
            FROM LOAN l
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            JOIN CREDIT_SCORE cs ON f.farmer_code = cs.farmer_code
            WHERE l.loan_state = 'PENDING'
            AND f.center_code = :1
            ORDER BY l.application_date ASC
        """, (center_code,))
    return cursor.fetchall()

def get_admin_stats(cursor, center_code=None, is_super=False):
    if is_super:
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT f.farmer_code) AS total_farmers,
                COUNT(DISTINCT CASE WHEN k.identity_verified = 'VERIFIED' THEN k.farmer_code END) AS kyc_verified,
                COUNT(CASE WHEN l.loan_state = 'ACTIVE' THEN 1 END) AS active_loans,
                NVL(SUM(CASE WHEN l.loan_state = 'ACTIVE' THEN l.amount ELSE 0 END), 0) AS total_disbursed,
                ROUND(NVL(SUM(CASE WHEN l.loan_state = 'CLOSED' THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(COUNT(CASE WHEN l.loan_state IN ('CLOSED', 'ACTIVE', 'DEFAULTED') THEN 1 END), 0), 0), 2) AS repayment_rate,
                NVL(SUM(CASE WHEN l.loan_state = 'DEFAULTED' THEN l.amount ELSE 0 END), 0) AS defaulted_amount
            FROM FARMER f
            LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
            LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
        """)
    else:
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT f.farmer_code) AS total_farmers,
                COUNT(DISTINCT CASE WHEN k.identity_verified = 'VERIFIED' THEN k.farmer_code END) AS kyc_verified,
                COUNT(CASE WHEN l.loan_state = 'ACTIVE' THEN 1 END) AS active_loans,
                NVL(SUM(CASE WHEN l.loan_state = 'ACTIVE' THEN l.amount ELSE 0 END), 0) AS total_disbursed,
                ROUND(NVL(SUM(CASE WHEN l.loan_state = 'CLOSED' THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(COUNT(CASE WHEN l.loan_state IN ('CLOSED', 'ACTIVE', 'DEFAULTED') THEN 1 END), 0), 0), 2) AS repayment_rate,
                NVL(SUM(CASE WHEN l.loan_state = 'DEFAULTED' THEN l.amount ELSE 0 END), 0) AS defaulted_amount
            FROM FARMER f
            LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
            LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
            WHERE f.center_code = :1
        """, (center_code,))
    return cursor.fetchone()

def get_subordinates(cursor, person_id, center_code=None, is_super=False):
    if is_super:
        cursor.execute("""
            SELECT 
                p.person_id,
                p.first_name || ' ' || p.last_name AS admin_name,
                a.admin_code,
                a.assigned_center_code,
                c.center_name
            FROM ADMIN a
            JOIN PERSON p ON a.person_id = p.person_id
            LEFT JOIN IFARMER_CENTER c ON a.assigned_center_code = c.center_code
            WHERE a.supervisor_id = :1
            ORDER BY p.first_name
        """, (person_id,))
    else:
        cursor.execute("""
            SELECT 
                p.person_id,
                p.first_name || ' ' || p.last_name AS admin_name,
                a.admin_code,
                a.assigned_center_code,
                c.center_name
            FROM ADMIN a
            JOIN PERSON p ON a.person_id = p.person_id
            LEFT JOIN IFARMER_CENTER c ON a.assigned_center_code = c.center_code
            WHERE a.supervisor_id = :1
            AND a.assigned_center_code = :2
            ORDER BY p.first_name
        """, (person_id, center_code))
    return cursor.fetchall()

def get_community_posts(cursor):
    cursor.execute("""
        SELECT 
            post_id,
            content,
            TO_CHAR(post_date, 'DD-Mon-YYYY') AS post_date,
            image
        FROM COMMUNITY_POST
        ORDER BY post_date DESC
    """)
    return cursor.fetchall()

def get_loan_detail(cursor, loan_no):
    cursor.execute("""
        SELECT 
            l.loan_no,
            l.amount,
            l.interest_rate,
            l.tenure_months,
            l.purpose,
            TO_CHAR(l.application_date, 'DD-Mon-YYYY') AS application_date,
            TO_CHAR(l.approval_date, 'DD-Mon-YYYY') AS approval_date,
            TO_CHAR(l.disbursement_date, 'DD-Mon-YYYY') AS disbursement_date,
            l.loan_state,
            f.farmer_code,
            p.first_name || ' ' || p.last_name AS farmer_name,
            p.login_phone,
            p.nid,
            p.village,
            p.upazila,
            p.district,
            k.identity_verified AS kyc_status,
            k.land_legal_status,
            cs.score AS credit_score
        FROM LOAN l
        JOIN FARMER f ON l.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN CREDIT_SCORE cs ON f.farmer_code = cs.farmer_code
        WHERE l.loan_no = :1
    """, (loan_no,))
    return cursor.fetchone()

def get_inventory_alerts(cursor, center_code=None, is_super=False):
    if is_super:
        cursor.execute("""
            SELECT 
                name,
                quantity,
                center_code
            FROM INVENTORY
            WHERE quantity < 10
            ORDER BY quantity ASC
        """)
    else:
        cursor.execute("""
            SELECT 
                name,
                quantity
            FROM INVENTORY
            WHERE center_code = :1
            AND quantity < 10
            ORDER BY quantity ASC
        """, (center_code,))
    return cursor.fetchall()

def get_center_list(cursor, is_super=False, center_code=None):
    if is_super:
        cursor.execute("""
            SELECT 
                center_code,
                center_name
            FROM IFARMER_CENTER
            WHERE center_state = 'ACTIVE'
            ORDER BY center_name
        """)
    else:
        cursor.execute("""
            SELECT 
                center_code,
                center_name
            FROM IFARMER_CENTER
            WHERE center_code = :1
            ORDER BY center_name
        """, (center_code,))
    return cursor.fetchall()