# ============================================================
# advisor_queries.py — Oracle-native advisor module queries.
# ============================================================


def get_advisor_by_person(cursor, person_id):
    cursor.execute("""
        SELECT A.ADVISOR_ID, A.PERSON_ID, P.FIRST_NAME, P.LAST_NAME,
               P.LOGIN_PHONE, A.SPECIALIZATION, A.BIO, A.EXPERIENCE_YEARS,
               A.QUALIFICATION, NVL(A.RATING, 5.0), NVL(A.TOTAL_BOOKINGS, 0),
               NVL(A.IS_AVAILABLE, 'YES')
        FROM ADVISOR A
        JOIN PERSON P ON A.PERSON_ID = P.PERSON_ID
        WHERE A.PERSON_ID = :1
    """, (person_id,))
    return cursor.fetchone()


def get_advisor_by_id(cursor, advisor_id):
    cursor.execute("""
        SELECT A.ADVISOR_ID, P.FIRST_NAME, P.LAST_NAME, P.LOGIN_PHONE,
               A.SPECIALIZATION, A.BIO, A.EXPERIENCE_YEARS, A.QUALIFICATION,
               NVL(A.RATING, 5.0), NVL(A.TOTAL_BOOKINGS, 0),
               NVL(A.IS_AVAILABLE, 'YES')
        FROM ADVISOR A
        JOIN PERSON P ON A.PERSON_ID = P.PERSON_ID
        WHERE A.ADVISOR_ID = :1
    """, (advisor_id,))
    return cursor.fetchone()


def get_advisor_rates(cursor, advisor_id):
    cursor.execute("""
        SELECT RATE_TYPE, AMOUNT, NVL(CURRENCY, 'BDT')
        FROM ADVISOR_RATE
        WHERE ADVISOR_ID = :1
        ORDER BY RATE_TYPE
    """, (advisor_id,))
    return cursor.fetchall()


def get_advisor_availability(cursor, advisor_id):
    cursor.execute("""
        SELECT DAY_OF_WEEK, START_TIME, END_TIME, IS_AVAILABLE
        FROM ADVISOR_AVAILABILITY
        WHERE ADVISOR_ID = :1
        ORDER BY CASE DAY_OF_WEEK
                    WHEN 'SATURDAY'  THEN 1
                    WHEN 'SUNDAY'    THEN 2
                    WHEN 'MONDAY'    THEN 3
                    WHEN 'TUESDAY'   THEN 4
                    WHEN 'WEDNESDAY' THEN 5
                    WHEN 'THURSDAY'  THEN 6
                    WHEN 'FRIDAY'    THEN 7
                 END
    """, (advisor_id,))
    return cursor.fetchall()


def list_all_advisors(cursor, search=None, specialization=None, only_available=False):
    sql = """
        SELECT A.ADVISOR_ID, P.FIRST_NAME, P.LAST_NAME, P.LOGIN_PHONE,
               A.SPECIALIZATION, A.BIO, A.EXPERIENCE_YEARS, A.QUALIFICATION,
               NVL(A.RATING, 5.0), NVL(A.TOTAL_BOOKINGS, 0),
               NVL(A.IS_AVAILABLE, 'YES')
        FROM ADVISOR A
        JOIN PERSON P ON A.PERSON_ID = P.PERSON_ID
        WHERE 1=1
    """
    params = []
    if search:
        sql += """ AND (
            UPPER(P.FIRST_NAME) LIKE :1 OR
            UPPER(P.LAST_NAME)  LIKE :1 OR
            UPPER(A.SPECIALIZATION) LIKE :1
        )"""
        params.append(f"%{search.upper()}%")
    if specialization:
        sql += f" AND UPPER(A.SPECIALIZATION) LIKE :{len(params) + 1}"
        params.append(f"%{specialization.upper()}%")
    if only_available:
        sql += " AND NVL(A.IS_AVAILABLE,'YES') = 'YES'"
    sql += """
        ORDER BY CASE WHEN NVL(A.IS_AVAILABLE,'YES')='YES' THEN 0 ELSE 1 END,
                 NVL(A.RATING, 5.0) DESC,
                 NVL(A.TOTAL_BOOKINGS, 0) DESC
    """
    cursor.execute(sql, tuple(params))
    return cursor.fetchall()


def list_all_specializations(cursor):
    cursor.execute("SELECT DISTINCT SPECIALIZATION FROM ADVISOR ORDER BY SPECIALIZATION")
    return [r[0] for r in cursor.fetchall() if r[0]]


def upsert_advisor_rate(cursor, advisor_id, rate_type, amount):
    cursor.execute("""
        SELECT RATE_ID FROM ADVISOR_RATE
        WHERE ADVISOR_ID = :1 AND RATE_TYPE = :2
    """, (advisor_id, rate_type))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE ADVISOR_RATE SET AMOUNT = :1, UPDATED_AT = SYSDATE
            WHERE RATE_ID = :2
        """, (amount, row[0]))
    else:
        cursor.execute("""
            INSERT INTO ADVISOR_RATE (RATE_ID, ADVISOR_ID, RATE_TYPE, AMOUNT, CURRENCY)
            VALUES (ADVISOR_RATE_SEQ.NEXTVAL, :1, :2, :3, 'BDT')
        """, (advisor_id, rate_type, amount))


def replace_availability(cursor, advisor_id, days, start_time, end_time):
    cursor.execute("DELETE FROM ADVISOR_AVAILABILITY WHERE ADVISOR_ID = :1", (advisor_id,))
    for day in days:
        cursor.execute("""
            INSERT INTO ADVISOR_AVAILABILITY
                (AVAILABILITY_ID, ADVISOR_ID, DAY_OF_WEEK, START_TIME, END_TIME, IS_AVAILABLE)
            VALUES (ADVISOR_AVAIL_SEQ.NEXTVAL, :1, :2, :3, :4, 'YES')
        """, (advisor_id, day, start_time, end_time))


# Dashboard version — combined name, phone, duration_hours
def get_bookings_for_advisor_dashboard(cursor, advisor_id):
    cursor.execute("""
        SELECT B.BOOKING_ID,
               TO_CHAR(B.SCHEDULED_DATE, 'YYYY-MM-DD'),
               B.START_TIME, B.END_TIME, B.DURATION_HOURS, B.RATE_TYPE,
               B.TOTAL_AMOUNT, B.PAYMENT_STATUS, B.BOOKING_STATUS,
               B.CONSULTATION_TOPIC, B.NOTES,
               P.FIRST_NAME || ' ' || P.LAST_NAME,
               P.LOGIN_PHONE,
               B.FARMER_ID,
               TO_CHAR(B.BOOKING_DATE, 'YYYY-MM-DD HH24:MI'),
               NVL(R.RATING, 0), R.REVIEW
        FROM ADVISOR_BOOKING B
        JOIN FARMER F ON B.FARMER_ID = F.FARMER_CODE
        JOIN PERSON P ON F.PERSON_ID = P.PERSON_ID
        LEFT JOIN ADVISOR_RATING R ON B.BOOKING_ID = R.BOOKING_ID
        WHERE B.ADVISOR_ID = :1
        ORDER BY B.BOOKING_DATE DESC
    """, (advisor_id,))
    return cursor.fetchall()


# /my-bookings version (advisor viewing their bookings)
def get_bookings_for_advisor(cursor, advisor_id):
    cursor.execute("""
        SELECT B.BOOKING_ID,
               TO_CHAR(B.SCHEDULED_DATE, 'YYYY-MM-DD'),
               B.START_TIME, B.END_TIME, B.RATE_TYPE, B.TOTAL_AMOUNT,
               B.PAYMENT_STATUS, B.BOOKING_STATUS, B.CONSULTATION_TOPIC,
               P.FIRST_NAME,
               P.LAST_NAME,
               A.SPECIALIZATION,
               NVL(A.RATING, 5.0),
               B.FARMER_ID,
               B.NOTES,
               NVL(R.RATING, 0),
               R.REVIEW,
               P.LOGIN_PHONE
        FROM ADVISOR_BOOKING B
        JOIN FARMER F ON B.FARMER_ID = F.FARMER_CODE
        JOIN PERSON P ON F.PERSON_ID = P.PERSON_ID
        JOIN ADVISOR A ON B.ADVISOR_ID = A.ADVISOR_ID
        LEFT JOIN ADVISOR_RATING R ON B.BOOKING_ID = R.BOOKING_ID
        WHERE B.ADVISOR_ID = :1
        ORDER BY B.BOOKING_DATE DESC
    """, (advisor_id,))
    return cursor.fetchall()


# /my-bookings version (farmer viewing their bookings)
def get_bookings_for_farmer(cursor, farmer_code):
    cursor.execute("""
        SELECT B.BOOKING_ID,
               TO_CHAR(B.SCHEDULED_DATE, 'YYYY-MM-DD'),
               B.START_TIME, B.END_TIME, B.RATE_TYPE, B.TOTAL_AMOUNT,
               B.PAYMENT_STATUS, B.BOOKING_STATUS, B.CONSULTATION_TOPIC,
               P.FIRST_NAME,
               P.LAST_NAME,
               A.SPECIALIZATION,
               NVL(A.RATING, 5.0),
               B.ADVISOR_ID,
               B.NOTES,
               NVL(R.RATING, 0),
               R.REVIEW,
               P.LOGIN_PHONE
        FROM ADVISOR_BOOKING B
        JOIN ADVISOR A ON B.ADVISOR_ID = A.ADVISOR_ID
        JOIN PERSON P ON A.PERSON_ID = P.PERSON_ID
        LEFT JOIN ADVISOR_RATING R ON B.BOOKING_ID = R.BOOKING_ID
        WHERE B.FARMER_ID = :1
        ORDER BY B.BOOKING_DATE DESC
    """, (farmer_code,))
    return cursor.fetchall()


def get_advisor_reviews(cursor, advisor_id, limit=10):
    cursor.execute("""
        SELECT * FROM (
            SELECT R.RATING, R.REVIEW,
                   TO_CHAR(R.CREATED_AT, 'YYYY-MM-DD'),
                   P.FIRST_NAME || ' ' || P.LAST_NAME,
                   B.CONSULTATION_TOPIC
            FROM ADVISOR_RATING R
            JOIN FARMER F ON R.FARMER_ID = F.FARMER_CODE
            JOIN PERSON P ON F.PERSON_ID = P.PERSON_ID
            JOIN ADVISOR_BOOKING B ON R.BOOKING_ID = B.BOOKING_ID
            WHERE R.ADVISOR_ID = :1
            ORDER BY R.CREATED_AT DESC
        ) WHERE ROWNUM <= :2
    """, (advisor_id, int(limit)))
    return cursor.fetchall()
def get_user_notifications(cursor, person_id, limit=10):
    cursor.execute("""
        SELECT * FROM (
            SELECT NOTIF_ID, NVL(TITLE,'নোটিফিকেশন'), MESSAGE,
                   NVL(LINK, '/'), NVL(IS_READ, 'NO'),
                   TO_CHAR(CREATED_AT, 'YYYY-MM-DD HH24:MI'),
                   NVL(NOTIFICATION_TYPE, 'GENERAL')
            FROM NOTIFICATION
            WHERE PERSON_ID = :1
            ORDER BY CREATED_AT DESC
        ) WHERE ROWNUM <= :2
    """, (person_id, int(limit)))
    return cursor.fetchall()

def count_unread_notifications(cursor, person_id):
    cursor.execute("""
        SELECT COUNT(*) FROM NOTIFICATION
        WHERE PERSON_ID = :1 AND NVL(IS_READ, 'NO') = 'NO'
    """, (person_id,))
    row = cursor.fetchone()
    return row[0] if row else 0


def create_booking(cursor, advisor_id, farmer_code, agent_code,
                   scheduled_date, start_time, end_time, duration_hours,
                   rate_type, total_amount, topic):
    cursor.execute("""
        INSERT INTO ADVISOR_BOOKING
            (BOOKING_ID, ADVISOR_ID, FARMER_ID, AGENT_ID, SCHEDULED_DATE,
             START_TIME, END_TIME, DURATION_HOURS, RATE_TYPE, TOTAL_AMOUNT,
             PAYMENT_STATUS, BOOKING_STATUS, CONSULTATION_TOPIC)
        VALUES
            (ADVISOR_BOOKING_SEQ.NEXTVAL, :1, :2, :3,
             TO_DATE(:4, 'YYYY-MM-DD'), :5, :6, :7, :8, :9,
             'PENDING', 'PENDING', :10)
    """, (advisor_id, farmer_code, agent_code, scheduled_date,
          start_time, end_time, duration_hours, rate_type, total_amount, topic))
    cursor.execute("SELECT ADVISOR_BOOKING_SEQ.CURRVAL FROM DUAL")
    return cursor.fetchone()[0]


def update_booking_status(cursor, booking_id, new_status, notes=None):
    if notes is not None:
        cursor.execute("""
            UPDATE ADVISOR_BOOKING
            SET BOOKING_STATUS = :1, NOTES = :2
            WHERE BOOKING_ID = :3
        """, (new_status, notes, booking_id))
    else:
        cursor.execute("""
            UPDATE ADVISOR_BOOKING SET BOOKING_STATUS = :1 WHERE BOOKING_ID = :2
        """, (new_status, booking_id))


def complete_booking(cursor, booking_id):
    cursor.execute("""
        UPDATE ADVISOR_BOOKING
        SET BOOKING_STATUS = 'COMPLETED', PAYMENT_STATUS = 'PAID'
        WHERE BOOKING_ID = :1
    """, (booking_id,))


def upsert_booking_rating(cursor, booking_id, advisor_id, farmer_code, rating, review):
    cursor.execute("SELECT RATING_ID FROM ADVISOR_RATING WHERE BOOKING_ID = :1",
                   (booking_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE ADVISOR_RATING SET RATING = :1, REVIEW = :2 WHERE RATING_ID = :3
        """, (rating, review, row[0]))
    else:
        cursor.execute("""
            INSERT INTO ADVISOR_RATING
                (RATING_ID, BOOKING_ID, ADVISOR_ID, FARMER_ID, RATING, REVIEW)
            VALUES
                (ADVISOR_RATING_SEQ.NEXTVAL, :1, :2, :3, :4, :5)
        """, (booking_id, advisor_id, farmer_code, rating, review))


def update_advisor_profile(cursor, person_id, specialization, bio,
                            qualification, experience_years, phone=None):
    cursor.execute("""
        UPDATE ADVISOR
        SET SPECIALIZATION = :1, BIO = :2, QUALIFICATION = :3,
            EXPERIENCE_YEARS = :4
        WHERE PERSON_ID = :5
    """, (specialization, bio, qualification, experience_years, person_id))
    if phone:
        cursor.execute("UPDATE PERSON SET LOGIN_PHONE = :1 WHERE PERSON_ID = :2",
                       (phone, person_id))
        cursor.execute("""
            UPDATE PHONE SET PHONE_NUMBER = :1
            WHERE PERSON_ID = :2 AND IS_PRIMARY = 'YES'
        """, (phone, person_id))


def toggle_advisor_availability(cursor, person_id):
    cursor.execute("SELECT IS_AVAILABLE FROM ADVISOR WHERE PERSON_ID = :1", (person_id,))
    row = cursor.fetchone()
    if not row:
        return None
    new_val = 'NO' if row[0] == 'YES' else 'YES'
    cursor.execute("UPDATE ADVISOR SET IS_AVAILABLE = :1 WHERE PERSON_ID = :2",
                   (new_val, person_id))
    return new_val


def mark_notification_read(cursor, notif_id, person_id):
    cursor.execute("""
        UPDATE NOTIFICATION SET IS_READ = 'YES'
        WHERE NOTIF_ID = :1 AND PERSON_ID = :2
    """, (notif_id, person_id))


def mark_all_notifications_read(cursor, person_id):
    cursor.execute("""
        UPDATE NOTIFICATION SET IS_READ = 'YES'
        WHERE PERSON_ID = :1 AND NVL(IS_READ, 'NO') = 'NO'
    """, (person_id,))