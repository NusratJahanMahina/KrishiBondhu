

-- 1. Create the Sequence for auto-incrementing referral IDs
CREATE SEQUENCE referral_seq
START WITH 1001
INCREMENT BY 1
NOCACHE
NOCYCLE;

-- 2. Create the Trigger
CREATE OR REPLACE TRIGGER trg_farmer_referral_insert
BEFORE INSERT ON FARMER_REFERRAL
FOR EACH ROW
DECLARE
    v_kyc_status VARCHAR2(20);
BEGIN
    -- Auto-generate referral_id if NULL
    IF :NEW.referral_id IS NULL THEN
        :NEW.referral_id := 'REF-' || referral_seq.NEXTVAL;
    END IF;
 
    -- Auto-set referral_date if NULL
    IF :NEW.referral_date IS NULL THEN
        :NEW.referral_date := SYSDATE;
    END IF;
 
    -- Set status based on referee's KYC status
    BEGIN
        SELECT identity_verified
        INTO v_kyc_status
        FROM KYC
        WHERE farmer_code = :NEW.referee_code;
 
        IF v_kyc_status = 'VERIFIED' THEN
            :NEW.status := 'ACCEPTED';
        ELSE
            :NEW.status := 'PENDING';
        END IF;
 
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            :NEW.status := 'PENDING';
    END;
 
EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Error in trg_farmer_referral_insert: ' || SQLERRM);
        RAISE;
END;
/

////////////////////// CREDIT SCORE UPDATE TRIGGER //////////////////////

CREATE OR REPLACE TRIGGER trg_update_score_on_repayment
AFTER INSERT ON REPAYMENT
FOR EACH ROW
DECLARE
    v_farmer_code VARCHAR2(20);
    v_repayments  NUMBER;
    v_referrals   NUMBER;
    v_overdue     NUMBER;
    v_score       NUMBER;
    v_earned      NUMBER;
    v_penalty     NUMBER;
BEGIN
    SELECT farmer_code INTO v_farmer_code
    FROM LOAN
    WHERE loan_no = :NEW.loan_no;
 
    SELECT
        NVL((SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = v_farmer_code AND activity_type = 'REPAYMENT'), 0),
        NVL((SELECT COUNT(*) FROM ACTIVITY_RECORD WHERE farmer_code = v_farmer_code AND activity_type = 'REFERRAL'), 0),
        NVL((SELECT COUNT(*) FROM REPAYMENT r JOIN LOAN l ON r.loan_no = l.loan_no
             WHERE l.farmer_code = v_farmer_code AND r.payment_state = 'OVERDUE'), 0)
    INTO v_repayments, v_referrals, v_overdue
    FROM DUAL;
 
    v_earned := LEAST(v_repayments * 10, 50)
              + LEAST(v_referrals * 10, 20);
    v_penalty := LEAST(v_overdue * 5, 20);
    v_score := GREATEST(1, LEAST(100, 20 + v_earned - v_penalty));
 
    MERGE INTO CREDIT_SCORE cs
    USING (SELECT v_farmer_code AS farmer_code FROM DUAL) src
    ON (cs.farmer_code = src.farmer_code)
    WHEN MATCHED THEN
        UPDATE SET cs.score = v_score, cs.last_update = SYSDATE
    WHEN NOT MATCHED THEN
        INSERT (farmer_code, score, last_update) VALUES (v_farmer_code, v_score, SYSDATE);
 
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        DBMS_OUTPUT.PUT_LINE('No loan found for: ' || :NEW.loan_no);
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Error in trg_update_score_on_repayment: ' || SQLERRM);
END;
/