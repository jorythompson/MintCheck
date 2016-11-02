import dominate.tags as tags
from emailSender import EmailSender
from dateutil.relativedelta import relativedelta
import locale

BORDER_STYLE = "border-bottom:1px solid black"
CREDIT_CARD_COLOR = "cyan"
WARNING_COLOR = "red"
BANK_COLOR = "green"


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
                                account_type = str(mint_account["accountType"])
                                account_message = "This"
                                if "bank" in account_type.lower():
                                    account_color = BANK_COLOR
                                    account_message += " is a bank account"
                                elif "credit" in account_type.lower():
                                    account_message += " credit card"
                                    account_color = CREDIT_CARD_COLOR
                                    next_payment_amount = mint_account["dueAmt"]
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
                                    tags.h1(f, style="color:" + account_color)
                                    fis_title_saved = True
                                try:
                                    acc = user.rename_accounts[account_name]
                                except KeyError:
                                    acc = account_name
                                transactions, total = self.transactions.get_transactions(fi, account_name, start_date)
                                tags.h2(acc + " has a balance of " +
                                        locale.currency(mint_account["value"], grouping=True) +
                                        ".  Total transactions for this report is " +
                                        locale.currency(total, grouping=True) + ".", style="color:" + account_color)
                                with tags.table(rules="cols", frame="box"):
                                    with tags.thead():
                                        tags.th("Date")
                                        tags.th("Merchant")
                                        tags.th("Amount", colspan="2", style=BORDER_STYLE)
                                        tags.tr()
                                        tags.th("", style=BORDER_STYLE)
                                        tags.th("", style=BORDER_STYLE)
                                        tags.th("Credit", style=BORDER_STYLE)
                                        tags.th("Debit", style=BORDER_STYLE)
                                    for transaction in transactions:
                                        with tags.tbody():
                                            with tags.tbody():
                                                color = "white"
                                                for warning in self.config.mint_warning_keywords:
                                                    if warning in transaction["merchant"].lower() \
                                                            or warning in transaction["mmerchant"].lower()\
                                                            or warning in transaction["omerchant"].lower():
                                                        bad_transactions.append(transaction)
                                                        color = WARNING_COLOR
                                                        break
                                                tags.td(transaction["date"].strftime('%b %d'), bgcolor=color)
                                                tags.td(transaction["omerchant"], bgcolor=color)
                                                amount = transaction["amount"]
                                                if transaction["isDebit"]:
                                                    tags.td("", bgcolor=color)
                                                    amount = -amount
                                                    tags.td(locale.currency(amount, grouping=True),
                                                            style="text-align:right",
                                                            bgcolor=color)
                                                else:
                                                    tags.td(locale.currency(amount, grouping=True),
                                                            style="text-align:right",
                                                            bgcolor=color)
                                                    tags.td("", bgcolor=color)
                fees_html = ""
                if len(bad_transactions) > 0:
                    self.logger.debug("assembling bad transactions")
                    fees_html = tags.html()
                    with fees_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h3("The following charges should be looked into")
                        tags.h1("Fees and Charges")
                        with tags.table(rules="cols", frame="box"):
                            with tags.thead():
                                tags.th("Date")
                                tags.th("Financial Institution")
                                tags.th("Account")
                                tags.th("Merchant")
                                tags.th("Amount", colspan="2", style=BORDER_STYLE)
                                tags.tr()
                                tags.th("", style=BORDER_STYLE)
                                tags.th("", style=BORDER_STYLE)
                                tags.th("", style=BORDER_STYLE)
                                tags.th("", style=BORDER_STYLE)
                                tags.th("Credit", style=BORDER_STYLE)
                                tags.th("Debit", style=BORDER_STYLE)
                            for transaction in bad_transactions:
                                with tags.tbody():
                                    with tags.tbody():
                                        tags.td(transaction["date"].strftime('%b %d'))
                                        try:
                                            f = user.rename_institutions[transaction["fi"]]
                                        except KeyError:
                                            f = transaction["fi"]
                                        tags.td(f)
                                        try:
                                            a = user.rename_accounts[transaction["account"]]
                                        except KeyError:
                                            a = transaction["account"]
                                        tags.td(a)
                                        tags.td(transaction["omerchant"])
                                        amount = locale.currency(transaction["amount"], grouping=True)
                                        if transaction["isDebit"]:
                                            tags.td("")
                                            tags.td("-" + amount, style="text-align:right")
                                        else:
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
                        tags.h1("Current Balances in Accounts")
                        tags.h2("Credit cards are highlighted", style="color:" + CREDIT_CARD_COLOR)
                        with tags.table(rules="cols", frame="box"):
                            with tags.thead():
                                tags.th("Financial Institution", style=BORDER_STYLE)
                                tags.th("Account", style=BORDER_STYLE)
                                tags.th("Notes", style=BORDER_STYLE)
                                tags.th("Amount", style=BORDER_STYLE)
                                tags.tr()
                            total = 0
                            handled_accounts = []
                            for account in accounts:
                                if account["currentBalance"] > 0 and not account["isClosed"] \
                                        and not account["name"] in handled_accounts:
                                    handled_accounts.append(account["name"])
                                    color_style = ""
                                    if account["accountType"] == "credit":
                                        color_style = ";background-color:" + CREDIT_CARD_COLOR
                                    with tags.tbody():
                                        with tags.tbody():
                                            tags.td(account["fiName"], style=BORDER_STYLE + color_style)
                                            tags.td(account["name"], style=BORDER_STYLE + color_style)
                                            notes = ""
                                            if account["accountType"] == "credit":
                                                next_payment_amount = account["dueAmt"]
                                                next_payment_date = account["dueDate"]
                                                if next_payment_amount is not None and next_payment_date is not None:
                                                    notes = locale.currency(next_payment_amount, grouping=True) + " due " +\
                                                            next_payment_date.strftime("%a, %b %d")
                                                elif next_payment_amount is not None and next_payment_amount > 0:
                                                    notes = locale.currency(next_payment_amount, grouping=True) + \
                                                            " is due in the near future"
                                                elif next_payment_date is not None and next_payment_amount > 0:
                                                    notes = "payment due " + next_payment_date.strftime("%a, %b %d")
                                            tags.td(notes, style=BORDER_STYLE + color_style)
                                            tags.td(locale.currency(account["value"], grouping=True),
                                                    style=BORDER_STYLE + color_style)
                                            total += account["value"]
                            tags.td("Total", style=BORDER_STYLE + color_style)
                            tags.td("", style=BORDER_STYLE + color_style)
                            tags.td("", style=BORDER_STYLE + color_style)
                            tags.td(locale.currency(total, grouping=True),
                                    style=BORDER_STYLE + color_style)
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
                    tags.h6("Banks", style="color:" + BANK_COLOR)
                    tags.h6("Credit Cards", style="color:" + CREDIT_CARD_COLOR)
                    tags.h6("Warnings", style="color:" + WARNING_COLOR)

                message = str(report_period_html) + message
                email_sender = EmailSender(self.config.email_connection, self.logger)
                for email in user.email:
                    self.logger.debug("Sending email to " + email)
                    if self.config.debug_copy_admin:
                        cc = self.config.general_admin_email
                    else:
                        cc = None
                    email_sender.send(email, user.subject, message, cc)
