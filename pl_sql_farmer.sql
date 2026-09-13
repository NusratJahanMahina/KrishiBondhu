create or replace procedure update_credit_scores is
   cursor c_farmers is
   select farmer_code
     from farmer
    where account_status = 'ACTIVE';

   v_farmer_code farmer.farmer_code%type;
   v_repayments  number;
   v_referrals   number;
   v_overdue     number;
   v_score       number;
   v_earned      number;
   v_penalty     number;
begin
   dbms_output.put_line('=== Starting Credit Score Update ===');
   open c_farmers;
   loop
      fetch c_farmers into v_farmer_code;
      exit when c_farmers%notfound;
        
        -- Count activities (no likes)
      select nvl(
         (
            select count(*)
              from activity_record
             where farmer_code = v_farmer_code
               and activity_type = 'REPAYMENT'
         ),
         0
      ),
             nvl(
                (
                   select count(*)
                     from activity_record
                    where farmer_code = v_farmer_code
                      and activity_type = 'REFERRAL'
                ),
                0
             ),
             nvl(
                (
                   select count(*)
                     from repayment r
                     join loan l
                   on r.loan_no = l.loan_no
                    where l.farmer_code = v_farmer_code
                      and r.payment_state = 'OVERDUE'
                ),
                0
             )
        into
         v_repayments,
         v_referrals,
         v_overdue
        from dual;
        
        -- Calculate earned and penalty points
      v_earned := least(
         v_repayments * 10,
         50
      ) + least(
         v_referrals * 10,
         20
      );
      v_penalty := least(
         v_overdue * 5,
         20
      );
        
        -- Final score (clamped between 1 and 100)
      v_score := greatest(
         1,
         least(
            100,
            20 + v_earned - v_penalty
         )
      );
        
        -- Update or Insert
      merge into credit_score cs
      using (
         select v_farmer_code as farmer_code
           from dual
      ) src on ( cs.farmer_code = src.farmer_code )
      when matched then update
      set cs.score = v_score,
          cs.last_update = sysdate
      when not matched then
      insert (
         farmer_code,
         score,
         last_update )
      values
         ( v_farmer_code,
           v_score,
           sysdate );

      dbms_output.put_line('Farmer: '
                           || v_farmer_code
                           || ' | Repayments: '
                           || v_repayments
                           || ' | Referrals: '
                           || v_referrals
                           || ' | Overdue: '
                           || v_overdue
                           || ' | Score: ' || v_score);
   end loop;

   close c_farmers;
   commit;
   dbms_output.put_line('=== All credit scores updated successfully! ===');
exception
   when others then
      dbms_output.put_line('Error occurred: ' || sqlerrm);
      if c_farmers%isopen then
         close c_farmers;
      end if;
      rollback;
      raise;
end update_credit_scores;
/