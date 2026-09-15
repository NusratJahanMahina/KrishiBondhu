

def get_agent_dashboard_data(cursor, person_id):
    cursor.execute("""
        SELECT a.agent_code, c.center_name, p.upazila, p.district,
               a.is_active, p.login_phone, a.join_date
        FROM FIELD_AGENT a
        LEFT JOIN IFARMER_CENTER c ON a.center_code = c.center_code
        JOIN PERSON p ON a.person_id = p.person_id
        WHERE a.person_id = :1
    """, (person_id,))
    personal = cursor.fetchone()
    if not personal:
        return None

    agent_code = personal[0]

    cursor.execute("""
        SELECT total_farmers, kyc_verified, pending_loans, pending_deliveries, performance_score
        FROM V_AGENT_DASHBOARD_SUMMARY WHERE agent_code = :1
    """, (agent_code,))
    stats = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) FROM LOAN l JOIN FARMER f ON l.farmer_code = f.farmer_code
        WHERE f.agent_code = :1 AND l.loan_state IN ('ACTIVE', 'CLOSED')
    """, (agent_code,))
    loans_approved = cursor.fetchone()[0]

    return (
        personal[0], personal[1], personal[2], personal[3], personal[4],
        personal[5], personal[6],
        stats[0] if stats else 0,
        stats[1] if stats else 0,
        loans_approved,
        stats[2] if stats else 0,
        stats[3] if stats else 0,
        stats[4] if stats else 0,
    )


def get_agent_code(cursor, person_id):
    cursor.execute("SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_center_code(cursor, person_id):
    cursor.execute("SELECT TRIM(center_code) FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_agent_verification_status(cursor, person_id):
    cursor.execute("SELECT verification_status FROM FIELD_AGENT WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else 'PENDING'


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
        WHERE TRIM(f.center_code) = TRIM(:1)
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
        WHERE TRIM(f.center_code) = TRIM(:1)
        AND (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL)
        ORDER BY f.registration_date ASC
    """, (center_code,))
    return cursor.fetchall()

def get_pending_loans(cursor, center_code, current_agent_code):
    # Step 1: Get basic loan rows (the exact query that works)
    cursor.execute("""
        SELECT 
            l.loan_no,
            f.farmer_code,
            INITCAP(p.first_name) || ' ' || INITCAP(p.last_name),
            TO_CHAR(l.amount, 'FM999,999,999'),
            INITCAP(l.purpose),
            TO_CHAR(l.application_date, 'DD-Mon-YYYY'),
            NVL(f.agent_code, 'N/A'),
            NVL((SELECT p2.first_name || ' ' || p2.last_name
                 FROM FIELD_AGENT fa2
                 JOIN PERSON p2 ON fa2.person_id = p2.person_id
                 WHERE fa2.agent_code = f.agent_code), 'N/A')
        FROM LOAN l
        JOIN FARMER f ON l.farmer_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE f.center_code = :1
          AND l.loan_state = 'PENDING'
        ORDER BY l.application_date ASC
    """, (center_code,))

    rows = cursor.fetchall()

    # Step 2: Compute ownership in Python (no SQL CASE statement)
    result = []
    for r in rows:
        loan_id = r[0]
        code = r[1]
        name = r[2]
        amount = r[3]
        purpose = r[4]
        applied = r[5]
        agent_code = r[6]
        agent_name = r[7]

        if agent_code == current_agent_code:
            ownership = 'MINE'
        elif agent_code == 'N/A':
            ownership = 'UNASSIGNED'
        else:
            ownership = 'OTHER'

        result.append((loan_id, code, name, amount, purpose, applied,
                       ownership, agent_name, agent_code))

    return result


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
        WHERE TRIM(center_code) = TRIM(:1)
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
        WHERE TRIM(f.center_code) = TRIM(:1)
        AND f.agent_code IS NULL
        AND (k.identity_verified IS NULL OR k.identity_verified = 'PENDING')
        AND l.loan_no IS NULL
        ORDER BY days_since_reg DESC
    """, (center_code,))
    return cursor.fetchall()


def get_pending_purchases(cursor, person_id):
    cursor.execute("""
        SELECT 
            v.purchase_id,
            v.farmer_code,
            v.farmer_name,
            v.login_phone,
            v.address,
            TO_CHAR(v.purchase_date, 'DD-Mon-YYYY') AS ordered,
            v.payment_method,
            v.payment_status,
            v.item_count,
            v.total_amount
        FROM V_AGENT_PENDING_DELIVERIES v
        WHERE v.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
        ORDER BY 
            CASE v.payment_status WHEN 'CONFIRMED' THEN 1 WHEN 'SHIPPED' THEN 2 ELSE 3 END,
            v.purchase_date ASC
    """, (person_id,))
    return cursor.fetchall()


def get_order_detail(cursor, purchase_id, agent_person_id):
    cursor.execute("""
        SELECT 
            p.purchase_id,
            f.farmer_code,
            INITCAP(pe.first_name) || ' ' || INITCAP(pe.last_name) AS farmer_name,
            pe.login_phone,
            INITCAP(pe.village) AS village,
            INITCAP(pe.upazila) AS upazila,
            INITCAP(pe.district) AS district,
            TO_CHAR(p.purchase_date, 'DD-Mon-YYYY') AS ordered,
            NVL(p.payment_method, 'CASH') AS payment_method,
            p.payment_status,
            NVL(p.transaction_reference, 'N/A') AS txn_ref
        FROM PURCHASE p
        JOIN FARMER f ON p.farmer_code = f.farmer_code
        JOIN PERSON pe ON f.person_id = pe.person_id
        WHERE p.purchase_id = :1
          AND p.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :2)
    """, (purchase_id, agent_person_id))
    return cursor.fetchone()


def get_order_items(cursor, purchase_id):
    cursor.execute("""
        SELECT 
            oi.item_id,
            i.name AS product_name,
            oi.quantity,
            NVL(i.unit, 'unit') AS unit,
            oi.unit_price,
            oi.total_cost
        FROM ORDERED_ITEM oi
        JOIN INVENTORY i ON oi.inventory_id = i.inventory_id
        WHERE oi.purchase_id = :1
        ORDER BY i.name
    """, (purchase_id,))
    return cursor.fetchall()


def get_community_posts(cursor):
    cursor.execute("""
        SELECT post_id, content, TO_CHAR(post_date, 'DD-Mon-YYYY') AS post_date, image
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


def get_monthly_performance(cursor, person_id):
    cursor.execute("""
        SELECT 
            TO_CHAR(k.verified_date, 'YYYY-MM') AS month,
            COUNT(DISTINCT k.kyc_id) AS kyc_verified,
            COUNT(DISTINCT l.loan_no) AS loans_approved
        FROM FIELD_AGENT a
        LEFT JOIN KYC k ON a.agent_code = k.agent_code
        LEFT JOIN FARMER f ON f.agent_code = a.agent_code
        LEFT JOIN LOAN l ON l.farmer_code = f.farmer_code AND l.loan_state = 'ACTIVE'
        WHERE a.person_id = :1
        GROUP BY TO_CHAR(k.verified_date, 'YYYY-MM')
        ORDER BY month DESC
    """, (person_id,))
    return cursor.fetchall()


def get_followup_farmers(cursor, person_id):
    cursor.execute("""
        SELECT 
            f.farmer_code,
            p.first_name || ' ' || p.last_name AS farmer_name,
            p.login_phone,
            l.loan_no AS loan_id,
            l.amount AS loan_amount,
            NVL(SUM(r.amount_paid), 0) AS total_paid,
            l.amount - NVL(SUM(r.amount_paid), 0) AS remaining_balance,
            ROUND(SYSDATE - MAX(r.payment_date)) AS days_since_last_payment
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        JOIN LOAN l ON f.farmer_code = l.farmer_code
        LEFT JOIN REPAYMENT r ON l.loan_no = r.loan_no
        WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
        AND l.loan_state = 'ACTIVE'
        GROUP BY f.farmer_code, p.first_name, p.last_name, p.login_phone, l.loan_no, l.amount
        HAVING l.amount - NVL(SUM(r.amount_paid), 0) > 0
        ORDER BY days_since_last_payment DESC
    """, (person_id,))
    return cursor.fetchall()


def get_absorption_rate(cursor, person_id):
    cursor.execute("""
        WITH agent_loans AS (
            SELECT 
                f.farmer_code,
                l.loan_no AS loan_id,
                l.amount AS loan_amount,
                l.approval_date
            FROM LOAN l
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
            AND l.loan_state IN ('ACTIVE', 'CLOSED')
        ),
        agent_purchases AS (
            SELECT 
                p.farmer_code,
                p.purchase_id,
                SUM(oi.total_cost) AS total_spent,
                p.purchase_date
            FROM PURCHASE p
            JOIN ORDERED_ITEM oi ON p.purchase_id = oi.purchase_id
            WHERE p.farmer_code IN (SELECT farmer_code FROM agent_loans)
            GROUP BY p.farmer_code, p.purchase_id, p.purchase_date
        )
        SELECT 
            al.farmer_code,
            al.loan_amount,
            NVL(SUM(ap.total_spent), 0) AS total_spent_on_inputs,
            ROUND(NVL(SUM(ap.total_spent), 0) / NULLIF(al.loan_amount, 0) * 100, 2) AS absorption_percentage,
            CASE 
                WHEN NVL(SUM(ap.total_spent), 0) / NULLIF(al.loan_amount, 0) >= 0.8 THEN 'GOOD'
                WHEN NVL(SUM(ap.total_spent), 0) / NULLIF(al.loan_amount, 0) >= 0.5 THEN 'MODERATE'
                ELSE 'POOR'
            END AS absorption_rating
        FROM agent_loans al
        LEFT JOIN agent_purchases ap ON al.farmer_code = ap.farmer_code
        GROUP BY al.farmer_code, al.loan_amount
        ORDER BY absorption_percentage DESC
    """, (person_id,))
    return cursor.fetchall()


def get_risk_prediction(cursor, person_id):
    cursor.execute("""
        SELECT 
            farmer_code,
            farmer_name,
            credit_score,
            repayment_reliability,
            total_asset_value,
            outstanding_loan,
            risk_category
        FROM V_RISK_PREDICTION
        WHERE farmer_code IN (
            SELECT farmer_code FROM FARMER WHERE agent_code = (
                SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1
            )
        )
        ORDER BY risk_category, credit_score
    """, (person_id,))
    return cursor.fetchall()


def get_farmer_kyc_summary(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            GET_KYC_SUMMARY(:1)       AS summary,
            IS_KYC_COMPLETE(:1)       AS complete,
            IS_KYC_LOAN_ELIGIBLE(:1)  AS eligible
        FROM DUAL
    """, (farmer_code,))
    return cursor.fetchone()


def get_agent_tasks(cursor, person_id):
    cursor.execute("""
        SELECT * FROM (
            SELECT 
                'KYC' AS task_type,
                f.farmer_code AS farmer_code,
                INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS farmer_name,
                'Verify KYC documents' AS description,
                TO_CHAR(f.registration_date, 'DD-Mon-YYYY') AS task_date,
                1 AS priority_order
            FROM FARMER f
            JOIN PERSON p ON f.person_id = p.person_id
            LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
            WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
              AND (k.identity_verified = 'PENDING' OR k.identity_verified IS NULL)
            
            UNION ALL
            
            SELECT 
                'DELIVERY' AS task_type,
                f.farmer_code AS farmer_code,
                INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS farmer_name,
                'Deliver: ' || i.name || ' x ' || TO_CHAR(oi.quantity) AS description,
                TO_CHAR(pu.purchase_date, 'DD-Mon-YYYY') AS task_date,
                2 AS priority_order
            FROM PURCHASE pu
            JOIN FARMER f ON pu.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            JOIN ORDERED_ITEM oi ON pu.purchase_id = oi.purchase_id
            JOIN INVENTORY i ON oi.inventory_id = i.inventory_id
            WHERE pu.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
              AND pu.payment_status IN ('CONFIRMED', 'SHIPPED')
            
            UNION ALL
            
            SELECT 
                'REPAYMENT' AS task_type,
                f.farmer_code AS farmer_code,
                INITCAP(p.first_name) || ' ' || INITCAP(p.last_name) AS farmer_name,
                'Overdue: ' || l.loan_no AS description,
                TO_CHAR(r.payment_date, 'DD-Mon-YYYY') AS task_date,
                1 AS priority_order
            FROM REPAYMENT r
            JOIN LOAN l ON r.loan_no = l.loan_no
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            WHERE f.agent_code = (SELECT agent_code FROM FIELD_AGENT WHERE person_id = :1)
              AND r.payment_state = 'OVERDUE'
        )
        ORDER BY priority_order ASC, task_date ASC
    """, (person_id,))
    return cursor.fetchall()