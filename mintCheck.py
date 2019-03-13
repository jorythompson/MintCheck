import sys
import traceback
import mintapi
import mintObjects
import mintReport
import argparse
import pickle
import datetime
from dateutil.relativedelta import relativedelta
from mintConfigFile import MintConfigFile
from emailSender import EmailSender
from random import randint
import time
import logging
import logging.config
from mintSheets import MintSheet
import os
import thompco_utils

# from datetime import datetime, date, time
########################################################################################################################
# put a script into /etc/cron.daily (or under /etc/cron.X) and run the following to verify:
# run-parts --test /etc/cron.daily
########################################################################################################################


class MintCheck:
    def __init__(self):
        logger = thompco_utils.get_logger()
        self.args = None
        self.accounts = None
        self.mint_transactions = None
        self.args = MintCheck._get_args()
        self.config = MintConfigFile(self.args.config, test_email=self.args.validate_emails,
                                     validate=self.args.validate_ini)
        self.now = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.prompt_for_text = None
        self.mint = None
        logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))

    def connect(self):
        return mintapi.Mint.create(email=self.config.mint_username, password=self.config.mint_password,
                                   headless=self.config.headless, mfa_method="sms")

    def _get_data(self, start_date):
        logger = thompco_utils.get_logger()
        logger.info("getting transactions from " + start_date.strftime('%m/%d/%Y') + "...")
        if self.config.debug_mint_download:
            logger.debug("Connecting to Mint...")
            self.mint = self.connect()
            logger.info("getting accounts...")
            self.accounts = self.mint.get_accounts(get_detail=False)
            logger.info("Getting transactions...")
            self.mint_transactions = self.mint.get_transactions_json(include_investment=False,
                                                                     skip_duplicates=self.config.mint_remove_duplicates,
                                                                     start_date=start_date.strftime('%m/%d/%y'))
            logger.debug("pickling mint objects...")
            self.pickle_mint()
        else:
            self.unpickle_mint()
        self.mint_transactions = mintObjects.MintTransactions(self.mint_transactions)
        if self.config.debug_debugging:
            self.accounts.dump()
            self.mint_transactions.dump()

        logger.info("assembling \"paid from\" accounts")
        for paid_from in self.config.paid_from:
            for account in self.accounts:
                if paid_from["debit account"] == account["accountName"]:
                    paid_from["balance"] = account["value"]
                    break

    @staticmethod
    def _get_args():
        parser = argparse.ArgumentParser(description='Read Information from Mint')
        parser.add_argument('--live', action="store_true", default=False,
                            help='Indicates Mint Checker is running live and should sleep a random period of time before '
                                 'hitting Mint.com.  It also refreshes Mint and sleeps for 15 minutes while Mint '
                                 'updates itself.')
        parser.add_argument('--config', required=True,
                            help='Configuration file containing your username, password,etc')
        parser.add_argument('--validate_ini', action="store_true", default=False,
                            help='Validates the input configuration file')
        parser.add_argument('--validate-emails',  action="store_true", default=False,
                            help='Validates sending emails to all users in the configuration file')
        parser.add_argument('--prompt-for-text',  action="store_true", default=False,
                            help='Requests Mint to send validation via text')
        return parser.parse_args()

    @staticmethod
    def get_start_date(now, week_start, month_start, frequencies_needed):
        start_date = None
        frequency = None
        week_start = week_start.lower()
        today = now.strftime("%A").lower()
        if (now.day == month_start) and ("monthly" in frequencies_needed):
            start_date = now + relativedelta(months=-1)
            frequency = "monthly"
        elif week_start == today and "biweekly" in frequencies_needed \
                and ((month_start+7 <= now.day < month_start+14)
                     or (month_start+21 <= now.day < month_start+28)):
            start_date = now + relativedelta(days=-14)
            frequency = "biweekly"
        elif today == week_start and "weekly" in frequencies_needed:
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
            max_day_error = 0
            for sheet in self.config.google_sheets:
                if sheet.day_error > max_day_error:
                    max_day_error = sheet.day_error
            start_date, ignore = self.get_start_date(self.now, self.config.general_week_start,
                                                     self.config.general_month_start, frequencies_needed)
            if start_date is not None:
                self._get_data(start_date - datetime.timedelta(days=max_day_error))
                mint_sheet = MintSheet(self.config, start_date)
                report = mintReport.PrettyPrint(self.accounts, self.mint_transactions, mint_sheet,
                                                self.config)
                report.send_data()

    def pickle_mint(self):
        logger = thompco_utils.get_logger()
        logger.debug("pickling mint objects...")
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'wb') as handle:
                pickle.dump(self.accounts, handle)
                pickle.dump(self.mint_transactions, handle)

    def unpickle_mint(self):
        logger = thompco_utils.get_logger()
        logger.debug("unpicking mint objects...")
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'rb') as handle:
                self.accounts = pickle.load(handle)
                self.mint_transactions = pickle.load(handle)


def main():
    logger = thompco_utils.get_logger()
    local_path = os.path.dirname(os.path.abspath(__file__))
    log_configuration_file = os.path.join(local_path, 'logging.conf')
    logging.config.fileConfig(log_configuration_file)
    logger.info("Getting logging configuration from:" + log_configuration_file)
    success = False
    mint_check = None
    for attempt in range(3):
        # Occasionally Mint fails with strange exceptions.  This loop will try several times before giving up.
        # Note that each failure will email the exception to the appropriate recipients
        if not success:
            if mint_check is None:
                mint_check = MintCheck()
            try:
                if mint_check.args.live:
                    sleep_time = randint(0, 60 * mint_check.config.general_sleep)
                    logger.info("Waiting a random time so we don't connect to Mint at the same time every day."
                                + "  Starting to sleep at " + datetime.datetime.now().strftime('%H:%M:%S') + " for "
                                + datetime.datetime.fromtimestamp(sleep_time).strftime('%M minutes and %S seconds')
                                + ", waking at "
                                + (datetime.datetime.now() +
                                   datetime.timedelta(seconds=sleep_time)).strftime('%H:%M:%S'))
                    time.sleep(sleep_time)
                mint_check.collect_and_send()
                success = True
            except Exception as e:
                if "Session has expired" not in str(e):
                    logger.critical("Exception caught!")
                    print(traceback.format_exc())
                    if mint_check is None:
                        logger.critical("mint_check is None")
                    elif mint_check.mint is None:
                        logger.critical("mint_check.mint is None")
                    else:
                        mint_check.mint.driver.quit()
                    type_, value_, traceback_ = sys.exc_info()
                    traceback.print_exc()
                    tb = traceback.format_exception(type_, value_, traceback_)
                    for line in tb:
                        logger.critical(line)
                    logger.critical("Last exception follows:")
                    type_, value_, traceback_ = sys.exc_info()
                    traceback.print_exc()
                    message = "<html>"
                    message += "<b><center>Problem with Mint Checker</center></b><br>"
                    tb = traceback.format_exception(type_, value_, traceback_)
                    for line in tb:
                        message += line + "<br>"
                        logger.critical(line)
                    message += "\nLog information:\n"
                    email_sender = EmailSender(mint_check.config.email_connection)
                    for email_to in mint_check.config.general_exceptions_to:
                        try:
                            email_sender.send(to_email=email_to, subject="Exception caught in Mint Checker",
                                              message=message, attach_file=thompco_utils.get_log_file_name())
                        except Exception as e:
                            email_sender.send(to_email=email_to, subject="Exception caught in Mint Checker",
                                              message=message)
    logger.info("Done!")


if __name__ == "__main__":
    main()
