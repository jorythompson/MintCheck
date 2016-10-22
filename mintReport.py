import dominate.tags as tags
from emailSender import EmailSender

BORDER_STYLE = "border-bottom:1px solid black"


class PrettyPrint:
    def __init__(self, budgets, accounts, transactions, config):
        self.config = config
        self.budgets = budgets
        self.accounts = accounts
        self.transactions = transactions
        self.doc = None

    def save(self):
        for user in self.config.users:
            bad_transactions = []
            html = tags.html()
            with html.add(tags.body()).add(tags.div(id='content')):
                fis = self.transactions.get_financial_institutions()
                fis_title_saved = False
                for fi in fis:
                    accounts = self.transactions.get_accounts(fi)
                    for account in accounts:
                        account = str(account)
                        if account in user.accounts or "all" in user.accounts:
                            if not fis_title_saved:
                                try:
                                    f = user.rename_institutions[fi]
                                except KeyError:
                                    f = fi
                                tags.h1(f)
                                fis_title_saved = True
                            try:
                                acc = user.rename_accounts[account]
                            except KeyError:
                                acc = account
                            tags.h2(acc)
                            transactions = self.transactions.get_transactions(fi, account)
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
                                            for warning in self.config.warning_keywords:
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
            html2 = tags.html()
            with html2.add(tags.body()).add(tags.div(id='content')):
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

            email_sender = EmailSender(self.config.email_connection)
            email_sender.send(user.email, user.subject, str(html2) + str(html))
            with open(user.name + ".html", 'w') as f:
                f.write(str(html))
            with open(user.name + "_header.html", 'w') as f:
                f.write(str(html2))

#                    print transaction.fi() + ", " + transaction.account() + "," + str(
#                        transaction.date()) + "," + transaction.merchant() + "," + str(transaction.amount())
