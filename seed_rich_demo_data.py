import sqlite3
from datetime import datetime, timedelta

def seed_rich_data(db_path="krishibondhu.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("🌱 Seeding rich agricultural demo data into KrishiBondhu database...")

    try:
        # ==========================================
        # 1. CENTERS (iFarmer Service Centers)
        # ==========================================
        centers = [
            (101, 'ঢাকা কেন্দ্রীয় কৃষি কেন্দ্র', 'ঢাকা সদর', 'ঢাকা'),
            (102, 'চট্টগ্রাম উপকূলীয় এগ্রো হাব', 'পটিয়া', 'চট্টগ্রাম'),
            (103, 'রাজশাহী বরেন্দ্র কৃষি সেবা কেন্দ্র', 'গোদাগাড়ী', 'রাজশাহী'),
            (104, 'বগুড়া আধুনিক শস্য ও সার কেন্দ্র', 'শিবগঞ্জ', 'বগুড়া'),
            (105, 'ময়মনসিংহ কৃষি প্রযুক্তি কেন্দ্র', 'ত্রিশাল', 'ময়মনসিংহ'),
            (106, 'যশোর ফুল ও সবজি সেবা হাব', 'ঝিকরগাছা', 'যশোর'),
            (107, 'দিনাজপুর লিচু ও শস্য উন্নয়ন কেন্দ্র', 'বীরগঞ্জ', 'দিনাজপুর'),
            (108, 'বরিশাল ভাসমান কৃষি ও পেয়ারা কেন্দ্র', 'বানারীপাড়া', 'বরিশাল')
        ]
        for c in centers:
            cursor.execute("""
                INSERT INTO IFARMER_CENTER (center_code, center_name, upazila, district)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(center_code) DO UPDATE SET
                    center_name = excluded.center_name,
                    upazila = excluded.upazila,
                    district = excluded.district
            """, c)

        # ==========================================
        # 2. PERSONS (Users across all 4 roles)
        # ==========================================
        users = [
            # Admins
            (4001, 'অ্যাডমিন', 'ব্যবহারকারী', 'admin', 'password123', '01941234567', 'ADMIN'),
            (4002, 'সিস্টেম', 'কন্ট্রোলার', 'admin2', 'password123', '01941234568', 'ADMIN'),

            # Field Agents
            (2001, 'করিম', 'সাহেব', 'agent1', 'password123', '01721234567', 'AGENT'),
            (2002, 'জামিলা', 'আক্তার', 'agent2', 'password123', '01722345678', 'AGENT'),
            (2003, 'নাজমুল', 'হক', 'agent3', 'password123', '01723456789', 'AGENT'),
            (2004, 'তাসলিমা', 'নাসরিন', 'agent4', 'password123', '01724567890', 'AGENT'),
            (2005, 'হাসান', 'মাহমুদ', 'agent5', 'password123', '01725678901', 'AGENT'),

            # Advisors
            (3001, 'ড. সামসুদ্দিন', 'আহমেদ', 'advisor1', 'password123', '01831234567', 'ADVISOR'),
            (3002, 'প্রফেসর ড. মাহফুজুল', 'হক', 'advisor2', 'password123', '01832345678', 'ADVISOR'),
            (3003, 'কৃষিবিদ নুসরাত', 'জাহান', 'advisor3', 'password123', '01833456789', 'ADVISOR'),
            (3004, 'ড. আব্দুল', 'কাদির', 'advisor4', 'password123', '01834567890', 'ADVISOR'),
            (3005, 'কৃষিবিদ মো: হাবিবুর', 'রহমান', 'advisor5', 'password123', '01835678901', 'ADVISOR'),

            # Farmers
            (1001, 'রহিম', 'আহমেদ', 'farmer1', 'password123', '01911234567', 'FARMER'),
            (1002, 'ফাতিমা', 'বেগম', 'farmer2', 'password123', '01912345678', 'FARMER'),
            (1003, 'করিম', 'মিয়া', 'farmer3', 'password123', '01913345789', 'FARMER'),
            (1004, 'মো: আনোয়ার', 'হোসেন', 'farmer4', 'password123', '01914456780', 'FARMER'),
            (1005, 'সুলতানা', 'রাজিয়া', 'farmer5', 'password123', '01915567891', 'FARMER'),
            (1006, 'আব্দুর', 'রাজ্জাক', 'farmer6', 'password123', '01916678902', 'FARMER'),
            (1007, 'মো: কবিরুল', 'ইসলাম', 'farmer7', 'password123', '01917789013', 'FARMER'),
            (1008, 'মমতাজ', 'বেগম', 'farmer8', 'password123', '01918890124', 'FARMER')
        ]
        for u in users:
            cursor.execute("""
                INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(person_id) DO UPDATE SET
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    login_phone = excluded.login_phone,
                    role = excluded.role
            """, u)

        # ==========================================
        # 3. FIELD AGENTS
        # ==========================================
        field_agents = [
            (2001, 2001, 101, 'YES', '2024-01-15'),
            (2002, 2002, 102, 'YES', '2024-03-01'),
            (2003, 2003, 104, 'YES', '2024-05-10'),
            (2004, 2004, 105, 'YES', '2024-07-20'),
            (2005, 2005, 106, 'YES', '2024-09-01')
        ]
        for fa in field_agents:
            cursor.execute("""
                INSERT INTO FIELD_AGENT (agent_code, person_id, center_code, is_active, join_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(agent_code) DO UPDATE SET
                    center_code = excluded.center_code,
                    is_active = excluded.is_active
            """, fa)

        # ==========================================
        # 4. FARMERS
        # ==========================================
        farmers = [
            (1001, 1001, 2001, 101, 4.5, '2024-02-10'),
            (1002, 1002, 2001, 101, 3.2, '2024-03-15'),
            (1003, 1003, 2002, 102, 6.0, '2024-04-01'),
            (1004, 1004, 2003, 104, 8.5, '2024-05-12'),
            (1005, 1005, 2005, 106, 2.8, '2024-06-20'),
            (1006, 1006, 2003, 107, 12.0, '2024-07-05'),
            (1007, 1007, 2001, 103, 5.5, '2024-08-18'),
            (1008, 1008, 2002, 108, 3.0, '2024-09-01')
        ]
        for f in farmers:
            cursor.execute("""
                INSERT INTO FARMER (farmer_code, person_id, agent_code, center_code, land_area, registration_date)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(farmer_code) DO UPDATE SET
                    agent_code = excluded.agent_code,
                    center_code = excluded.center_code,
                    land_area = excluded.land_area
            """, f)

        # ==========================================
        # 5. KYC VERIFICATIONS
        # ==========================================
        kyc_entries = [
            (1001, 2001, 'VERIFIED', '2024-02-12'),
            (1002, 2001, 'VERIFIED', '2024-03-18'),
            (1003, 2002, 'VERIFIED', '2024-04-05'),
            (1004, 2003, 'VERIFIED', '2024-05-15'),
            (1005, 2005, 'PENDING', None),
            (1006, 2003, 'VERIFIED', '2024-07-10'),
            (1007, 2001, 'PENDING', None),
            (1008, 2002, 'VERIFIED', '2024-09-03')
        ]
        cursor.execute("DELETE FROM KYC")
        for k in kyc_entries:
            cursor.execute("""
                INSERT INTO KYC (farmer_code, agent_code, identity_verified, verification_date)
                VALUES (?, ?, ?, ?)
            """, k)

        # ==========================================
        # 6. ADVISORS & RATES & AVAILABILITY
        # ==========================================
        cursor.execute("DELETE FROM ADVISOR_RATING")
        cursor.execute("DELETE FROM ADVISOR_BOOKING")
        cursor.execute("DELETE FROM ADVISOR_AVAILABILITY")
        cursor.execute("DELETE FROM ADVISOR_RATE")
        cursor.execute("DELETE FROM ADVISOR")

        advisors = [
            (3001, 3001, 'মৃত্তিকা পুষ্টি ও সার ব্যবস্থাপনা', 'মাটির পুষ্টিমান বিশ্লেষণ, সার প্রয়োগের ভারসাম্য ও মাটির স্বাস্থ্য রক্ষায় ১২ বছরের অভিজ্ঞতা।', 12, 'পিএইচডি (মৃত্তিকা বিজ্ঞান, বাকৃবি)', 'YES', 4.9, 38),
            (3002, 3002, 'শস্য বালাই ও কীটতত্ত্ব বিশেষজ্ঞ', 'ধান, গম ও ভুট্টার ক্ষতিকর পোকা ও রোগ নিয়ন্ত্রণে আধুনিক সমন্বিত বালাই ব্যবস্থাপনা (IPM) বিশেষজ্ঞ।', 15, 'এমএস ইন এনটমোলজি (ইরি ফেলো)', 'YES', 5.0, 52),
            (3003, 3003, 'উদ্যানতত্ত্ব ও ফলমূল চাষ বিশেষজ্ঞ', 'আম, লিচু, ড্রাগন ও উচ্চমূল্যের সবজির বাণিজ্যিক চাষাবাদ ও রোগ নিরাময়ে পরামর্শক।', 8, 'বিএসসি ও এমএসসি ইন হর্টিকালচার (শেকৃবি)', 'YES', 4.8, 29),
            (3004, 3004, 'জৈব কৃষি ও ভার্মিকম্পোস্ট প্রযুক্তিবিদ', 'রাসায়নিক মুক্ত নিরাপদ খাদ্য উৎপাদন, ট্রাইকোডার্মা ও জৈব বালাইনাশক উৎপাদনে বিশেষ অভিজ্ঞ।', 10, 'এম.এস.সি. (জৈব কৃষি প্রযুক্তি)', 'YES', 4.9, 44),
            (3005, 3005, 'আধুনিক সেচ ও ড্রিপ ইরিগেশন প্রকৌশলী', 'সৌর বিদ্যুৎ চালিত সেচ, ড্রিপ ও স্প্রিংকলার প্রযুক্তির মাধ্যমে ৫০% পানি সাশ্রয়ী কৃষি সমাধান।', 7, 'বিএসসি ইন এগ্রিকালচারাল ইঞ্জিনিয়ারিং', 'YES', 4.7, 21)
        ]
        for adv in advisors:
            cursor.execute("""
                INSERT INTO ADVISOR (advisor_id, person_id, specialization, bio, experience_years, qualification, is_available, rating, total_bookings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, adv)

        # Rates for all advisors
        cursor.execute("DELETE FROM ADVISOR_RATE")
        rates = [
            (3001, 'HOURLY', 400.0), (3001, 'DAILY', 2800.0),
            (3002, 'HOURLY', 500.0), (3002, 'DAILY', 3500.0),
            (3003, 'HOURLY', 350.0), (3003, 'DAILY', 2500.0),
            (3004, 'HOURLY', 300.0), (3004, 'DAILY', 2200.0),
            (3005, 'HOURLY', 450.0), (3005, 'DAILY', 3200.0)
        ]
        for r in rates:
            cursor.execute("""
                INSERT INTO ADVISOR_RATE (advisor_id, rate_type, amount, currency)
                VALUES (?, ?, ?, 'BDT')
            """, r)

        # Availability
        cursor.execute("DELETE FROM ADVISOR_AVAILABILITY")
        days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'SATURDAY']
        for adv in advisors:
            for day in days:
                cursor.execute("""
                    INSERT INTO ADVISOR_AVAILABILITY (advisor_id, day_of_week, start_time, end_time, is_available)
                    VALUES (?, ?, '09:00', '17:00', 'YES')
                """, (adv[0], day))

        # ==========================================
        # 7. KRISHI LOANS PORTFOLIO
        # ==========================================
        loans = [
            (101, 1001, 'ACTIVE', '2024-03-01', '2024-02-15', 24),
            (102, 1002, 'ACTIVE', '2024-04-10', '2024-03-25', 12),
            (103, 1003, 'CLOSED', '2023-01-15', '2023-01-02', 12),
            (104, 1004, 'ACTIVE', '2024-05-20', '2024-05-01', 36),
            (105, 1005, 'PENDING', None, '2024-08-25', 18),
            (106, 1006, 'ACTIVE', '2024-07-15', '2024-07-01', 24),
            (107, 1007, 'PENDING', None, '2024-08-30', 12),
            (108, 1008, 'CLOSED', '2023-06-01', '2023-05-15', 12)
        ]
        for l in loans:
            cursor.execute("""
                INSERT INTO LOAN (loan_no, farmer_code, loan_state, approval_date, application_date, tenure_months)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(loan_no) DO UPDATE SET
                    loan_state = excluded.loan_state,
                    approval_date = excluded.approval_date,
                    application_date = excluded.application_date,
                    tenure_months = excluded.tenure_months
            """, l)

        # ==========================================
        # 8. CENTER SUPPLIES & INVENTORY
        # ==========================================
        inventory = [
            (2001, 'উন্নত ব্রি ধান-৮৯ বীজ', 150, 'কেজি', 550.0),
            (2001, 'ইউরিয়া সার (দানাদার)', 200, 'কেজি', 850.0),
            (2001, 'ডিএপি সার (DAP)', 120, 'কেজি', 1100.0),
            (2001, 'এমওপি পটাশ সার', 80, 'কেজি', 750.0),
            (2002, 'অটোস্টিন ৫০ ডব্লিউডিজি কীটনাশক', 45, 'লিটার', 1250.0),
            (2002, 'হাইব্রিড ভুট্টা বীজ - পায়োনিয়ার', 90, 'কেজি', 680.0),
            (2003, 'বিএডিসি উন্নত গোল আলু বীজ (ডায়মন্ড)', 300, 'বস্তা', 2400.0),
            (2003, 'ভার্মিকম্পোস্ট অর্গানিক সার', 180, 'বস্তা', 450.0),
            (2004, 'উন্নত সরিষা বীজ (বারি-১৪)', 65, 'কেজি', 420.0),
            (2005, 'জিংক সালফেট ও বোরন মিশ্রণ', 8, 'কেজি', 920.0) # Low stock test item
        ]
        cursor.execute("DELETE FROM INVENTORY")
        for item in inventory:
            cursor.execute("""
                INSERT INTO INVENTORY (agent_code, item_name, quantity, unit, price)
                VALUES (?, ?, ?, ?, ?)
            """, item)

        # ==========================================
        # 9. ADVISOR BOOKINGS & PRESCRIPTIONS
        # ==========================================
        bookings = [
            (3001, 1001, 2001, '2024-08-10', '10:00', '12:00', 2.0, 'HOURLY', 800.0, 'PAID', 'COMPLETED', 'বোরো ধানের পাতার আগা শুকিয়ে যাওয়া ও সমাধান', 'মাটিতে পটাশ সারের ঘাটতি রয়েছে। প্রতি বিঘায় ৫ কেজি এমওপি সার ও জিংক স্প্রে করার পরামর্শ দেওয়া হলো।'),
            (3002, 1001, 2001, '2024-08-25', '14:00', '16:00', 2.0, 'HOURLY', 1000.0, 'PAID', 'COMPLETED', 'ধানের ব্লাস্ট ও মাজরা পোকা দমন', 'ব্লাস্টের জন্য ট্রুপার ৭৫ ডব্লিউপি ১ গ্রাম প্রতি লিটার পানিতে মিশিয়ে বিকেলে স্প্রে করুন। মাজরা পোকার জন্য আলোক ফাঁদ ব্যবহার করুন।'),
            (3003, 1004, 2003, '2024-08-28', '09:00', '17:00', 8.0, 'DAILY', 2500.0, 'PAID', 'COMPLETED', 'আলু চাষের আধুনিক রোপণ ও রোগ প্রতিরোধ', 'আলুর আর্লি ব্লাইট প্রতিরোধে কপার অক্সিক্লোরাইড স্প্রে করুন। সেচের পর পানি যেন জমে না থাকে সেদিকে খেয়াল রাখুন।'),
            (3004, 1005, 2005, '2024-09-05', '11:00', '13:00', 2.0, 'HOURLY', 600.0, 'PAID', 'CONFIRMED', 'সবজির জৈব বালাই ব্যবস্থাপনা', None),
            (3002, 1006, 2003, '2024-09-08', '15:00', '17:00', 2.0, 'HOURLY', 1000.0, 'PENDING', 'PENDING', 'আমের মুকুলে হপার পোকা নিয়ন্ত্রণ', None)
        ]
        cursor.execute("DELETE FROM ADVISOR_BOOKING")
        for b in bookings:
            cursor.execute("""
                INSERT INTO ADVISOR_BOOKING (advisor_id, farmer_id, agent_id, scheduled_date, start_time, end_time, duration_hours, rate_type, total_amount, payment_status, booking_status, consultation_topic, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, b)

        # Reviews
        cursor.execute("DELETE FROM ADVISOR_RATING")
        reviews = [
            (1, 3001, 1001, 5, 'ডাক্তার সামসুদ্দিন স্যারের প্রেসক্রিপশন অনুযায়ী সার দিয়ে মাত্র ৭ দিনে ধানের পাতা আবার সতেজ সবুজ হয়েছে। অত্যন্ত অভিজ্ঞ ও বিনয়ী।'),
            (2, 3002, 1001, 5, 'ব্লাস্ট রোগের সঠিক প্রতিষেধক সময়মতো পাওয়ায় পুরো এক একরের ফসল রক্ষা পেয়েছে। আন্তরিক ধন্যবাদ কৃষিবন্ধুকে।'),
            (3, 3003, 1004, 5, 'সারাদিনের সরেজমিন পরামর্শে আলুর বীজ শোধন ও পরিচর্যা সম্পর্কে চমৎকার দিকনির্দেশনা পেয়েছি।')
        ]
        for rev in reviews:
            cursor.execute("""
                INSERT INTO ADVISOR_RATING (booking_id, advisor_id, farmer_id, rating, review)
                VALUES (?, ?, ?, ?, ?)
            """, rev)

        # ==========================================
        # 10. COMMUNITY POSTS & NOTICES
        # ==========================================
        posts = [
            (4001, '🌾 বোরো মৌসুমে সার ও কীটনাশক সংগ্রহ সংক্রান্ত জরুরী নোটিশ', 'সকল কৃষক ও মাঠ কর্মকর্তাদের জানানো যাচ্ছে যে, উপজেলা কৃষি অফিসের মাধ্যমে সরকার নির্ধারিত মূল্যে পর্যাপ্ত ইউরিয়া, ডিএপি ও এমওপি সারের মজুত প্রস্তুত রাখা হয়েছে। অবৈধ মজুতদারি দেখা গেলে সাথে সাথে হেল্পলাইনে জানান।'),
            (4001, '⚡ কৃষি ঋণ কিস্তি পরিশোধ ও নতুন আবেদন কর্মসূচি ২০২৬', 'যেসব কৃষক পূর্ববর্তী ঋণের কিস্তি শতভাগ পরিশোধ করেছেন, তারা অবিলম্বে পরবর্তী ফসলের জন্য দ্বিগুণ পরিমাণের কৃষি উন্নয়ন ঋণের জন্য আবেদন করতে পারবেন।'),
            (4001, '🌧️ আবহাওয়া পূর্বাভাস ও শস্য রক্ষা নির্দেশিকা', 'আগামী ৩ দিন উত্তরাঞ্চল ও মধ্যাঞ্চলে মাঝারি থেকে ভারী বৃষ্টিপাতের সম্ভাবনা রয়েছে। নিচু জমির পরিপক্ক ফসল দ্রুত কেটে নিরাপদ স্থানে সংরক্ষণ করুন এবং ড্রেনেজ ব্যবস্থা সচল রাখুন।'),
            (2001, '📢 ঢাকা সেন্টার - নতুন ব্রি ধান-৮৯ বীজ বিতরণ শুরু', 'ঢাকা আঞ্চলিক সেন্টারে উন্নত ব্রি ধান-৮৯ বীজ এসে পৌঁছেছে। কৃষকরা তাদের কৃষক কার্ড প্রদর্শন করে নির্ধারিত মূল্যে বীজ সংগ্রহ করতে পারবেন।')
        ]
        cursor.execute("DELETE FROM COMMUNITY_POST")
        for p in posts:
            cursor.execute("""
                INSERT INTO COMMUNITY_POST (author_id, title, content)
                VALUES (?, ?, ?)
            """, p)

        # ==========================================
        # 11. IN-APP NOTIFICATIONS
        # ==========================================
        notifications = [
            (1001, '✅ কৃষি ঋণ অনুমোদিত হয়েছে!', 'অভিনন্দন রহিম আহমেদ! আপনার কৃষি ঋণ #101 (মেয়াদ: ২৪ মাস) কেন্দ্রীয়ভাবে অনুমোদিত হয়েছে।', '/dashboard'),
            (1001, '📋 নতুন প্রেসক্রিপশন ও পরামর্শ নোট!', 'ড. সামসুদ্দিন আপনার পরামর্শ সেশনের প্রেসক্রিপশন নোট আপলোড করেছেন। বিস্তারিত দেখতে ক্লিক করুন।', '/dashboard'),
            (3001, '🔔 নতুন নিয়োগ অনুরোধ!', 'কৃষক রহিম আহমেদ আপনাকে পরামর্শের জন্য নিয়োগ করেছেন। বিষয়: বোরো ধানের পাতার রোগ সমাধান।', '/advisor/dashboard'),
            (2001, '🌾 নতুন কৃষক নিবন্ধন সম্পন্ন!', 'আপনার সেন্টারে নতুন কৃষক মো: কবিরুল ইসলাম নিবন্ধিত হয়েছেন। অনুগ্রহ করে কেওয়াইসি যাচাই করুন।', '/agent/dashboard'),
            (1002, '📢 আবহাওয়া সতর্কতা জারি', 'আগামী ৪৮ ঘণ্টায় বজ্রসহ বৃষ্টির পূর্বাভাস। আলু ও রবি শস্যের নিষ্কাশন নালা পরিষ্কার রাখুন।', '/dashboard')
        ]
        cursor.execute("DELETE FROM NOTIFICATION")
        for n in notifications:
            cursor.execute("""
                INSERT INTO NOTIFICATION (person_id, title, message, link)
                VALUES (?, ?, ?, ?)
            """, n)

        conn.commit()
        print("✨ Successfully populated KrishiBondhu with rich realistic demo data!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error seeding rich data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_rich_data()
