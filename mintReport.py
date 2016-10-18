import dominate.tags as tags


class PrettyPrint:
    def __init__(self, users, budgets, accounts, transactions, net_worth):
        self.users = users
        self.budgets = budgets
        self.accounts = accounts
        self.transactions = transactions
        self.net_worth = net_worth
        self.doc = None

    def save(self):
        for user in self.users:
            file_name = user.name + ".html"
            html = tags.html()
            with html.add(tags.body()).add(tags.div(id='content')):
                fis = self.transactions.get_financial_institutions()
                fis_title_saved = False
                for fi in fis:
                    accounts = self.transactions.get_accounts(fi)
                    for account in accounts:
                        account =str(account)
                        if account in user.accounts or "all" in user.accounts:
                            if not fis_title_saved:
                                tags.h1(fi)
                                fis_title_saved = True
                            tags.h2(account)
                            transactions = self.transactions.get_transactions(fi, account)
                            with tags.table(rules="cols", frame="box"):
                                with tags.thead():
                                    tags.th("Date")
                                    tags.th("Merchant")
                                    tags.th("Amount", colspan="2")
                                    tags.tr()
                                    tags.th("")
                                    tags.th("")
                                    tags.th("Credit")
                                    tags.th("Debit")
                                for transaction in transactions:
                                    with tags.tbody():
                                        with tags.tbody():
                                            tags.td(transaction.date().strftime('%b %d'))
                                            tags.td(transaction.merchant())
                                            if transaction["isDebit"]:
                                                tags.td("")
                                                tags.td("-" + transaction.amount(), style="text-align:right")
                                            else:
                                                tags.td(transaction.amount(), style="text-align:right")
                                                tags.td("")
            with open(file_name, 'w') as f:
                f.write(str(html))

#                    print transaction.fi() + ", " + transaction.account() + "," + str(
#                        transaction.date()) + "," + transaction.merchant() + "," + str(transaction.amount())
