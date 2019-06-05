import pickle
import dominate.tags as tags
from dominate.util import raw
from emailSender import EmailSender
import locale
from operator import itemgetter
import datetime
from itertools import tee, chain, islice
from mintCheck import MintCheck
from datetime import datetime, date, time
import os
import dateutil
from thompcoutils.log_utils import get_logger, get_log_file_name
import thompcoutils.config_utils as config_utils

BORDER_STYLE = "border-bottom:1px solid black"
CURRENCY_STYLE = "${:,.2f}"


class PrettyPrint:
    def __init__(self, mint, sheets):
        self.config = mint.config
        self.net_worth = mint.net_worth
        self.credit_score = mint.credit_score
        self.accounts = mint.accounts
        self.transactions = mint.mint_transactions
        self.sheets = sheets
        self.now = datetime.combine(date.today(), time())
        self.doc = None
        self.fis = None

    @staticmethod
    def previous_and_next(some_iterable):
        previous_iterable, items, next_iterable = tee(some_iterable, 3)
        previous_iterable = chain([None], previous_iterable)
        next_iterable = chain(islice(next_iterable, 1, None), [None])
        return zip(previous_iterable, items, next_iterable)

    @staticmethod
    def create_debit_accounts(debit_accounts, missing_debit_accounts):
        logger = get_logger()
        balances = False
        debit_accounts_html = tags.html()
        if len(debit_accounts) > 0 or len(missing_debit_accounts) > 0:
            sorted_debit_accounts = sorted(debit_accounts, key=itemgetter('mint next payment date'))
            logger.info("assembling debit account list")
            with debit_accounts_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Required Balances in Debit Accounts Due Soon", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("")
                        tags.th("Debit Account", colspan="2", style=BORDER_STYLE)
                        tags.th("Credit Account", colspan="2", style=BORDER_STYLE)
                        tags.th("")
                        tags.th("")
                        tags.tr(style=BORDER_STYLE)
                        tags.th("Due")
                        tags.th("Account")
                        tags.th("Available")
                        tags.th("institution")
                        tags.th("Account")
                        tags.th("Amount")
                        tags.th("Total Amount")
                        tags.tr(style=BORDER_STYLE)
                    total = 0
                    for previous_iterable, debit_account, next_iterable in \
                            PrettyPrint.previous_and_next(sorted_debit_accounts):
                        with tags.tbody():
                            total += debit_account["mint credit account"]["currentBalance"]
                            account_field = ""
                            balance_field = ""
                            total_field = ""
                            date_field = ""
                            border = None
                            if next_iterable is None or (next_iterable["debit account"] is None or (
                                            next_iterable["debit account"] != debit_account["debit account"]
                                    or next_iterable["mint next payment date"] != debit_account[
                                        "mint next payment date"])):
                                account_field = debit_account["mint paid from account"]
                                balance_field = locale.currency(debit_account["mint paid from amount"], grouping=True)
                                total_field = locale.currency(total, grouping=True)
                                date_field = debit_account["mint next payment date"].strftime("%a, %b %d")
                                total = 0
                                border = BORDER_STYLE
                            tags.td(date_field, align="right", style=border)
                            tags.td(account_field, style=border)
                            tags.td(balance_field, align="right", style=border)
                            tags.td(debit_account["mint credit account"]["fiName"], style=border)
                            tags.td(debit_account["mint credit account"]["accountName"], style=border)
                            tags.td(
                                locale.currency(debit_account["mint credit account"]["currentBalance"], grouping=True),
                                align="right", style=border)
                            tags.td(total_field, align="right", style=border)
                            balances = True
        if not balances:
            with debit_accounts_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Required Balances For This Period", align="center")
        return debit_accounts_html

    def create_activity(self, start_date, user, handled_accounts, user_accounts):
        bad_transactions = []
        activity_html = tags.html()
        activity = False
        fg_color = self.config.account_type_bank_fg
        with activity_html.add(tags.body()).add(tags.div(id='content')):
            tags.h1("Activity By Account", align="center")
            for fi in self.fis:
                fis_title_saved = False
                for account in self.accounts:
                    if fi == account["fiName"] and self.config.mint_ignore_accounts not in account["accountName"] and \
                            (account["accountName"] in user.active_accounts or "all" in user.active_accounts):
                        activity = True
                        if account not in handled_accounts:
                            # handled_accounts.append(account)
                            user_accounts[user] = account["accountName"]
                            account_message = "This"
                            if account["accountType"] == "bank":
                                fg_color = self.config.account_type_bank_fg
                                account_message += " is a bank account"
                            elif account["accountType"] == "credit":
                                fg_color = self.config.account_type_credit_fg
                                account_message += " credit card"
                                next_payment_date = self.config.get_next_payment_date(account["dueDate"])
                                next_payment_amount = account["dueAmt"]
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
                                account_message += account["accountType"].strip()
                            if not fis_title_saved:
                                try:
                                    f = user.rename_institutions[fi]
                                except KeyError:
                                    f = fi
                                tags.h1(f, style="color:" + fg_color
                                                 + ";text-align:center")
                                fis_title_saved = True
                            try:
                                renamed_account = user.rename_accounts[account["accountName"]]
                            except KeyError:
                                renamed_account = account["accountName"]
                            transactions, total = self.transactions.get_transactions(fi, account["accountName"],
                                                                                     start_date)
                            if len(transactions) > 0:
                                tags.h3(renamed_account + " (Account " +
                                        account["yodleeAccountNumberLast4"].replace("...", "") + ") has a balance of " +
                                        locale.currency(account["value"], grouping=True) +
                                        ".  Total transactions for this report is " +
                                        locale.currency(total, grouping=True) + ":",
                                        style="color:" + fg_color, align="center")
                                with tags.table(rules="cols", frame="box", align="center"):
                                    with tags.thead(style=BORDER_STYLE):
                                        tags.th("Date")
                                        tags.th("Merchant")
                                        tags.th("Type")
                                        tags.th("Amount", colspan="2", style=BORDER_STYLE)
                                        with tags.tr(style=BORDER_STYLE):
                                            tags.th("")
                                            tags.th("")
                                            tags.th("")
                                            tags.th("Credit")
                                            tags.th("Debit")
                                    total_credit = 0
                                    total_debit = 0
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
                                                tags.td(transaction["category"])
                                                amount = locale.currency(transaction["amount"], grouping=True)
                                                if transaction["isDebit"]:
                                                    total_debit += transaction["amount"]
                                                    if transaction["amount"] < self.config.min_spend_threshold:
                                                        min_max_color = "color:" + self.config.min_spend_color +\
                                                                        '; font-weight:bold'
                                                    elif transaction["amount"] > self.config.max_spend_threshold:
                                                        min_max_color = "color:" + self.config.max_spend_color  + \
                                                                        '; font-weight:bold'
                                                    else:
                                                        min_max_color = None
                                                    tags.td("")
                                                    tags.td("-" + amount, align="right", style=min_max_color)
                                                else:
                                                    total_credit += transaction["amount"]
                                                    tags.td(amount, align="right")
                                                    tags.td("")
                                    tags.td("")
                                    tags.td("")
                                    tags.td("")
                                    tags.td(locale.currency(total_credit, grouping=True), align="right",
                                            style="border:thin solid black")
                                    tags.td(locale.currency(-total_debit, grouping=True), align="right",
                                            style="border:thin solid black")
        if not activity:
            with activity_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Transactions For This Period", align="center")
        return activity_html, bad_transactions

    def create_balance_warnings(self, balance_warnings, user):
        logger = get_logger()
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
                            # noinspection PyBroadException
                            try:
                                due_date = dateutil.parser.parse(str(warning[0]["dueDate"]))
                            except Exception:
                                due_date = None
                            tags.td(amount, align="right")
                            if due_date is None or due_date == "":
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

    @staticmethod
    def get_fees(bad_transactions, user):
        logger = get_logger()
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
        logger = get_logger()
        accounts = []
        logger.info("assembling account lists")
        for account in self.accounts:
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
                    color_style = ""
                    for account in accounts:
                        if account["currentBalance"] > 0 \
                                and not account["isClosed"] \
                                and not account["name"] in handled_accounts:
                            handled_accounts.append(account["name"])
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
                                        next_payment_date = self.config.get_next_payment_date(account["dueDate"])
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
                                                # noinspection PyBroadException
                                                try:
                                                    debit_amount = locale.currency(paid_from["balance"], grouping=True)
                                                except Exception:
                                                    debit_amount = None
                                                if next_payment_date is not None and next_payment_date >= self.now:
                                                    paid_noted = True
                                                    paid_from["mint paid from account"] = paid_from["debit account"]
                                                    paid_from["mint next payment date"] = next_payment_date
                                                    paid_from["mint credit account"] = account
                                                    paid_from_amount = 0
                                                    for mint_account in accounts:
                                                        if paid_from["debit account"] == mint_account["accountName"]:
                                                            paid_from_amount = mint_account["value"]
                                                            break
                                                    paid_from["mint paid from amount"] = paid_from_amount
                                                    debit_accounts.append(paid_from)
                                                break
                                        if not paid_noted:
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
        logger = get_logger()
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

    @staticmethod
    def get_credit_score(score):
        if score >= 800:
            title = "Exceptional"
            min_value = 800
            max_value = 850
        elif score >= 740:
            title = "Very Good"
            min_value = 740
            max_value = 799
        elif score >= 670:
            title = "Good"
            min_value = 670
            max_value = 739
        elif score >= 580:
            title = "Fair"
            min_value = 580
            max_value = 669
        else:
            title = "Very Poor"
            min_value = 300
            max_value = 579
        return {"title": title, "min": min_value, "max": max_value}

    def create_net_worth_credit_score(self):
        file_name = os.path.join(self.config.general_html_folder,"credit_net_worth.ini")
        history = config_utils.HiLow(file_name)
        credit_history = history.write_value("credit_score", self.credit_score)
        net_worth_history = history.write_value("net_worth", self.net_worth)
        logger = get_logger()
        logger.info("assembling net worth and credit report")
        net_worth_html = tags.html()
        with net_worth_html.add(tags.body()).add(tags.div(id='content')):
            with tags.table(rules="cols", frame="box", align="center"):
                with tags.thead(style=BORDER_STYLE):
                    tags.th("Net Worth", colspan="2", style=BORDER_STYLE)
                    tags.th("Credit Report", colspan="2", style=BORDER_STYLE)
                    with tags.tr(style=BORDER_STYLE):
                        if self.net_worth is None:
                            tags.td("not available")
                        else:
                            tags.td(CURRENCY_STYLE.format(self.net_worth), colspan="2", align="center")
                        if self.credit_score is None:
                            tags.td("not available")
                        else:
                            credit_score = self.get_credit_score(self.credit_score)
                            tags.td("{} {} ({}-{})".format(self.credit_score,
                                                           credit_score["title"], credit_score["min"],
                                                           credit_score["max"]),
                                    align="center", colspan="2")
                    with tags.tr(style=BORDER_STYLE):
                        tags.th("min", style=BORDER_STYLE)
                        tags.th("max", style=BORDER_STYLE)
                        tags.th("min", style=BORDER_STYLE)
                        tags.th("max", style=BORDER_STYLE)
                    with tags.tr(stype=BORDER_STYLE):
                        tags.td(CURRENCY_STYLE.format(net_worth_history[config_utils.HiLow.low_tag]), align="center")
                        tags.td(CURRENCY_STYLE.format(net_worth_history[config_utils.HiLow.hi_tag]), align="center")
                        tags.td(credit_history[config_utils.HiLow.low_tag], align="center")
                        tags.td(credit_history[config_utils.HiLow.hi_tag], align="center")
        return net_worth_html

    def create_deposit_warnings(self, user):
        logger = get_logger()
        sheets = self.sheets.get_missing_deposits(self.transactions, user)
        deposit_warnings_html = tags.html()
        if len(sheets) > 0:
            logger.info("assembling missing deposits")
            with deposit_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h1("Managed Deposits", align="center")
                with tags.table(rules="cols", frame="box", align="center"):
                    with tags.thead(style=BORDER_STYLE):
                        tags.th("Reference")
                        tags.th("Notes")
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
                            tags.td(deposit["notes"])
                            tags.td(deposit["deposit_account"])
                            tags.td(deposit["expected_deposit_date"].strftime("%a, %b %d"))
                            tags.td(actual_deposit_date)
                            tags.td(locale.currency(deposit["deposit_amount"], grouping=True))
        else:
            with deposit_warnings_html.add(tags.body()).add(tags.div(id='content')):
                tags.h5("No Managed Deposits For This Period", align="center")
        return deposit_warnings_html

    def pickle_previous_accounts(self, new_accounts):
        if self.config.previous_accounts_pickle_file is not None:
            with open(self.config.previous_accounts_pickle_file, 'wb') as handle:
                pickle.dump(new_accounts, handle)

    def unpickle_previous_accounts(self):
        previous_accounts = []
        if self.config.previous_accounts_pickle_file is not None and os.path.isfile(
                self.config.previous_accounts_pickle_file):
            with open(self.config.previous_accounts_pickle_file, 'rb') as handle:
                previous_accounts = pickle.load(handle)
        return previous_accounts

    @staticmethod
    def identify_missing_accounts():
        missing_accounts_html = tags.html()
        return missing_accounts_html

    def send_data(self):
        logger = get_logger()
        logger.debug("starting send_data")
        user_accounts = {}
        missing_accounts_html = self.identify_missing_accounts()
        for user in self.config.users:
            handled_accounts = []
            if user.display_credit_report:
                net_worth_credit_score_html = self.create_net_worth_credit_score()
            else:
                net_worth_credit_score_html = None
            deposit_warnings_html = self.create_deposit_warnings(user)
            if user.name not in self.config.general_users and "all" not in self.config.general_users:
                continue
            logger.info("handling user:" + user.name)
            start_date, report_frequency = MintCheck.get_start_date(self.now, self.config.general_week_start,
                                                                    self.config.general_month_start, user.frequency)
            balance_warnings = []
            for account in self.accounts:
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
                self.fis = self.transactions.get_financial_institutions(start_date)
                activity_html, bad_transactions = \
                    self.create_activity(start_date, user, handled_accounts, user_accounts)
                balance_warnings_html = self.create_balance_warnings(balance_warnings, user)
                fees_html = self.get_fees(bad_transactions, user)
                accounts_html, accounts, debit_accounts, missing_debit_accounts = self.get_accounts(user)
                debit_accounts_html = PrettyPrint.create_debit_accounts(debit_accounts, missing_debit_accounts)
                message = ""
                debug_html = self.create_debug_section()
                if debug_html is not None:
                    message += str(debug_html)
                if net_worth_credit_score_html is not None:
                    message += str(net_worth_credit_score_html)
                if missing_accounts_html is not None:
                    message += str(missing_accounts_html)
                if debit_accounts_html is not None:
                    message += str(debit_accounts_html)
                if balance_warnings is not None:
                    message += str(balance_warnings_html)
                if fees_html is not None:
                    message += str(fees_html)
                if deposit_warnings_html is not None:
                    message += str(deposit_warnings_html)
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
                    raw_html = 'Color Key:<br>' \
                               'Account Types: <font color="{}">' \
                               '"Credit cards"</font>, <font color="{}">' \
                               '"Bank Accounts"</font>, <font color="{}">' \
                               '"Verified Deposits"</font>, <font color="{}">' \
                               '"Missing Deposits"</font>'.format(self.config.account_type_credit_fg,
                                                                  self.config.account_type_bank_fg,
                                                                  self.config.sheets_paid_color,
                                                                  self.config.sheets_unpaid_color)
                    raw_html += "<br>Keywords: "
                    last_color = list(self.config.color_tags)[-1]
                    last_keyword = list(self.config.color_tags[last_color])[-1]
                    comma = ","
                    for color in self.config.color_tags:
                        for keyword in self.config.color_tags[color]:
                            if keyword == last_keyword and color == last_color:
                                comma = ""
                            raw_html += '<font color="{}">"{}"</font>{} '.format(color,  keyword, comma)
                    if self.config.general_month_start == 1:
                        indicator = "st"
                    elif self.config.general_month_start == 2:
                        indicator = "nd"
                    elif self.config.general_month_start == 3:
                        indicator = "rd"
                    else:
                        indicator = "th"
                    raw_html += "<br>Month starts on the {}{}, week starts on {}".format(
                        self.config.general_month_start,
                        indicator,
                        self.config.general_week_start.capitalize())
                    tags.div(raw(raw_html))
                message = str(report_period_html) + message
                if self.config.debug_save_html is not None:
                    file_name = os.path.join(self.config.general_html_folder,
                                             user.name + "_" + self.config.debug_save_html)
                    logger.debug("saving html file to {}".format(file_name))
                    with open(file_name, "w") as out_html:
                        out_html.write(message)
                if self.config.debug_send_email:
                    email_sender = EmailSender(self.config.email_connection)
                    for email in user.email:
                        logger.debug("Sending email to {}".format(email))
                        if email.lower() == self.config.general_admin_email.lower() and self.config.debug_attach_log:
                            log_file = get_log_file_name()
                        else:
                            log_file = None
                        email_sender.send(to_email=email, subject=user.subject, message=message, attach_file=log_file)
                else:
                    logger.debug("Not sending emails")
