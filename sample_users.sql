-- ============================================
-- Sample User Data for KrishiBondhu
-- ============================================
-- Run this SQL script to insert test users into the PERSON table

-- FARMER USERS
INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (1001, 'রহিম', 'আহমেদ', 'farmer1', 'password123', '01911234567', 'farmer');

INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (1002, 'ফাতিমা', 'বেগম', 'farmer2', 'password123', '01912345678', 'farmer');

-- AGENT USERS
INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (2001, 'করিম', 'সাহেব', 'agent1', 'password123', '01721234567', 'agent');

INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (2002, 'জামিলা', 'আক্তার', 'agent2', 'password123', '01722345678', 'agent');

-- ADVISOR USERS
INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (3001, 'ডাক্তার', 'শামসুদ্দিন', 'advisor1', 'password123', '01831234567', 'advisor');

-- ADMIN USERS
INSERT INTO PERSON (person_id, first_name, last_name, username, password, login_phone, role)
VALUES (4001, 'অ্যাডমিন', 'ব্যবহারকারী', 'admin', 'password123', '01941234567', 'admin');

-- COMMIT CHANGES
COMMIT;

-- ============================================
-- TEST USER CREDENTIALS
-- ============================================
-- Username: farmer1 | Password: password123 | Phone: 01911234567
-- Username: farmer2 | Password: password123 | Phone: 01912345678
-- Username: agent1  | Password: password123 | Phone: 01721234567
-- Username: agent2  | Password: password123 | Phone: 01722345678
-- Username: advisor1| Password: password123 | Phone: 01831234567
-- Username: admin   | Password: password123 | Phone: 01941234567

-- You can also login with phone numbers:
-- Phone: 01911234567 | Password: password123
-- Phone: 01912345678 | Password: password123
-- etc.
