from thompcoutils.log_utils import get_logger
from datetime import datetime
import inspect
import logging
import re


def clean_dictionary(name, transactions):
    logger = get_logger()
    logger.debug(name + " before:")
    logger.debug(str(transactions))
    for transaction in transactions:
        for key in transaction:
            clean_key = to_string(key)
            transaction[clean_key] = to_string(transaction[clean_key])
            transaction[clean_key] = parse_all(clean_key, transaction[clean_key])
    return transactions


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
    cy = datetime.isocalendar(datetime.today())[0]
    # noinspection PyBroadException
    try:
        newdate = datetime.strptime(dateraw + str(cy), '%b %d%Y')
    except Exception:
        newdate = datetime.strptime(dateraw, '%m/%d/%y')
    return newdate


def parse_all(key, val):
    this_type = to_string(type(val))
    if key in DATE_STRING_FIELDS:
        # noinspection PyBroadException
        try:
            val = datetime.strptime(val, "%m/%d/%Y")
        except Exception:
            val = None
    elif key in LONG_DATE_FIELDS:
        # noinspection PyBroadException
        try:
            val = datetime.fromtimestamp(val / 1e3)
        except Exception:
            val = None
    elif to_string(key) in MONTH_ONLY_DATE_FIELDS:
        # noinspection PyBroadException
        try:
            val = date_convert(val)
        except Exception:
            val = None
    elif to_string(key) in DOLLAR_FIELDS:
        # noinspection PyBroadException
        try:
            val = float(val.replace("$", "").replace(",", ""))
        except Exception:
            val = None
    elif val == "False":
        val = False
    elif val == "True":
        val = True
    elif "'unicode'" in this_type:
        val = to_string(val)
    return val


class MintTransactions:
    ##############################################
    # __init__: constructor for a MintTransactions
    # obj:      string that describes a group of transactions
    ##############################################
    def __init__(self, obj):
        self.transactions = clean_dictionary("MintTransactions", obj)

    def dump(self):
        logger = get_logger()
        for transaction in self.transactions:
            logger.debug("Dumping Transaction")
            for key in transaction:
                logger.debug("\t\t" + key + ":" + to_string(transaction[key]))

    def get_financial_institutions(self, start_date):
        fis = []
        for transaction in self.transactions:
            if transaction["fi"] not in fis and transaction['date'] is not None and transaction["date"] >= start_date:
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
        transactions.sort(key=lambda item: item['date'], reverse=True)
        return transactions, total


class MintAccounts:
    ##############################################
    # __init__: constructor for a MintAccounts
    # obj:      string that describes a group of accounts
    ##############################################
    def __init__(self, obj):
        self.accounts = clean_dictionary("MintAccounts", obj)

    def get_account(self, name):
        for account in self.accounts:
            if account["accountName"] == name:
                return account
        return None

    def dump(self):
        logger = get_logger()
        for account in self.accounts:
            logger.debug("Dumping " + account["name"])
            for key in account:
                logger.debug("\t\t" + key + ":" + to_string(account[key]))


def to_string(obj):
    if isinstance(obj, str):
        return re.sub(r'[^\x00-\x7f]', r'', obj)
    else:
        return str(obj)
