import glob
import dominate
import dominate.tags as tags


class PrettyPrint:
    def __init__(self, budgets, accounts, transactions, net_worth):
        self.budgets = budgets
        self.accounts = accounts
        self.transactions = transactions
        self.net_worth = net_worth
        self.doc = None

    def save(self, file_name):
        html = tags.html()
        with html.add(tags.body()).add(tags.div(id='content')):
            tags.h1("Main Page")
            fis = self.transactions.get_financial_institutions()
            for fi in fis:
                tags.h2(fi)
                print fi
                accounts = self.transactions.get_accounts(fi)
                for account in accounts:
                    transactions = self.transactions.get_transactions(fi, account)
                    with tags.table():
                        with tags.thead():
                            tags.th("Account")
                            tags.th("Date")
                            tags.th("Merchant")
                            tags.th("Amount")
                        for transaction in transactions:
                            with tags.tbody():
                                with tags.tbody():
                                    tags.td(transaction.account())
                                    tags.td(transaction.date())
                                    tags.td(transaction.merchant())
                                    tags.td(transaction.amount())
        with open(file_name, 'w') as f:
            f.write(str(html))

#                    print transaction.fi() + ", " + transaction.account() + "," + str(
#                        transaction.date()) + "," + transaction.merchant() + "," + str(transaction.amount())
