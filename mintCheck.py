import mintapi
import ConfigParser
import mintObjects
import mintReport
import argparse
import cPickle
import datetime

MINT_USER = "Mint User"
MINT_COOKIES = "Mint Cookies"


def get_args():
    parser = argparse.ArgumentParser(description='Read Information from Mint')
    parser.add_argument('--config', help='Configuration file containing your username, password, and mint cookie')
    args = parser.parse_args()
    return args.config


def read_config(config_file):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    username = config.get(MINT_USER, "username")
    password = config.get(MINT_USER, "password")
    cookie = config.get(MINT_COOKIES, "cookie")
    return username, password, cookie


def pickle(budgets, accounts, transactions, net_worth):
    with open('filename.pickle', 'wb') as handle:
        cPickle.dump(budgets, handle)
        cPickle.dump(accounts, handle)
        cPickle.dump(transactions, handle)
        cPickle.dump(net_worth, handle)
    pass


def unpickle():
    with open('filename.pickle', 'rb') as handle:
        budgets = cPickle.load(handle)
        accounts = cPickle.load(handle)
        transactions = cPickle.load(handle)
        net_worth = cPickle.load(handle)

    return budgets, accounts, transactions, net_worth


def main():
    dev = False

    if dev:
        print "unpicking..."
        budgets, accounts, transactions, net_worth = unpickle()
    else:
        config_file = get_args()
        username, password, cookie = read_config(config_file)
        print "connecting..."
        mint = mintapi.Mint(email=username, password=password, ius_session=cookie)

        # Get basic account information
        # accounts = mint.get_accounts()
        # Get extended account detail at the expense of speed - requires an
        # additional API call for each account
        print "getting accounts..."
        accounts = mint.get_accounts(get_detail=True)

        # Get budget information
        print "getting budgets..."
        budgets = mint.get_budgets()

        # Get transactions
        # transactions = mint.get_transactions()  # as pandas dataframe
        # print mint.get_transactions_csv(include_investment=False) # as raw csv data
        first_of_month = datetime.date.today()
        first_of_month = datetime.datetime.strptime(str(first_of_month.year) + "-" + str(first_of_month.month) + "-1","%Y-%m-%d")
        print "getting transactions from " + str(first_of_month) + "..."
        transactions = mint.get_transactions_json(include_investment=False, skip_duplicates=False,
                                                  start_date=first_of_month)

        # Get net worth
        print "getting net worth..."
        net_worth = mint.get_net_worth()

        print "pickling..."
        pickle(budgets, accounts, transactions, net_worth)
        # Initiate an account refresh

        print "refreshing..."
        refresh = mint.initiate_account_refresh()
        print "done!"
        print refresh

#    for account in accounts:
#        acc = mintObjects.MintAccount(account)
#        acc.dump()

    print "getting Budgets..."
    mint_budgets = mintObjects.MintBudgets(budgets)
#    mint_budgets.dump()

    print "getting Transactions..."
    mint_transactions = mintObjects.MintTransactions(transactions)
#    mint_transactions.dump()

    print "Creating HTML..."
    report = mintReport.PrettyPrint(mint_budgets, accounts, mint_transactions, net_worth)

    print "Saving HTML..."
    report.save("test.html")
    # print mint.get_transactions_csv(include_investment=False) # as raw csv data
    # print mint.get_transactions_json(include_investment=False, skip_duplicates=False)

    print net_worth
    print "Done!"

if __name__ == "__main__":
    main()
