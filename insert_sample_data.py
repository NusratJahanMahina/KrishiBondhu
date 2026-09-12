import sqlite3
import time
import random

def generate_id():
    return int(str(int(time.time() * 1000)) + str(random.randint(10, 99)))

def insert_sample_data(db_path="krishibondhu.db"):
    """Insert sample test data into SQLite database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Insert test users (PERSON table)
        test_users = [
            # Farmers
            (1001, 'রহিম', 'আহমেদ', 'farmer1', 'password123', '01911234567', 'FARMER'),
            (1002, 'ফাতিমা', 'বেগম', 'farmer2', 'password123', '01912345678', 'FARMER'),
            (1003, 'করিম', 'মিয়া', 'farmer3', 'password123', '01913345789', 'FARMER'),
            
            # Agents
            (2001, 'করিম', 'সাহেব', 'agent1', 'password123', '01721234567', 'AGENT'),
            (2002, 'জামিলা', 'আক্তার', 'agent2', 'password123', '01722345678', 'AGENT'),
            
            # Advisors
            (3001, 'ডাক্তার', 'শামসুদ্দিন', 'advisor1', 'password123', '01831234567', 'ADVISOR'),
            
            # Admin
            (4001, 'অ্যাডমিন', 'ব্যবহারকারী', 'admin', 'password123', '01941234567', 'ADMIN'),
        ]
        
        for user in test_users:
            cursor.execute("""
                INSERT OR IGNORE INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, user)
        
        # Insert phone numbers
        for user in test_users:
            person_id = user[0]
            phone = user[5]
            cursor.execute("""
                INSERT OR IGNORE INTO PHONE (person_id, phone_number, phone_type, is_primary)
                VALUES (?, ?, ?, ?)
            """, (person_id, phone, 'PERSONAL', 'YES'))
        
        # Insert Centers
        centers = [
            (101, 'ঢাকা সেন্টার', 'ঢাকা সদর', 'ঢাকা'),
            (102, 'চট্টগ্রাম সেন্টার', 'চট্টগ্রাম', 'চট্টগ্রাম'),
            (103, 'রাজশাহী সেন্টার', 'রাজশাহী', 'রাজশাহী'),
        ]
        
        for center in centers:
            cursor.execute("""
                INSERT OR IGNORE INTO IFARMER_CENTER (center_code, center_name, upazila, district)
                VALUES (?, ?, ?, ?)
            """, center)
        
        # Insert Field Agents
        agents = [
            (2001, 2001, 101),  # Agent 1 in center 101
            (2002, 2002, 102),  # Agent 2 in center 102
        ]
        
        for agent_code, person_id, center_code in agents:
            cursor.execute("""
                INSERT OR IGNORE INTO FIELD_AGENT (agent_code, person_id, center_code, is_active)
                VALUES (?, ?, ?, ?)
            """, (agent_code, person_id, center_code, 'YES'))
        
        # Insert Farmers
        farmers = [
            (1001, 1001, 2001, 101, 5.0),  # Farmer 1 under Agent 1
            (1002, 1002, 2001, 101, 3.5),  # Farmer 2 under Agent 1
            (1003, 1003, 2002, 102, 8.0),  # Farmer 3 under Agent 2
        ]
        
        for farmer_code, person_id, agent_code, center_code, land_area in farmers:
            cursor.execute("""
                INSERT OR IGNORE INTO FARMER (farmer_code, person_id, agent_code, center_code, land_area)
                VALUES (?, ?, ?, ?, ?)
            """, (farmer_code, person_id, agent_code, center_code, land_area))
        
        # Insert KYC records
        kyc_data = [
            (1001, 2001, 'VERIFIED'),
            (1002, 2001, 'PENDING'),
            (1003, 2002, 'VERIFIED'),
        ]
        
        for farmer_code, agent_code, status in kyc_data:
            cursor.execute("""
                INSERT OR IGNORE INTO KYC (farmer_code, agent_code, identity_verified)
                VALUES (?, ?, ?)
            """, (farmer_code, agent_code, status))
        
        # Insert sample loans
        loans = [
            (101, 1001, 'ACTIVE', '2025-01-01', 24),
            (102, 1002, 'PENDING', '2025-02-01', 12),
            (103, 1003, 'CLOSED', '2024-01-01', 24),
        ]
        
        for loan_no, farmer_code, state, approval_date, tenure in loans:
            cursor.execute("""
                INSERT OR IGNORE INTO LOAN (loan_no, farmer_code, loan_state, approval_date, tenure_months)
                VALUES (?, ?, ?, ?, ?)
            """, (loan_no, farmer_code, state, approval_date, tenure))
        
        # Insert sample inventory
        inventory = [
            (2001, 'বীজ - ধান', 100, 'কেজি', 500.0),
            (2001, 'সার - ইউরিয়া', 50, 'কেজি', 800.0),
            (2002, 'কীটনাশক', 20, 'লিটার', 1200.0),
        ]
        
        for agent_code, item, qty, unit, price in inventory:
            cursor.execute("""
                INSERT INTO INVENTORY (agent_code, item_name, quantity, unit, price)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_code, item, qty, unit, price))
        
        # Insert advisor data with detailed profiles
        advisor_data = [
            (3001, 'মৃত্তিকা ও সার ব্যবস্থাপনা', 'মাটির পুষ্টিমান বিশ্লেষণ এবং সার প্রয়োগের বিশেষজ্ঞ', 12, 'এম.এস.সি. কৃষি বিজ্ঞান'),
        ]
        
        for person_id, specialization, bio, exp_years, qualification in advisor_data:
            advisor_id = generate_id()
            cursor.execute("""
                INSERT INTO ADVISOR (advisor_id, person_id, specialization, bio, experience_years, qualification, is_available)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (advisor_id, person_id, specialization, bio, exp_years, qualification, 'YES'))
        
        # Insert advisor rates (hourly and daily)
        cursor.execute("SELECT advisor_id FROM ADVISOR LIMIT 1")
        advisors = cursor.fetchall()
        
        rates_data = [
            # First advisor - hourly and daily rates
            (advisors[0][0], 'HOURLY', 500.0),      # ৳500/hour
            (advisors[0][0], 'DAILY', 3500.0),      # ৳3500/day
        ]
        
        for advisor_id, rate_type, amount in rates_data:
            cursor.execute("""
                INSERT INTO ADVISOR_RATE (advisor_id, rate_type, amount, currency)
                VALUES (?, ?, ?, ?)
            """, (advisor_id, rate_type, amount, 'BDT'))
        
        # Insert advisor availability (weekly schedule)
        availability_data = [
            # Advisor 1
            (advisors[0][0], 'MONDAY', '09:00', '17:00'),
            (advisors[0][0], 'WEDNESDAY', '09:00', '17:00'),
            (advisors[0][0], 'FRIDAY', '09:00', '17:00'),
            (advisors[0][0], 'SATURDAY', '10:00', '16:00'),
        ]
        
        for advisor_id, day, start_time, end_time in availability_data:
            cursor.execute("""
                INSERT INTO ADVISOR_AVAILABILITY (advisor_id, day_of_week, start_time, end_time, is_available)
                VALUES (?, ?, ?, ?, ?)
            """, (advisor_id, day, start_time, end_time, 'YES'))
        
        # Insert sample bookings
        booking_data = [
            (advisors[0][0], 1001, 2001, '2025-02-15', '10:00', '12:00', 2.0, 'HOURLY', 1000.0, 'PAID', 'COMPLETED', 'ধান চাষের নতুন পদ্ধতি'),
            (advisors[0][0], 1002, 2001, '2025-02-20', '14:00', '17:00', 3.0, 'HOURLY', 1500.0, 'PAID', 'COMPLETED', 'মাটি পরীক্ষা এবং সুপারিশ'),
            (advisors[0][0], 1003, 2002, '2025-02-25', '08:00', '16:00', 8.0, 'DAILY', 3500.0, 'PAID', 'COMPLETED', 'সম্পূর্ণ দিনের পরামর্শ'),
        ]
        
        for advisor_id, farmer_id, agent_id, sched_date, start_time, end_time, duration, rate_type, amount, pay_status, book_status, topic in booking_data:
            cursor.execute("""
                INSERT INTO ADVISOR_BOOKING (advisor_id, farmer_id, agent_id, scheduled_date, start_time, end_time, duration_hours, rate_type, total_amount, payment_status, booking_status, consultation_topic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (advisor_id, farmer_id, agent_id, sched_date, start_time, end_time, duration, rate_type, amount, pay_status, book_status, topic))
        
        # Insert sample ratings
        cursor.execute("SELECT booking_id, advisor_id, farmer_id FROM ADVISOR_BOOKING LIMIT 3")
        bookings = cursor.fetchall()
        
        rating_data = [
            (bookings[0][0], bookings[0][1], bookings[0][2], 5, 'অসাধারণ পরামর্শ এবং অত্যন্ত সহায়ক ছিল।'),
            (bookings[1][0], bookings[1][1], bookings[1][2], 5, 'খুবই দক্ষ এবং অভিজ্ঞ পরামর্শদাতা।'),
            (bookings[2][0], bookings[2][1], bookings[2][2], 4, 'ভালো পরামর্শ কিন্তু আরও বিস্তারিত চেয়েছিলাম।'),
        ]
        
        for booking_id, advisor_id, farmer_id, rating, review in rating_data:
            cursor.execute("""
                INSERT INTO ADVISOR_RATING (booking_id, advisor_id, farmer_id, rating, review)
                VALUES (?, ?, ?, ?, ?)
            """, (booking_id, advisor_id, farmer_id, rating, review))
        
        conn.commit()
        print("✅ Sample data inserted successfully!")
        print("\n📋 TEST CREDENTIALS:")
        print("=" * 50)
        print("USERNAME           PASSWORD      PHONE")
        print("=" * 50)
        print("farmer1            password123   01911234567")
        print("farmer2            password123   01912345678")
        print("farmer3            password123   01913345789")
        print("agent1             password123   01721234567")
        print("agent2             password123   01722345678")
        print("advisor1           password123   01831234567")
        print("admin              password123   01941234567")
        print("=" * 50)
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    insert_sample_data()
