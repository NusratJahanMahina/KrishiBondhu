# ============================================
# ADMIN QUERIES
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
            SELECT name, quantity, center_code
            FROM INVENTORY
            WHERE quantity < 10
            ORDER BY quantity ASC
        """)
    else:
        cursor.execute("""
            SELECT name, quantity
            FROM INVENTORY
            WHERE center_code = :1
            AND quantity < 10
            ORDER BY quantity ASC
        """, (center_code,))
    return cursor.fetchall()


def get_center_list(cursor, is_super=False, center_code=None):
    if is_super or not center_code:
        cursor.execute("""
            SELECT center_code, center_name
            FROM IFARMER_CENTER
            WHERE center_state = 'ACTIVE'
            ORDER BY center_name
        """)
    else:
        cursor.execute("""
            SELECT center_code, center_name
            FROM IFARMER_CENTER
            WHERE center_code = :1
            ORDER BY center_name
        """, (center_code,))
    return cursor.fetchall()


# ============================================
# SEARCH
# ============================================


def search_farmers(cursor, keyword):
    kw = '%' + keyword.upper() + '%'
    cursor.execute("""
        SELECT 
            f.farmer_code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone,
            p.village || ', ' || p.upazila AS location,
            NVL(k.identity_verified, 'PENDING') AS kyc_status,
            NVL(c.center_name, 'N/A') AS center_name
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
        WHERE UPPER(f.farmer_code) LIKE :1
           OR UPPER(p.first_name) LIKE :1
           OR UPPER(p.last_name) LIKE :1
           OR p.login_phone LIKE :1
           OR UPPER(p.village) LIKE :1
           OR UPPER(p.upazila) LIKE :1
        ORDER BY f.farmer_code
    """, (kw,))
    return cursor.fetchall()


def search_loans(cursor, keyword):
    kw = '%' + keyword.upper() + '%'
    cursor.execute("""
        SELECT 
            l.loan_no,
            f.farmer_code,
            p.first_name || ' ' || p.last_name AS farmer_name,
            TO_CHAR(l.amount, 'FM999,999,999') AS amount,
            l.purpose,
            l.loan_state,
            TO_CHAR(l.application_date, 'DD-Mon-YYYY') AS applied
        FROM LOAN l
        JOIN FARMER f ON l.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE UPPER(l.loan_no) LIKE :1
           OR UPPER(l.purpose) LIKE :1
           OR UPPER(l.loan_state) LIKE :1
           OR UPPER(f.farmer_code) LIKE :1
           OR UPPER(p.first_name) LIKE :1
           OR UPPER(p.last_name) LIKE :1
        ORDER BY l.application_date DESC
    """, (kw,))
    return cursor.fetchall()


# ============================================
# CTE REPORTS
# ============================================


def get_center_performance_report(cursor):
    cursor.execute("""
        WITH center_loan_count AS (
            SELECT 
                f.center_code,
                COUNT(l.loan_no) AS total_loans,
                NVL(SUM(CASE WHEN l.loan_state = 'ACTIVE' THEN l.amount ELSE 0 END), 0) AS total_disbursed
            FROM FARMER f
            LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
            GROUP BY f.center_code
        )
        SELECT 
            c.center_code,
            c.center_name,
            NVL(cl.total_loans, 0) AS total_loans,
            NVL(cl.total_disbursed, 0) AS total_disbursed
        FROM IFARMER_CENTER c
        INNER JOIN center_loan_count cl ON c.center_code = cl.center_code
        ORDER BY total_disbursed DESC
    """)
    return cursor.fetchall()


def get_kyc_summary_by_center(cursor):
    cursor.execute("""
        WITH verified_kyc_count AS (
            SELECT 
                f.center_code,
                COUNT(k.kyc_id) AS verified_count
            FROM FARMER f
            INNER JOIN KYC k ON f.farmer_code = k.farmer_code
            WHERE k.identity_verified = 'VERIFIED'
            GROUP BY f.center_code
        )
        SELECT 
            c.center_code,
            c.center_name,
            NVL(vk.verified_count, 0) AS verified_count
        FROM IFARMER_CENTER c
        LEFT JOIN verified_kyc_count vk ON c.center_code = vk.center_code
        ORDER BY verified_count DESC
    """)
    return cursor.fetchall()


def get_agent_activity_report(cursor):
    cursor.execute("""
        WITH agent_farmer_count AS (
            SELECT 
                f.agent_code,
                COUNT(f.farmer_code) AS farmer_count
            FROM FARMER f
            WHERE f.account_status = 'ACTIVE'
            GROUP BY f.agent_code
        )
        SELECT 
            fa.agent_code,
            p.first_name || ' ' || p.last_name AS agent_name,
            NVL(afc.farmer_count, 0) AS farmer_count
        FROM FIELD_AGENT fa
        INNER JOIN PERSON p ON fa.person_id = p.person_id
        LEFT JOIN agent_farmer_count afc ON fa.agent_code = afc.agent_code
        ORDER BY farmer_count DESC
    """)
    return cursor.fetchall()


# ============================================
# VIEW-BASED QUERIES
# ============================================


def get_pending_loans_view(cursor):
    cursor.execute("""
        SELECT 
            loan_no,
            farmer_code,
            farmer_name,
            farmer_phone,
            amount,
            purpose,
            loan_state,
            application_date,
            credit_score,
            center_name,
            kyc_status
        FROM V_ADMIN_LOAN_OVERVIEW
        WHERE loan_state = 'PENDING'
        ORDER BY application_date ASC
    """)
    return cursor.fetchall()


def get_center_summary_view(cursor):
    cursor.execute("""
        SELECT 
            center_code,
            center_name,
            district,
            total_farmers,
            verified_kyc,
            active_loans,
            total_disbursed
        FROM V_ADMIN_CENTER_SUMMARY
        ORDER BY total_disbursed DESC
    """)
    return cursor.fetchall()


def get_center_loan_count_function(cursor, center_code):
    cursor.execute("SELECT GET_CENTER_LOAN_COUNT(:1) FROM DUAL", (center_code,))
    row = cursor.fetchone()
    return row[0] if row else 0


# ============================================
# AUDIT LOG
# ============================================


def get_audit_log(cursor, limit=30):
    cursor.execute("""
        SELECT 
            TO_CHAR(action_date, 'DD-Mon-YYYY HH24:MI') AS action_time,
            action_type,
            target_id,
            old_state,
            new_state
        FROM ADMIN_AUDIT_LOG
        ORDER BY action_date DESC
        FETCH FIRST :1 ROWS ONLY
    """, (limit,))
    return cursor.fetchall()


# ============================================
# LIST FUNCTIONS (for the 6 button pages)
# ============================================


def list_all_farmers(cursor):
    cursor.execute("""
        SELECT 
            f.farmer_code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone,
            p.village || ', ' || p.upazila AS location,
            NVL(k.identity_verified, 'PENDING') AS kyc_status,
            NVL(c.center_name, 'N/A') AS center_name
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
        ORDER BY f.farmer_code
    """)
    return cursor.fetchall()


def list_all_agents(cursor):
    cursor.execute("""
        SELECT 
            fa.agent_code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone,
            NVL(c.center_name, 'N/A') AS center_name,
            fa.is_active,
            (SELECT COUNT(*) FROM FARMER f WHERE f.agent_code = fa.agent_code) AS farmer_count
        FROM FIELD_AGENT fa
        JOIN PERSON p ON fa.person_id = p.person_id
        LEFT JOIN IFARMER_CENTER c ON fa.center_code = c.center_code
        ORDER BY fa.agent_code
    """)
    return cursor.fetchall()


def list_all_centers(cursor):
    cursor.execute("""
        SELECT 
            center_code,
            center_name,
            district,
            upazila,
            phone,
            center_state,
            (SELECT COUNT(*) FROM FARMER f WHERE f.center_code = c.center_code) AS farmer_count
        FROM IFARMER_CENTER c
        ORDER BY center_name
    """)
    return cursor.fetchall()


def list_all_inventory(cursor):
    cursor.execute("""
        SELECT 
            i.inventory_id,
            i.name,
            i.quantity,
            i.unit_price,
            NVL(i.unit, 'unit') AS unit,
            NVL(c.center_name, 'N/A') AS center_name,
            i.location,
            i.manufacturer
        FROM INVENTORY i
        LEFT JOIN IFARMER_CENTER c ON i.center_code = c.center_code
        ORDER BY c.center_name, i.name
    """)
    return cursor.fetchall()


def list_all_banks(cursor):
    cursor.execute("""
        SELECT 
            bank_code,
            bank_name,
            branch_name,
            contact_person,
            phone,
            email,
            max_loan_limit,
            bank_state
        FROM BANK
        ORDER BY bank_name
    """)
    return cursor.fetchall()


def list_all_kyc(cursor):
    cursor.execute("""
        SELECT 
            k.kyc_id,
            k.farmer_code,
            p.first_name || ' ' || p.last_name AS farmer_name,
            NVL(k.identity_verified, 'PENDING') AS status,
            NVL(k.land_legal_status, 'N/A') AS land_status,
            TO_CHAR(k.verified_date, 'DD-Mon-YYYY') AS verified_date,
            k.nominee_name,
            k.nominee_relation
        FROM KYC k
        JOIN FARMER f ON k.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        ORDER BY k.kyc_id
    """)
    return cursor.fetchall()