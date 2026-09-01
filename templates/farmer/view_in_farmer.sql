create or replace view view_farmer_order_details as
   select pu.purchase_id,
          pu.farmer_code,
          pu.purchase_date,
          pu.payment_method,
          pu.payment_status,
          i.name as item_name,
          oi.quantity,
          oi.total_cost
     from purchase pu
     join ordered_item oi
   on pu.purchase_id = oi.purchase_id
     join inventory i
   on oi.inventory_id = i.inventory_id;