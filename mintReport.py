import dominate.tags as tags
from dominate.util import raw
from emailSender import EmailSender
from dateutil.relativedelta import relativedelta
import locale
from operator import itemgetter
import datetime
from itertools import tee, chain, izip, islice
from mintCheck import MintCheck
from datetime import datetime, date, time, timedelta
import os
import logging
import inspect
import thompco_utils


BORDER_STYLE = "border-bottom:1px solid black"


class PrettyPrint:
    def __init__(self, accounts, transactions, sheets, config):
        self.config = config
        self.accounts = accounts
        self.transactions = transactions
        self.sheets = sheets
        self.now = datetime.combine(date.today(), time())
        self.doc = None

    @staticmethod
    def previous_and_next(some_iterable):
        previous_iterable, items, next_iterable = tee(some_iterable, 3)
        previous_iterable = chain([None], previous_iterable)
        next_iterable = chain(islice(next_iterable, 1, None), [None])
        return izip(previous_iterable, items, next_iterable)

    @staticmethod
    def multi_key_sort(items, columns):
        comparators = [((itemgetter(col[1:].strip()), -1) if col.startswith('-') else
                      (itemgetter(col.strip()), 1)) for col in columns]

        def comparator(left, right):
            for fn, multiplier in comparators:
                result = cmp(fn(left), fn(right))
                if result:
                    return multiplier * result
            else:
                return 0

        return sorted(items, cmp=comparator)

    def create_debit_accounts(self, debit_accounts, missing_debit_accounts):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        debit_accounts_html = tags.html()
        if len(debit_accounts) > 0 or len(missing_debit_accounts) > 0:
            sorted_debit_accounts = PrettyPrint.multi_key_sort(debit_accounts,
                                                               ["mint next payment date", "mint paid from account"])
            logger.info("assembling debit account list")
            with debit_accounts_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Required Balances in Debit Accounts Due Soon", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Due")
                        tags.th("Financial Institution")
                        tags.th("Debit Account")
                        tags.th("Credit Account")
                        tags.th("Amount")
                        tags.th("Total Amount")
                        tags.tr(style=BORDER_STYLE)
                    total = 0
                    for previous_iterable, debit_account, next_iterable in \
                            PrettyPrint.previous_and_next(sorted_debit_accounts):
                        with tags.tbody():
                            total += debit_account["mint credit account"]["currentBalance"]
                            account_field = ""
                            total_field = ""
                            date_field = ""
                            border = None
                            if next_iterable is None or (next_iterable["debit account"] is None or (
                                            next_iterable["debit account"] != debit_account["debit account"]
                                    or next_iterable["mint next payment date"] != debit_account[
                                        "mint next payment date"])):
                                account_field = debit_account["mint paid from account"]
                                total_field = locale.currency(total, grouping=True)
                                date_field = debit_account["mint next payment date"].strftime("%a, %b %d")
                                total = 0
                                border = BORDER_STYLE
                            tags.td(date_field, align="right", style=border)
                            tags.td( debit_account["mint credit account"]["fiName"], style=border)
                            tags.td(account_field, style=border)
                            tags.td(debit_account["mint credit account"]["accountName"], style=border)
                            tags.td(
                                locale.currency(debit_account["mint credit account"]["currentBalance"], grouping=True),
                                align="right", style=border)
                            tags.td(total_field, align="right", style=border)
        else:
            with debit_accounts_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Required Balances For This Period", align="center")
        return debit_accounts_html

    def create_activity(self, start_date, user, handled_accounts, user_accounts):
        bad_transactions = []
        transactions = []
        activity_html = tags.html()
        activity = False
        with activity_html.add(tags.body()).add(tags.div(id='content')):
            fis = self.transactions.get_financial_institutions(start_date)
            for fi in fis:
                fis_title_saved = False
                account_names = self.transactions.get_accounts(fi, start_date)
                for account_name in account_names:
                    if self.config.mint_ignore_accounts not in account_name and \
                            (account_name in user.active_accounts or "all" in user.active_accounts):
                        activity = True
                        if account_name in handled_accounts:
                            continue
                        handled_accounts.append(account_name)
                        mint_account = self.accounts.get_account(account_name)
                        user_accounts[user] = mint_account
                        account_message = "This"
                        if mint_account["accountType"] == "bank":
                            fg_color = self.config.account_type_bank_fg
                            account_message += " is a bank account"
                        elif mint_account["accountType"] == "credit":
                            fg_color = self.config.account_type_credit_fg
                            account_message += " credit card"
                            next_payment_date = self.config.get_next_payment_date(account_name, mint_account["dueDate"])
                            next_payment_amount = mint_account["dueAmt"]
                            if next_payment_date is None:
                                next_payment_date = " on undetermined date"
                            else:
                                next_payment_date = " is due on " + next_payment_date.strftime("%a, %b %d")
                            if next_payment_amount is None:
                                next_payment_amount = " has an undetermined amount due"
                            else:
                                if next_payment_amount == 0:
                                    next_payment_amount = " has nothing due"
                                else:
                                    next_payment_amount = " has " + \
                                                          locale.currency(next_payment_amount, grouping=True) + \
                                                          " due"
                            account_message += next_payment_amount + " and is due on" + next_payment_date
                        else:
                            account_message += mint_account["accountType"].strip()
                        if not fis_title_saved:
                            try:
                                f = user.rename_institutions[fi]
                            except KeyError:
                                f = fi
                            tags.h1(f, style="color:" + fg_color
                                             + ";text-align:center")
                            fis_title_saved = True
                        try:
                            renamed_account = user.rename_accounts[account_name]
                        except KeyError:
                            renamed_account = account_name
                        transactions, total = self.transactions.get_transactions(fi, account_name, start_date)
                        tags.h3(renamed_account + " has a balance of " +
                                locale.currency(mint_account["value"], grouping=True) +
                                ".  Total transactions for this report is " +
                                locale.currency(total, grouping=True) + ":",
                                style="color:" + fg_color, align="center")
                        with tags.table(rules="cols", frame="box", align="center"):
                            with tags.thead(style=BORDER_STYLE):
                                tags.th("Date")
                                tags.th("Merchant")
                                tags.th("Amount", colspan="2", style=BORDER_STYLE)
                                with tags.tr(style=BORDER_STYLE):
                                    tags.th("")
                                    tags.th("")
                                    tags.th("Credit")
                                    tags.th("Debit")
                            for transaction in transactions:
                                fg_color = "black"
                                for color in self.config.color_tags:
                                    for word in self.config.color_tags[color]:
                                        if word in transaction["merchant"].lower() \
                                                or word in transaction["mmerchant"].lower() \
                                                or word in transaction["omerchant"].lower():
                                            fg_color = color
                                            bad_transactions.append([transaction, fg_color])
                                            break
                                    else:
                                        continue
                                    break
                                with tags.tbody():
                                    with tags.tr(style="color:" + fg_color):
                                        tags.td(transaction["date"].strftime('%b %d'))
                                        tags.td(transaction["omerchant"])
                                        amount = transaction["amount"]
                                        if transaction["isDebit"]:
                                            tags.td("")
                                            tags.td(locale.currency(-amount, grouping=True),
                                                    align="right")
                                        else:
                                            tags.td(locale.currency(amount, grouping=True),
                                                    align="right")
                                            tags.td("")
        if not activity:
            with activity_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Transactions For This Period", align="center")
        return activity_html, transactions, bad_transactions

    def create_balance_warnings(self, balance_warnings, user):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        balance_warnings_html = tags.html()
        if len(balance_warnings) > 0:
            logger.info("assembling balance warnings")
            with balance_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Accounts With Balance Alerts", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Financial Institution")
                        tags.th("Account")
                        tags.th("Amount")
                        tags.th(" ")
                        tags.th("Threshold")
                        tags.th("Due")
                        tags.tr(style=BORDER_STYLE)
                    for warning in balance_warnings:
                        color_style = ""
                        if warning[0]["accountType"] == "bank":
                            color_style = ";color:" + self.config.account_type_bank_fg
                        elif warning[0]["accountType"] == "credit":
                            color_style = ";color:" + self.config.account_type_credit_fg
                        with tags.tr(style=BORDER_STYLE + color_style):
                            try:
                                f = user.rename_institutions[warning[0]["fiName"]]
                            except KeyError:
                                f = warning[0]["fiName"]
                            tags.td(f)
                            try:
                                renamed_account = user.rename_accounts[warning[0]["accountName"]]
                            except KeyError:
                                renamed_account = warning[0]["accountName"]
                            tags.td(renamed_account)
                            value = locale.currency(warning[0]["value"], grouping=True)
                            tags.td(value, align="right")
                            tags.td(warning[1].comparator)
                            amount = locale.currency(warning[1].amount, grouping=True)
                            try:
                                due_date = warning[0]["dueDate"]
                            except:
                                due_date = None
                            tags.td(amount, align="right")
                            if due_date is None:
                                if warning[0]["accountType"] == "credit":
                                    due_date = "unknown"
                                else:
                                    due_date = ""
                            else:
                                due_date = due_date.strftime("%a, %b %d")
                            tags.td(due_date)
        else:
            with balance_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Accounts With Balance Alerts For This Period", align="center")
        return balance_warnings_html

    def get_fees(self, bad_transactions, user):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        fees_html = tags.html()
        if len(bad_transactions) > 0:
            logger.info("assembling bad transactions")
            with fees_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Tagged Transactions", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Date")
                        tags.th("Financial Institution")
                        tags.th("Account")
                        tags.th("Merchant")
                        tags.th("Amount", colspan="2", style=BORDER_STYLE)
                        tags.tr(style=BORDER_STYLE)
                        tags.th("")
                        tags.th("")
                        tags.th("")
                        tags.th("")
                        tags.th("Credit")
                        tags.th("Debit")
                    for transaction in bad_transactions:
                        with tags.tr(style="color:" + transaction[1]):
                            tags.td(transaction[0]["date"].strftime('%b %d'))
                            try:
                                f = user.rename_institutions[transaction[0]["fi"]]
                            except KeyError:
                                f = transaction[0]["fi"]
                            tags.td(f)
                            try:
                                a = user.rename_accounts[transaction[0]["account"]]
                            except KeyError:
                                a = transaction[0]["account"]
                            tags.td(a)
                            tags.td(transaction[0]["omerchant"])
                            if transaction[0]["isDebit"]:
                                tags.td("")
                                amount = locale.currency(-transaction[0]["amount"], grouping=True)
                                tags.td(amount, style="text-align:right")
                            else:
                                amount = locale.currency(transaction[0]["amount"], grouping=True)
                                tags.td(amount, style="text-align:right")
                                tags.td("")
        else:
            with fees_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Flagged Transactions For This Period", align="center")
        return fees_html

    def get_accounts(self, user):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        accounts = []
        logger.info("assembling account lists")
        for account in self.accounts.accounts:
            for account_name in user.active_accounts:
                if (account_name == "all" or account_name == account["name"]) \
                        and self.config.mint_ignore_accounts not in account["name"] \
                        and account not in accounts:
                    accounts.append(account)
        debit_accounts = []
        missing_debit_accounts = []
        if len(accounts) > 0:
            accounts_html = tags.html()
            with accounts_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Current Balances in Accounts", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Financial Institution")
                        tags.th("Account")
                        tags.th("Amount")
                        tags.th("Due")
                        tags.th("Paid From")
                        tags.th("balance")
                        tags.tr(style=BORDER_STYLE)
                    total = 0
                    handled_accounts = []
                    for account in accounts:
                        if account["currentBalance"] > 0 \
                                and not account["isClosed"] \
                                and not account["name"] in handled_accounts:
                            handled_accounts.append(account["name"])
                            color_style = ""
                            if account["accountType"] == "bank":
                                color_style = ";color:" + self.config.account_type_bank_fg
                            elif account["accountType"] == "credit":
                                color_style = ";color:" + self.config.account_type_credit_fg
                            with tags.tbody():
                                with tags.tr(style=BORDER_STYLE + color_style):
                                    tags.td(account["fiName"])
                                    tags.td(account["name"])
                                    tags.td(locale.currency(account["currentBalance"], grouping=True), align="right")
                                    if account["accountType"] == "credit":
                                        next_payment_date = self.config.get_next_payment_date(
                                            account["name"], account["dueDate"])
                                        if next_payment_date is None:
                                            tags.td("N/A", align="center")
                                        else:
                                            tags.td(next_payment_date.strftime("%a, %b %d"))
                                        debit_account = None
                                        debit_amount = None
                                        paid_noted = False
                                        for paid_from in self.config.paid_from:
                                            if paid_from["credit account"] == account["name"]:
                                                debit_account = paid_from["debit account"]
                                                try:
                                                    debit_amount = locale.currency(paid_from["balance"], grouping=True)
                                                except:
                                                    debit_amount = None
                                                if next_payment_date is not None and next_payment_date >= self.now:
                                                    paid_noted = True
                                                    paid_from["mint paid from account"] = paid_from["debit account"]
                                                    paid_from["mint next payment date"] = next_payment_date
                                                    paid_from["mint credit account"] = account
                                                    debit_accounts.append(paid_from)
                                                break
                                        if not paid_noted and account["accountType"] == "credit" \
                                                and next_payment_date is not None and next_payment_date >= self.now:
                                            missing_debit_accounts.append(account)
                                        if debit_account is None:
                                            tags.td("N/A", align="center")
                                        else:
                                            tags.td(debit_account)
                                        if debit_amount is None:
                                            tags.td("N/A", align="center")
                                        else:
                                            tags.td(debit_amount, align="right")
                                    else:
                                        tags.td("")
                                        tags.td("")
                                        tags.td("")
                                    total += account["value"]
                    with tags.tr(style=BORDER_STYLE + color_style):
                        tags.td("Total")
                        tags.td("")
                        tags.td(locale.currency(total, grouping=True))
                        tags.td("")
                        tags.td("")
                        tags.td("")
        else:
            accounts_html = ""
        return accounts_html, accounts, debit_accounts, missing_debit_accounts

    def create_debug_section(self):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        debug_html = None
        if not self.config.debug_send_email or not self.config.debug_mint_download \
                or not self.config.debug_sheets_download:
            debug_html = tags.html()
            logger.info("assembling debug section")
            with debug_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("*** WARNING - DEBUG VALUES SET ***", align="center", style="color:red")
                if not self.config.debug_send_email:
                    tags.h3("Not sending emails", align="center", style="color:red")
                if not self.config.debug_mint_download:
                    tags.h3("Not downloading data from Mint", align="center", style="color:red")
                if not self.config.debug_sheets_download:
                    tags.h3("Not downloading data from Google sheets", align="center", style="color:red")
        return debug_html

    def create_deposit_warnings(self, user):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        sheets = self.sheets.get_missing_deposits(self.transactions, user)
        deposit_warnings_html = tags.html()
        if len(sheets) > 0:
            logger.info("assembling missing deposits")
            with deposit_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Managed Deposits", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Reference")
                        tags.th("Deposit Account")
                        tags.th("Expected Deposit Date")
                        tags.th("Actual Deposit Date")
                        tags.th("Amount", colspan="2", style=BORDER_STYLE)
                    for deposit in sheets:
                        if deposit["actual_deposit_date"] is None:
                            color = self.config.sheets_unpaid_color
                            actual_deposit_date = "NONE"
                        else:
                            color = self.config.sheets_paid_color
                            actual_deposit_date = deposit["actual_deposit_date"].strftime("%a, %b %d")
                        with tags.tr(style="color:" + color):
                            tags.td(deposit["billing_account"])
                            tags.td(deposit["deposit_account"])
                            tags.td(deposit["expected_deposit_date"].strftime("%a, %b %d"))
                            tags.td(actual_deposit_date)
                            tags.td(locale.currency(deposit["deposit_amount"], grouping=True))
        else:
            with deposit_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Managed Deposits For This Period", align="center")
        return deposit_warnings_html

    def send_data(self):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        logger.debug("starting send_data")
        user_accounts = {}
        for user in self.config.users:
            handled_accounts = []
            deposit_warnings_html = self.create_deposit_warnings(user)
            if user.name not in self.config.general_users and "all" not in self.config.general_users:
                continue
            logger.info("handling user:" + user.name)
            start_date, report_frequency = MintCheck.get_start_date(self.now, self.config.general_week_start,
                                                                    self.config.general_month_start, user.frequency)
            balance_warnings = []
            for account in self.accounts.accounts:
                if (self.config.mint_ignore_accounts not in account["name"]) and (
                                account["name"] in user.active_accounts
                        or "all" in user.active_accounts and not account["isClosed"]):
                    logger.debug("Processing account " + account["name"] + " for user:" + user.name)
                    t = None
                    for warning in self.config.balance_warnings:
                        if account["name"] == warning.account_name:
                            t = account, warning
                            break
                    if t is None:
                        if account["accountType"] == "credit":
                            t = account, self.config.balance_warning_credit
                        elif account["accountType"] == "bank":
                            t = account, self.config.balance_warning_bank
                    if t is not None:
                        if t[1].comparator == ">" and abs(account["value"]) > t[1].amount:
                            balance_warnings.append(t)
                        elif t[1].comparator == "<" and abs(account["value"]) < t[1].amount:
                            balance_warnings.append(t)
                        elif t[1].comparator == "=" and abs(account["value"]) == t[1].amount:
                            balance_warnings.append(t)
            if start_date is not None:
                activity_html, transactions, bad_transactions = \
                    self.create_activity(start_date, user, handled_accounts, user_accounts)
                balance_warnings_html = self.create_balance_warnings(balance_warnings, user)
                fees_html = self.get_fees(bad_transactions, user)
                accounts_html, accounts, debit_accounts, missing_debit_accounts = self.get_accounts(user)
                debit_accounts_html = self.create_debit_accounts(debit_accounts, missing_debit_accounts)
                message = ""
                debug_html = self.create_debug_section()
                if debug_html is not None:
                    message += str(debug_html)
                if debit_accounts_html is not None:
                    message += str(debit_accounts_html)
                if balance_warnings is not None:
                    message += str(balance_warnings_html)
                if fees_html is not None:
                    message += str(fees_html)
                if deposit_warnings_html is not None:
                    message += str(deposit_warnings_html)
                if len(transactions) > 0:
                    message += str(activity_html)
                if len(accounts) > 0:
                    message += str(accounts_html)
                if message == "":
                    no_activity_html = tags.html()
                    with no_activity_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("There was no activity for the selected accounts during this period")
                    message = str(no_activity_html)
                report_period_html = tags.html()
                with report_period_html.add(tags.body()).add(tags.div(id='content')):
                    tags.h4("This " + report_frequency + " report was prepared for " + user.name
                            + " on " + datetime.now().strftime("%m/%d/%y at %I:%M:%S %p")
                            + " starting on " + start_date.strftime("%m/%d/%y at %I:%M:%S %p"))
                    raw_html = 'Colors are as follows:<br>' \
                               + 'Account Types:<font color="' + self.config.account_type_credit_fg + '">' \
                               + 'Credit cards</font>, ' + '<font color="' + self.config.account_type_bank_fg + '">' \
                               + 'Bank Accounts</font>, ' + '<font color="' + self.config.sheets_paid_color + '">' \
                               + 'Verified Deposits</font>, ' + '<font color="' + self.config.sheets_unpaid_color + '">' \
                               + 'Missing Deposits</font>'
                    raw_html += "<br>Keywords: "
                    for color in self.config.color_tags:
                        for keyword in self.config.color_tags[color]:
                            raw_html += '<font color = "' + color + '" >' + keyword + ', </font>'
                    tags.div(raw(raw_html))
                message = str(report_period_html) + message
                if self.config.debug_save_html is not None:
                    file_name = os.path.join(self.config.general_html_folder,
                                             user.name + "_" +self.config.debug_save_html)
                    logger.debug("saving html file to " + file_name)
                    with open(file_name, "w") as out_html:
                        out_html.write(message)
                if self.config.debug_send_email:
                    email_sender = EmailSender(self.config.email_connection)
                    for email in user.email:
                        logger.debug("Sending email to " + email)
                        if email.lower() == self.config.general_admin_email.lower() and self.config.debug_attach_log:
                            log_file =thompco_utils.get_log_file_name()
                        else:
                            log_file = None
                        if self.config.debug_copy_admin:
                            cc = self.config.general_admin_email
                        else:
                            cc = None
                        email_sender.send(email, user.subject, message, cc, attach_file=log_file)
                else:
                    logger.debug("Not sending emails")
