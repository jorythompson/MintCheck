import dominate.tags as tags
from emailSender import EmailSender
import datetime
from dateutil.relativedelta import relativedelta
from mintObjects import  MintAccount
import logging

BORDER_STYLE = "border-bottom:1px solid black"


class PrettyPrint:
    def __init__(self, accounts, transactions, config, start_date, logger):
        self.config = config
        self.accounts = accounts
        self.transactions = transactions
        self.start_date = start_date
        self.doc = None
        self.logger = logger

    def send_data(self, frequency):
        self.logger.debug("starting send_data")
        # now = datetime.datetime.now()
        now = datetime.datetime.strptime('10/04/2016', '%m/%d/%Y')
        for user in self.config.users:
            start_date = None
            report_frequency = None
            if "monthly" in user.frequency and "monthly" in frequency:
                start_date = self.start_date
                report_frequency = "monthly"
            elif "weekly" in user.frequency and "weekly" in frequency:
                start_date = now + relativedelta(days=-7)
                report_frequency = "weekly"
            elif "daily" in user.frequency and "daily" in frequency:
                start_date = now + relativedelta(days=-1)
                report_frequency = "daily"
            if start_date is not None:
                bad_transactions = []
                transactions = []
                html = tags.html()
                with html.add(tags.body()).add(tags.div(id='content')):
                    fis = self.transactions.get_financial_institutions(start_date)
                    fis_title_saved = False
                    for fi in fis:
                        account_names = self.transactions.get_accounts(fi, start_date)
                        for account_name in account_names:
                            account_name = str(account_name)
                            if account_name in user.accounts or "all" in user.accounts:
                                mint_account = self.accounts.get_account(account_name)
                                account_type = str(mint_account.account_type())
                                account_message = "This"
                                if "bank" in account_type.lower():
                                    account_message += " is a bank account"
                                elif "credit" in account_type.lower():
                                    account_message += " credit card"
                                    next_payment_amount = mint_account.next_payment_amount()
                                    next_payment_date = mint_account.next_payment_date()
                                    if next_payment_amount is None or next_payment_amount == 0:
                                        account_message += " has nothing due but the payment date is normally on " +\
                                                           str(next_payment_date)
                                    else:
                                        if next_payment_date is None:
                                            next_payment_date = "<unknown>"
                                        account_message += " has an amount of " + (next_payment_amount) + " due on " + str(next_payment_date)
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
                                tags.h2(acc)
                                tags.h3(account_message)
                                transactions = self.transactions.get_transactions(fi, account_name, start_date)
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
                                                if transaction.is_debit():
                                                    tags.td("", bgcolor=color)
                                                    tags.td("-" + transaction.amount(), style="text-align:right",
                                                            bgcolor=color)
                                                else:
                                                    tags.td(transaction.amount(), style="text-align:right", bgcolor=color)
                                                    tags.td("", bgcolor=color)
                if len(bad_transactions) > 0:
                    html2 = tags.html()
                    with html2.add(tags.body()).add(tags.div(id='content')):
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
                                        if transaction.is_debit():
                                            tags.td("")
                                            tags.td("-" + transaction.amount(), style="text-align:right")
                                        else:
                                            tags.td(transaction.amount(), style="text-align:right")
                                            tags.td("")

                message = ""
                if len(bad_transactions) > 0:
                    message = str(html2)
                if len(transactions) > 0:
                    message += str(html)

                if message != "":
                    html = tags.html()
                    with html.add(tags.body()).add(tags.div(id='content')):
                        tags.h4("This " + report_frequency + " report was prepared for " + user.name + " starting on " + \
                              start_date.strftime('%m/%d/%y'))
                    message = str(html) + message
                    email_sender = EmailSender(self.config.email_connection, self.logger)
                    email_sender.send(user.email, user.subject,message)
