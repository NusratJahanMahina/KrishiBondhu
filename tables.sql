---------------------------------------------------------------------------------------------------17-8

   SET DEFINE OFF;

drop table post_like cascade constraints;
drop table community_post cascade constraints;
drop table ordered_item cascade constraints;
drop table purchase cascade constraints;
drop table loan_service cascade constraints;
drop table repayment cascade constraints;
drop table loan cascade constraints;
drop table kyc cascade constraints;
drop table farmer cascade constraints;
drop table field_agent cascade constraints;
drop table bank cascade constraints;
drop table ifarmer_center cascade constraints;
drop table phone cascade constraints;
drop table person cascade constraints;
drop table inventory cascade constraints;

drop sequence person_seq;
drop sequence farmer_seq;
drop sequence kyc_seq;
drop sequence loan_seq;
drop sequence purchase_seq;
drop sequence service_seq;
drop sequence repayment_seq;

create sequence person_seq start with 2000;
create sequence farmer_seq start with 1000;
create sequence kyc_seq start with 1000;
create sequence loan_seq start with 5000;
create sequence purchase_seq start with 10000;
create sequence service_seq start with 1000;
create sequence repayment_seq start with 1000;

create table person (
   person_id   number primary key,
   first_name  varchar2(50) not null,
   last_name   varchar2(50) not null,
   login_phone varchar2(15) unique not null,
   nid         varchar2(20) unique,
   gender      varchar2(10) check ( gender in ( 'Male',
                                           'Female',
                                           'Other' ) ),
   username    varchar2(50) unique not null,
   password    varchar2(100) not null,
   role        varchar2(20) not null check ( role in ( 'FARMER',
                                                'AGENT',
                                                'ADMIN',
                                                'ADVISOR' ) ),
   village     varchar2(50),
   upazila     varchar2(50),
   district    varchar2(50),
   created_at  date default sysdate,
   last_login  date
);

create table phone (
   person_id    number not null,
   phone_number varchar2(15) not null,
   phone_type   varchar2(20) default 'PERSONAL' check ( phone_type in ( 'PERSONAL',
                                                                      'FAMILY',
                                                                      'BUSINESS',
                                                                      'NOMINEE',
                                                                      'EMERGENCY' ) ),
   is_primary   varchar2(3) default 'NO' check ( is_primary in ( 'YES',
                                                               'NO' ) ),
   constraint pk_phone primary key ( person_id,
                                     phone_number ),
   constraint fk_phone_person foreign key ( person_id )
      references person ( person_id )
         on delete cascade
);

create table ifarmer_center (
   center_code  varchar2(20) primary key,
   center_name  varchar2(100) not null unique,
   district     varchar2(50),
   upazila      varchar2(50),
   phone        varchar2(15),
   opening_date date default sysdate,
   center_state varchar2(20) default 'ACTIVE' check ( center_state in ( 'ACTIVE',
                                                                        'INACTIVE' ) ),
   manager_code number,
   constraint fk_center_manager foreign key ( manager_code )
      references person ( person_id )
);

create table bank (
   bank_code      varchar2(20) primary key,
   bank_name      varchar2(100) not null unique,
   branch_name    varchar2(50),
   address        varchar2(255),
   contact_person varchar2(50),
   phone          varchar2(15),
   email          varchar2(100),
   agreement_date date default sysdate,
   max_loan_limit number default 200000,
   bank_state     varchar2(20) default 'ACTIVE' check ( bank_state in ( 'ACTIVE',
                                                                    'INACTIVE' ) )
);

create table field_agent (
   agent_code  varchar2(20) primary key,
   person_id   number unique not null,
   center_code varchar2(20),
   join_date   date default sysdate,
   is_active   varchar2(1) default 'Y' check ( is_active in ( 'Y',
                                                            'N' ) ),
   constraint fk_agent_person foreign key ( person_id )
      references person ( person_id ),
   constraint fk_agent_center foreign key ( center_code )
      references ifarmer_center ( center_code )
);

create table farmer (
   farmer_code       varchar2(20) primary key,
   person_id         number unique not null,
   center_code       varchar2(20),
   agent_code        varchar2(20),
   registration_date date default sysdate,
   account_status    varchar2(20) default 'ACTIVE' check ( account_status in ( 'ACTIVE',
                                                                            'INACTIVE',
                                                                            'SUSPENDED' ) ),
   constraint fk_farmer_person foreign key ( person_id )
      references person ( person_id ),
   constraint fk_farmer_center foreign key ( center_code )
      references ifarmer_center ( center_code ),
   constraint fk_farmer_agent foreign key ( agent_code )
      references field_agent ( agent_code )
);

create table kyc (
   kyc_id            varchar2(20) primary key,
   farmer_code       varchar2(20) not null unique,
   agent_code        varchar2(20) not null,
   nid_front_ref     varchar2(255),
   nid_back_ref      varchar2(255),
   land_dolil_ref    varchar2(255),
   land_legal_status varchar2(50),
   identity_verified varchar2(20) default 'PENDING' check ( identity_verified in ( 'PENDING',
                                                                                   'VERIFIED',
                                                                                   'REJECTED' ) ),
   verified_by       varchar2(20),
   verified_date     date,
   remarks           varchar2(500),
   constraint fk_kyc_farmer foreign key ( farmer_code )
      references farmer ( farmer_code ),
   constraint fk_kyc_agent foreign key ( agent_code )
      references field_agent ( agent_code ),
   constraint fk_kyc_verified_by foreign key ( verified_by )
      references field_agent ( agent_code )
);

create table loan (
   loan_no             varchar2(20) primary key,
   farmer_code         varchar2(20) not null,
   center_code         varchar2(20) not null,
   bank_code           varchar2(20) not null,
   amount              number(12,2) not null check ( amount between 500 and 200000 ),
   interest_rate       number default 10,
   tenure_months       number default 12,
   purpose             varchar2(255),
   application_date    date default sysdate,
   approval_date       date,
   rejection_reason    varchar2(500),
   disbursement_date   date,
   disbursement_method varchar2(50),
   collection_point    varchar2(100),
   release_state       varchar2(20),
   loan_state          varchar2(30) default 'PENDING' check ( loan_state in ( 'PENDING',
                                                                     'ACTIVE',
                                                                     'CLOSED',
                                                                     'DEFAULTED',
                                                                     'REJECTED' ) ),
   approved_by         number,
   constraint fk_loan_farmer foreign key ( farmer_code )
      references farmer ( farmer_code ),
   constraint fk_loan_center foreign key ( center_code )
      references ifarmer_center ( center_code ),
   constraint fk_loan_bank foreign key ( bank_code )
      references bank ( bank_code ),
   constraint fk_loan_approved_by foreign key ( approved_by )
      references person ( person_id )
);

create table repayment (
   loan_no        varchar2(20) not null,
   installment_no number(3) not null,
   amount_paid    number(12,2) not null,
   payment_date   date default sysdate,
   payment_method varchar2(20) check ( payment_method in ( 'CASH',
                                                           'MOBILE_BANKING',
                                                           'BANK_TRANSFER',
                                                           'CHEQUE' ) ),
   late_fee       number(10,2) default 0,
   payment_state  varchar2(20) default 'PAID' check ( payment_state in ( 'PAID',
                                                                        'PARTIAL',
                                                                        'OVERDUE' ) ),
   collected_by   varchar2(20),
   notes          varchar2(500),
   constraint pk_repayment primary key ( loan_no,
                                         installment_no ),
   constraint fk_repayment_loan foreign key ( loan_no )
      references loan ( loan_no )
         on delete cascade
);

create table loan_service (
   service_id             varchar2(20) primary key,
   loan_no                varchar2(20) not null,
   agent_code             varchar2(20) not null,
   service_type           varchar2(20) not null check ( service_type in ( 'COLLECTION',
                                                                'EXTENSION_REQUEST',
                                                                'FOLLOW_UP' ) ),
   amount                 number(12,2),
   payment_method         varchar2(20) check ( payment_method in ( 'CASH',
                                                           'MOBILE_BANKING',
                                                           'CHEQUE' ) ),
   extra_months_requested number(2),
   reason                 varchar2(500),
   supporting_doc         varchar2(255),
   service_date           date default sysdate,
   notes                  varchar2(500),
   status                 varchar2(20) default 'PENDING' check ( status in ( 'PENDING',
                                                             'CONFIRMED',
                                                             'APPROVED',
                                                             'REJECTED' ) ),
   admin_remarks          varchar2(500),
   approved_by            varchar2(20),
   approval_date          date,
   constraint fk_service_loan foreign key ( loan_no )
      references loan ( loan_no ),
   constraint fk_service_agent foreign key ( agent_code )
      references field_agent ( agent_code )
);

create table purchase (
   purchase_id           varchar2(20) primary key,
   farmer_code           varchar2(20) not null,
   agent_code            varchar2(20) not null,
   purchase_date         date default sysdate,
   payment_method        varchar2(100),
   payment_status        varchar2(30) default 'PENDING' check ( payment_status in ( 'PENDING',
                                                                             'CONFIRMED',
                                                                             'SHIPPED',
                                                                             'DELIVERED',
                                                                             'CANCELLED' ) ),
   transaction_reference varchar2(50),
   constraint fk_purchase_farmer foreign key ( farmer_code )
      references farmer ( farmer_code ),
   constraint fk_purchase_agent foreign key ( agent_code )
      references field_agent ( agent_code )
);

create table inventory (
   inventory_id varchar2(20) primary key,
   center_code  varchar2(20) not null,
   name         varchar2(100) not null,
   quantity     number default 0,
   unit_price   number(12,2),
   expiry_date  date,
   location     varchar2(100),
   manufacturer varchar2(100),
   managed_by   number,
   constraint fk_inventory_center foreign key ( center_code )
      references ifarmer_center ( center_code ),
   constraint fk_inventory_managed_by foreign key ( managed_by )
      references person ( person_id )
);

create table ordered_item (
   item_id      varchar2(20) primary key,
   purchase_id  varchar2(20) not null,
   inventory_id varchar2(20) not null,
   quantity     number not null,
   unit_price   number(12,2) not null,
   total_cost   number(12,2),
   constraint fk_ordered_item_purchase foreign key ( purchase_id )
      references purchase ( purchase_id ),
   constraint fk_ordered_item_inventory foreign key ( inventory_id )
      references inventory ( inventory_id )
);

create table community_post (
   post_id   varchar2(20) primary key,
   admin_id  number not null,
   content   varchar2(4000) not null,
   post_date date default sysdate,
   image     varchar2(255),
   constraint fk_post_admin foreign key ( admin_id )
      references person ( person_id )
);

create table post_like (
   post_id     varchar2(20) not null,
   farmer_code varchar2(20) not null,
   liked_date  date default sysdate,
   constraint pk_post_like primary key ( post_id,
                                         farmer_code ),
   constraint fk_post_like_post foreign key ( post_id )
      references community_post ( post_id )
         on delete cascade,
   constraint fk_post_like_farmer foreign key ( farmer_code )
      references farmer ( farmer_code )
         on delete cascade
);




   SET DEFINE OFF;

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 1001,
     'Karim',
     'Hossain',
     '01711111111',
     '1234567890',
     'Male',
     'agent_karim',
     'pass123',
     'AGENT',
     'Mirpur DOHS',
     'Mirpur',
     'Dhaka',
     sysdate - 400 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 1002,
     'Rafiq',
     'Mia',
     '01722222222',
     '2345678901',
     'Male',
     'agent_rafiq',
     'pass123',
     'AGENT',
     'Rangpur Sadar',
     'Rangpur Sadar',
     'Rangpur',
     sysdate - 350 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 1003,
     'Hasan',
     'Ali',
     '01733333333',
     '3456789012',
     'Male',
     'agent_hasan',
     'pass123',
     'AGENT',
     'Boalia',
     'Boalia',
     'Rajshahi',
     sysdate - 200 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 1004,
     'Admin',
     'MIST',
     '01799999999',
     '9999999999',
     'Male',
     'admin_mist',
     'pass123',
     'ADMIN',
     'Dhaka',
     'Dhaka',
     'Dhaka',
     sysdate - 500 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 2001,
     'Sabina',
     'Begum',
     '01744444444',
     '4567890123',
     'Female',
     'farmer_sabina',
     'pass123',
     'FARMER',
     'Mirpur-10',
     'Mirpur',
     'Dhaka',
     sysdate - 30 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 2002,
     'Abdul',
     'Karim',
     '01755555555',
     '5678901234',
     'Male',
     'farmer_abdul',
     'pass123',
     'FARMER',
     'Pallabi',
     'Mirpur',
     'Dhaka',
     sysdate - 20 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 2003,
     'Mokhles',
     'Rahman',
     '01766666666',
     '6789012345',
     'Male',
     'farmer_mokhles',
     'pass123',
     'FARMER',
     'Rangpur Sadar',
     'Rangpur Sadar',
     'Rangpur',
     sysdate - 15 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 2004,
     'Rohim',
     'Mia',
     '01777777777',
     '7890123456',
     'Male',
     'farmer_rohim',
     'pass123',
     'FARMER',
     'Kafrul',
     'Mirpur',
     'Dhaka',
     sysdate - 10 );

insert into person (
   person_id,
   first_name,
   last_name,
   login_phone,
   nid,
   gender,
   username,
   password,
   role,
   village,
   upazila,
   district,
   created_at
) values
   ( 2005,
     'Korim',
     'Ali',
     '01788888888',
     '8901234567',
     'Male',
     'farmer_korim',
     'pass123',
     'FARMER',
     'Rangpur Sadar',
     'Rangpur Sadar',
     'Rangpur',
     sysdate - 5 );

insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 1001,
     '01711111111',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 1001,
     '01711111112',
     'NOMINEE',
     'NO' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 1002,
     '01722222222',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 1003,
     '01733333333',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 1004,
     '01799999999',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 2001,
     '01744444444',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 2002,
     '01755555555',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 2003,
     '01766666666',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 2004,
     '01777777777',
     'PERSONAL',
     'YES' );
insert into phone (
   person_id,
   phone_number,
   phone_type,
   is_primary
) values
   ( 2005,
     '01788888888',
     'PERSONAL',
     'YES' );

insert into ifarmer_center (
   center_code,
   center_name,
   district,
   upazila,
   phone,
   opening_date,
   center_state,
   manager_code
) values
   ( 'C-001',
     'Dhaka Main Center',
     'Dhaka',
     'Mirpur',
     '02-9111111',
     sysdate,
     'ACTIVE',
     1004 );

insert into ifarmer_center (
   center_code,
   center_name,
   district,
   upazila,
   phone,
   opening_date,
   center_state,
   manager_code
) values
   ( 'C-002',
     'Rangpur Hub',
     'Rangpur',
     'Rangpur Sadar',
     '0521-61111',
     sysdate,
     'ACTIVE',
     1004 );

insert into ifarmer_center (
   center_code,
   center_name,
   district,
   upazila,
   phone,
   opening_date,
   center_state,
   manager_code
) values
   ( 'C-003',
     'Rajshahi Center',
     'Rajshahi',
     'Boalia',
     '0721-77111',
     sysdate,
     'ACTIVE',
     1004 );

insert into bank (
   bank_code,
   bank_name,
   branch_name,
   address,
   contact_person,
   phone,
   email,
   agreement_date,
   max_loan_limit,
   bank_state
) values
   ( 'BK-001',
     'Islami Bank',
     'Mirpur Branch',
     'Mirpur-10, Dhaka',
     'Mr. Rahman',
     '01700000001',
     'info@islamibank.com',
     sysdate - 100,
     200000,
     'ACTIVE' );

insert into bank (
   bank_code,
   bank_name,
   branch_name,
   address,
   contact_person,
   phone,
   email,
   agreement_date,
   max_loan_limit,
   bank_state
) values
   ( 'BK-002',
     'Sonali Bank',
     'Rangpur Sadar Branch',
     'Rangpur Sadar',
     'Mrs. Sultana',
     '01700000002',
     'info@sonalibank.com',
     sysdate - 80,
     200000,
     'ACTIVE' );

insert into field_agent (
   agent_code,
   person_id,
   center_code,
   join_date,
   is_active
) values
   ( 'AG-001',
     1001,
     'C-001',
     sysdate - 365,
     'Y' );

insert into field_agent (
   agent_code,
   person_id,
   center_code,
   join_date,
   is_active
) values
   ( 'AG-002',
     1002,
     'C-002',
     sysdate - 300,
     'Y' );

insert into field_agent (
   agent_code,
   person_id,
   center_code,
   join_date,
   is_active
) values
   ( 'AG-003',
     1003,
     'C-003',
     sysdate - 200,
     'Y' );

insert into farmer (
   farmer_code,
   person_id,
   center_code,
   agent_code,
   registration_date,
   account_status
) values
   ( 'FR-001',
     2001,
     'C-001',
     'AG-001',
     sysdate - 30,
     'ACTIVE' );

insert into farmer (
   farmer_code,
   person_id,
   center_code,
   agent_code,
   registration_date,
   account_status
) values
   ( 'FR-002',
     2002,
     'C-001',
     'AG-001',
     sysdate - 20,
     'ACTIVE' );

insert into farmer (
   farmer_code,
   person_id,
   center_code,
   agent_code,
   registration_date,
   account_status
) values
   ( 'FR-003',
     2003,
     'C-002',
     'AG-002',
     sysdate - 15,
     'ACTIVE' );

insert into farmer (
   farmer_code,
   person_id,
   center_code,
   agent_code,
   registration_date,
   account_status
) values
   ( 'FR-004',
     2004,
     'C-001',
     'AG-001',
     sysdate - 10,
     'ACTIVE' );

insert into farmer (
   farmer_code,
   person_id,
   center_code,
   agent_code,
   registration_date,
   account_status
) values
   ( 'FR-005',
     2005,
     'C-002',
     'AG-002',
     sysdate - 5,
     'ACTIVE' );

insert into kyc (
   kyc_id,
   farmer_code,
   agent_code,
   nid_front_ref,
   nid_back_ref,
   land_dolil_ref,
   land_legal_status,
   identity_verified,
   verified_by,
   verified_date,
   remarks
) values
   ( 'KYC-001',
     'FR-001',
     'AG-001',
     'nid_front_001.jpg',
     'nid_back_001.jpg',
     'land_doc_001.jpg',
     'VERIFIED',
     'VERIFIED',
     'AG-001',
     sysdate - 25,
     'Verified physically.' );

insert into kyc (
   kyc_id,
   farmer_code,
   agent_code,
   nid_front_ref,
   nid_back_ref,
   land_dolil_ref,
   land_legal_status,
   identity_verified,
   verified_by,
   verified_date,
   remarks
) values
   ( 'KYC-002',
     'FR-002',
     'AG-001',
     'nid_front_002.jpg',
     'nid_back_002.jpg',
     'land_doc_002.jpg',
     'PENDING',
     'PENDING',
     null,
     null,
     null );

insert into kyc (
   kyc_id,
   farmer_code,
   agent_code,
   nid_front_ref,
   nid_back_ref,
   land_dolil_ref,
   land_legal_status,
   identity_verified,
   verified_by,
   verified_date,
   remarks
) values
   ( 'KYC-003',
     'FR-003',
     'AG-002',
     'nid_front_003.jpg',
     'nid_back_003.jpg',
     'land_doc_003.jpg',
     'VERIFIED',
     'VERIFIED',
     'AG-002',
     sysdate - 10,
     'Verified physically.' );

insert into kyc (
   kyc_id,
   farmer_code,
   agent_code,
   nid_front_ref,
   nid_back_ref,
   land_dolil_ref,
   land_legal_status,
   identity_verified,
   verified_by,
   verified_date,
   remarks
) values
   ( 'KYC-004',
     'FR-004',
     'AG-001',
     'nid_front_004.jpg',
     'nid_back_004.jpg',
     'land_doc_004.jpg',
     'PENDING',
     'PENDING',
     null,
     null,
     null );

insert into kyc (
   kyc_id,
   farmer_code,
   agent_code,
   nid_front_ref,
   nid_back_ref,
   land_dolil_ref,
   land_legal_status,
   identity_verified,
   verified_by,
   verified_date,
   remarks
) values
   ( 'KYC-005',
     'FR-005',
     'AG-002',
     'nid_front_005.jpg',
     'nid_back_005.jpg',
     'land_doc_005.jpg',
     'VERIFIED',
     'VERIFIED',
     'AG-002',
     sysdate - 3,
     'Verified physically.' );

insert into loan (
   loan_no,
   farmer_code,
   center_code,
   bank_code,
   amount,
   interest_rate,
   tenure_months,
   purpose,
   application_date,
   approval_date,
   rejection_reason,
   disbursement_date,
   disbursement_method,
   collection_point,
   release_state,
   loan_state,
   approved_by
) values
   ( 'LN-001',
     'FR-001',
     'C-001',
     'BK-001',
     50000,
     10,
     12,
     'Boro Season',
     sysdate - 2,
     null,
     null,
     null,
     null,
     null,
     null,
     'PENDING',
     null );

insert into loan (
   loan_no,
   farmer_code,
   center_code,
   bank_code,
   amount,
   interest_rate,
   tenure_months,
   purpose,
   application_date,
   approval_date,
   rejection_reason,
   disbursement_date,
   disbursement_method,
   collection_point,
   release_state,
   loan_state,
   approved_by
) values
   ( 'LN-002',
     'FR-003',
     'C-002',
     'BK-002',
     30000,
     10,
     12,
     'Vegetable',
     sysdate - 1,
     null,
     null,
     null,
     null,
     null,
     null,
     'PENDING',
     null );

insert into loan (
   loan_no,
   farmer_code,
   center_code,
   bank_code,
   amount,
   interest_rate,
   tenure_months,
   purpose,
   application_date,
   approval_date,
   rejection_reason,
   disbursement_date,
   disbursement_method,
   collection_point,
   release_state,
   loan_state,
   approved_by
) values
   ( 'LN-003',
     'FR-005',
     'C-002',
     'BK-002',
     70000,
     10,
     12,
     'Poultry',
     sysdate - 7,
     sysdate - 3,
     null,
     sysdate - 2,
     'CASH',
     'Center',
     'RELEASED',
     'ACTIVE',
     1004 );

insert into loan (
   loan_no,
   farmer_code,
   center_code,
   bank_code,
   amount,
   interest_rate,
   tenure_months,
   purpose,
   application_date,
   approval_date,
   rejection_reason,
   disbursement_date,
   disbursement_method,
   collection_point,
   release_state,
   loan_state,
   approved_by
) values
   ( 'LN-004',
     'FR-002',
     'C-001',
     'BK-001',
     25000,
     10,
     12,
     'Irrigation',
     sysdate - 4,
     null,
     null,
     null,
     null,
     null,
     null,
     'PENDING',
     null );

insert into loan (
   loan_no,
   farmer_code,
   center_code,
   bank_code,
   amount,
   interest_rate,
   tenure_months,
   purpose,
   application_date,
   approval_date,
   rejection_reason,
   disbursement_date,
   disbursement_method,
   collection_point,
   release_state,
   loan_state,
   approved_by
) values
   ( 'LN-005',
     'FR-001',
     'C-001',
     'BK-001',
     20000,
     10,
     12,
     'Fertilizer',
     sysdate - 30,
     sysdate - 28,
     null,
     sysdate - 27,
     'CASH',
     'Center',
     'RELEASED',
     'CLOSED',
     1004 );

insert into repayment (
   loan_no,
   installment_no,
   amount_paid,
   payment_date,
   payment_method,
   late_fee,
   payment_state,
   collected_by,
   notes
) values
   ( 'LN-003',
     1,
     20000,
     sysdate - 5,
     'CASH',
     0,
     'PAID',
     'AG-002',
     'Payment collected.' );

insert into repayment (
   loan_no,
   installment_no,
   amount_paid,
   payment_date,
   payment_method,
   late_fee,
   payment_state,
   collected_by,
   notes
) values
   ( 'LN-003',
     2,
     15000,
     sysdate - 35,
     'BANK_TRANSFER',
     0,
     'OVERDUE',
     'AG-002',
     'Farmer missed payment.' );

insert into repayment (
   loan_no,
   installment_no,
   amount_paid,
   payment_date,
   payment_method,
   late_fee,
   payment_state,
   collected_by,
   notes
) values
   ( 'LN-005',
     1,
     20000,
     sysdate - 25,
     'CASH',
     0,
     'PAID',
     'AG-001',
     'Loan fully paid.' );

insert into loan_service (
   service_id,
   loan_no,
   agent_code,
   service_type,
   amount,
   payment_method,
   extra_months_requested,
   reason,
   supporting_doc,
   service_date,
   notes,
   status,
   admin_remarks,
   approved_by,
   approval_date
) values
   ( 'SRV-001',
     'LN-003',
     'AG-002',
     'COLLECTION',
     10000,
     'CASH',
     null,
     null,
     null,
     sysdate - 1,
     'Collected from farmer at his home.',
     'PENDING',
     null,
     null,
     null );

insert into loan_service (
   service_id,
   loan_no,
   agent_code,
   service_type,
   amount,
   payment_method,
   extra_months_requested,
   reason,
   supporting_doc,
   service_date,
   notes,
   status,
   admin_remarks,
   approved_by,
   approval_date
) values
   ( 'SRV-002',
     'LN-003',
     'AG-002',
     'EXTENSION_REQUEST',
     null,
     null,
     2,
     'Crop damaged due to heavy rain. Need 2 months extension.',
     null,
     sysdate - 3,
     null,
     'PENDING',
     null,
     null,
     null );

insert into purchase (
   purchase_id,
   farmer_code,
   agent_code,
   purchase_date,
   payment_method,
   payment_status,
   transaction_reference
) values
   ( 'PUR-001',
     'FR-001',
     'AG-001',
     sysdate - 3,
     null,
     'CONFIRMED',
     'TXN-001' );

insert into purchase (
   purchase_id,
   farmer_code,
   agent_code,
   purchase_date,
   payment_method,
   payment_status,
   transaction_reference
) values
   ( 'PUR-002',
     'FR-003',
     'AG-002',
     sysdate - 2,
     null,
     'CONFIRMED',
     'TXN-002' );

insert into purchase (
   purchase_id,
   farmer_code,
   agent_code,
   purchase_date,
   payment_method,
   payment_status,
   transaction_reference
) values
   ( 'PUR-003',
     'FR-002',
     'AG-001',
     sysdate - 1,
     null,
     'PENDING',
     'TXN-003' );

insert into purchase (
   purchase_id,
   farmer_code,
   agent_code,
   purchase_date,
   payment_method,
   payment_status,
   transaction_reference
) values
   ( 'PUR-004',
     'FR-005',
     'AG-002',
     sysdate - 4,
     null,
     'CONFIRMED',
     'TXN-004' );

insert into purchase (
   purchase_id,
   farmer_code,
   agent_code,
   purchase_date,
   payment_method,
   payment_status,
   transaction_reference
) values
   ( 'PUR-005',
     'FR-004',
     'AG-001',
     sysdate - 1,
     null,
     'PENDING',
     'TXN-005' );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-001',
     'C-001',
     'Urea Fertilizer',
     500,
     1200,
     null,
     'Warehouse A',
     'BCIC',
     1004 );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-002',
     'C-001',
     'Hybrid Rice Seed',
     200,
     2500,
     null,
     'Warehouse B',
     'BRRI',
     1004 );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-003',
     'C-002',
     'Pesticide',
     100,
     800,
     null,
     'Shelf 1',
     'Syngenta',
     1004 );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-004',
     'C-001',
     'DAP Fertilizer',
     300,
     1500,
     null,
     'Warehouse A',
     'BCIC',
     1004 );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-005',
     'C-002',
     'Vegetable Seed',
     150,
     1800,
     null,
     'Shelf 2',
     'BADC',
     1004 );

insert into inventory (
   inventory_id,
   center_code,
   name,
   quantity,
   unit_price,
   expiry_date,
   location,
   manufacturer,
   managed_by
) values
   ( 'INV-006',
     'C-001',
     'Pesticide - Confidor',
     0,
     500,
     null,
     'Shelf 3',
     'Bayer',
     1004 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-001',
     'PUR-001',
     'INV-001',
     50,
     1200,
     60000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-002',
     'PUR-001',
     'INV-002',
     20,
     2500,
     50000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-003',
     'PUR-002',
     'INV-003',
     10,
     800,
     8000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-004',
     'PUR-004',
     'INV-003',
     15,
     800,
     12000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-005',
     'PUR-004',
     'INV-005',
     30,
     1800,
     54000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-006',
     'PUR-003',
     'INV-001',
     10,
     1200,
     12000 );

insert into ordered_item (
   item_id,
   purchase_id,
   inventory_id,
   quantity,
   unit_price,
   total_cost
) values
   ( 'PI-007',
     'PUR-005',
     'INV-002',
     5,
     2500,
     12500 );

insert into community_post (
   post_id,
   admin_id,
   content,
   post_date,
   image
) values
   ( 'POST-001',
     1004,
     'Advisory: Use DAP fertilizer at the rate of 50kg per bigha for Boro season.',
     sysdate - 2,
     null );

insert into community_post (
   post_id,
   admin_id,
   content,
   post_date,
   image
) values
   ( 'POST-002',
     1004,
     'Livestock Alert: Watch for foot-and-mouth disease in cattle. Consult your local vet.',
     sysdate - 1,
     null );

insert into post_like (
   post_id,
   farmer_code,
   liked_date
) values
   ( 'POST-001',
     'FR-001',
     sysdate - 1 );

insert into post_like (
   post_id,
   farmer_code,
   liked_date
) values
   ( 'POST-001',
     'FR-003',
     sysdate - 1 );

insert into post_like (
   post_id,
   farmer_code,
   liked_date
) values
   ( 'POST-002',
     'FR-005',
     sysdate - 1 );

commit;