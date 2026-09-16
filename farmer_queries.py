def get_farmer_code(cursor, person_id):
    cursor.execute("SELECT farmer_code FROM FARMER WHERE person_id = :1", (person_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_farmer_dashboard_stats(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM LOAN WHERE farmer_code = :1 AND loan_state = 'ACTIVE') as active_loans,
            (SELECT COUNT(*) FROM REPAYMENT r JOIN LOAN l ON r.loan_no = l.loan_no 
             WHERE l.farmer_code = :1 AND r.payment_state = 'OVERDUE') as pending_repayments,
            (SELECT COUNT(*) FROM ATTENDS WHERE farmer_code = :1) as total_consultations,
            (SELECT NVL(identity_verified, 'PENDING') FROM KYC WHERE farmer_code = :1) as kyc_status
        FROM DUAL
    """, (farmer_code,))
    return cursor.fetchone()

def get_recent_activity(cursor, farmer_code):
    cursor.execute("""
        SELECT activity_type, description, TO_CHAR(activity_date, 'DD-Mon-YYYY HH24:MI') as act_date
        FROM ACTIVITY_RECORD
        WHERE farmer_code = :1
        ORDER BY activity_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_farmer_loans(cursor, farmer_code):
    """Uses the VIEW_FARMER_LOAN_DETAILS view (simplified version)"""
    cursor.execute("""
        SELECT 
            loan_no,
            amount,
            purpose,
            loan_state,
            TO_CHAR(application_date, 'DD-Mon-YYYY') AS applied_date,
            TO_CHAR(due_date, 'DD-Mon-YYYY') AS due_date
        FROM VIEW_FARMER_LOAN_DETAILS
        WHERE farmer_code = :1
        ORDER BY application_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_loan_repayments(cursor, loan_no):
    cursor.execute("""
        SELECT installment_no, amount_paid, TO_CHAR(payment_date, 'DD-Mon-YYYY') as pay_date, 
               payment_method, late_fee, payment_state
        FROM REPAYMENT
        WHERE loan_no = :1
        ORDER BY installment_no
    """, (loan_no,))
    return cursor.fetchall()

def get_all_farmer_repayments(cursor, farmer_code):
    cursor.execute("""
        SELECT r.loan_no, r.installment_no, r.amount_paid, 
               TO_CHAR(r.payment_date, 'DD-Mon-YYYY') as pay_date,
               r.payment_method, r.late_fee, r.payment_state
        FROM REPAYMENT r
        JOIN LOAN l ON r.loan_no = l.loan_no
        WHERE l.farmer_code = :1
        ORDER BY r.payment_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_farmer_assets(cursor, farmer_code):
    cursor.execute("""
        SELECT asset_type, asset_name, quantity, unit, 
               TO_CHAR(acquisition_date, 'DD-Mon-YYYY') as acq_date,
               TO_CHAR(expected_completion_date, 'DD-Mon-YYYY') as exp_date, 
               revenue_generated, total_expense, 
               (revenue_generated - total_expense) as profit, asset_status
        FROM ASSET
        WHERE farmer_code = :1
        ORDER BY acquisition_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_farmer_consultations(cursor, farmer_code):
    cursor.execute("""
        SELECT c.session_id, 
               NVL(p.first_name || ' ' || p.last_name, 'Not Assigned') as advisor_name, 
               c.topic, 
               TO_CHAR(a.scheduled_date, 'DD-Mon-YYYY') as sched_date,
               TO_CHAR(a.actual_date, 'DD-Mon-YYYY') as actual_date, 
               a.resolution_status, 
               a.notes,
               TO_CHAR(c.created_at, 'DD-Mon-YYYY') as created_date
        FROM ATTENDS a
        JOIN CONSULTATION c ON a.session_id = c.session_id
        LEFT JOIN PERSON p ON a.advisor_id = p.person_id
        WHERE a.farmer_code = :1
        ORDER BY a.scheduled_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_community_posts(cursor, farmer_code):
    cursor.execute("""
        SELECT cp.post_id, p.first_name || ' ' || p.last_name as author, cp.content, 
               TO_CHAR(cp.post_date, 'DD-Mon-YYYY') as post_date,
               (SELECT COUNT(*) FROM POST_LIKE pl WHERE pl.post_id = cp.post_id) as like_count,
               (SELECT COUNT(*) FROM POST_LIKE pl 
                WHERE pl.post_id = cp.post_id AND pl.farmer_code = :1) as user_liked
        FROM COMMUNITY_POST cp
        JOIN PERSON p ON cp.admin_id = p.person_id
        ORDER BY cp.post_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def get_farmer_credit_score(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            score,
            TO_CHAR(last_update, 'DD-Mon-YYYY HH24:MI') as last_update
        FROM CREDIT_SCORE
        WHERE farmer_code = :1
    """, (farmer_code,))
    return cursor.fetchone()

def get_credit_breakdown(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            NVL((SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND activity_type = 'REPAYMENT'), 0) as repayments,
            NVL((SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND activity_type = 'REFERRAL'), 0) as referrals,
            NVL((SELECT COUNT(*) FROM REPAYMENT r 
                 JOIN LOAN l ON r.loan_no = l.loan_no 
                 WHERE l.farmer_code = :1 AND r.payment_state = 'OVERDUE'), 0) as overdue,
            NVL((SELECT COUNT(*) FROM LOAN WHERE farmer_code = :1 AND loan_state = 'ACTIVE'), 0) as active_loans
        FROM DUAL
    """, (farmer_code,))
    return cursor.fetchone()

def get_notifications(cursor, farmer_code):
    cursor.execute("""
        SELECT notification_id, message, 
               TO_CHAR(created_at, 'DD-Mon-YYYY HH24:MI') as created_at, 
               is_read, notification_type, link
        FROM NOTIFICATION
        WHERE farmer_code = :1
        ORDER BY created_at DESC
    """, (farmer_code,))
    return cursor.fetchall()

def mark_notifications_read(cursor, farmer_code):
    cursor.execute("UPDATE NOTIFICATION SET is_read = 'YES' WHERE farmer_code = :1 AND is_read = 'NO'", (farmer_code,))




def get_center_code_for_farmer(cursor, farmer_code):
    cursor.execute("SELECT center_code FROM FARMER WHERE farmer_code = :1", (farmer_code,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_inventory_items(cursor, center_code):
    cursor.execute("""
        SELECT 
            i.inventory_id,
            i.name,
            i.quantity,
            i.price_per_unit,
            CASE 
                WHEN s.inventory_id IS NOT NULL THEN 'SEED'
                WHEN f.inventory_id IS NOT NULL THEN 'FERTILIZER'
                WHEN c.inventory_id IS NOT NULL THEN 'CHEMICAL'
                ELSE 'OTHER'
            END AS category,
            i.unit,
            i.min_stock_level
        FROM INVENTORY i
        LEFT JOIN SEED_INVENTORY s ON i.inventory_id = s.inventory_id
        LEFT JOIN FERTILIZER_INVENTORY f ON i.inventory_id = f.inventory_id
        LEFT JOIN CHEMICAL_INVENTORY c ON i.inventory_id = c.inventory_id
        WHERE i.center_code = :1 AND i.quantity > 0
        ORDER BY i.name
    """, (center_code,))
    return cursor.fetchall()

def get_farmer_agent_code(cursor, farmer_code):
    cursor.execute("SELECT agent_code FROM FARMER WHERE farmer_code = :1", (farmer_code,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_farmer_order_history(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            purchase_id,
            purchase_date,
            payment_status,
            payment_method,
            item_name,
            quantity,
            total_cost
        FROM VIEW_FARMER_ORDER_DETAILS
        WHERE farmer_code = :1
        ORDER BY purchase_date DESC
    """, (farmer_code,))
    return cursor.fetchall()

def create_new_purchase(cursor, farmer_code, agent_code, payment_method, generate_id_func):
    purchase_id = 'PUR-' + str(generate_id_func())[:8]
    cursor.execute("""
        INSERT INTO PURCHASE (purchase_id, farmer_code, agent_code, payment_method, payment_status, purchase_date)
        VALUES (:1, :2, :3, :4, 'PENDING', SYSDATE)
    """, (purchase_id, farmer_code, agent_code, payment_method))
    return purchase_id

def add_item_to_purchase(cursor, purchase_id, inventory_id, quantity, unit_price, generate_id_func):
    total_cost = quantity * unit_price
    item_id = 'PI-' + str(generate_id_func())[:8]
    
    cursor.execute("""
        INSERT INTO ORDERED_ITEM (item_id, purchase_id, inventory_id, quantity, unit_price, total_cost)
        VALUES (:1, :2, :3, :4, :5, :6)
    """, (item_id, purchase_id, inventory_id, quantity, unit_price, total_cost))
    
    cursor.execute("""
        UPDATE INVENTORY 
        SET quantity = quantity - :1 
        WHERE inventory_id = :2
    """, (quantity, inventory_id))




def search_farmer_by_name(cursor, name_search):
    cursor.execute("""
        SELECT f.farmer_code, p.first_name, p.last_name, p.login_phone
        FROM FARMER f
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE UPPER(p.first_name || ' ' || p.last_name) LIKE UPPER('%' || :1 || '%')
        AND f.account_status = 'ACTIVE'
    """, (name_search,))
    return cursor.fetchall()

def create_farmer_referral(cursor, referrer_code, referee_code):
    cursor.execute("""
        INSERT INTO FARMER_REFERRAL (referrer_code, referee_code)
        VALUES (:1, :2)
    """, (referrer_code, referee_code))

def get_my_referrals(cursor, farmer_code):
    cursor.execute("""
        SELECT r.referral_id,
               p.first_name || ' ' || p.last_name AS referee_name,
               TO_CHAR(r.referral_date, 'DD-Mon-YYYY') AS referral_date,
               r.status
        FROM FARMER_REFERRAL r
        JOIN FARMER f ON r.referee_code = f.farmer_code
        JOIN PERSON p ON f.person_id = p.person_id
        WHERE r.referrer_code = :1
        ORDER BY r.referral_date DESC
    """, (farmer_code,))
    return cursor.fetchall()