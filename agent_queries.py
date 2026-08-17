# ============================================
# AGENT QUERIES - VERSION 2 (Agent Module)
# All functions needed for the Agent UI.
# ============================================

def get_agent_dashboard_data(cursor, person_id):
    cursor.execute("""
        SELECT 
            a.agent_code,
            c.center_name,
            p.upazila,
            p.district,
            a.is_active AS working_status,
            p.login_phone,
            a.join_date,
            (SELECT COUNT(*) FROM FARMER f WHERE f.agent_code = a.agent_code) AS total_farmers,
            (SELECT COUNT(*) FROM KYC k WHERE k.agent_code = a.agent_code AND k.identity_verified = 'VERIFIED') AS kyc_done,
            (SELECT COUNT(*) FROM LOAN l JOIN FARMER f ON l.farmer_code = f.farmer_code WHERE f.agent_code = a.agent_code AND l.loan_state IN ('ACTIVE', 'CLOSED')) AS loans_approved,
            (SELECT COUNT(*) FROM LOAN l JOIN FARMER f ON l.farmer_code = f.farmer_code WHERE f.agent_code = a.agent_code AND l.loan_state = 'PENDING') AS pending_loans,
            (SELECT COUNT(*) FROM PURCHASE p WHERE p.agent_code = a.agent_code AND p.payment_status = 'CONFIRMED') AS pending_deliveries
        FROM FIELD_AGENT a
        LEFT JOIN IFARMER_CENTER c ON a.center_code = c.center_code
        JOIN PERSON p ON a.person_id = p.person_id
        WHERE a.person_id = :1
    """, (person_id,))
    return cursor.fetchone()


def get_agent_code(cursor, person_id):
    cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_center_code(cursor, person_id):
    cursor.execute("SELECT center_code FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_my_farmers(cursor, person_id):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS name,
            p.login_phone AS phone,
            NVL(k.identity_verified, 'PENDING') AS kyc_status,
            CASE 
                WHEN ll.loan_no IS NULL THEN 'No Loan'
                WHEN ll.loan_state = 'CLOSED' THEN 'Paid'
                WHEN ll.loan_state = 'ACTIVE' THEN 'Active Loan'
                WHEN ll.loan_state = 'PENDING' THEN 'Loan Pending'
                ELSE ll.loan_state
            END AS loan_status,
            TO_CHAR(ADD_MONTHS(ll.approval_date, ll.tenure_months), 'DD-Mon-YYYY') AS due_date,
            CASE 
                WHEN EXISTS (SELECT 1 FROM PURCHASE pu WHERE pu.farmer_code = f.farmer_code AND pu.payment_status NOT IN ('DELIVERED', 'CANCELLED')) 
                THEN 'Yes' ELSE 'No' 
            END AS pending_order
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN (
            SELECT 
                farmer_code,
                loan_no,
                loan_state,
                approval_date,
                tenure_months,
                ROW_NUMBER() OVER (PARTITION BY farmer_code ORDER BY application_date DESC) AS rn
            FROM LOAN
        ) ll ON f.farmer_code = ll.farmer_code AND ll.rn = 1
        WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
        ORDER BY f.farmer_code
    """, (person_id,))
    return cursor.fetchall()


def get_pending_kyc_count(cursor, center_code):
    cursor.execute("""
        SELECT COUNT(*) FROM FARMER f
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        WHERE f.center_code = :1
        AND (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL)
    """, (center_code,))
    return cursor.fetchone()[0]


def get_pending_kyc(cursor, center_code):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS name,
            p.login_phone AS phone,
            p.upazila AS village,
            TO_CHAR(f.registration_date, 'DD-Mon-YYYY') AS registered
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        WHERE f.center_code = :1
        AND (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL)
        AND EXISTS (SELECT 1 FROM LOAN l WHERE l.farmer_code = f.farmer_code)
        ORDER BY f.registration_date ASC
    """, (center_code,))
    return cursor.fetchall()


def get_pending_loans(cursor, center_code):
    cursor.execute("""
        SELECT 
            l.loan_no AS loan_id,
            f.farmer_code AS code,
            INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS name,
            TO_CHAR(l.amount, 'FM999,999,999') AS amount,
            INITCAP(l.purpose) AS purpose,
            TO_CHAR(l.application_date, 'DD-Mon-YYYY') AS applied
        FROM LOAN l
        JOIN FARMER f ON l.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE f.center_code = :1
        AND l.loan_state = 'PENDING'
        ORDER BY l.application_date ASC
    """, (center_code,))
    return cursor.fetchall()


def get_agent_inventory(cursor, center_code):
    cursor.execute("""
        SELECT 
            INITCAP(name) AS item,
            quantity AS stock,
            TO_CHAR(unit_price, 'FM999,999') AS price,
            CASE 
                WHEN quantity = 0 THEN 'Out of Stock'
                WHEN quantity < 10 THEN 'Low Stock'
                ELSE 'In Stock'
            END AS status
        FROM INVENTORY
        WHERE center_code = :1
        ORDER BY name
    """, (center_code,))
    return cursor.fetchall()


def get_outreach_farmers(cursor, center_code):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS name,
            p.login_phone AS phone,
            INITCAP(p.upazila) AS village,
            ROUND(SYSDATE - f.registration_date) AS days_since_reg
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
        WHERE f.center_code = :1
        AND (k.identity_verified IS NULL OR k.identity_verified = 'PENDING')
        AND l.loan_no IS NULL
        ORDER BY days_since_reg DESC
    """, (center_code,))
    return cursor.fetchall()


def get_pending_purchases(cursor, center_code):
    cursor.execute("""
        SELECT 
            p.purchase_id AS order_id,
            f.farmer_code AS code,
            INITCAP(pe.first_name) || ' ' || INITCAP(pe.last_name) AS name,
            TO_CHAR(p.purchase_date, 'DD-Mon-YYYY') AS ordered,
            TO_CHAR((SELECT NVL(SUM(total_cost), 0) FROM ORDERED_ITEM oi WHERE oi.purchase_id = p.purchase_id), 'FM999,999,999') AS total_amount,
            NVL(p.payment_method, 'Not Specified') AS payment
        FROM PURCHASE p
        JOIN FARMER f ON p.farmer_code = f.farmer_code
        JOIN PERSON pe ON f.person_id = pe.person_id
        WHERE f.center_code = :1
        AND p.payment_status = 'CONFIRMED'
        ORDER BY p.purchase_date ASC
    """, (center_code,))
    return cursor.fetchall()


def get_community_posts(cursor):
    cursor.execute("""
        SELECT post_id, content, TO_CHAR(post_date, 'DD-Mon-YYYY') AS post_date
        FROM COMMUNITY_POST
        ORDER BY post_date DESC
    """)
    return cursor.fetchall()


def get_agent_ranking(cursor):
    cursor.execute("""
        SELECT 
            a.agent_code,
            p.first_name || ' ' || p.last_name AS agent_name,
            COUNT(k.kyc_id) AS total_kyc,
            SUM(CASE WHEN k.identity_verified = 'VERIFIED' THEN 1 ELSE 0 END) AS verified_kyc,
            ROUND(SUM(CASE WHEN k.identity_verified = 'VERIFIED' THEN 1 ELSE 0 END) * 100.0 / COUNT(k.kyc_id), 2) AS success_rate,
            RANK() OVER (ORDER BY SUM(CASE WHEN k.identity_verified = 'VERIFIED' THEN 1 ELSE 0 END) * 100.0 / COUNT(k.kyc_id) DESC) AS rank
        FROM FIELD_AGENT a
        JOIN PERSON p ON a.person_id = p.person_id
        LEFT JOIN KYC k ON a.agent_code = k.agent_code
        GROUP BY a.agent_code, p.first_name, p.last_name
        HAVING COUNT(k.kyc_id) > 0
        ORDER BY success_rate DESC
    """)
    return cursor.fetchall()


def get_farmer_detail(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            f.farmer_code,
            INITCAP(p.first_name) AS first_name,
            INITCAP(p.last_name) AS last_name,
            p.login_phone,
            p.nid,
            p.gender,
            INITCAP(p.village) AS village,
            INITCAP(p.upazila) AS upazila,
            INITCAP(p.district) AS district,
            TO_CHAR(f.registration_date, 'DD-Mon-YYYY') AS registration_date,
            f.account_status,
            0 AS total_points,
            NULL AS referred_by,
            NULL AS referral_date,
            NULL AS referral_status
        FROM FARMER f, PERSON p
        WHERE f.person_id = p.person_id
        AND f.farmer_code = :1
    """, (farmer_code,))
    return cursor.fetchone()


def get_farmer_loans(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            loan_no AS loan_id,
            TO_CHAR(amount, 'FM999,999,999') AS amount,
            interest_rate,
            tenure_months,
            INITCAP(purpose) AS purpose,
            loan_state AS status,
            TO_CHAR(application_date, 'DD-Mon-YYYY') AS application_date,
            TO_CHAR(approval_date, 'DD-Mon-YYYY') AS approval_date,
            TO_CHAR(disbursement_date, 'DD-Mon-YYYY') AS disbursement_date
        FROM LOAN
        WHERE farmer_code = :1
        ORDER BY application_date DESC
    """, (farmer_code,))
    return cursor.fetchall()


def get_farmer_repayments(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            r.loan_no,
            r.installment_no,
            TO_CHAR(r.amount_paid, 'FM999,999,999') AS amount_paid,
            TO_CHAR(r.payment_date, 'DD-Mon-YYYY') AS payment_date,
            r.payment_method,
            r.payment_state,
            TO_CHAR(r.late_fee, 'FM999,999,999') AS late_fee
        FROM REPAYMENT r
        JOIN LOAN l ON r.loan_no = l.loan_no
        WHERE l.farmer_code = :1
        ORDER BY r.payment_date DESC
    """, (farmer_code,))
    return cursor.fetchall()


def get_farmer_purchases(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            purchase_id,
            TO_CHAR(purchase_date, 'DD-Mon-YYYY') AS purchase_date,
            payment_method,
            payment_status AS status,
            transaction_reference
        FROM PURCHASE
        WHERE farmer_code = :1
        ORDER BY purchase_date DESC
    """, (farmer_code,))
    return cursor.fetchall()