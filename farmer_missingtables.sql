-- Create the missing tables for the Farmer Dashboard
create table asset (
   asset_id                 varchar2(20) primary key,
   farmer_code              varchar2(20) not null,
   asset_type               varchar2(50),
   asset_name               varchar2(100),
   quantity                 number,
   unit                     varchar2(20),
   acquisition_date         date,
   expected_completion_date date,
   revenue_generated        number(12,2),
   total_expense            number(12,2),
   asset_status             varchar2(20) default 'ACTIVE',
   constraint fk_asset_farmer foreign key ( farmer_code )
      references farmer ( farmer_code )
);

create table consultation (
   session_id        varchar2(20) primary key,
   farmer_code       varchar2(20) not null,
   advisor_id        number not null,
   topic             varchar2(255),
   scheduled_date    date,
   actual_date       date,
   resolution_status varchar2(20) default 'PENDING',
   notes             varchar2(500),
   constraint fk_cons_farmer foreign key ( farmer_code )
      references farmer ( farmer_code ),
   constraint fk_cons_advisor foreign key ( advisor_id )
      references person ( person_id )
);

create table credit_score (
   farmer_code varchar2(20) primary key,
   score       number default 0,
   last_update date default sysdate,
   constraint fk_score_farmer foreign key ( farmer_code )
      references farmer ( farmer_code )
);

create table notification (
   notif_id    varchar2(20) primary key,
   farmer_code varchar2(20) not null,
   message     varchar2(500),
   created_at  date default sysdate,
   is_read     varchar2(3) default 'NO',
   constraint fk_notif_farmer foreign key ( farmer_code )
      references farmer ( farmer_code )
);