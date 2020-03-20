from thompcoutils.log_utils import get_logger, get_log_file_name
import thompcoutils.os_utils as os_utils
import traceback
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
import os
import sys
import psutil
sys.path.insert(0, '../mintapi')
import mintapi


# from datetime import datetime, date, time
########################################################################################################################
# put a script into /etc/cron.daily (or under /etc/cron.X) and run the following to verify:
# run-parts --test /etc/cron.daily
########################################################################################################################


class MintCheck:
    def __init__(self):
        logger = get_logger()
        self.args = None
        self.accounts = None
        self.mint_transactions = None
        self.args = MintCheck._get_args()
        self.config = MintConfigFile(self.args.config, test_email=self.args.validate_emails)
        self.now = datetime.datetime.now()
        self.prompt_for_text = None
        self.mint = None
        self.credit_score = None
        self.net_worth = None
        self.attention = None
        self.status = "constructing"
        logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))

    def connect(self):
        logger = get_logger()
        self.status = "creating Mint API connection.  Could be up to {} minute{}".\
            format(self.config.wait_for_sync,
                   '' if self.config.wait_for_sync == 1 else 's')
        if os.path.exists(self.config.session_path):
            if not os.path.isdir(self.config.session_path):
                raise Exception("{} must either not exist or be a folder".format(self.config.session_path))
        else:
            os.makedirs(self.config.session_path)

        logger.debug(self.status)
        return mintapi.Mint.create(email=self.config.mint_username, password=self.config.mint_password,
                                   headless=self.config.headless, mfa_method="sms",
                                   session_path=self.config.session_path,
                                   wait_for_sync=True, wait_for_sync_timeout=self.config.wait_for_sync*60)

    def _get_data(self):
        logger = get_logger()
        start_date = datetime.datetime.today() - datetime.timedelta(days=31)
        logger.info("getting transactions from " + start_date.strftime('%m/%d/%Y') + "...")
        if self.config.debug_mint_download:
            logger.debug("Connecting to Mint...")
            self.status = "Connecting"
            self.mint = self.connect()
            self.attention = self.mint.get_attention()
            logger.info("getting accounts...")
            self.accounts = self.mint.get_accounts(get_detail=False)
            logger.info("Getting transactions...")
            self.mint_transactions = self.mint.get_transactions_json(include_investment=True,
                                                                     skip_duplicates=self.config.mint_remove_duplicates,
                                                                     start_date=start_date.strftime('%m/%d/%y'))
            message = "Getting net worth...{}{}"
            try:
                self.net_worth = self.mint.get_net_worth(self.accounts)
                logger.debug(message.format("success", ""))
            except Exception as e:
                logger.debug(message.format("failed", str(e)))
            message = "Getting credit score...{}{}"
            try:
                self.credit_score = self.mint.get_credit_score()
                logger.debug(message.format("success", ""))
            except Exception as e:
                self.credit_score = None
                logger.debug(message.format("failed", str(e)))
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
                            help='Indicates Mint Checker is running live and should sleep a random period of time '
                                 'before hitting Mint.com.  It also refreshes Mint and sleeps while Mint updates '
                                 'itself.')
        parser.add_argument('--config', required=True,
                            help='Configuration file containing your username, password,etc')
        parser.add_argument('--validate_ini', action="store_true", default=False,
                            help='Validates the input configuration file')
        parser.add_argument('--validate-emails',  action="store_true", default=False,
                            help='Validates sending emails to all users in the configuration file')
        parser.add_argument('--prompt-for-text',  action="store_true", default=False,
                            help='Requests Mint to send validation via text')
        return parser.parse_args()

    """
    This is really the right way to get the start date.  It looks at the frequencies needed and the current date to
    determine the date to begin collecting data from.  Currently I am using today - 31 (one month of data) to ensure
    we get enough data for subsequent testing.
    """
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
            '''
            This is intended to limit the data required for this report.  For now, I am looking back 31 days.
            start_date, ignore = self.get_start_date(self.now, self.config.general_week_start,
                                                     self.config.general_month_start, frequencies_needed)
            if start_date is not None:
                self._get_data(start_date - datetime.timedelta(days=max_day_error))
            '''
            self._get_data()
            report = mintReport.PrettyPrint(self)
            report.send_data()

    def pickle_mint(self):
        logger = get_logger()
        logger.debug("pickling mint objects...")
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'wb') as handle:
                pickle.dump(self.accounts, handle)
                pickle.dump(self.mint_transactions, handle)
                pickle.dump(self.credit_score, handle)
                pickle.dump(self.net_worth, handle)
                pickle.dump(self.attention, handle)

    def unpickle_mint(self):
        logger = get_logger()
        logger.debug("unpicking mint objects...")
        if self.config.debug_mint_pickle_file is not None:
            with open(self.config.debug_mint_pickle_file, 'rb') as handle:
                self.accounts = pickle.load(handle)
                self.mint_transactions = pickle.load(handle)
                self.credit_score = pickle.load(handle)
                self.net_worth = pickle.load(handle)
                self.attention = pickle.load(handle)


def kill_chrome(all_chromes=False):
    if all_chromes:
        if os_utils.os_type() == os_utils.OSType.WINDOWS:
            chrome_processes = os_utils.find_processes("chrome.exe")
        else:
            chrome_processes = os_utils.find_processes("Google Chrome")
        for process in chrome_processes:
            os_utils.kill_process(process)
    else:
        if os_utils.os_type() == os_utils.OSType.WINDOWS:
            chrome_processes = os_utils.find_processes("chrome.exe")
            parents = []
            for parent in chrome_processes:
                for child in chrome_processes:
                    if child.ppid() == parent.pid:
                        parents.append(parent)
                        break
            chrome_processes = parents
        else:
            chrome_processes = os_utils.find_processes("Google Chrome")

        for process in chrome_processes:
            child_processes = os_utils.list_child_processes(process.pid)
            if len(child_processes) < 10:
                os_utils.kill_process(process)


def kill_procs(session_path):
    for proc in psutil.process_iter():
        try:
            # this returns the list of opened files by the current process
            flist = proc.open_files()
            if flist:
                print("PID:{}, Name:{}".format(proc.pid, proc._name))
                if "Google" in proc._name:
                    for nt in flist:
                        print("\t", nt.path)
                        if session_path in nt:
                            os_utils.kill_process(proc)
                            print("\t", nt.path)

        # This catches a race condition where a process ends
        # before we can examine its files
        except Exception as err:
            print("****", err)
    pass


def load_log_config():
    logger = get_logger()
    local_path = os.path.dirname(os.path.abspath(__file__))
    log_configuration_file = os.path.join(local_path, 'logging.conf')
    logging.config.fileConfig(log_configuration_file)
    # os.remove(logger.manager.root.handlers[0].baseFilename)
    # logging.config.fileConfig(log_configuration_file)
    logger.info("Beginning logging with configuration from:" + log_configuration_file)


def main():
    load_log_config()
    logger = get_logger()
    success = False
    mint_check = MintCheck()
    email_sender = EmailSender(mint_check.config.email_connection)
    for attempt in range(mint_check.config.max_retries):
        # Occasionally Mint fails with strange exceptions.  This loop will try several times before giving up.
        # Note that each failure will email the exception to the appropriate recipients
        if not success:
            if mint_check is None:
                mint_check = MintCheck()
            else:
                kill_chrome(mint_check.config.kill_all_chromes)
                # kill_procs(mint_check.config.session_path)
            try:
                if mint_check.args.live:
                    sleep_time = randint(0, 60 * mint_check.config.general_sleep)
                    logger.info("Waiting a random time so we don't connect to Mint at the same time every day."
                                + "  Starting to sleep at " + datetime.datetime.now().strftime('%H:%M:%S') + " for "
                                + datetime.datetime.fromtimestamp(sleep_time).strftime('%M minute(s) and %S second(s)')
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
                    elif mint_check.mint.driver is None:
                        logger.critical("mint_check.mint.driver is None")
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
                    subject = "Exception {} of {} caught in Mint Checker at {} while {}".\
                        format(attempt+1, mint_check.config.max_retries, mint_check.now, mint_check.status)
                    send_admin_message(email_sender, mint_check.config.general_exceptions_to, subject=subject,
                                       message=message)
    if not success:
        send_admin_message(email_sender, mint_check.config.general_exceptions_to,
                           "Too many attempts {}".format(mint_check.config.max_retries),
                           "The connection is timing out")

    logger.info("Done!")


def send_admin_message(email_sender, admin_emails, subject, message):
    for email_to in admin_emails:
        # noinspection PyBroadException
        try:
            email_sender.send(to_email=email_to,
                              subject=subject,
                              message=message, attach_file=get_log_file_name())
        except Exception:
            email_sender.send(to_email=email_to, subject=subject,
                              message=message)


if __name__ == "__main__":
    main()
