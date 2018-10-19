# Coupon Code App

This app is meant to stream line processing coupon codes and tracking information

## Features/Functions

* Admin can import CSV formatted where Column A is the Code and Column B is the Item Reference for available codes
* Admin can download redeemed codes to process for shipping with the status of "PENDING SHIPPING" and will include redeemer's shipping info
* Redeemed Codes that have no Tracking information added to it but has been used in a redemption will be set as status "PENDING SHIPPING"
* Admin can upload redeemed items with tracking info, which will email the user that their order has been processed.
* Admin can download history of orders.
* There will be one public screen for users to redeem their codes and add shipping information

Using Postgress
sudo apt-get install postgresql