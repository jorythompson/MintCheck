import sys
import traceback
import mintapi
import mintObjects
import mintReport
import argparse
import cPickle
import datetime
from dateutil.relativedelta import relativedelta
from mintConfigFile import MintConfigFile
from emailSender import EmailSender
from random import randint
import time

########################################################################################################################
# put a script into /etc/cron.daily (or under /etc/cron.X) and run the following to verify:
# run-parts --test /etc/cron.daily
########################################################################################################################


class MintCheck:
    def __init__(self):
        self.args = None
        self.accounts = None
        self.mint_transactions = None
        self.args = MintCheck._get_args()
        self.config = MintConfigFile(self.args.config, test_email=self.args.validate_emails,
                                     validate=self.args.validate_ini)
        self.logger = self.config.logger
        self.now = datetime.datetime.now()
        self.logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))

    def connect(self):
        return mintapi.Mint(email=self.config.mint_username, password=self.config.mint_password,
                            ius_session=self.config.mint_cookie, thx_guid=self.config.mint_cookie_2)

    def _get_data(self, start_date):
        self.logger.info("getting data...")
        if self.config.debug_download:
            self.logger.debug("Connecting to Mint...")
            mint = self.connect()
            # todo remove if True below
            if True: #self.args.live:
                self.logger.debug("Refreshing Mint")
                mint.initiate_account_refresh()
                self.logger.debug("Closing the Mint connection")
                mint.close()
                sleep_time = 5 * 60 + randint(0, 5 * 60)  # sleep 5 minutes + some random time while mint refreshes
                self.logger.info("Waiting for Mint to update accounts. Starting to sleep at "
                                 + datetime.datetime.now().strftime('%H:%M:%S') + " for "
                                 + datetime.datetime.fromtimestamp(sleep_time).strftime('%M minutes and %S seconds')
                                 + " waking at " + (datetime.datetime.now() +
                                                     datetime.timedelta(seconds=sleep_time)).strftime('%H:%M:%S'))
                time.sleep(sleep_time)
                self.logger.debug("Reconnecting to Mint...")
                mint = self.connect()
            self.logger.info("getting accounts...")
            self.accounts = mintObjects.MintAccounts(mint.get_accounts(get_detail=True), self.logger)
            self.logger.info("Getting transactions...")
            self.mint_transactions = mintObjects.MintTransactions(
                mint.get_transactions_json(include_investment=False, skip_duplicates=self.config.mint_remove_duplicates,
                                           start_date=start_date.strftime('%m/%d/%y')), self.logger)
            self.logger.debug("pickling...")
            self.pickle()
        else:
            self.logger.debug("unpicking...")
            self.unpickle()
            if self.config.debug_debugging:
                self.accounts.dump(self.logger)
                self.mint_transactions.dump(self.logger)

        self.logger.info("assembling \"paid from\" accounts")
        for paid_from in self.config.paid_from:
            for account in self.accounts.accounts:
                if paid_from["debit account"] == account["accountName"]:
                    paid_from["balance"] = account["value"]
                    break
        pass

    @staticmethod
    def _get_args():
        parser = argparse.ArgumentParser(description='Read Information from Mint')
        parser.add_argument('--live', action="store_true", default=False,
                            help='Indicates MintCheck is running live and should sleep a random period of time before '
                                 'hitting Mint.com.  It also refreshes Mint and sleeps for 15 minutes while Mint '
                                 'updates itself.')
        parser.add_argument('--config', required=True, help='Configuration file containing your username, password, and mint cookie')
        parser.add_argument('--validate_ini', action="store_true", default=False, help='Validates the input configuration file')
        parser.add_argument('--validate_emails',  action="store_true", default=False, help='Validates sending emails to all users in the configuration file')
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
            start_date = self.now + relativedelta(days=-8)
            frequency = ["daily", "weekly"]
        elif "daily" in data_needed:
            start_date = self.now + relativedelta(days=-2)
            frequency = ["daily"]
        else:
            start_date = None
            frequency = None
        if start_date is not None:
            self.logger.info("getting transactions from " + start_date.strftime('%m/%d/%Y') + "...")
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
        with open(self.config.debug_pickle_file, 'wb') as handle:
            # cPickle.dump(self.budgets, handle)
            cPickle.dump(self.accounts, handle)
            cPickle.dump(self.mint_transactions, handle)
            # cPickle.dump(self.net_worth, handle)

    def unpickle(self):
        with open(self.config.debug_pickle_file, 'rb') as handle:
            # self.budgets = cPickle.load(handle)
            self.accounts = cPickle.load(handle)
            self.mint_transactions = cPickle.load(handle)
            # self.net_worth = cPickle.load(handle)


def main():
    mint_check = MintCheck()
    logger = None
    for count in range(1, 4):
        try:
            if mint_check.args.live:
                sleep_time = randint(0, 60 * mint_check.config.general_sleep)
                mint_check.logger.info("Waiting a random time so we don't connect to Mint at the same time every day."
                                       "  Starting to sleep at " + datetime.datetime.now().strftime('%H:%M:%S') +
                                       " for " +
                                        datetime.datetime.fromtimestamp(sleep_time).strftime(
                                            '%M minutes and %S seconds') + " waking at " +
                                        (datetime.datetime.now() +
                                         datetime.timedelta(seconds=sleep_time)).strftime('%H:%M:%S'))
                time.sleep(sleep_time)
            logger = mint_check.logger
            mint_check.collect_and_send()
            break
        except Exception as (e):
            if count >= 4:
                failed_message = "Exception caught!  Tried " + str(count) + " times.  Last exception follows:"
                if logger is not None:
                    logger.critical(failed_message)
                type_, value_, traceback_ = sys.exc_info()
                traceback.print_exc()
                message = "<html>"
                message += "<b><center>" + failed_message + "</center></b><br>"
                tb = traceback.format_exception(type_, value_, traceback_)
                for line in tb:
                    message += line + "<br>"
                    if logger is not None:
                        logger.critical(line)
                message += "\n Log information:\n"
                with open(mint_check.config.general_log_file, 'r') as f:
                    data = f.read().replace("\n", "<br>")
                message += data
                email_sender = EmailSender(mint_check.config.email_connection, mint_check.logger)
                for email_to in mint_check.config.general_exceptions_to:
                    if mint_check.config.debug_copy_admin:
                        cc = mint_check.config.general_admin_email
                    else:
                        cc = None
                    email_sender.send(email_to, "Exception caught in MintCheck", message, cc)
    mint_check.logger.info("Done!")

if __name__ == "__main__":
    main()
