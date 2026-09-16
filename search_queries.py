# =======================================================================
# search_queries.py — Oracle 11g compatible multi-entity search
# land_area derived from ASSET (LAND-type only)
# =======================================================================


def search_farmers(cursor, query_term="", center_code=None, limit=50):
    pattern = f"%{query_term.upper()}%"
    sql = """
        SELECT * FROM (
            SELECT 
                f.farmer_code,
                p.first_name || ' ' || p.last_name AS farmer_name,
                p.login_phone,
                p.username,
                NVL(la.land_area, 0) AS land_area,
                NVL(c.center_name, 'N/A') AS center_name,
                NVL(c.district, 'N/A') AS district,
                NVL(c.upazila, 'N/A') AS upazila,
                NVL(k.identity_verified, 'PENDING') AS kyc_status,
                f.registration_date
            FROM FARMER f
            JOIN PERSON p ON f.person_id = p.person_id
            LEFT JOIN IFARMER_CENTER c ON f.center_code = c.center_code
            LEFT JOIN KYC k ON f.farmer_code = k.farmer_code
            LEFT JOIN (
                SELECT farmer_code, SUM(quantity) AS land_area
                FROM ASSET
                WHERE asset_type = 'LAND'
                GROUP BY farmer_code
            ) la ON f.farmer_code = la.farmer_code
            WHERE (
                UPPER(p.first_name) LIKE :1 OR 
                UPPER(p.last_name) LIKE :2 OR 
                UPPER(p.login_phone) LIKE :3 OR 
                UPPER(p.username) LIKE :4 OR
                UPPER(TO_CHAR(f.farmer_code)) LIKE :5 OR
                UPPER(NVL(c.center_name, 'X')) LIKE :6 OR
                UPPER(NVL(c.district, 'X')) LIKE :7 OR
                UPPER(NVL(c.upazila, 'X')) LIKE :8
            )
            ORDER BY f.farmer_code ASC
        ) WHERE ROWNUM <= """ + str(int(limit))
    cursor.execute(sql, tuple([pattern] * 8))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def search_advisors(cursor, query_term="", limit=50):
    pattern = f"%{query_term.upper()}%"
    sql = """
        SELECT * FROM (
            SELECT 
                a.advisor_id,
                p.first_name || ' ' || p.last_name AS advisor_name,
                p.login_phone,
                a.specialization,
                a.experience_years,
                a.qualification,
                a.is_available,
                NVL(a.rating, 5.0) AS rating,
                NVL(a.total_bookings, 0) AS total_bookings
            FROM ADVISOR a
            JOIN PERSON p ON a.person_id = p.person_id
            WHERE (
                UPPER(p.first_name) LIKE :1 OR 
                UPPER(p.last_name) LIKE :2 OR 
                UPPER(a.specialization) LIKE :3 OR 
                UPPER(p.login_phone) LIKE :4 OR
                UPPER(NVL(a.qualification, 'X')) LIKE :5 OR
                UPPER(TO_CHAR(a.advisor_id)) LIKE :6
            )
            ORDER BY NVL(a.rating, 5.0) DESC, NVL(a.total_bookings, 0) DESC
        ) WHERE ROWNUM <= """ + str(int(limit))
    cursor.execute(sql, tuple([pattern] * 6))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def search_loans(cursor, query_term="", loan_state=None, limit=50):
    pattern = f"%{query_term.upper()}%"
    sql = """
        SELECT * FROM (
            SELECT 
                l.loan_no,
                l.farmer_code,
                p.first_name || ' ' || p.last_name AS farmer_name,
                p.login_phone,
                l.amount,
                l.purpose,
                l.loan_state,
                l.tenure_months,
                l.application_date,
                l.approval_date,
                NVL((SELECT SUM(amount_paid) FROM REPAYMENT WHERE loan_no = l.loan_no), 0) AS total_repaid
            FROM LOAN l
            JOIN FARMER f ON l.farmer_code = f.farmer_code
            JOIN PERSON p ON f.person_id = p.person_id
            WHERE (
                UPPER(TO_CHAR(l.loan_no)) LIKE :1 OR
                UPPER(p.first_name) LIKE :2 OR
                UPPER(p.last_name) LIKE :3 OR
                UPPER(p.login_phone) LIKE :4 OR
                UPPER(NVL(l.purpose, 'X')) LIKE :5 OR
                UPPER(l.loan_state) LIKE :6
            )
            ORDER BY l.loan_no DESC
        ) WHERE ROWNUM <= """ + str(int(limit))
    cursor.execute(sql, tuple([pattern] * 6))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def search_inventory(cursor, query_term="", limit=50):
    pattern = f"%{query_term.upper()}%"
    sql = """
        SELECT * FROM (
            SELECT 
                i.inventory_id,
                i.name AS item_name,
                i.quantity,
                i.unit,
                i.price_per_unit AS price,
                i.center_code AS agent_code,
                NVL(c.center_name, 'N/A') AS agent_name,
                NVL(c.phone, 'N/A') AS agent_phone
            FROM INVENTORY i
            LEFT JOIN IFARMER_CENTER c ON i.center_code = c.center_code
            WHERE (
                UPPER(i.name) LIKE :1 OR
                UPPER(NVL(c.center_name, 'X')) LIKE :2 OR
                UPPER(NVL(i.unit, 'X')) LIKE :3 OR
                UPPER(TO_CHAR(i.inventory_id)) LIKE :4
            )
            ORDER BY i.quantity ASC
        ) WHERE ROWNUM <= """ + str(int(limit))
    cursor.execute(sql, tuple([pattern] * 4))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def search_centers(cursor, query_term="", limit=50):
    pattern = f"%{query_term.upper()}%"
    sql = """
        SELECT * FROM (
            SELECT 
                c.center_code,
                c.center_name,
                c.district,
                c.upazila,
                (SELECT COUNT(*) FROM FARMER WHERE center_code = c.center_code) AS farmer_count,
                (SELECT COUNT(*) FROM FIELD_AGENT WHERE center_code = c.center_code) AS agent_count
            FROM IFARMER_CENTER c
            WHERE (
                UPPER(c.center_name) LIKE :1 OR
                UPPER(NVL(c.district, 'X')) LIKE :2 OR
                UPPER(NVL(c.upazila, 'X')) LIKE :3 OR
                UPPER(TO_CHAR(c.center_code)) LIKE :4
            )
            ORDER BY c.center_code ASC
        ) WHERE ROWNUM <= """ + str(int(limit))
    cursor.execute(sql, tuple([pattern] * 4))
    cols = [c[0].lower() for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]
