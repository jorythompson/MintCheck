from dateutil import parser


class MintTransactions:
    ##############################################
    # __init__: constructor for a MintTransactions
    # obj:      string that describes a group of transactions
    ##############################################
    def __init__(self, obj):
        self.obj = obj
        self.transactions = []
        for transaction in obj:
            self.transactions.append(MintTransaction(transaction))

    def get_financial_institutions(self, start_date):
        fis = []
        for transaction in self.transactions:
            if transaction.fi() not in fis and transaction.date() >= start_date:
                fis.append(transaction.fi())
        return fis

    def get_accounts(self, fi, start_date):
        accounts = []
        for transaction in self.transactions:
            if transaction.fi() == fi and transaction.account() not in accounts and transaction.date() >= start_date:
                accounts.append(transaction.account())
        return accounts

    def get_transactions(self, fi, account, start_date):
        transactions = []
        for transaction in self.transactions:
            if transaction.fi() == fi and transaction.account() == account and \
                            transaction.account() not in transactions and transaction.date() >= start_date:
                transactions.append(transaction)
        return MintTransactions.sort_by_key(transactions, 'date')
#        sorted_transactions = sorted(transactions, key=itemgetter('date'))
#        sorted_transactions = sorted(transactions, key=lambda k: k['date'])
#        return sorted_transactions

    @staticmethod
    def sort_by_key(transactions, key):
        trans = []
        for k in transactions:
            i = 0
            while i < len(trans):
                if trans[i].date() > k.date():
#                if datetime.strptime(trans[i][key], MintTransactions.DATE_FORMAT) > \
#                        datetime.strptime(k[key], MintTransactions.DATE_FORMAT):
                    break
                else:
                    i += 1
            trans.insert(i, k)
        return trans

    def dump(self):
        for transaction in self.transactions:
            transaction.dump()


class MintTransaction:
    ##############################################
    # __init__: constructor for a MintTransaction
    # obj:      dictionary that describes a single transaction
    ##############################################
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, item):
        try:
            return self.obj[item]
        except KeyError:
            return None

    def available_money(self):
        try:
            return self.obj['availableMoney']
        except KeyError:
            return None

    def next_payment_amount(self):
        try:
            return self.obj['nextPaymentAmount']
        except KeyError:
            return None

    def interest_rate(self):
        try:
            return self.obj['interestRate']
        except KeyError:
            return None

    def is_account_not_found(self):
        try:
            return self.obj['isAccountNotFound']
        except KeyError:
            return None

    def due_amount(self):
        try:
            return self.obj['dueAmt']
        except KeyError:
            return None

    def add_account_date(self):
        try:
            return self.obj['addAccountDate']
        except KeyError:
            return None

    def is_host_account(self):
        try:
            return self.obj['isHostAccount']
        except KeyError:
            return None

    def due_date(self):
        try:
            return self.obj['dueDate']
        except KeyError:
            return None

    def account_id(self):
        try:
            return self.obj['accountId']
        except KeyError:
            return None

    def linked_account_id(self):
        try:
            return self.obj['linkedAccountId']
        except KeyError:
            return None

    def possible_linked_accounts(self):
        try:
            return self.obj['possibleLinkAccounts']
        except KeyError:
            return None

    def file_login_status(self):
        try:
            return self.obj['fiLoginStatus']
        except KeyError:
            return None

    def exclusion_type(self):
        try:
            return self.obj['exclusionType']
        except KeyError:
            return None

    def id(self):
        try:
            return self.obj['id']
        except KeyError:
            return None

    def add_account_date_in_date(self):
        try:
            return self.obj['addAccountDateInDate']
        except KeyError:
            return None

    def yodlee_account_number_last_4(self):
        try:
            return self.obj['yodleeAccountNumberLast4']
        except KeyError:
            return None

    def fi_last_updated(self):
        try:
            return self.obj['fiLastUpdated']
        except KeyError:
            return None

    def account_name(self):
        try:
            return self.obj['accountName']
        except KeyError:
            return None

    def cc_aggr_status(self):
        try:
            return self.obj['ccAggrStatus']
        except KeyError:
            return None

    def kast_updated_in_string(self):
        try:
            return self.obj['lastUpdatedInString']
        except KeyError:
            return None

    def file_login_display_name(self):
        try:
            return self.obj['fiLoginDisplayName']
        except KeyError:
            return None

    def yodlee_account_id(self):
        try:
            return self.obj['yodleeAccountId']
        except KeyError:
            return None

    def next_payment_date(self):
        try:
            return self.obj['nextPaymentDate']
        except KeyError:
            return None

    def linked_account(self):
        try:
            return self.obj['linkedAccount']
        except KeyError:
            return None

    def status(self):
        try:
            return self.obj['status']
        except KeyError:
            return None

    def fi_login_id(self):
        try:
            return self.obj['fiLoginId']
        except KeyError:
            return None

    def username(self):
        try:
            return self.obj['userName']
        except KeyError:
            return None

    def last_updated(self):
        try:
            return self.obj['lastUpdated']
        except KeyError:
            return None

    def is_closed(self):
        try:
            return self.obj['isClosed']
        except KeyError:
            return None

    def value(self):
        try:
            return self.obj['value']
        except KeyError:
            return None

    def account_type(self):
        try:
            return self.obj['accountType']
        except KeyError:
            return None

    def is_account_closed_by_mint(self):
        try:
            return self.obj['isAccountClosedByMint']
        except KeyError:
            return None

    def total_fees(self):
        try:
            return self.obj['totalFees']
        except KeyError:
            return None

    def fi_login_ui_status(self):
        try:
            return self.obj['fiLoginUIStatus']
        except KeyError:
            return None

    def link_status(self):
        try:
            return self.obj['linkStatus']
        except KeyError:
            return None

    def is_error(self):
        try:
            return self.obj['isError']
        except KeyError:
            return None

    def is_active(self):
        try:
            return self.obj['isActive']
        except KeyError:
            return None

    def link_creation_time(self):
        try:
            return self.obj['linkCreationTime']
        except KeyError:
            return None

    def name(self):
        try:
            return self.obj['name']
        except KeyError:
            return None

    def account_type_int(self):
        try:
            return self.obj['accountTypeInt']
        except KeyError:
            return None

    def yodlee_name(self):
        try:
            return self.obj['yodleeName']
        except KeyError:
            return None

    def fi_name(self):
        try:
            return self.obj['fiName']
        except KeyError:
            return None

    def usage_type(self):
        try:
            return self.obj['usageType']
        except KeyError:
            return None

    def account_status(self):
        try:
            return self.obj['accountStatus']
        except KeyError:
            return None

    def is_hidden_from_planning_trends(self):
        try:
            return self.obj['isHiddenFromPlanningTrends']
        except KeyError:
            return None

    def account_system_status(self):
        try:
            return self.obj['accountSystemStatus']
        except KeyError:
            return None

    def class_type(self):
        try:
            return self.obj['klass']
        except KeyError:
            return None

    def total_credit(self):
        try:
            return self.obj['totalCredit']
        except KeyError:
            return None

    def current_balance(self):
        try:
            return self.obj['currentBalance']
        except KeyError:
            return None

    def close_date(self):
        try:
            return self.obj['closeDate']
        except KeyError:
            return None

    def fi_last_updated_in_date(self):
        try:
            return self.obj['fiLastUpdatedInDate']
        except KeyError:
            return None

    def manual_type(self):
        try:
            return self.obj['manualType']
        except KeyError:
            return None

    def merchant(self):
        try:
            return self.obj['merchant']
        except KeyError:
            return None

    def m_merchant(self):
        try:
            return self.obj['mmerchant']
        except KeyError:
            return None

    def labels(self):
        try:
            return self.obj['labels']
        except KeyError:
            return None

    def o_merchant(self):
        try:
            return self.obj['omerchant']
        except KeyError:
            return None

    def is_percent(self):
        try:
            return self.obj['isPercent']
        except KeyError:
            return None

    def category(self):
        try:
            return self.obj['category']
        except KeyError:
            return None

    def run_merchant(self):
        try:
            return self.obj['ruleMerchant']
        except KeyError:
            return None

    def is_pending(self):
        try:
            return self.obj['isPending']
        except KeyError:
            return None

    def is_debit(self):
        try:
            return self.obj['isDebit']
        except KeyError:
            return None

    def note(self):
        try:
            return self.obj['note']
        except KeyError:
            return None

    def is_spending(self):
        try:
            return self.obj['isSpending']
        except KeyError:
            return None

    def rule_category_id(self):
        try:
            return self.obj['ruleCategoryId']
        except KeyError:
            return None

    def is_linked_to_rule(self):
        try:
            return self.obj['isLinkedToRule']
        except KeyError:
            return None

    def category_id(self):
        try:
            return self.obj['categoryId']
        except KeyError:
            return None

    def rule_category(self):
        try:
            return self.obj['ruleCategory']
        except KeyError:
            return None

    def m_category(self):
        try:
            return self.obj['mcategory']
        except KeyError:
            return None

    def is_after_fi_creation_time(self):
        try:
            return self.obj['isAfterFiCreationTime']
        except KeyError:
            return None

    def is_check(self):
        try:
            return self.obj['isCheck']
        except KeyError:
            return None

    def is_first_date(self):
        try:
            return self.obj['isFirstDate']
        except KeyError:
            return None

    def o_date(self):
        try:
            return self.obj['odate']
        except KeyError:
            return None

    def number_matched_by_rule(self):
        try:
            return self.obj['numberMatchedByRule']
        except KeyError:
            return None

    def date(self):
        try:
            rtn = parser.parse(self.obj['date'])
            return rtn
        except KeyError:
            return None

    def fi(self):
        try:
            return self.obj['fi']
        except KeyError:
            return None

    def is_child(self):
        try:
            return self.obj['isChild']
        except KeyError:
            return None

    def account(self):
        try:
            return self.obj['account']
        except KeyError:
            return None

    def has_attachments(self):
        try:
            return self.obj['hasAttachments']
        except KeyError:
            return None

    def has_category__id(self):
        try:
            return self.obj['userCategoryId']
        except KeyError:
            return None

    def amount(self):
        try:
            return self.obj['amount']
        except KeyError:
            return None

    def is_transfer(self):
        try:
            return self.obj['isTransfer']
        except KeyError:
            return None

    def txn_type(self):
        try:
            return self.obj['txnType']
        except KeyError:
            return None

    def is_edited(self):
        try:
            return self.obj['isEdited']
        except KeyError:
            return None

    def is_duplicate(self):
        try:
            return self.obj['isDuplicate']
        except KeyError:
            return None

    def is_matched(self):
        try:
            return self.obj['isMatched']
        except KeyError:
            return None

    def dump(self):
        print "Transaction:" + str(self.merchant()) + " (" + str(self.date()) + ")"
        items = MintTransaction.__dict__
        for item in items:
            if item != "dump" and item != "__init__":
                to_call = getattr(self, item)
                if callable(to_call):
                    print str(item) + ":" + str(to_call())
        print "========="


class MintBudget:
    ##############################################
    # __init__: constructor for a MintBudget
    # obj:      dictionary that describes a budget
    ##############################################
    def __init__(self, obj):
        self.obj = obj

    def cat_type_filter(self):
        try:
            return self.obj['catTypeFilter']
        except KeyError:
            return None

    def ram_t(self):
        try:
            return self.obj['ramt']
        except KeyError:
            return None

    def cat(self):
        try:
            return self.obj['cat']
        except KeyError:
            return None

    def pid(self):
        try:
            return self.obj['pid']
        except KeyError:
            return None

    def amt(self):
        try:
            return self.obj['amt']
        except KeyError:
            return None

    def is_income(self):
        try:
            return self.obj['isIncome']
        except KeyError:
            return None

    def is_transfer(self):
        try:
            return self.obj['isTransfer']
        except KeyError:
            return None

    def bgt(self):
        try:
            return self.obj['bgt']
        except KeyError:
            return None

    def ex(self):
        try:
            return self.obj['ex']
        except KeyError:
            return None

    def id(self):
        try:
            return self.obj['id']
        except KeyError:
            return None

    def st(self):
        try:
            return self.obj['st']
        except KeyError:
            return None

    def type(self):
        try:
            return self.obj['type']
        except KeyError:
            return None

    def is_expense(self):
        try:
            return self.obj['isExpense']
        except KeyError:
            return None

    def _r_bal(self):
        try:
            return self.obj['rbal']
        except KeyError:
            return None

    def dump(self):
        print "Budget:" + str(self.cat()) + " (" + str(self.type()) + ")"
        items = MintBudget.__dict__
        for item in items:
            if item != "dump" and item != "__init__":
                to_call = getattr(self, item)
                if callable(to_call):
                    print str(item) + ":" + str(to_call())
        print "========="


class MintBudgets:
    ##############################################
    # __init__: constructor for a MintBudgets
    # obj:      dictionary that describes a group of Budget
    ##############################################
    def __init__(self, obj):
        self.obj = obj
        self.budgets = []
        for budget_type in obj:
            for budget in self.obj[budget_type]:
                budget['type'] = budget_type
                self.budgets.append(MintBudget(budget))

    def dump(self):
        for budget in self.budgets:
            budget.dump()


class MintAccounts:
    ##############################################
    # __init__: constructor for a MintAccounts
    # obj:      string that describes a group of accounts
    ##############################################
    def __init__(self, obj):
        self.obj = obj
        self.accounts = []
        for account in obj:
            self.accounts.append(MintTransaction(account))

    def get_account(self, name):
        for account in self.accounts:
            if account["accountName"] == name:
                return account
        return None


class MintAccount:
    ##############################################
    # __init__: constructor for a MintBudget
    # obj:      dictionary that describes a budget
    ##############################################
    def __init__(self, obj):
        self.obj = obj

    def account_name(self):
        try:
            return self.obj['accountName']
        except KeyError:
            return None

    def is_closed(self):
        try:
            return self.obj['isClosed']
        except KeyError:
            return None

    def close_date(self):
        try:
            return self.obj['closeDateInDate']
        except KeyError:
            return None

    def last_updated(self):
        try:
            return self.obj['lastUpdatedInDate']
        except KeyError:
            return None

    def is_terminal(self):
        try:
            return self.obj['isTerminal']
        except KeyError:
            return None

    def currency(self):
        try:
            return self.obj['currency']
        except KeyError:
            return None

    def interest_rate(self):
        try:
            return self.obj['interestRate']
        except KeyError:
            return None

    def account_found(self):
        try:
            return self.obj['isAccountNotFound']
        except KeyError:
            return None

    def account_added_date(self):
        try:
            return self.obj['addAccountDate']
        except KeyError:
            return None

    def is_host_account(self):
        try:
            return self.obj['isHostAccount']
        except KeyError:
            return None

    def account_id(self):
        try:
            return self.obj['accountId']
        except KeyError:
            return None

    def linked_account_id(self):
        try:
            return self.obj['linkedAccountId']
        except KeyError:
            return None

    def possible_linked_accounts(self):
        try:
            return self.obj['possibleLinkAccounts']
        except KeyError:
            return None

    def fi_login_status(self):
        try:
            return self.obj['fiLoginStatus']
        except KeyError:
            return None

    def exclusion_type(self):
        try:
            return self.obj['exclusionType']
        except KeyError:
            return None

    def account_add_date(self):
        try:
            return self.obj['addAccountDateInDate']
        except KeyError:
            return None

    def youdlee_account_number_last_4(self):
        try:
            return self.obj['yodleeAccountNumberLast4']
        except KeyError:
            return None

    def fi_last_updated(self):
        try:
            return self.obj['fiLastUpdated']
        except KeyError:
            return None

    def cc_aggr_status(self):
        try:
            return self.obj['ccAggrStatus']
        except KeyError:
            return None

    def last_updated_in_string(self):
        try:
            return self.obj['lastUpdatedInString']
        except KeyError:
            return None

    def fi_loging_display_name(self):
        try:
            return self.obj['fiLoginDisplayName']
        except KeyError:
            return None

    def yudlee_account_id(self):
        try:
            return self.obj['yodleeAccountId']
        except KeyError:
            return None

    def linked_account(self):
        try:
            return self.obj['linkedAccount']
        except KeyError:
            return None

    def status(self):
        try:
            return self.obj['status']
        except KeyError:
            return None

    def file_login_id(self):
        try:
            return self.obj['fiLoginId']
        except KeyError:
            return None

    def user_name(self):
        try:
            return self.obj['userName']
        except KeyError:
            return None

    def value(self):
        try:
            return self.obj['value']
        except KeyError:
            return None

    def account_type(self):
        try:
            return self.obj['accountType']
        except KeyError:
            return None

    def is_account_closed_by_mint(self):
        try:
            return self.obj['isAccountClosedByMint']
        except KeyError:
            return None

    def fi_login_ui_status(self):
        try:
            return self.obj['fiLoginUIStatus']
        except KeyError:
            return None

    def link_status(self):
        try:
            return self.obj['linkStatus']
        except KeyError:
            return None

    def is_error(self):
        try:
            return self.obj['isError']
        except KeyError:
            return None

    def is_active(self):
        try:
            return self.obj['isActive']
        except KeyError:
            return None

    def link_creation_time(self):
        try:
            return self.obj['linkCreationTime']
        except KeyError:
            return None

    def name(self):
        try:
            return self.obj['name']
        except KeyError:
            return None

    def yodlee_name(self):
        try:
            return self.obj['yodleeName']
        except KeyError:
            return None

    def fi_name(self):
        try:
            return self.obj['fiName']
        except KeyError:
            return None

    def usage_type(self):
        try:
            return self.obj['usageType']
        except KeyError:
            return None

    def account_status(self):
        try:
            return self.obj['accountStatus']
        except KeyError:
            return None

    def is_hidden_from_planning_trends(self):
        try:
            return self.obj['isHiddenFromPlanningTrends']
        except KeyError:
            return None

    def account_system_status(self):
        try:
            return self.obj['accountSystemStatus']
        except KeyError:
            return None

    def class_name(self):
        try:
            return self.obj['klass']
        except KeyError:
            return None

    def current_balance(self):
        try:
            return self.obj['currentBalance']
        except KeyError:
            return None

    def fi_last_updated_in_date(self):
        try:
            return self.obj['fiLastUpdatedInDate']
        except KeyError:
            return None

    def dump(self):
        print self.account_name()
        print "Account:" + str(self.account_name())
        items = MintAccount.__dict__
        for item in items:
            if item != "dump" and item != "__init__":
                to_call = getattr(self, item)
                if callable(to_call):
                    print str(item) + ":" + str(to_call())
        print "========="
