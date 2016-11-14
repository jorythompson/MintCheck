import dominate.tags as tags
from dominate.util import raw
from emailSender import EmailSender
from dateutil.relativedelta import relativedelta
import locale
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
                            account_name = str(account_name)
                            if account_name in user.active_accounts or "all" in user.active_accounts:
                                if account_name in handled_accounts:
                                    continue
                                handled_accounts.append(account_name)
                                mint_account = self.accounts.get_account(account_name)
                                user_accounts[user] = mint_account
                                account_type = str(mint_account["accountType"]).lower()
                                account_message = "This"
                                if "bank" in account_type:
                                    fg_color = self.config.account_type_bank_fg
                                    bg_color = self.config.account_type_bank_bg
                                    account_message += " is a bank account"
                                elif "credit" in account_type:
                                    account_message += " credit card"
                                    due_now = mint_account["dueDate"]
                                    next_payment_amount = mint_account["dueAmt"]
                                    trigger_date = now + datetime.timedelta(days=-self.config.past_due_days_before)
                                    if due_now is not None and due_now <= trigger_date and next_payment_amount > 0:
                                        fg_color = self.config.past_due_fg_color
                                        bg_color = self.config.past_due_bg_color
                                    else:
                                        fg_color = self.config.account_type_credit_fg
                                        bg_color = self.config.account_type_credit_bg
                                    next_payment_date = mint_account["dueDate"]
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
                                    account_message += account_type.strip()
                                if not fis_title_saved:
                                    try:
                                        f = user.rename_institutions[fi]
                                    except KeyError:
                                        f = fi
                                    tags.h1(f, style="color:" + fg_color + ";" + "background-color:" + bg_color
                                                     + ";text-align:center")
                                    fis_title_saved = True
                                try:
                                    acc = user.rename_accounts[account_name]
                                except KeyError:
                                    acc = account_name
                                transactions, total = self.transactions.get_transactions(fi, account_name, start_date)
                                tags.h2(acc + " has a balance of " +
                                        locale.currency(mint_account["value"], grouping=True) +
                                        ".  Total transactions for this report is " +
                                        locale.currency(total, grouping=True) + ".",
                                        style="color:" + fg_color + ";" + "background-color:" + bg_color)
                                with tags.table(rules="cols", frame="box"):
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
                                                if word in transaction["merchant"] \
                                                        or word in transaction["mmerchant"] \
                                                        or word in transaction["omerchant"]:
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
                                                            style="text-align:right")
                                                else:
                                                    tags.td(locale.currency(amount, grouping=True),
                                                            style="text-align:right")
                                                    tags.td("")
                fees_html = ""
                if len(bad_transactions) > 0:
                    self.logger.debug("assembling bad transactions")
                    fees_html = tags.html()
                    with fees_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("Flagged Transactions", align="center")
                        with tags.table(rules="cols", frame="box"):
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
                        if account_name == "all" or account_name == account["name"] and account not in accounts:
                            accounts.append(account)
                accounts_html = ""
                if len(accounts) > 0:
                    accounts_html = tags.html()
                    with accounts_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("Current Balances in Accounts", align="center")
                        raw_html = 'Colors are as follows:<font color="' + self.config.account_type_credit_fg\
                                   + '">Credit cards</font>, '\
                                   + '<font color="' + self.config.account_type_bank_fg\
                                   + '">Bank Accounts</font>'
                        tags.div(raw(raw_html))
                        with tags.table(rules="cols", frame="box"):
                            with tags.thead(style=BORDER_STYLE):
                                tags.th("Financial Institution")
                                tags.th("Account")
                                tags.th("Notes")
                                tags.th("Amount")
                                tags.tr(style=BORDER_STYLE)
                            total = 0
                            handled_accounts = []
                            for account in accounts:
                                if account["currentBalance"] > 0 \
                                        and not account["isClosed"] \
                                        and not account["name"] in handled_accounts:
                                    handled_accounts.append(account["name"])
                                    color_style = ""
                                    account_type = account["accountType"].lower()
                                    if "bank" in account_type:
                                        color_style = ";color:" + self.config.account_type_bank_fg + ";" + "background-color:" + bg_color
                                    if "credit" in account_type:
                                        color_style = ";color:" + self.config.account_type_credit_fg \
                                                      + ";" + "background-color:" + bg_color
                                    with tags.tbody():
                                        with tags.tr(style=BORDER_STYLE + color_style):
                                            tags.td(account["fiName"])
                                            tags.td(account["name"])
                                            notes = ""
                                            if account["accountType"] == "credit":
                                                next_payment_amount = account["currentBalance"]
                                                next_payment_date = account["dueDate"]
                                                if next_payment_amount is not None and next_payment_date is not None:
                                                    notes = locale.currency(next_payment_amount, grouping=True) + " due " +\
                                                            next_payment_date.strftime("%a, %b %d")
                                                elif next_payment_amount is not None and next_payment_amount > 0:
                                                    notes = locale.currency(next_payment_amount, grouping=True) + \
                                                            " is due in the near future"
                                                elif next_payment_date is not None and next_payment_amount > 0:
                                                    notes = "payment due " + next_payment_date.strftime("%a, %b %d")
                                            tags.td(notes)
                                            tags.td(locale.currency(account["currentBalance"], grouping=True))
                                            total += account["value"]
                            with tags.tr(style=BORDER_STYLE + color_style):
                                tags.td("Total")
                                tags.td("")
                                tags.td("")
                                tags.td(locale.currency(total, grouping=True))
                    message = ""
                if len(bad_transactions) > 0:
                    message = str(fees_html)
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
                        # tags.h1("this is some text", style="color:red").h1("more text", style="color:green")
                        # .add("font color=" + BANK_COLOR).add("Banks are this color")\
                        # .add(fg_color=CREDIT_CARD_COLOR).add("Credit Cards are this color")
                message = str(report_period_html) + message
                with open("mailing.html", "w") as out_html:
                    out_html.write(message)
                email_sender = EmailSender(self.config.email_connection, self.logger)
                for email in user.email:
                    self.logger.debug("Sending email to " + email)
                    if self.config.debug_copy_admin:
                        cc = self.config.general_admin_email
                    else:
                        cc = None
                    email_sender.send(email, user.subject, message, cc)
