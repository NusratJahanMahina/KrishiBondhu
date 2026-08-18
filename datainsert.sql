-- ============================================================
-- RE-INSERT DATA FOR ATTENDS (Since the table is empty)
-- ============================================================

-- 1. Create the Consultation Sessions (Parent records)
INSERT INTO CONSULTATION (session_id, topic) 
VALUES ('CS-001', 'Boro Paddy Fertilizer Advice');

INSERT INTO CONSULTATION (session_id, topic) 
VALUES ('CS-002', 'Livestock Health Checkup');

-- 2. Insert the Ternary Relationships (Child records)
-- Admin (1004) advises Sabina (FR-001)
INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, resolution_status, notes)
VALUES (1004, 'FR-001', 'CS-001', TO_DATE('2026-08-25', 'YYYY-MM-DD'), 'PENDING', 'Sabina requested advice on DAP usage.');

-- Admin (1004) advises Abdul (FR-002)
INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, resolution_status, notes)
VALUES (1004, 'FR-002', 'CS-001', TO_DATE('2026-08-28', 'YYYY-MM-DD'), 'PENDING', 'Abdul wants to know about Boro season planning.');

-- Admin (1004) advises Sabina (FR-001) again
INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, resolution_status, notes)
VALUES (1004, 'FR-001', 'CS-002', TO_DATE('2026-09-01', 'YYYY-MM-DD'), 'SCHEDULED', 'Routine cattle health check for Sabina.');

COMMIT;