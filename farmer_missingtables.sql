-- ============================================
-- ADD MISSING TABLES FOR FARMER DASHBOARD
-- ============================================

-- ACTIVITY_RECORD Table for tracking all activities
CREATE TABLE ACTIVITY_RECORD (
    activity_id VARCHAR2(20) PRIMARY KEY,
    farmer_code VARCHAR2(20) NOT NULL,
    activity_type VARCHAR2(30) CHECK (activity_type IN ('REFERRAL', 'LIKE', 'REPAYMENT', 'LOAN_APPLICATION', 'CONSULTATION')),
    description VARCHAR2(500),
    activity_date DATE DEFAULT SYSDATE,
    reference_id VARCHAR2(20),
    CONSTRAINT fk_activity_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code)
);

-- CONSULTATION Table
CREATE TABLE CONSULTATION (
    session_id VARCHAR2(20) PRIMARY KEY,
    farmer_code VARCHAR2(20) NOT NULL,
    advisor_id NUMBER,
    topic VARCHAR2(255) NOT NULL,
    scheduled_date DATE,
    actual_date DATE,
    resolution_status VARCHAR2(20) DEFAULT 'PENDING' CHECK (resolution_status IN ('PENDING', 'ACCEPTED', 'COMPLETED', 'CANCELLED')),
    notes VARCHAR2(500),
    created_at DATE DEFAULT SYSDATE,
    CONSTRAINT fk_consult_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code),
    CONSTRAINT fk_consult_advisor FOREIGN KEY (advisor_id) REFERENCES PERSON(person_id)
);

-- ASSET Table
CREATE TABLE ASSET (
    asset_id VARCHAR2(20) PRIMARY KEY,
    farmer_code VARCHAR2(20) NOT NULL,
    asset_type VARCHAR2(30) CHECK (asset_type IN ('LAND', 'LIVESTOCK', 'EQUIPMENT', 'POULTRY', 'AQUACULTURE', 'VEHICLE', 'OTHER')),
    asset_name VARCHAR2(100) NOT NULL,
    quantity NUMBER DEFAULT 1,
    unit VARCHAR2(20),
    acquisition_date DATE DEFAULT SYSDATE,
    expected_completion_date DATE,
    revenue_generated NUMBER(12,2) DEFAULT 0,
    total_expense NUMBER(12,2) DEFAULT 0,
    asset_status VARCHAR2(20) DEFAULT 'ACTIVE' CHECK (asset_status IN ('ACTIVE', 'COMPLETED', 'SOLD', 'INACTIVE')),
    notes VARCHAR2(500),
    CONSTRAINT fk_asset_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code)
);

-- CREDIT_SCORE Table
CREATE TABLE CREDIT_SCORE (
    farmer_code VARCHAR2(20) PRIMARY KEY,
    score NUMBER(3) DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
    last_update DATE DEFAULT SYSDATE,
    CONSTRAINT fk_credit_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code)
);

-- NOTIFICATION Table
CREATE TABLE NOTIFICATION (
    notification_id VARCHAR2(20) PRIMARY KEY,
    farmer_code VARCHAR2(20) NOT NULL,
    message VARCHAR2(500) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    is_read VARCHAR2(3) DEFAULT 'NO' CHECK (is_read IN ('YES', 'NO')),
    notification_type VARCHAR2(30) CHECK (notification_type IN ('LOAN', 'KYC', 'PAYMENT', 'CONSULTATION', 'SYSTEM')),
    link VARCHAR2(200),
    CONSTRAINT fk_notif_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code)
);

-- ============================================
-- DATABASE TRIGGERS FOR NOTIFICATIONS
-- ============================================

-- Trigger for Loan Status Changes
CREATE OR REPLACE TRIGGER trg_loan_notification
AFTER UPDATE OF loan_state ON LOAN
FOR EACH ROW
DECLARE
    v_notif_id VARCHAR2(20);
    v_message VARCHAR2(500);
BEGIN
    IF :NEW.loan_state = 'ACTIVE' AND :OLD.loan_state = 'PENDING' THEN
        v_message := 'Your loan ' || :NEW.loan_no || ' has been approved! Amount: ' || :NEW.amount || ' BDT';
    ELSIF :NEW.loan_state = 'CLOSED' AND :OLD.loan_state = 'ACTIVE' THEN
        v_message := 'Your loan ' || :NEW.loan_no || ' has been fully paid off. Congratulations!';
    ELSIF :NEW.loan_state = 'DEFAULTED' AND :OLD.loan_state = 'ACTIVE' THEN
        v_message := 'Your loan ' || :NEW.loan_no || ' is now in default. Please contact your agent immediately.';
    ELSIF :NEW.loan_state = 'REJECTED' AND :OLD.loan_state = 'PENDING' THEN
        v_message := 'Your loan ' || :NEW.loan_no || ' has been rejected. Reason: ' || :NEW.rejection_reason;
    END IF;
    
    IF v_message IS NOT NULL THEN
        v_notif_id := 'NOT-' || TO_CHAR(SYSDATE, 'YYYYMMDDHH24MISS') || '-' || :NEW.farmer_code;
        INSERT INTO NOTIFICATION (notification_id, farmer_code, message, created_at, notification_type)
        VALUES (v_notif_id, :NEW.farmer_code, v_message, SYSDATE, 'LOAN');
    END IF;
END;
/

-- Trigger for KYC Status Changes
CREATE OR REPLACE TRIGGER trg_kyc_notification
AFTER UPDATE OF identity_verified ON KYC
FOR EACH ROW
DECLARE
    v_notif_id VARCHAR2(20);
    v_message VARCHAR2(500);
    v_farmer_code VARCHAR2(20);
BEGIN
    SELECT farmer_code INTO v_farmer_code FROM KYC WHERE kyc_id = :NEW.kyc_id;
    
    IF :NEW.identity_verified = 'VERIFIED' AND :OLD.identity_verified = 'PENDING' THEN
        v_message := 'Your KYC has been verified successfully! You can now apply for loans.';
    ELSIF :NEW.identity_verified = 'REJECTED' AND :OLD.identity_verified = 'PENDING' THEN
        v_message := 'Your KYC has been rejected. Please contact your agent for more information.';
    END IF;
    
    IF v_message IS NOT NULL THEN
        v_notif_id := 'NOT-' || TO_CHAR(SYSDATE, 'YYYYMMDDHH24MISS') || '-' || v_farmer_code;
        INSERT INTO NOTIFICATION (notification_id, farmer_code, message, created_at, notification_type)
        VALUES (v_notif_id, v_farmer_code, v_message, SYSDATE, 'KYC');
    END IF;
END;
/

-- Trigger for Repayment
CREATE OR REPLACE TRIGGER trg_repayment_notification
AFTER INSERT ON REPAYMENT
FOR EACH ROW
DECLARE
    v_notif_id VARCHAR2(20);
    v_message VARCHAR2(500);
    v_farmer_code VARCHAR2(20);
BEGIN
    SELECT farmer_code INTO v_farmer_code FROM LOAN WHERE loan_no = :NEW.loan_no;
    
    v_message := 'Payment of ' || :NEW.amount_paid || ' BDT received for loan ' || :NEW.loan_no || '. Installment ' || :NEW.installment_no || ' paid.';
    v_notif_id := 'NOT-' || TO_CHAR(SYSDATE, 'YYYYMMDDHH24MISS') || '-' || v_farmer_code;
    INSERT INTO NOTIFICATION (notification_id, farmer_code, message, created_at, notification_type)
    VALUES (v_notif_id, v_farmer_code, v_message, SYSDATE, 'PAYMENT');
END;
/

-- ============================================
-- SAMPLE DATA FOR NEW TABLES
-- ============================================

-- Sample Credit Scores
INSERT INTO CREDIT_SCORE (farmer_code, score, last_update)
SELECT farmer_code, 75 + MOD(ROWNUM, 25), SYSDATE FROM FARMER;

-- Sample Consultations
INSERT INTO CONSULTATION (session_id, farmer_code, advisor_id, topic, scheduled_date, resolution_status, notes)
VALUES ('CON-001', 'FR-001', 1004, 'Boro Season Planning', SYSDATE + 2, 'PENDING', 'Need advice on fertilizer selection');

INSERT INTO CONSULTATION (session_id, farmer_code, advisor_id, topic, scheduled_date, resolution_status, notes)
VALUES ('CON-002', 'FR-003', 1004, 'Poultry Disease Management', SYSDATE - 1, 'COMPLETED', 'Discussed vaccination schedule');

-- Sample Assets
INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
VALUES ('AST-001', 'FR-001', 'LAND', 'Agricultural Land', 2, 'Bigha', SYSDATE - 365, NULL, 150000, 50000, 'ACTIVE');

INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
VALUES ('AST-002', 'FR-003', 'LIVESTOCK', 'Dairy Cows', 3, 'Head', SYSDATE - 180, SYSDATE + 30, 120000, 80000, 'ACTIVE');

-- Sample Activity Records
INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
VALUES ('ACT-001', 'FR-001', 'REPAYMENT', 'Paid installment 1 for loan LN-003', SYSDATE - 5, 'LN-003');

INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
VALUES ('ACT-002', 'FR-001', 'LIKE', 'Liked community post POST-001', SYSDATE - 2, 'POST-001');

INSERT INTO ACTIVITY_RECORD (activity_id, farmer_code, activity_type, description, activity_date, reference_id)
VALUES ('ACT-003', 'FR-001', 'REFERRAL', 'Referred farmer FR-002 to the platform', SYSDATE - 10, 'FR-002');

-- Sample Notifications
INSERT INTO NOTIFICATION (notification_id, farmer_code, message, created_at, is_read, notification_type)
VALUES ('NOT-001', 'FR-001', 'Your loan LN-001 has been approved! Amount: 50000 BDT', SYSDATE - 1, 'NO', 'LOAN');

INSERT INTO NOTIFICATION (notification_id, farmer_code, message, created_at, is_read, notification_type)
VALUES ('NOT-002', 'FR-003', 'Your KYC has been verified successfully!', SYSDATE - 2, 'NO', 'KYC');

COMMIT;