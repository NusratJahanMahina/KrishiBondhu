-- 1. Create the Sequence for auto-incrementing referral IDs
create sequence referral_seq start with 1001 increment by 1 nocache nocycle;

-- 2. Create the Trigger
create or replace trigger trg_farmer_referral_insert before
   insert on farmer_referral
   for each row
declare
   v_kyc_status varchar2(20);
begin
    -- Auto-generate referral_id if NULL
   if :new.referral_id is null then
      :new.referral_id := 'REF-' || referral_seq.nextval;
   end if;
    
    -- Auto-set referral_date if NULL
   if :new.referral_date is null then
      :new.referral_date := sysdate;
   end if;
    
    -- Set status based on referee's KYC status
   begin
      select identity_verified
        into v_kyc_status
        from kyc
       where farmer_code = :new.referee_code;

      if v_kyc_status = 'VERIFIED' then
         :new.status := 'ACCEPTED';
      else
         :new.status := 'PENDING';
      end if;

   exception
      when no_data_found then
         :new.status := 'PENDING';
   end;

exception
   when others then
      dbms_output.put_line('Error in trg_farmer_referral_insert: ' || sqlerrm);
      raise;
end;
/



create or replace trigger trg_update_score_on_repayment after
   insert on repayment
   for each row
declare
   v_farmer_code varchar2(20);
   v_repayments  number;
   v_referrals   number;
   v_overdue     number;
   v_score       number;
   v_earned      number;
   v_penalty     number;
begin
   select farmer_code
     into v_farmer_code
     from loan
    where loan_no = :new.loan_no;

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
   v_score := greatest(
      1,
      least(
         100,
         20 + v_earned - v_penalty
      )
   );

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

exception
   when no_data_found then
      dbms_output.put_line('No loan found for: ' || :new.loan_no);
   when others then
      dbms_output.put_line('Error in trg_update_score_on_repayment: ' || sqlerrm);
end;
/