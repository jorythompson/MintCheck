# MintChecker Mint Reporting Tool

## About
MintChecker accesses a user's Mint.com account, provides various analysis on the accounts there based on configuration
data in the file.  It then emails the result to one or more accounts.


## Installation
You will probably need to install the following modules (there may be more, depending on how you have currently configured your python environment.

```shell
 pip install -y requests selenium-requests xmltodict dominate python-dateutil gspread oauth2client google-auth-oauthlib
````

## Configuration
The provided sample.ini file must be edited with your own information:

````
[mint connection]
# username is the username to access mint
username: MINT@USERNAME.COM

# password is the password to access mint
password: MY_PASSWORD

# these two cookies are obtained from your browser when accessing mint (will be removed at a later date)
# remove_duplicates indicate duplicate entries should be removed
remove_duplicates: False

# any account name containing this keyword will be ignored.  This is set in Mint by renaming the account and adding this
# keyword
ignore_accounts_containing: duplicate_keyword

# run in headless mode. By default, the specified browser will pop up.  If this is intended to be run autonomously or on a machine with no graphic interface, this should be set to True
headless=True




[debug]
# download indicates the data should be retrieved from mint.  If it doesn't, it will get the data from a previous
# download that stored its values in the pickle_file
mint_download: True

# saves the email as a file (as well as emails it, if set)
save_html: mailing.html

# mint_pickle_file is used to store the massaged collected data to be used if download is False
mint_pickle_file: MintCheck.pickle

# debugging indicates that additional debug (extremely verbose) logging should be turned on.
debugging: False

# sheets_download indicates that google sheets data should be downloaded
sheets_download: True

# copy_admin will copy admin_email (under the [General] section) with all emails
copy_admin: True

# attach_log indicates the log is to be attached to the admin_email in the general section
attach_log: False

# indicates that MintCheck should send emails (default is True)
send_email: True

# Specified the file to save downloaded accounts in:
accounts_pickle_file:Accounts.pickle

# DEBUG:To prevent sheets downloads, uncomment:
# download_sheets:False
# DEBUG:To prevent file downloads, uncomment:
# download_mint:False
# DEBUG:To prevent emails, uncomment:
# send_email:False




[general]
pickle_folder:pickle
html_folder:html
week_start:monday
month_start:1
admin_email:my_email@goes_here.com
users:"all"
# DEBUG:To mail to only me, uncomment the following (overrides looking for users in braces)
users:"Me"
max_sleep:10
exceptions_to:"jorythompson@gmail.com"
google_sheets:"all", "My Sheet"




[google_sheets]
json_file:MintCheck.json
max_day_error:7
paid_color:blueviolet
unpaid_color:crimson




[My Sheet]
# %Y year (2016)
# %B month (December)
sheet_name:Transactions for West New Haven Plaza %Y
amount_col:M
notes_col:L
date_col:K
start_row:9
tab_name:%B
deposit_account:Fu Hwa Checking - 2213




[paid from]
credit card #1:checking account #a
credit card #2:checking account #b




[balance warnings]
credit card #1 >10
checking account #b < 100




[colors]
red:"fee", "charge"
purple:"keyword"




[account_types]
bank_fg_color:green
credit_fg_color:orange




[past_due]
days_before:5
fg_color:green




[locale]
Linux:en_US.utf8
Windows:us_us




[email connection]
username:my_email@google.com
password:password (i.e. Google application password)
from:Mint Checker




[User 1]
email:"user1@host1.com"
subject:All Accounts
active_accounts:"all"
ignore_accounts:
frequency:"daily", "monthly", "weekly", "biweekly"
rename_account:
rename_institution:
#accounts:"all"




[User 2]
email:"user2@host2.com"
subject:only accounts needed by user 2
active_accounts:"account name1", "account name2"
ignore_accounts:
frequency:"monthly", "weekly"
rename_account:
rename_institution:
````