Transformation|Column|Definition|Data Type|Position|Format|Length|Required|Valid Vales|Notes
Default to '00040' for Consumer Create Tranert records only for Accounts which were charged-off yesterday (chrgoff_dt = batch date). i.e. IF Charge-Off if CHG-OFF-CD = '1' and M-DATE-PAID-OFF = Batch Date|BK-NUM-ERT|A number, defined on the Bank Control Operation tables, which identifies the bank to which the account is to be associated.|Numeric|1.0|9(5)|5.0|Y|Bank Control Table|CTM: BN
Default to '00040' for Consumer Create Tranert records only for Accounts which were charged-off yesterday (chrgoff_dt = batch date). i.e. IF Charge-Off if CHG-OFF-CD = '1' and M-DATE-PAID-OFF = Batch Date|BK-NUM-ERT|A number, defined on the Bank Control Operation tables, which identifies the bank to which the account is to be associated.|Numeric|1.0|9(5)|5.0|Y|Bank Control Table|CTM: BN
Default to '001'|APP-ERT|The application to which the account is to be associated.|Numeric|6.0|9(3)|3.0|Y|Application Control Table|CTM: AP
LN-NUM-ERT = BR + CUS + LN|LN-NUM-ERT|The account number that is associated with the account.|String|9.0||18.0|Y||
Nullable --> Leave Blank|REF-NUM-ERT|The applicable reference number for the transaction.|String|27.0||3.0|N/A||Initialize to spaces
Nullable --> Leave Blank|FILLER|Filler for account key|String|30.0||130.0|N/A||Initialize to spaces
|EFF-DAT-ERT|The date the transaction was effective.|Date|160.0|MM/DD/CCYY|10.0|Y||
Default to '32010'|TRN-COD-ERT|The transaction code for the transaction.|Numeric|170.0|9(5)|5.0|Y|32010.0|
if 1st account in batch then '1'; if 2nd account in batch then '2'; . . . if nth account in batch then 'n';|BAT-ITM-NUM-ERT|The sequential number for this item within the batch.|Numeric|175.0|9(9)|9.0|Y||
Nullable --> Leave Blank|INP-SRC-COD-ERT|The source of the transaction.|Numeric|184.0|9(3)|3.0|N/A||Initialize to spaces
Nullable --> Leave Blank|TRN-CNT-ERT|The total number of transactions in the batch.|Numeric|187.0|9(3)|3.0|N/A||Initialize to spaces
