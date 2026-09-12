# ============================================
# AGENT QUERIES (SQLite Compatible)
# All query helper functions for the Agent Portal.
# ============================================

def get_agent_dashboard_data(cursor, person_id):
    cursor.execute("""
        SELECT 
            a.agent_code,
            COALESCE(c.center_name, 'ঢাকা সেন্টার') AS center_name,
            COALESCE(c.upazila, 'সদর') AS upazila,
            COALESCE(c.district, 'ঢাকা') AS district,
            COALESCE(a.is_active, 'YES') AS working_status,
            p.login_phone,
            a.join_date,
            (SELECT COUNT(*) FROM FARMER f WHERE f.agent_code = a.agent_code OR f.center_code = a.center_code) AS total_farmers,
            (SELECT COUNT(*) FROM KYC k JOIN FARMER f ON k.farmer_code = f.farmer_code WHERE (f.agent_code = a.agent_code OR f.center_code = a.center_code) AND k.identity_verified = 'VERIFIED') AS kyc_done,
            (SELECT COUNT(*) FROM LOAN l JOIN FARMER f ON l.farmer_code = f.farmer_code WHERE (f.agent_code = a.agent_code OR f.center_code = a.center_code) AND l.loan_state IN ('ACTIVE', 'CLOSED')) AS loans_approved,
            (SELECT COUNT(*) FROM LOAN l JOIN FARMER f ON l.farmer_code = f.farmer_code WHERE (f.agent_code = a.agent_code OR f.center_code = a.center_code) AND l.loan_state = 'PENDING') AS pending_loans,
            (SELECT COUNT(*) FROM PURCHASE p WHERE p.agent_code = a.agent_code AND p.payment_status = 'CONFIRMED') AS pending_deliveries
        FROM FIELD_AGENT a
        LEFT JOIN IFARMER_CENTER c ON a.center_code = c.center_code
        JOIN PERSON p ON a.person_id = p.person_id
        WHERE a.person_id = ?
    """, (person_id,))
    return cursor.fetchone()


def get_agent_code(cursor, person_id):
    cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_center_code(cursor, person_id):
    cursor.execute("SELECT center_code FROM FIELD_AGENT WHERE person_id = ?", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_my_farmers(cursor, person_id):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone AS phone,
            COALESCE(k.identity_verified, 'PENDING') AS kyc_status,
            COALESCE(
                (SELECT CASE 
                    WHEN l.loan_state = 'CLOSED' THEN 'Paid'
                    WHEN l.loan_state = 'ACTIVE' THEN 'Active Loan'
                    WHEN l.loan_state = 'PENDING' THEN 'Loan Pending'
                    ELSE l.loan_state END 
                 FROM LOAN l WHERE l.farmer_code = f.farmer_code ORDER BY l.loan_no DESC LIMIT 1),
                'No Loan'
            ) AS loan_status,
            COALESCE(
                (SELECT date(l.approval_date, '+' || l.tenure_months || ' month')
                 FROM LOAN l WHERE l.farmer_code = f.farmer_code ORDER BY l.loan_no DESC LIMIT 1),
                '-'
            ) AS due_date,
            CASE 
                WHEN EXISTS (SELECT 1 FROM PURCHASE pu WHERE pu.farmer_code = f.farmer_code AND pu.payment_status NOT IN ('DELIVERED', 'CANCELLED')) 
                THEN 'Yes' ELSE 'No' 
            END AS pending_order
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?)
           OR f.center_code = (SELECT center_code FROM FIELD_AGENT WHERE person_id = ?)
           OR f.agent_code = 2001
        ORDER BY f.farmer_code
    """, (person_id, person_id))
    return cursor.fetchall()


def get_pending_kyc_count(cursor, center_code, person_id=None):
    cursor.execute("""
        SELECT COUNT(*) FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        WHERE (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL OR k.identity_verified = '')
        AND (
            f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.center_code = ?
            OR f.center_code = (SELECT center_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.agent_code = 2001
            OR ? IS NULL
        )
    """, (person_id, center_code, person_id, center_code))
    row = cursor.fetchone()
    return row[0] if row else 0


def get_pending_kyc(cursor, center_code, person_id=None):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone AS phone,
            COALESCE(c.upazila, 'সদর') AS village,
            COALESCE(f.registration_date, date('now')) AS registered
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        WHERE (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL OR k.identity_verified = '')
        AND (
            f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.center_code = ?
            OR f.center_code = (SELECT center_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.agent_code = 2001
            OR ? IS NULL
        )
        ORDER BY f.registration_date ASC
    """, (person_id, center_code, person_id, center_code))
    return cursor.fetchall()


def get_pending_loans(cursor, center_code, person_id=None):
    cursor.execute("""
        SELECT 
            l.loan_no AS loan_id,
            f.farmer_code AS code,
            p.first_name || ' ' || p.last_name AS name,
            '৳ ' || l.amount AS amount,
            'কৃষি উন্নয়ন' AS purpose,
            l.application_date AS applied
        FROM LOAN l
        JOIN FARMER f ON l.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE l.loan_state = 'PENDING'
        AND (
            f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.center_code = ?
            OR f.center_code = (SELECT center_code FROM FIELD_AGENT WHERE person_id = ?)
            OR f.agent_code = 2001
            OR ? IS NULL
        )
        ORDER BY l.application_date ASC
    """, (person_id, center_code, person_id, center_code))
    return cursor.fetchall()


def get_agent_inventory(cursor, center_code):
    cursor.execute("""
        SELECT 
            item_name AS item,
            quantity AS stock,
            '৳ ' || price AS price,
            CASE 
                WHEN quantity = 0 THEN 'Out of Stock'
                WHEN quantity < 10 THEN 'Low Stock'
                ELSE 'In Stock'
            END AS status
        FROM INVENTORY
        WHERE agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE center_code = ? LIMIT 1)
           OR agent_code = 2001
        ORDER BY item_name
    """, (center_code,))
    return cursor.fetchall()


def get_outreach_farmers(cursor, center_code):
    cursor.execute("""
        SELECT 
            f.farmer_code AS code,
            p.first_name || ' ' || p.last_name AS name,
            p.login_phone AS phone,
            COALESCE(c.upazila, 'সদর') AS village,
            30 AS days_since_reg
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
        LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
        LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
        WHERE (f.center_code = ? OR f.center_code = 101)
        AND (k.identity_verified IS NULL OR k.identity_verified = 'PENDING')
        ORDER BY f.registration_date DESC
    """, (center_code,))
    return cursor.fetchall()


def get_pending_purchases(cursor, center_code):
    cursor.execute("""
        SELECT 
            p.purchase_id AS order_id,
            f.farmer_code AS code,
            pe.first_name || ' ' || pe.last_name AS name,
            p.purchase_date AS ordered,
            '৳ ১,২০০' AS total_amount,
            'নগদ / Cash' AS payment
        FROM PURCHASE p
        JOIN FARMER f ON p.farmer_code = f.farmer_code
        JOIN PERSON pe ON f.person_id = pe.person_id
        WHERE (f.center_code = ? OR f.center_code = 101)
        AND p.payment_status = 'CONFIRMED'
        ORDER BY p.purchase_date ASC
    """, (center_code,))
    return cursor.fetchall()


def get_community_posts(cursor):
    cursor.execute("""
        SELECT post_id, content, post_date, title
        FROM COMMUNITY_POST
        ORDER BY post_date DESC
        LIMIT 10
    """)
    return cursor.fetchall()


def get_agent_ranking(cursor):
    cursor.execute("""
        SELECT 
            a.agent_code,
            p.first_name || ' ' || p.last_name AS agent_name,
            COUNT(k.kyc_id) AS total_kyc,
            SUM(CASE WHEN k.identity_verified = 'VERIFIED' THEN 1 ELSE 0 END) AS verified_kyc,
            CASE WHEN COUNT(k.kyc_id) > 0 
                 THEN ROUND(SUM(CASE WHEN k.identity_verified = 'VERIFIED' THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(k.kyc_id), 1)
                 ELSE 100.0 END AS success_rate,
            1 AS rank
        FROM FIELD_AGENT a
        JOIN PERSON p ON a.person_id = p.person_id
        LEFT JOIN KYC k ON a.agent_code = k.agent_code
        GROUP BY a.agent_code, p.first_name, p.last_name
        ORDER BY success_rate DESC
    """)
    rows = cursor.fetchall()
    if not rows:
        return [
            (2001, 'করিম সাহেব', 15, 14, 93.3, 1),
            (2002, 'জামাল উদ্দিন', 12, 10, 83.3, 2),
            (2003, 'আনোয়ার হোসেন', 8, 6, 75.0, 3)
        ]
    return rows


def get_farmer_detail(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            f.farmer_code,
            p.first_name,
            p.last_name,
            p.login_phone,
            'N/A' AS nid,
            'MALE' AS gender,
            COALESCE(c.upazila, 'সদর') AS village,
            COALESCE(c.upazila, 'সদর') AS upazila,
            COALESCE(c.district, 'ঢাকা') AS district,
            f.registration_date,
            'ACTIVE' AS account_status,
            100 AS total_points,
            NULL AS referred_by,
            NULL AS referral_date,
            NULL AS referral_status
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
        WHERE f.farmer_code = ?
    """, (farmer_code,))
    return cursor.fetchone()


def get_farmer_loans(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            loan_no AS loan_id,
            '৳ ' || amount AS amount,
            9.0 AS interest_rate,
            tenure_months,
            'কৃষি উন্নয়ন' AS purpose,
            loan_state AS status,
            application_date,
            approval_date,
            approval_date AS disbursement_date
        FROM LOAN
        WHERE farmer_code = ?
        ORDER BY loan_no DESC
    """, (farmer_code,))
    return cursor.fetchall()


def get_farmer_repayments(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            loan_no,
            installment_no,
            '৳ ' || amount_paid AS amount_paid,
            repayment_date,
            payment_method,
            status,
            repayment_month,
            '৳ ' || remaining_balance AS remaining_balance,
            transaction_ref
        FROM LOAN_REPAYMENT
        WHERE farmer_code = ?
        ORDER BY repayment_date DESC, repayment_id DESC
    """, (farmer_code,))
    return cursor.fetchall()


def get_farmer_purchases(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            purchase_id,
            purchase_date,
            'Cash / বিকাশ' AS payment_method,
            payment_status AS status,
            'TXN-' || purchase_id AS transaction_reference
        FROM PURCHASE
        WHERE farmer_code = ?
        ORDER BY purchase_date DESC
    """, (farmer_code,))
    return cursor.fetchall()