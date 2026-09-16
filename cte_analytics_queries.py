# =======================================================================
# cte_analytics_queries.py — Oracle 11g compatible CTEs
# land_area is derived from ASSET (LAND-type only)
# =======================================================================


def get_regional_center_ranking_cte(cursor):
    cursor.execute("""
        WITH CenterStats AS (
            SELECT 
                c.center_code, c.center_name,
                NVL(c.upazila, 'সদর') AS upazila,
                NVL(c.district, 'ঢাকা') AS district,
                COUNT(DISTINCT f.farmer_code) AS total_farmers,
                COUNT(DISTINCT a.agent_code) AS total_agents,
                COUNT(DISTINCT l.loan_no) AS total_loans_count,
                NVL(SUM(CASE WHEN l.loan_state = 'ACTIVE' THEN l.amount ELSE 0 END), 0) AS active_loan_volume,
                NVL(SUM(l.amount), 0) AS total_loan_disbursed
            FROM IFARMER_CENTER c
            LEFT JOIN FARMER f ON c.center_code = f.center_code
            LEFT JOIN FIELD_AGENT a ON c.center_code = a.center_code
            LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
            GROUP BY c.center_code, c.center_name, c.upazila, c.district
        ),
        CenterRankings AS (
            SELECT 
                center_code, center_name, upazila, district,
                total_farmers, total_agents, total_loans_count,
                active_loan_volume, total_loan_disbursed,
                DENSE_RANK() OVER (ORDER BY total_loan_disbursed DESC) AS performance_rank,
                CASE 
                    WHEN total_loan_disbursed >= 100000 THEN 'TIER-A (High Impact)'
                    WHEN total_loan_disbursed >= 50000 THEN 'TIER-B (Growing)'
                    ELSE 'TIER-C (Emerging)'
                END AS operational_tier
            FROM CenterStats
        )
        SELECT * FROM CenterRankings ORDER BY performance_rank ASC
    """)
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_farmer_credit_risk_tiering_cte(cursor, limit=50):
    cursor.execute("""
        SELECT * FROM (
            WITH FarmerFinancials AS (
                SELECT 
                    f.farmer_code,
                    p.first_name || ' ' || p.last_name AS farmer_name,
                    p.login_phone,
                    NVL(la.land_area, 0) AS land_area,
                    NVL(c.center_name, 'Unknown') AS center_name,
                    COUNT(DISTINCT l.loan_no) AS total_loans_applied,
                    NVL(SUM(CASE WHEN l.loan_state = 'ACTIVE' THEN l.amount ELSE 0 END), 0) AS active_loan_exposure,
                    NVL(SUM(CASE WHEN l.loan_state = 'CLOSED' THEN l.amount ELSE 0 END), 0) AS closed_loan_amount,
                    NVL(SUM(r.amount_paid), 0) AS total_repayments_made,
                    NVL(k.identity_verified, 'PENDING') AS kyc_status
                FROM FARMER f
                JOIN PERSON p ON f.person_id = p.person_id
                LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
                LEFT JOIN LOAN l ON f.farmer_code = l.farmer_code
                LEFT JOIN REPAYMENT r ON l.loan_no = r.loan_no
                LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
                LEFT JOIN (
                    SELECT farmer_code, SUM(quantity) AS land_area
                    FROM ASSET
                    WHERE asset_type = 'LAND'
                    GROUP BY farmer_code
                ) la ON f.farmer_code = la.farmer_code
                GROUP BY f.farmer_code, p.first_name, p.last_name, p.login_phone,
                         NVL(la.land_area, 0), c.center_name, k.identity_verified
            ),
            RiskClassification AS (
                SELECT 
                    farmer_code, farmer_name, login_phone, land_area, center_name,
                    total_loans_applied, active_loan_exposure, closed_loan_amount,
                    total_repayments_made, kyc_status,
                    CASE 
                        WHEN kyc_status != 'VERIFIED' THEN 'KYC_UNVERIFIED_RISK'
                        WHEN active_loan_exposure > 70000 THEN 'HIGH_EXPOSURE'
                        WHEN active_loan_exposure > 0 THEN 'MODERATE_ACTIVE'
                        WHEN closed_loan_amount > 0 THEN 'PRIME_RELIABLE'
                        ELSE 'NEW_APPLICANT'
                    END AS risk_category,
                    CASE 
                        WHEN total_loans_applied = 0 THEN 70
                        WHEN active_loan_exposure > 0 AND total_repayments_made > 0 THEN 85
                        WHEN active_loan_exposure > 0 AND total_repayments_made = 0 THEN 60
                        WHEN closed_loan_amount > 0 THEN 95
                        ELSE 75
                    END AS estimated_credit_score
                FROM FarmerFinancials
            )
            SELECT * FROM RiskClassification
            ORDER BY active_loan_exposure DESC, estimated_credit_score DESC
        ) WHERE ROWNUM <= """ + str(int(limit)))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_advisor_revenue_matrix_cte(cursor):
    cursor.execute("""
        WITH BookingAgg AS (
            SELECT b.advisor_id,
                COUNT(b.booking_id) AS total_sessions,
                COUNT(CASE WHEN b.booking_status = 'COMPLETED' THEN 1 END) AS completed_sessions,
                COUNT(CASE WHEN b.booking_status = 'CONFIRMED' THEN 1 END) AS confirmed_sessions,
                NVL(SUM(CASE WHEN b.payment_status = 'PAID' THEN b.total_amount ELSE 0 END), 0) AS total_revenue
            FROM ADVISOR_BOOKING b GROUP BY b.advisor_id
        ),
        RatingAgg AS (
            SELECT advisor_id,
                COUNT(rating_id) AS total_reviews,
                ROUND(AVG(rating), 2) AS avg_review_score
            FROM ADVISOR_RATING GROUP BY advisor_id
        ),
        AdvisorPerformance AS (
            SELECT a.advisor_id,
                p.first_name || ' ' || p.last_name AS advisor_name,
                p.login_phone, a.specialization, a.experience_years, a.is_available,
                NVL(r.avg_review_score, NVL(a.rating, 5.0)) AS rating,
                NVL(r.total_reviews, 0) AS total_reviews,
                NVL(b.total_sessions, 0) AS total_sessions,
                NVL(b.completed_sessions, 0) AS completed_sessions,
                NVL(b.confirmed_sessions, 0) AS confirmed_sessions,
                NVL(b.total_revenue, 0) AS total_revenue
            FROM ADVISOR a
            JOIN PERSON p ON a.person_id = p.person_id
            LEFT JOIN BookingAgg b ON a.advisor_id = b.advisor_id
            LEFT JOIN RatingAgg r ON a.advisor_id = r.advisor_id
        )
        SELECT * FROM AdvisorPerformance ORDER BY total_revenue DESC, rating DESC
    """)
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_recursive_loan_schedule_cte(cursor, loan_no=None):
    if not loan_no:
        cursor.execute("SELECT loan_no FROM (SELECT loan_no FROM LOAN ORDER BY loan_no ASC) WHERE ROWNUM = 1")
        row = cursor.fetchone()
        if not row:
            return []
        loan_no = row[0]

    cursor.execute("""
        SELECT 
            LEVEL AS installment_no,
            sub.loan_no, sub.farmer_name, sub.loan_amount, sub.tenure, sub.installment_amount,
            CASE WHEN sub.loan_amount - (LEVEL * sub.installment_amount) < 0 THEN 0
                 ELSE ROUND(sub.loan_amount - (LEVEL * sub.installment_amount), 2)
            END AS remaining_balance,
            TO_CHAR(ADD_MONTHS(sub.start_date, LEVEL), 'YYYY-MM-DD') AS due_date
        FROM (
            SELECT l.loan_no, l.amount AS loan_amount,
                   NVL(l.tenure_months, 6) AS tenure,
                   ROUND(l.amount / NVL(l.tenure_months, 6), 2) AS installment_amount,
                   NVL(l.approval_date, l.application_date) AS start_date,
                   p.first_name || ' ' || p.last_name AS farmer_name
            FROM LOAN l
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            WHERE l.loan_no = :1
        ) sub
        CONNECT BY LEVEL <= sub.tenure
    """, (loan_no,))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]
