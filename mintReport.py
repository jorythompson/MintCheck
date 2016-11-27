import dominate.tags as tags
from dominate.util import raw
from emailSender import EmailSender
from dateutil.relativedelta import relativedelta
import locale
import operator
import datetime

BORDER_STYLE = "border-bottom:1px solid black"


class PrettyPrint:
    def __init__(self, accounts, transactions, config, start_date, now, logger):
        self.config = config
        self.accounts = accounts
        self.transactions = transactions
        self.start_date = start_date
        self.now = now
        self.doc = None
        self.logger = logger

# TODO
# fees are not being colored
    def send_data(self, frequency):
        self.logger.debug("starting send_data")
        user_accounts = {}
        now = datetime.datetime.now()
        for user in self.config.users:
            handled_accounts = []
            if user.name not in self.config.general_users and "all" not in self.config.general_users:
                continue
            self.logger.debug("handling user:" + user.name)
            start_date = None
            report_frequency = None
            if "monthly" in user.frequency and "monthly" in frequency:
                start_date = self.start_date
                report_frequency = "monthly"
            elif "weekly" in user.frequency and "weekly" in frequency:
                start_date = self.now + relativedelta(days=-8)
                report_frequency = "weekly"
            elif "daily" in user.frequency and "daily" in frequency:
                start_date = self.now + relativedelta(days=-2)
                report_frequency = "daily"
            balance_warnings = []
            for account in self.accounts.accounts:
                if "two" in account["name"].lower():
                    print account["name"]
                if (self.config.mint_ignore_accounts not in account["name"]) and (\
                                account["name"] in user.active_accounts or \
                                        "all" in user.active_accounts and not account["isClosed"]):
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
                bad_transactions = []
                transactions = []
                activity_html = tags.html()
                with activity_html.add(tags.body()).add(tags.div(id='content')):
                    fis = self.transactions.get_financial_institutions(start_date)
                    fis_title_saved = False
                    for fi in fis:
                        account_names = self.transactions.get_accounts(fi, start_date)
                        for account_name in account_names:
                            if self.config.mint_ignore_accounts not in account_name and \
                                    (account_name in user.active_accounts or "all" in user.active_accounts):
                                if account_name in handled_accounts:
                                    continue
                                handled_accounts.append(account_name)
                                mint_account = self.accounts.get_account(account_name)
                                user_accounts[user] = mint_account
                                account_message = "This"
                                if mint_account["accountType"] == "bank":
                                    fg_color = self.config.account_type_bank_fg
                                    bg_color = self.config.account_type_bank_bg
                                    account_message += " is a bank account"
                                elif mint_account["accountType"] == "credit":
                                    account_message += " credit card"
                                    next_payment_date = self.config.get_next_payment_date(account_name, mint_account["dueDate"])
                                    next_payment_amount = mint_account["dueAmt"]
                                    trigger_date = now + datetime.timedelta(days=-self.config.past_due_days_before)
                                    if next_payment_date is not None and next_payment_date <= trigger_date\
                                            and next_payment_amount > 0:
                                        fg_color = self.config.past_due_fg_color
                                        bg_color = self.config.past_due_bg_color
                                    else:
                                        fg_color = self.config.account_type_credit_fg
                                        bg_color = self.config.account_type_credit_bg
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
                                                                  locale.currency(next_payment_amount, grouping=True) +\
                                                                  " due"
                                    account_message += next_payment_amount + " and is due on" + next_payment_date
                                else:
                                    account_message += mint_account["accountType"].strip()
                                if not fis_title_saved:
                                    try:
                                        f = user.rename_institutions[fi]
                                    except KeyError:
                                        f = fi
                                    tags.h1(f, style="color:" + fg_color + ";" + "background-color:" + bg_color
                                                     + ";text-align:center")
                                    fis_title_saved = True
                                try:
                                    renamed_account = user.rename_accounts[account_name]
                                except KeyError:
                                    renamed_account = account_name
                                transactions, total = self.transactions.get_transactions(fi, account_name, start_date)
                                tags.h2(renamed_account + " has a balance of " +
                                        locale.currency(mint_account["value"], grouping=True) +
                                        ".  Total transactions for this report is " +
                                        locale.currency(total, grouping=True) + ".",
                                        style="color:" + fg_color + ";" + "background-color:" + bg_color)
                                with tags.table(rules="cols", frame="box", align="center"):
                                    with tags.thead(style=BORDER_STYLE):
                                        tags.th("Date")
                                        tags.th("Merchant")
                                        tags.th("Amount", colspan="2")
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
                                                    bad_transactions.append([transaction, fg_color, bg_color])
                                                    break
                                            else:
                                                continue
                                            break
                                        with tags.tbody():
                                            with tags.tr(style="color:" + fg_color +
                                                    ";" + "background-color:" + bg_color):
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
                balance_warnings_html = ""
                if len(balance_warnings) > 0:
                    self.logger.debug("assembling balance warnings")
                    balance_warnings_html = tags.html()
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
                                    color_style = ";color:" + self.config.account_type_bank_fg + ";" + \
                                                  "background-color:" + bg_color
                                elif warning[0]["accountType"] == "credit":
                                    color_style = ";color:" + self.config.account_type_credit_fg \
                                                  + ";" + "background-color:" + bg_color
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

                fees_html = ""
                if len(bad_transactions) > 0:
                    self.logger.debug("assembling bad transactions")
                    fees_html = tags.html()
                    with fees_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("Flagged Transactions", align="center")
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
                accounts = []
                self.logger.debug("assembling account lists")
                for account in self.accounts.accounts:
                    for account_name in user.account_totals:
                        if (account_name == "all" or account_name == account["name"]) \
                                and self.config.mint_ignore_accounts not in account["name"] \
                                and account not in accounts:
                            accounts.append(account)
                accounts_html = ""
                debit_accounts = {}
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
                                        color_style = ";color:" + self.config.account_type_bank_fg + ";" +\
                                                      "background-color:" + bg_color
                                    elif account["accountType"] == "credit":
                                        color_style = ";color:" + self.config.account_type_credit_fg \
                                                      + ";" + "background-color:" + bg_color
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
                                                for paid_from in self.config.paid_from:
                                                    if paid_from["credit account"] == account["name"]:
                                                        debit_account = paid_from["debit account"]
                                                        debit_amount = locale.currency(paid_from["balance"],
                                                                                       grouping=True)
                                                        if next_payment_date is not None:
                                                            try:
                                                                debit_accounts[next_payment_date][paid_from["debit account"]] += account["currentBalance"]
                                                            except:
                                                                try:
                                                                    debit_accounts[next_payment_date][paid_from["debit account"]] = account["currentBalance"]
                                                                except:
                                                                    debit_accounts[next_payment_date] = {}
                                                                    debit_accounts[next_payment_date][paid_from["debit account"]] = account["currentBalance"]
                                                        break
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
                                tags.td("")
                                tags.td(locale.currency(total, grouping=True))
                    message = ""

                debit_accounts_html = ""
                if len(debit_accounts) > 0:
                    sorted_debit_accounts = sorted(debit_accounts.items(), key=operator.itemgetter(0))
                    self.logger.debug("Assembling debit account list")
                    debit_accounts_html = tags.html()
                    with debit_accounts_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("Required Balances in Debit Accounts", align="center")
                        with tags.table(rules="cols", frame="box", align="center"):
                            with tags.thead(style=BORDER_STYLE):
                                tags.th("Due")
                                tags.th("Account")
                                tags.th("Amount")
                                tags.tr(style=BORDER_STYLE)
                            for debit_account in sorted_debit_accounts:
                                with tags.tr(style=BORDER_STYLE + color_style):
                                    tags.td(debit_account[0].strftime("%a, %b %d"))
                                    for key in debit_accounts[debit_account[0]]:
                                        tags.td(key)
                                        tags.td(locale.currency(debit_accounts[debit_account[0]][key], grouping=True),
                                                align="right")

                if len(debit_accounts) > 0:
                    message += str(debit_accounts_html)
                if len(balance_warnings) > 0:
                    message += str(balance_warnings_html)
                if len(bad_transactions) > 0:
                    message += str(fees_html)
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
                    tags.h4("This " + report_frequency + " report was prepared for " + user.name + " starting on " + \
                            start_date.strftime('%m/%d/%y'))
                    raw_html = 'Colors are as follows:<br>Account Types:<font color="' + self.config.account_type_credit_fg\
                                + '">Credit cards</font>, '\
                                + '<font color="' + self.config.account_type_bank_fg\
                                + '">Bank Accounts</font>'
                    raw_html += "<br>Keywords: "
                    for color in self.config.color_tags:
                        for keyword in self.config.color_tags[color]:
                            raw_html += '<font color = "' + color + '" >' + keyword + ', </font>'
                    tags.div(raw(raw_html))
                        # tags.h1("this is some text", style="color:red").h1("more text", style="color:green")
                        # .add("font color=" + BANK_COLOR).add("Banks are this color")\
                        # .add(fg_color=CREDIT_CARD_COLOR).add("Credit Cards are this color")
                message = str(report_period_html) + message
                if self.config.debug_save_html is not None:
                    self.logger.debug("saving html file to " + self.config.debug_save_html)
                    with open(self.config.debug_save_html, "w") as out_html:
                        out_html.write(message)
                if self.config.debug_send_email:
                    email_sender = EmailSender(self.config.email_connection, self.logger)
                    for email in user.email:
                        self.logger.debug("Sending email to " + email)
                        if self.config.debug_copy_admin:
                            cc = self.config.general_admin_email
                        else:
                            cc = None
                        email_sender.send(email, user.subject, message, cc)
                else:
                    self.logger.debug("Not sending emails")