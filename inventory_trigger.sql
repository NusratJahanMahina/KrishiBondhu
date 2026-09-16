
CREATE SEQUENCE restock_seq
START WITH 5001
INCREMENT BY 1
NOCACHE
NOCYCLE;



CREATE OR REPLACE TRIGGER trg_inventory_restock_flag
AFTER UPDATE OF quantity ON INVENTORY
FOR EACH ROW
DECLARE
    v_already_flagged NUMBER;
BEGIN
    
    IF :NEW.quantity < :NEW.min_stock_level AND :OLD.quantity >= :OLD.min_stock_level THEN
        
      
        SELECT COUNT(*) INTO v_already_flagged
        FROM RESTOCK
        WHERE inventory_id = :NEW.inventory_id
        AND restock_status = 'PENDING';
        
        
        IF v_already_flagged = 0 THEN
            INSERT INTO RESTOCK (
                restock_id,
                inventory_id,
                item_name,
                current_qty,
                min_stock_level,
                shortfall,
                center_code,
                flagged_date,
                restock_status
            ) VALUES (
                'RS-' || restock_seq.NEXTVAL,
                :NEW.inventory_id,
                :NEW.name,
                :NEW.quantity,
                :NEW.min_stock_level,
                :NEW.min_stock_level - :NEW.quantity,
                :NEW.center_code,
                SYSDATE,
                'PENDING'
            );
            
            DBMS_OUTPUT.PUT_LINE('Restock flagged for: ' || :NEW.name);
        END IF;
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Error in trg_inventory_restock_flag: ' || SQLERRM);
END;
/