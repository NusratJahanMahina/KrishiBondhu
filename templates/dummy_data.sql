

-- ============================================================
-- 6. INSERT DATA  INTO INVENTORY
-- ============================================================
INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-001', 'C-001', 'Urea Fertilizer', 500, 50, 'kg', 1200, 'Warehouse A', 'BCIC');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-002', 'C-001', 'Hybrid Rice Seed', 200, 20, 'kg', 2500, 'Warehouse B', 'BRRI');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-003', 'C-001', 'Pesticide', 100, 15, 'bottle', 800, 'Shelf 1', 'Syngenta');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-004', 'C-001', 'DAP Fertilizer', 300, 30, 'kg', 1500, 'Warehouse A', 'BCIC');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-005', 'C-001', 'Vegetable Seed', 150, 15, 'kg', 1800, 'Shelf 2', 'BADC');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-006', 'C-001', 'Pesticide - Confidor', 80, 10, 'bottle', 950, 'Shelf 3', 'Bayer');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-007', 'C-001', 'Organic Compost', 250, 20, 'kg', 900, 'Warehouse A', 'ACI');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-008', 'C-001', 'Rice Seed BRRI-28', 300, 40, 'kg', 2000, 'Warehouse B', 'BRRI');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-009', 'C-001', 'Insecticide', 150, 25, 'bottle', 700, 'Shelf 1', 'Syngenta');

INSERT INTO INVENTORY (inventory_id, center_code, name, quantity, min_stock_level, unit, price_per_unit, location, manufacturer) 
VALUES ('INV-010', 'C-001', 'Tractor Spare Parts', 50, 10, 'piece', 5000, 'Shelf 3', 'Sonalika');

-- ============================================================
-- 7. INSERT DATA INTO THE 3 CHILD TABLES
-- ============================================================
-- Seeds
INSERT INTO SEED_INVENTORY (inventory_id, crop_name, variety, germination_rate, season) 
VALUES ('INV-002', 'Rice', 'Hybrid', 85, 'BORO');
INSERT INTO SEED_INVENTORY (inventory_id, crop_name, variety, germination_rate, season) 
VALUES ('INV-005', 'Vegetable', 'Local', 90, 'RABI');
INSERT INTO SEED_INVENTORY (inventory_id, crop_name, variety, germination_rate, season) 
VALUES ('INV-008', 'Rice', 'BRRI-28', 95, 'AMAN');

-- Fertilizers
INSERT INTO FERTILIZER_INVENTORY (inventory_id, npk_ratio, fertilizer_type, application_rate, application_method) 
VALUES ('INV-001', '46-0-0', 'UREA', '50kg per bigha', 'BROADCAST');
INSERT INTO FERTILIZER_INVENTORY (inventory_id, npk_ratio, fertilizer_type, application_rate, application_method) 
VALUES ('INV-004', '18-46-0', 'DAP', '40kg per bigha', 'DRILL');
INSERT INTO FERTILIZER_INVENTORY (inventory_id, npk_ratio, fertilizer_type, application_rate, application_method) 
VALUES ('INV-007', 'N/A', 'COMPOST', '100kg per bigha', 'BROADCAST');

-- Chemicals
INSERT INTO CHEMICAL_INVENTORY (inventory_id, active_ingredient, application_method, dosage_instruction, safety_level, purpose) 
VALUES ('INV-003', 'Cypermethrin', 'SPRAY', '10ml per 5L water', 'MEDIUM', 'INSECTICIDE');
INSERT INTO CHEMICAL_INVENTORY (inventory_id, active_ingredient, application_method, dosage_instruction, safety_level, purpose) 
VALUES ('INV-006', 'Imidacloprid', 'SPRAY', '5ml per 5L water', 'HIGH', 'INSECTICIDE');
INSERT INTO CHEMICAL_INVENTORY (inventory_id, active_ingredient, application_method, dosage_instruction, safety_level, purpose) 
VALUES ('INV-009', 'Cypermethrin', 'SPRAY', '15ml per 5L water', 'MEDIUM', 'INSECTICIDE');

-- ============================================================
-- DUMMY DATA FOR SABINA BEGUM (FR-001)
-- ============================================================

-- 1. ASSET DATA (For her Assets page)
INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
VALUES ('AST-001', 'FR-001', 'LAND', 'Cultivable Land', 2, 'Bigha', TO_DATE('2024-01-15', 'YYYY-MM-DD'), NULL, 150000, 50000, 'ACTIVE');

INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
VALUES ('AST-002', 'FR-001', 'LIVESTOCK', 'Dairy Cow', 3, 'Heads', TO_DATE('2025-03-01', 'YYYY-MM-DD'), TO_DATE('2025-12-01', 'YYYY-MM-DD'), 45000, 20000, 'ACTIVE');

INSERT INTO ASSET (asset_id, farmer_code, asset_type, asset_name, quantity, unit, acquisition_date, expected_completion_date, revenue_generated, total_expense, asset_status)
VALUES ('AST-003', 'FR-001', 'EQUIPMENT', 'Power Tiller', 1, 'Piece', TO_DATE('2024-06-10', 'YYYY-MM-DD'), NULL, 30000, 35000, 'ACTIVE');


-- 2. LOAN DATA (For her Loans page)
INSERT INTO LOAN (loan_no, farmer_code, center_code, bank_code, amount, interest_rate, tenure_months, purpose, application_date, approval_date, disbursement_date, loan_state, approved_by)
VALUES ('LN-101', 'FR-001', 'C-001', 'BK-001', 50000, 10, 12, 'Buying DAP Fertilizer', TO_DATE('2026-06-01', 'YYYY-MM-DD'), TO_DATE('2026-06-03', 'YYYY-MM-DD'), TO_DATE('2026-06-05', 'YYYY-MM-DD'), 'ACTIVE', 1004);

INSERT INTO LOAN (loan_no, farmer_code, center_code, bank_code, amount, interest_rate, tenure_months, purpose, application_date, approval_date, disbursement_date, loan_state, approved_by)
VALUES ('LN-102', 'FR-001', 'C-001', 'BK-001', 30000, 10, 12, 'Buying a Power Tiller', TO_DATE('2026-04-01', 'YYYY-MM-DD'), TO_DATE('2026-04-02', 'YYYY-MM-DD'), TO_DATE('2026-04-03', 'YYYY-MM-DD'), 'ACTIVE', 1004);

INSERT INTO LOAN (loan_no, farmer_code, center_code, bank_code, amount, interest_rate, tenure_months, purpose, application_date, approval_date, disbursement_date, loan_state, approved_by)
VALUES ('LN-103', 'FR-001', 'C-001', 'BK-001', 20000, 10, 6, 'Buying Seeds', TO_DATE('2026-03-01', 'YYYY-MM-DD'), TO_DATE('2026-03-02', 'YYYY-MM-DD'), TO_DATE('2026-03-03', 'YYYY-MM-DD'), 'CLOSED', 1004);


-- 3. REPAYMENT DATA (For her Repayments page)
INSERT INTO REPAYMENT (loan_no, installment_no, amount_paid, payment_date, payment_method, late_fee, payment_state, collected_by, notes)
VALUES ('LN-101', 1, 5000, TO_DATE('2026-07-01', 'YYYY-MM-DD'), 'CASH', 0, 'PAID', 'AG-001', 'First installment paid.');

INSERT INTO REPAYMENT (loan_no, installment_no, amount_paid, payment_date, payment_method, late_fee, payment_state, collected_by, notes)
VALUES ('LN-101', 2, 5000, TO_DATE('2026-08-01', 'YYYY-MM-DD'), 'MOBILE_BANKING', 0, 'PAID', 'AG-001', 'Second installment paid.');

INSERT INTO REPAYMENT (loan_no, installment_no, amount_paid, payment_date, payment_method, late_fee, payment_state, collected_by, notes)
VALUES ('LN-102', 1, 3000, TO_DATE('2026-05-01', 'YYYY-MM-DD'), 'CASH', 0, 'PAID', 'AG-001', 'First installment paid.');

INSERT INTO REPAYMENT (loan_no, installment_no, amount_paid, payment_date, payment_method, late_fee, payment_state, collected_by, notes)
VALUES ('LN-103', 1, 20000, TO_DATE('2026-06-01', 'YYYY-MM-DD'), 'CASH', 0, 'PAID', 'AG-001', 'Loan fully paid.');


-- 4. CONSULTATION DATA (For her Consultations page using ATTENDS table)
INSERT INTO CONSULTATION (session_id, topic)
VALUES ('CS-101', 'Fertilizer application advice');

INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, actual_date, resolution_status, notes)
VALUES (1004, 'FR-001', 'CS-101', TO_DATE('2026-08-20', 'YYYY-MM-DD'), TO_DATE('2026-08-20', 'YYYY-MM-DD'), 'RESOLVED', 'Advised to use DAP at 40kg per bigha.');

INSERT INTO CONSULTATION (session_id, topic)
VALUES ('CS-102', 'Crop rotation planning');

INSERT INTO ATTENDS (advisor_id, farmer_code, session_id, scheduled_date, actual_date, resolution_status, notes)
VALUES (1004, 'FR-001', 'CS-102', TO_DATE('2026-09-05', 'YYYY-MM-DD'), NULL, 'PENDING', 'Farmer wants to plan for next season.');

COMMIT;