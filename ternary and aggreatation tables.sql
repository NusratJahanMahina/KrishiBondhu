-- ============================================================
-- 1. ATTENDS: The Ternary Relationship Table
-- Connects ADVISOR, FARMER, and CONSULTATION
-- ============================================================
CREATE TABLE ATTENDS (
    advisor_id        NUMBER NOT NULL,
    farmer_code       VARCHAR2(20) NOT NULL,
    session_id        VARCHAR2(20) NOT NULL,
    scheduled_date    DATE,
    actual_date       DATE,
    resolution_status VARCHAR2(20) DEFAULT 'PENDING',
    notes             VARCHAR2(500),
    
    -- Composite Primary Key (The 3-way connection)
    CONSTRAINT pk_attends PRIMARY KEY (advisor_id, farmer_code, session_id),
    
    -- Foreign Keys to the 3 entities
    CONSTRAINT fk_attends_advisor FOREIGN KEY (advisor_id) REFERENCES PERSON(person_id),
    CONSTRAINT fk_attends_farmer FOREIGN KEY (farmer_code) REFERENCES FARMER(farmer_code),
    CONSTRAINT fk_attends_session FOREIGN KEY (session_id) REFERENCES CONSULTATION(session_id)
);

-- ============================================================
-- 2. FUNDS: The Aggregation Relationship Table
-- Connects IFARMER_CENTER, LOAN, and BANK
-- ============================================================
CREATE TABLE FUNDS (
    center_code VARCHAR2(20) NOT NULL,
    loan_no     VARCHAR2(20) NOT NULL,
    bank_code   VARCHAR2(20) NOT NULL,
    amount      NUMBER(12,2) NOT NULL,
    fund_date   DATE DEFAULT SYSDATE,
    
    -- Composite Primary Key
    CONSTRAINT pk_funds PRIMARY KEY (center_code, loan_no, bank_code),
    
    -- Foreign Keys to the aggregated entities
    CONSTRAINT fk_funds_center FOREIGN KEY (center_code) REFERENCES IFARMER_CENTER(center_code),
    CONSTRAINT fk_funds_loan FOREIGN KEY (loan_no) REFERENCES LOAN(loan_no),
    CONSTRAINT fk_funds_bank FOREIGN KEY (bank_code) REFERENCES BANK(bank_code)
);