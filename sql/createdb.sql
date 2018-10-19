create database coupon_redemption;

create table redemption_code (
    "redeemCode" varchar(20),
    "productRef" varchar(255),
    "firstName" varchar(100),
    "lastName" varchar(100),
    "address1" varchar(255),
    "address2" varchar(255),
    "city" varchar(100),
    "state" varchar(2),
    "postalCode" varchar(10),
    "country" varchar(100),
    "phone" varchar(16),
    "email" varchar(255),
    "tracking" varchar(100),
    "created" timestamp default CURRENT_TIMESTAMP,
    "updated" timestamp default CURRENT_TIMESTAMP,
    primary key ("redeemCode")
);

create user coupon_redemption_admin with password '<PASSWORD HERE>'';

grant select, insert, update, delete on table redemption_code to coupon_redemption_admin;
