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
import logging
from mintSheets import MintSheet

# from datetime import datetime, date, time
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
        self.now = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))

    def connect(self):
        return mintapi.Mint(email=self.config.mint_username, password=self.config.mint_password,
                            ius_session=self.config.mint_cookie, thx_guid=self.config.mint_cookie_2)

    def _get_data(self, start_date):
        self.logger.info("getting transactions from " + start_date.strftime('%m/%d/%Y') + "...")
        if self.config.debug_mint_download:
            self.logger.debug("Connecting to Mint...")
            mint = self.connect()
            if self.args.live:
                self.logger.debug("Refreshing Mint")
                mint.initiate_account_refresh()
                self.logger.debug("Closing the Mint connection")
                mint.close()
                sleep_time = 5 * 60 + randint(0, 5 * 60)  # sleep 5 minutes + some random time while mint refreshes
                self.logger.info("Waiting for Mint to update accounts. Starting to sleep at "
                                 + datetime.datetime.now().strftime('%H:%M:%S') + " for "
                                 + datetime.datetime.fromtimestamp(sleep_time).strftime('%M minutes and %S seconds')
                                 + ", waking at " + (datetime.datetime.now() +
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
            self.logger.debug("pickling mint objects...")
            self.pickle_mint()
        else:
            self.logger.debug("unpicking mint objects...")
            self.unpickle_mint()
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
        parser.add_argument('--config', required=True,
                            help='Configuration file containing your username, password, and mint cookie')
        parser.add_argument('--validate_ini', action="store_true", default=False,
                            help='Validates the input configuration file')
        parser.add_argument('--validate_emails',  action="store_true", default=False,
                            help='Validates sending emails to all users in the configuration file')
        return parser.parse_args()

    @staticmethod
    def get_start_date(now, week_start, month_start, frequencies_needed):
        start_date = None
        frequency = None
        if (now.day == month_start) and ("monthly" in frequencies_needed):
            start_date = now + relativedelta(months=-1)
            frequency = "monthly"
        elif now.strftime("%A").lower() == week_start.lower()\
                and "weekly" in frequencies_needed:
            start_date = now + relativedelta(days=-7)
            frequency = "weekly"
        elif "daily" in frequencies_needed:
            start_date = now + relativedelta(days=-1)
            frequency = "daily"
        return start_date, frequency

    def collect_and_send(self):
        frequencies_needed = []
        for user in self.config.users:
            for frequency in user.frequency:
                if frequency not in frequencies_needed:
                    frequencies_needed.append(frequency)

        if len(frequencies_needed) > 0:
            start_date, ignore = self.get_start_date(self.now, self.config.general_week_start,
                                                     self.config.general_month_start, frequencies_needed)
            if start_date is not None:
                self._get_data(start_date)
                mint_sheet = MintSheet(self.config, start_date)

                report = mintReport.PrettyPrint(self.accounts, self.mint_transactions, mint_sheet,
                                                self.config, start_date, self.logger)
                report.send_data()

    def pickle_mint(self):
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'wb') as handle:
                cPickle.dump(self.accounts, handle)
                cPickle.dump(self.mint_transactions, handle)

    def unpickle_mint(self):
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'rb') as handle:
                self.accounts = cPickle.load(handle)
                self.mint_transactions = cPickle.load(handle)


def main():
    mint_check = MintCheck()
    logger = mint_check.logger
    for count in range(1, 5):
        try:
            if mint_check.args.live:
                sleep_time = randint(0, 60 * mint_check.config.general_sleep)
                mint_check.logger.info("Waiting a random time so we don't connect to Mint at the same time every day."
                                       + "  Starting to sleep at " + datetime.datetime.now().strftime('%H:%M:%S')
                                       + " for "
                                       + datetime.datetime.fromtimestamp(sleep_time).
                                       strftime('%M minutes and %S seconds')
                                       + ", waking at " + (datetime.datetime.now()
                                                           + datetime.timedelta(seconds=sleep_time)).
                                       strftime('%H:%M:%S'))
                time.sleep(sleep_time)
            logger = mint_check.logger
            mint_check.collect_and_send()
            break
        except:
            if logger is None:
                logger = logging.getLogger(__name__)
            logger.critical("Exception caught!  Tried " + str(count) + " times.")
            type_, value_, traceback_ = sys.exc_info()
            traceback.print_exc()
            tb = traceback.format_exception(type_, value_, traceback_)
            for line in tb:
                logger.critical(line)
            if count >= 4:
                logger.critical("Last exception follows:")
                type_, value_, traceback_ = sys.exc_info()
                traceback.print_exc()
                message = "<html>"
                message += "<b><center>Problem with Mint Checker</center></b><br>"
                tb = traceback.format_exception(type_, value_, traceback_)
                for line in tb:
                    message += line + "<br>"
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
