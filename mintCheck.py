import mintapi
import mintObjects
import mintReport
import argparse
import cPickle
import datetime
from dateutil.relativedelta import relativedelta
from mintConfigFile import MintConfigFile

########################################################################################################################
# put a script into /etc/cron.daily (or under /etc/cron.X) and run the following to verify:
# run-parts --test /etc/cron.daily
########################################################################################################################


class MintCheck:
    PICKLE_FILE = "\\\\andraia\\jordan\\pythonDevelopment\\mintToEvernote\\MintCheck\\pickle.txt"

    def __init__(self):
        self.args = None
        self.accounts = None
        self.mint_transactions = None
        self.args = MintCheck.get_args()
        self.config = MintConfigFile(self.args.config)
        self.logger = self.config.logger
        self.now = datetime.datetime.now()
        # self.now = datetime.datetime.strptime('10/01/2016', '%m/%d/%Y') # first of month
        # self.now = datetime.datetime.strptime('10/27/2016', '%m/%d/%Y') # no activity for the last couple of days
        #self.now = datetime.datetime.strptime('10/02/2016', '%m/%d/%Y')  #
        self.logger.debug("Today is " + self.now.strftime('%m/%d/%Y'))

    def _get_data(self, start_date):
        if self.config.general_dev_only:
            self.logger.debug("unpicking...")
            self.unpickle()
        else:
            self.logger.debug("Connecting to Mint...")
            mint = mintapi.Mint(email=self.config.mint_username, password=self.config.mint_password,
                                ius_session=self.config.mint_cookie)
            self.logger.debug(("Getting transactions..."))
            self.mint_transactions = mintObjects.MintTransactions(
                mint.get_transactions_json(include_investment=False, skip_duplicates=False,
                                           start_date=start_date.strftime('%m/%d/%y')))
            self.logger.debug("getting accounts...")
            self.accounts = mintObjects.MintAccounts(mint.get_accounts(get_detail=True))
            self.logger.debug("pickling...")
            self.pickle()

    @staticmethod
    def get_args():
        parser = argparse.ArgumentParser(description='Read Information from Mint')
        parser.add_argument('--config', help='Configuration file containing your username, password, and mint cookie')
        return parser.parse_args()

    def get_start_date(self, data_needed):
        if self.now.day == 1 and \
                        "monthly" in data_needed and \
                        self.now.strftime("%A").lower() == self.config.general_week_start.lower() and \
                        "weekly" in data_needed:
            start_date = self.now + relativedelta(months=-1)
            frequency = ["monthly", "weekly", "daily"]
        elif self.now.day == 1 and "monthly" in data_needed:
            # first of the month: get all of last month
            start_date = self.now + relativedelta(months=-1)
            frequency = ["daily", "monthly"]
        elif self.now.strftime("%A").lower() == self.config.general_week_start.lower() and \
                        "weekly" in data_needed:
            # Sunday: get last weeks
            start_date = self.now + relativedelta(days=-7)
            frequency = ["daily", "weekly"]
        elif "daily" in data_needed:
            start_date = self.now + relativedelta(days=-1)
            frequency = ["daily"]
        else:
            start_date = None
            frequency = None
        self.logger.debug("getting transactions from " + start_date.strftime('%m/%d/%Y') + "...")
        return start_date, frequency

    def collect_and_send(self):
        data_needed = []
        for user in self.config.users:
            for frequency in user.frequency:
                if frequency not in data_needed:
                    data_needed.append(frequency)

        start_date, frequency = self.get_start_date(data_needed)
        if start_date is not None:
            self._get_data(start_date)
            report = mintReport.PrettyPrint(self.accounts, self.mint_transactions, self.config, start_date, self.now,
                                            self.logger)
            report.send_data(frequency)

    def pickle(self):
        with open(MintCheck.PICKLE_FILE, 'wb') as handle:
            # cPickle.dump(self.budgets, handle)
            cPickle.dump(self.accounts, handle)
            cPickle.dump(self.mint_transactions, handle)
            # cPickle.dump(self.net_worth, handle)

    def unpickle(self):
        with open(MintCheck.PICKLE_FILE, 'rb') as handle:
            # self.budgets = cPickle.load(handle)
            self.accounts = cPickle.load(handle)
            self.mint_transactions = cPickle.load(handle)
            # self.net_worth = cPickle.load(handle)


def main():
    mint_check = MintCheck()
    logger = mint_check.logger
    mint_check.collect_and_send()
    logger.debug("Done!")

if __name__ == "__main__":
    main()
