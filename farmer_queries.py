

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
    cursor.execute("""
        SELECT loan_no, amount, interest_rate, tenure_months, purpose, loan_state, 
               TO_CHAR(application_date, 'DD-Mon-YYYY') as app_date, 
               TO_CHAR(approval_date, 'DD-Mon-YYYY') as appr_date
        FROM LOAN
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
               TO_CHAR(c.scheduled_date, 'DD-Mon-YYYY') as sched_date,
               TO_CHAR(c.actual_date, 'DD-Mon-YYYY') as actual_date, 
               c.resolution_status, c.notes,
               TO_CHAR(c.created_at, 'DD-Mon-YYYY') as created_date
        FROM CONSULTATION c
        LEFT JOIN PERSON p ON c.advisor_id = p.person_id
        WHERE c.farmer_code = :1
        ORDER BY c.scheduled_date DESC
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
        SELECT score, TO_CHAR(last_update, 'DD-Mon-YYYY HH24:MI') as last_update
        FROM CREDIT_SCORE
        WHERE farmer_code = :1
    """, (farmer_code,))
    return cursor.fetchone()

def get_credit_breakdown(cursor, farmer_code):
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND activity_type = 'REFERRAL') as referrals,
            (SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND activity_type = 'LIKE') as likes,
            (SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = :1 AND activity_type = 'REPAYMENT') as repayments,
            (SELECT COUNT(*) FROM LOAN WHERE farmer_code = :1 AND loan_state = 'ACTIVE') as active_loans
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