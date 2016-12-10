from datetime import date, datetime


def clean_dictionary(name, obj, logger=None):
    if logger is not None:
        logger.debug(name + " before:")
        logger.debug(str(obj))
    for transaction in obj:
        for key in transaction:
            clean_key = str(key)
            transaction[clean_key] = transaction.pop(key)
            transaction[clean_key] = str(transaction[clean_key])
            transaction[clean_key] = parse_all(clean_key, transaction[clean_key])
    if logger is not None:
        logger.debug(name + " after:")
        logger.debug(str(obj))
    return obj

DATE_STRING_FIELDS = [
    'dueDate'
]

LONG_DATE_FIELDS = [
    'addAccountDate',
    'lastUpdated',
    'closeDate',
    'fiLastUpdated'
]

MONTH_ONLY_DATE_FIELDS = [
    "date",
    "odate"
]

DOLLAR_FIELDS = [
    "amount",
    "value",
    "dueAmt",
    "currentBalance"
]


def date_convert(dateraw):
    # Converts dates from json data
    cy = datetime.isocalendar(date.today())[0]
    try:
        newdate = datetime.strptime(dateraw + str(cy), '%b %d%Y')
    except:
        newdate = datetime.strptime(dateraw, '%m/%d/%y')
    return newdate


def parse_all(key, val):
    this_type = str(type(val))
    if key in DATE_STRING_FIELDS:
        try:
            val = datetime.strptime(val, "%m/%d/%Y")
        except:
            val = None
    elif key in LONG_DATE_FIELDS:
        try:
            val = datetime.fromtimestamp(val / 1e3)
        except:
            val = None
    elif str(key) in MONTH_ONLY_DATE_FIELDS:
        try:
            val = date_convert(val)
        except:
            val = None
    elif str(key) in DOLLAR_FIELDS:
        try:
            val = float(val.replace("$", "").replace(",",""))
        except:
            val = None
    elif val == "False":
        val = False
    elif val == "True":
        val = True
    elif "'unicode'" in this_type:
        val = str(val)
    return val


class MintTransactions:
    ##############################################
    # __init__: constructor for a MintTransactions
    # obj:      string that describes a group of transactions
    ##############################################
    def __init__(self, obj, logger):
        self.transactions = clean_dictionary("MintTransactions", obj, logger)

    def dump(self, logger):
        for transaction in self.transactions:
            logger.debug("Dumping Transaction")
            for key in transaction:
                logger.debug("\t\t" + key + ":" + str(transaction[key]))

    def get_financial_institutions(self, start_date):
        fis = []
        for transaction in self.transactions:
            if transaction["fi"] not in fis and transaction["date"] >= start_date:
                fis.append(transaction["fi"])
        return fis

    def get_accounts(self, fi, start_date):
        accounts = []
        for transaction in self.transactions:
            if transaction["fi"] == fi and transaction["account"] not in accounts and transaction["date"] >= start_date:
                accounts.append(transaction["account"])
        return accounts

    def get_transactions(self, fi, account, start_date):
        transactions = []
        total = 0.0
        for transaction in self.transactions:
            if transaction["fi"] == fi and transaction["account"] == account \
                    and transaction["account"] not in transactions and transaction["date"] >= start_date \
                    and transaction["amount"] > 0:
                transactions.append(transaction)
                amount = transaction["amount"]
                if transaction["isDebit"]:
                    total -= amount
                else:
                    total += amount
        return MintTransactions.sort_by_key(transactions, 'date'), total

    @staticmethod
    def sort_by_key(transactions, key):
        trans = []
        for k in transactions:
            i = 0
            while i < len(trans):
                if trans[i]["date"] > k["date"]:
                    break
                else:
                    i += 1
            trans.insert(i, k)
        return trans


class MintAccounts:
    ##############################################
    # __init__: constructor for a MintAccounts
    # obj:      string that describes a group of accounts
    ##############################################
    def __init__(self, obj, logger):
        self.accounts = clean_dictionary("MintAccounts", obj, logger)

    def get_account(self, name):
        for account in self.accounts:
            if account["accountName"] == name:
                return account
        return None

    def dump(self, logger):
        for account in self.accounts:
            logger.debug("Dumping " + account["name"])
            for key in account:
                logger.debug("\t\t" + key + ":" + str(account[key]))