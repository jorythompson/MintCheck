import dominate.tags as tags
from emailSender import EmailSender
from dateutil.relativedelta import relativedelta
import locale

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
        for user in self.config.users:
            self.logger.debug("handling user:" + user.name)
            start_date = None
            report_frequency = None
            if "monthly" in user.frequency and "monthly" in frequency:
                start_date = self.start_date
                report_frequency = "monthly"
            elif "weekly" in user.frequency and "weekly" in frequency:
                start_date = self.now + relativedelta(days=-7)
                report_frequency = "weekly"
            elif "daily" in user.frequency and "daily" in frequency:
                start_date = self.now + relativedelta(days=-1)
                report_frequency = "daily"
            activity_html = ""
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
                                mint_account = self.accounts.get_account(account_name)
                                user_accounts[user] = mint_account
                                account_type = str(mint_account.account_type())
                                account_message = "This"
                                account_color = "green"
                                if "bank" in account_type.lower():
                                    account_message += " is a bank account"
                                elif "credit" in account_type.lower():
                                    account_message += " credit card"
                                    account_color = "orange"
                                    next_payment_amount = mint_account.next_payment_amount()
                                    next_payment_date = mint_account.next_payment_date()
                                    if next_payment_date is None:
                                        next_payment_date = "<unknown>"
                                    if next_payment_amount is None or next_payment_amount == 0:
                                        account_message += " has nothing due but the payment date is normally on " +\
                                                           str(next_payment_date)
                                    else:
                                        account_color = "red"
                                        account_message += " has an amount of " + (next_payment_amount) + \
                                                           " due on " + str(next_payment_date)
                                else:
                                    account_message = account_type.strip()
                                if not fis_title_saved:
                                    try:
                                        f = user.rename_institutions[fi]
                                    except KeyError:
                                        f = fi
                                    tags.h1(f)
                                    fis_title_saved = True
                                try:
                                    acc = user.rename_accounts[account_name]
                                except KeyError:
                                    acc = account_name
                                transactions, total = self.transactions.get_transactions(fi, account_name, start_date)
                                tags.h2(acc + " has a balance of " +
                                        locale.currency(mint_account.value(), grouping=True) +
                                        ".  Total transactions for this report is " +
                                        locale.currency(total, grouping=True) + ".")
                                tags.h3(account_message, style="color:" + account_color)
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
                                                    if warning in transaction.merchant().lower():
                                                        bad_transactions.append(transaction)
                                                        color = "red"
                                                        break
                                                tags.td(transaction.date().strftime('%b %d'), bgcolor=color)
                                                tags.td(transaction.merchant(), bgcolor=color)
                                                amount = transaction.amount()
                                                if transaction.is_debit():
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
                                        tags.td(transaction.date().strftime('%b %d'))
                                        try:
                                            f = user.rename_institutions[transaction.fi()]
                                        except KeyError:
                                            f = transaction.fi()
                                        tags.td(f)
                                        try:
                                            a = user.rename_accounts[transaction.account()]
                                        except KeyError:
                                            a = transaction.account()
                                        tags.td(a)
                                        tags.td(transaction.merchant())
                                        amount = locale.currency(transaction.amount(), grouping=True)
                                        if transaction.is_debit():
                                            tags.td("")
                                            tags.td("-" + amount, style="text-align:right")
                                        else:
                                            tags.td(amount, style="text-align:right")
                                            tags.td("")
                accounts = []
                self.logger.debug("assembling accounts")
                for account in self.accounts.accounts:
                    for account_name in user.account_totals:
                        if account_name == "all" or account_name == account.name():
                            accounts.append(account)
                accounts_html = ""
                if len(accounts) > 0:
                    accounts_html = tags.html()
                    with accounts_html.add(tags.body()).add(tags.div(id='content')):
                        tags.h1("Current Balances in Accounts")
                        with tags.table(rules="cols", frame="box"):
                            with tags.thead():
                                tags.th("Financial Institution", style=BORDER_STYLE)
                                tags.th("Account", style=BORDER_STYLE)
                                tags.th("Amount", style=BORDER_STYLE)
                                tags.tr()
                            for account in accounts:
                                with tags.tbody():
                                    with tags.tbody():
                                        tags.td(account.fi_name())
                                        tags.td(account.name(), style=BORDER_STYLE)
                                        tags.td(locale.currency(account.value(), grouping=True), style=BORDER_STYLE)

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
                message = str(report_period_html) + message
                email_sender = EmailSender(self.config.email_connection, self.logger)
                for email in user.email:
                    self.logger.debug("Sending email to " + email)
                    email_sender.send(email, user.subject,message)
