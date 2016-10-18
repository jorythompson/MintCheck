import mintapi
import mintObjects
import mintReport
import argparse
import cPickle
import datetime
from mintConfigFile import MintConfigFile


class MintCheck:
    def __init__(self, dev=False):
        self.args = None
        self.budgets = None
        self.accounts = None
        self.transactions = None
        self.net_worth = None
        self.users = None
        self.mint_budgets = None
        self.mint_transactions = None
        self.args = MintCheck.get_args()
        self.config = MintConfigFile(self.args.config)
        self.users = self.config.users

        if dev:
            print "unpicking..."
            self.unpickle()
        else:
            today = datetime.date.today()
            first = today.replace(day=1)
            last_month = first - datetime.timedelta(days=1)
            last_month = last_month.replace(day=1)
            start_date = last_month.strftime("%m/%d/%y")
            print "getting transactions from " + start_date + "..."

            mint = mintapi.Mint(email=self.config.username, password=self.config.password, ius_session=self.config.cookie)

            # Get basic account information
            # accounts = mint.get_accounts()
            # Get extended account detail at the expense of speed - requires an
            # additional API call for each account
            print "getting accounts..."
            self.accounts = mint.get_accounts(get_detail=True)

            # Get budget information
            print "getting budgets..."
            self.budgets = mint.get_budgets()

            # Get transactions
            # transactions = mint.get_transactions()  # as pandas dataframe
            # print mint.get_transactions_csv(include_investment=False) # as raw csv data
            self.transactions = mint.get_transactions_json(include_investment=False, skip_duplicates=False,
                                                           start_date=start_date)

            # Get net worth
            print "getting net worth..."
            self.net_worth = mint.get_net_worth()

            print "pickling..."
            self.pickle()

        print "getting Budgets..."
        self.mint_budgets = self.get_budgets()
        #    mint_budgets.dump()

        print "getting Transactions..."
        self.mint_transactions = self.get_transactions()

    #    mint_transactions.dump()

    def get_budgets(self):
        print "getting Budgets..."
        return mintObjects.MintBudgets(self.budgets)

    def get_transactions(self):
        return mintObjects.MintTransactions(self.transactions)

    @staticmethod
    def get_args():
        parser = argparse.ArgumentParser(description='Read Information from Mint')
        parser.add_argument('--config', help='Configuration file containing your username, password, and mint cookie')
        return parser.parse_args()

    def pretty_print(self):
        return mintReport.PrettyPrint(self.users, self.mint_budgets, self.accounts, self.mint_transactions, self.net_worth)

    def pickle(self):
        with open('filename.pickle', 'wb') as handle:
            cPickle.dump(self.budgets, handle)
            cPickle.dump(self.accounts, handle)
            cPickle.dump(self.transactions, handle)
            cPickle.dump(self.net_worth, handle)

    def unpickle(self):
        with open('filename.pickle', 'rb') as handle:
            self.budgets = cPickle.load(handle)
            self.accounts = cPickle.load(handle)
            self.transactions = cPickle.load(handle)
            self.net_worth = cPickle.load(handle)


def main():
    mint_check = MintCheck(dev=True)

        # Initiate an account refresh

#        print "refreshing..."
#        refresh = mint.initiate_account_refresh()
#        print "done!"
#        print refresh

#    for account in accounts:
#        acc = mintObjects.MintAccount(account)
#        acc.dump()

    print "Creating HTML..."
    report = mint_check.pretty_print()

    print "Saving HTML..."
    report.save()
    # print mint.get_transactions_csv(include_investment=False) # as raw csv data
    # print mint.get_transactions_json(include_investment=False, skip_duplicates=False)

    print mint_check.net_worth
    print "Done!"

if __name__ == "__main__":
    main()
