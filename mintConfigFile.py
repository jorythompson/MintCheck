import ast
import logging.config
import logging.handlers
import locale
import datetime
import dateutil
from dateutil.relativedelta import relativedelta
from thompcoutils.log_utils import get_logger
from thompcoutils.config_utils import ConfigManager
from thompcoutils.email_utils import EmailConnectionConfig
import os
import platform
import pathlib

# mint connection block
MINT_TITLE = "mint connection"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
HEADLESS = "headless"
SESSION_PATH = "session_path"
MINT_REMOVE_DUPLICATES = "remove_duplicates"
MINT_IGNORE_ACCOUNTS = "ignore_accounts_containing"
MFA_TITLE = "mfa"

# multi factor authentication block
MFA_METHOD = 'mfa_method'
IMAP_ACCOUNT = 'imap_account'
IMAP_PASSWORD = 'imap_password'
IMAP_SERVER = 'imap_server'
IMAP_FOLDER = 'imap_folder'


# general block
GENERAL_TITLE = "general"
GENERAL_WEEK_START = "week_start"
GENERAL_MONTH_START = "month_start"
GENERAL_ADMIN_EMAIL = "admin_email"
GENERAL_USERS = "users"
GENERAL_MAX_SLEEP = "max_sleep"
GENERAL_EXCEPTIONS_TO = "exceptions_to"
GENERAL_PICKLE_FOLDER = "pickle_folder"
GENERAL_HTML_FOLDER = "html_folder"
GENERAL_POST_CONNECT_SLEEP = "post_connect_sleep"
GENERAL_MAX_RETRIES = "max_retries"
GENERAL_MIN_SPEND_THRESHOLD = "min_spend_threshold"
GENERAL_MIN_SPEND_COLOR = "min_spend_color"
GENERAL_MAX_SPEND_THRESHOLD = "max_spend_threshold"
GENERAL_MAX_SPEND_COLOR = "max_spend_color"
GENERAL_CREDIT_REPORT_TITLE = "credit_report_title"
GENERAL_NET_WORTH_TITLE = "net_worth_title"

# Email block
EMAIL_TITLE = 'email connection'

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACTIVE_ACCOUNTS = "active_accounts"
USER_ACCOUNTS = "accounts"
ALLOWED_USER_FREQUENCIES = ["daily", "weekly", "monthly", "biweekly"]
USER_FREQUENCY = "frequency"
USER_RENAME_ACCOUNT = "rename_account"
USER_RENAME_INSTITUTION = "rename_institution"
CREDIT_REPORT = "credit_report"

LOCALE_TITLE = "locale"

DEBUG_TITLE = "debug"
DEBUG_MINT_DOWNLOAD = "download_mint"
DEBUG_MINT_PICKLE_FILE = "mint_pickle_file"
ACCOUNTS_PICKLE_FILE = "accounts_pickle_file"
DEBUG_DEBUGGING = "debugging"
DEBUG_COPY_ADMIN = "copy_admin"
DEBUG_SAVE_HTML = "save_html"
DEBUG_SEND_EMAIL = "send_email"
DEBUG_ATTACH_LOG = "attach_log"

COLORS_TITLE = "colors"
ACCOUNT_TYPES_TITLE = "account_types"
ACCOUNT_TYPES_BANK_FG = "bank_fg_color"
ACCOUNT_TYPES_CREDIT_FG = "credit_fg_color"

PAST_DUE_TITLE = "past_due"
PAST_DUE_DAYS_BEFORE = "days_before"
PAST_DUE_FOREGROUND_COLOR = "fg_color"
PAST_DUE_BACKGROUND_COLOR = "bg_color"


BALANCE_WARNINGS_TITLE = "balance warnings"
PAID_FROM_TITLE = "paid from"

SKIP_TITLES = [MINT_TITLE, GENERAL_TITLE, EMAIL_TITLE, LOCALE_TITLE, DEBUG_TITLE, COLORS_TITLE,
               ACCOUNT_TYPES_TITLE, PAST_DUE_TITLE, BALANCE_WARNINGS_TITLE, PAID_FROM_TITLE, MFA_TITLE]


class ConfigManagerException(Exception):
    pass


class BalanceWarning:
    def __init__(self, key, val):
        self.account_name = key
        for comparator in [">", "<", "="]:
            if comparator in val:
                self.amount = float(val.replace(comparator, "").replace("$", "").replace(",", ""))
                self.comparator = comparator

    def dump(self):
        dump_config_value("account name", self.account_name)
        dump_config_value("comparator", self.comparator)
        dump_config_value("amount", self.amount)


class MintUser:
    # Throws an exception if email and active_accounts are not set
    def __init__(self, name, cfg_mgr):
        logger = get_logger()
        self.name = name
        self.email = cfg_mgr.read_entry(
            name,
            USER_EMAIL,
            ["first@a.com", "second@b.com"],
            "a list of emails you want to send this user's information to")
        self.subject = cfg_mgr.read_entry(
            name,
            USER_SUBJECT,
            "Hello from Mint Checker"
            "The subject line of the email message")
        self.frequency = cfg_mgr.read_entry(
            name,
            USER_FREQUENCY,
            ALLOWED_USER_FREQUENCIES,
            "How often do you want to be informed?")
        for freq in self.frequency:
            if freq not in ALLOWED_USER_FREQUENCIES:
                logger.warn("only values in " + str(ALLOWED_USER_FREQUENCIES) + " are permitted for "
                            + USER_FREQUENCY)
                raise ConfigManagerException("invalid user frequency")
        self.rename_accounts = cfg_mgr.read_entry(
            name,
            USER_RENAME_ACCOUNT,
            {"old name": "new name", "mint name": "my name"},
            "Rename accounts that Mint may have trouble with")
        self.rename_institutions = cfg_mgr.read_entry(
            name,
            USER_RENAME_INSTITUTION,
            {"old name": "new name", "mint name": "my name"},
            "Rename accounts that Mint may have trouble with")
        self.display_credit_report = cfg_mgr.read_entry(
            name, CREDIT_REPORT, False,
            "True want to report the mint user's credit report and net worth")
        self.active_accounts = cfg_mgr.read_entry(
            name,
            USER_ACTIVE_ACCOUNTS,
            ["account 1", "account 2"],
            "List of accounts for this user")
        pass

    def dump(self):
        dump_config_value(self.name)
        dump_config_value(USER_EMAIL, self.email)
        dump_config_value(USER_SUBJECT, self.subject)
        dump_config_value(USER_ACTIVE_ACCOUNTS, self.active_accounts)
        dump_config_value(USER_FREQUENCY, self.frequency)
        dump_config_value(USER_RENAME_ACCOUNT, self.rename_accounts)
        dump_config_value(USER_RENAME_INSTITUTION, self.rename_institutions)
        dump_config_value(CREDIT_REPORT, self.display_credit_report)


def dump_config_value(key, value=None):
    if value is None:
        print()
        print("[" + key + "]")
    else:
        print(key + ":" + str(value))


class MintConfigFile:
    def __init__(self, file_name, validate=False, test_email=False, out_file=None):
        logger = get_logger()
        create = out_file is not None
        cfg_mgr = ConfigManager(file_name, create=create)
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.debug("Starting session.old")
        self.mfa_method = cfg_mgr.read_entry(
            MFA_TITLE, MFA_METHOD,
            "MFA method",
            "Can be 'email' or 'soft-token'")
        self.imap_server = cfg_mgr.read_entry(
            MFA_TITLE, IMAP_SERVER,
            "imap.gmail.com",
            "IMAP server host name to connect to when retrieving MFA via email")
        self.imap_account = cfg_mgr.read_entry(
            MFA_TITLE, IMAP_ACCOUNT,
            "IMAP user account",
            "account name used to log in to your IMAP server")
        self.imap_password = cfg_mgr.read_entry(
            MFA_TITLE, IMAP_PASSWORD,
            "IMAP user password",
            "account password used to log in to your IMAP server")
        self.imap_folder = cfg_mgr.read_entry(
            MFA_TITLE, IMAP_FOLDER,
            "INBOX",
            "IMAP folder that receives MFA email")
        self.mint_username = cfg_mgr.read_entry(
            MINT_TITLE, MINT_USER_USERNAME,
            "Mint Username",
            "username to access Mint")
        self.mint_password = cfg_mgr.read_entry(
            MINT_TITLE, MINT_USER_PASSWORD,
            "Mint Password",
            "Password to access Mint")
        self.headless = cfg_mgr.read_entry(
            MINT_TITLE, HEADLESS,
            True,
            "True if you don't want chrome browser to display")
        session_path = cfg_mgr.read_entry(
            MINT_TITLE, SESSION_PATH,
            "session.old",
            "Location of the chromedriver session.old data")
        self.session_path = os.path.join(pathlib.Path(__file__).parent.absolute(), session_path)
        self.mint_ignore_accounts = cfg_mgr.read_entry(
            MINT_TITLE, MINT_IGNORE_ACCOUNTS,
            "duplicate",
            "accounts containing this string will be ignored")
        self.mint_remove_duplicates = cfg_mgr.read_entry(
            MINT_TITLE, MINT_REMOVE_DUPLICATES,
            True,
            "Sometimes Mint will duplicate accounts and transactions,"
            " setting this to True will help prevent this")
        colors = cfg_mgr.read_section(
            COLORS_TITLE,
            {"red": "\"fee, charge\"", "blue": "\"deposit\""},
            "Colors are used to indicate key words are in the transaction")
        self.color_tags = {}
        if colors is not None:
            for color in colors:
                self.color_tags[color] = ast.literal_eval("[" + colors[color].lower() + "]")
        self.general_week_start = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_WEEK_START,
            "Monday",
            "The day of the week that week starts")
        self.kill_all_chromes = cfg_mgr.read_entry(
            GENERAL_TITLE, "kill_all_chromes",
            False,
            "Kill ALL Chrome processes - good for servers")
        self.wait_for_sync = cfg_mgr.read_entry(
            GENERAL_TITLE, "wait_for_sync",
            5,
            "Wait for sync with Mint before proceeding (minutes)")

        self.general_month_start = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_MONTH_START,
            1,
            "The day of the month the month starts")
        self.credit_report_title = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_CREDIT_REPORT_TITLE,
            "Credit Report",
            "Title for the Credit Report section of the HTML")
        self.net_worth_title = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_NET_WORTH_TITLE,
            "Net Worth",
            "Title for the Net Worth section of the HTML")
        balance_warnings = cfg_mgr.read_section(
            BALANCE_WARNINGS_TITLE,
            {"Chase Checking": "< 25", "Savings": ">= 100"},
            "List of accounts with triggers that will be displayed")
        self.balance_warnings = []
        if balance_warnings is not None:
            for key in balance_warnings:
                try:
                    balance_warning = BalanceWarning(key, balance_warnings[key])
                    if balance_warning.account_name == "credit":
                        self.balance_warning_credit = balance_warning
                    elif balance_warning.account_name == "bank":
                        self.balance_warning_bank = balance_warning
                    else:
                        self.balance_warnings.append(balance_warning)
                except Exception as e:
                    logger.exception(e)
                    pass
        from_to = cfg_mgr.read_section(
            PAID_FROM_TITLE,
            {"PayPal": "Main Checking", "Chase Credit": "Savings"},
            "List of debit accounts and the accounts they are paid from")
        self.paid_from = []
        if not create:
            for (key, val) in from_to.items():
                temp = dict()
                temp["credit account"] = key
                temp["debit account"] = val
                self.paid_from.append(temp)
        self.locale_vals = cfg_mgr.read_section(
            LOCALE_TITLE,
            {"Linux": "en_US.utf8", "Windows": "us_us", "Darwin": "en_US.UTF - 8"},
            "Locals for displaying time and money")
        if self.locale_vals is not None:
            locale.setlocale(locale.LC_ALL, self.locale_vals[platform.system()])
        self.general_admin_email = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_ADMIN_EMAIL,
            ["admin@mydomain.com, admin2@domain2.com"],
            "Google email address of the account mails will be sent from")
        general_users = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_USERS,
            "\"user 1\", \"user 2\", \"all\"",
            "List of users to send emails to")
        if general_users is not None:
            self.general_users = ast.literal_eval("[" + general_users + "]")
        self.general_sleep = cfg_mgr.read_entry(
            GENERAL_TITLE, GENERAL_MAX_SLEEP,
            10,
            "Time to sleep before connecting to Mint\n"
            "Useful when running this at the same time every day\n"
            "(It will not look like a machine is hitting Mint)")
        self.general_exceptions_to = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_EXCEPTIONS_TO,
            "errors@mydomein.com, errors2@mydomein2.com",
            "email address to send exceptions to (generally an admin)")
        self.general_exceptions_to = self.general_exceptions_to.split(",")
        self.general_html_folder = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_HTML_FOLDER,
            "C:\\temp",
            "location of html file (if printed)\nThis is for debugging")
        if self.general_html_folder is not None:
            if not os.path.exists(self.general_html_folder):
                os.makedirs(self.general_html_folder)

        self.max_retries = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_MAX_RETRIES,
            10,
            "Maximum number of retries to connect to Mint before giving up")
        self.min_spend_threshold = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_MIN_SPEND_THRESHOLD,
            100,
            "Transactions less than this amount will be flagged")
        self.min_spend_color = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_MIN_SPEND_COLOR,
            "red",
            "Transactions less than the min threshold will be highlighted in this color")
        self.max_spend_threshold = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_MAX_SPEND_THRESHOLD,
            100,
            "Transactions more than this amount will be flagged")
        self.max_spend_color = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_MAX_SPEND_COLOR,
            "red",
            "Transactions more than the min threshold will be highlighted in this color")
        self.debug_mint_download = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_MINT_DOWNLOAD,
            False,
            "If False, MintChecker will attempt to use pickle files with "
            "data previously collected.\nThis is for Debugging")
        self.debug_save_html = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_SAVE_HTML,
            "html.txt",
            "If True, the html that is attached to the emails will be saved\nThis is for debugging")
        self.debug_send_email = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_SEND_EMAIL,
            True,
            "If False, it will prevent MintChecker from sending any emails\nThis is for debugging")
        self.debug_attach_log = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_ATTACH_LOG,
            True,
            "If True, will attach the log file to the email to the admin\nThis is for debugging")
        debug_mint_pickle_file = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_MINT_PICKLE_FILE,
            "pickle.pkl",
            "The name of the pickle file to store transactions in.\n"
            "This is useful to save time for development and debugging\nThis is for debugging")
        previous_accounts_pickle_file = cfg_mgr.read_entry(
            DEBUG_TITLE,
            ACCOUNTS_PICKLE_FILE,
            "accounts.pickle",
            "The name of the pickle file to store accounts in.\n"
            "This is useful to save time for development and debugging\nThis is for debugging")
        self.general_pickle_folder = cfg_mgr.read_entry(
            GENERAL_TITLE,
            GENERAL_PICKLE_FOLDER,
            "C:\\temp",
            "The location (folder) of pickle files")
        if not create:
            pickle_path = os.path.join(self.current_dir, self.general_pickle_folder)
            if not os.path.exists(pickle_path):
                os.makedirs(pickle_path)
            self.debug_mint_pickle_file = os.path.join(pickle_path, debug_mint_pickle_file)
            self.previous_accounts_pickle_file = os.path.join(pickle_path, previous_accounts_pickle_file)

        self.debug_debugging = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_DEBUGGING,
            False,
            "If True, MintCheck will dump data to the screen")
        self.debug_copy_admin = cfg_mgr.read_entry(
            DEBUG_TITLE,
            DEBUG_COPY_ADMIN,
            False,
            "If True, MintChecker will copy the admin on all debugging")
        self.account_type_credit_fg = cfg_mgr.read_entry(
            ACCOUNT_TYPES_TITLE,
            ACCOUNT_TYPES_CREDIT_FG,
            "green",
            "This indicates the color for credit accounts")
        self.account_type_bank_fg = cfg_mgr.read_entry(
            ACCOUNT_TYPES_TITLE,
            ACCOUNT_TYPES_BANK_FG,
            "blue",
            "This indicates the color for bank accounts")
        self.past_due_days_before = cfg_mgr.read_entry(
            PAST_DUE_TITLE,
            PAST_DUE_DAYS_BEFORE,
            5,
            "This indicates the color to present a credit account if it is due within the number of days")
        self.past_due_fg_color = cfg_mgr.read_entry(
            PAST_DUE_TITLE,
            PAST_DUE_FOREGROUND_COLOR,
            "red",
            "This indicates the color to present a credit account if it is "
                                                    "past due")
        self.email_connection = EmailConnectionConfig(cfg_mgr)
        self.users = []
        self.worst_day_error = 0
        for section in cfg_mgr.config.sections():
            if section not in SKIP_TITLES:
                if section in self.general_users or "all" in self.general_users:
                    try:
                        self.users.append(MintUser(section, cfg_mgr))
                    except Exception as e:
                        logger.exception(e)
                        logger.debug("skipping Sheet section " + section + " in configuration file")

        if (validate or test_email) and not create:
            # mint connection block
            dump_config_value(MINT_TITLE)
            dump_config_value(MINT_USER_USERNAME, self.mint_username)
            dump_config_value(MINT_USER_PASSWORD, self.mint_password)
            dump_config_value(MINT_REMOVE_DUPLICATES, self.mint_remove_duplicates)
            dump_config_value(MINT_IGNORE_ACCOUNTS, self.mint_ignore_accounts)

            # general block
            dump_config_value(GENERAL_TITLE)
            dump_config_value(GENERAL_WEEK_START, self.general_week_start)
            dump_config_value(GENERAL_MONTH_START, self.general_month_start)
            dump_config_value(GENERAL_ADMIN_EMAIL, self.general_admin_email)
            dump_config_value(GENERAL_USERS, self.general_users)
            dump_config_value(GENERAL_EXCEPTIONS_TO, self.general_exceptions_to)
            dump_config_value(GENERAL_MAX_SLEEP, self.general_sleep)

            # debug block
            dump_config_value(DEBUG_TITLE)
            dump_config_value(DEBUG_MINT_DOWNLOAD, self.debug_mint_download)
            dump_config_value(DEBUG_TITLE, self.debug_save_html)
            dump_config_value(DEBUG_MINT_PICKLE_FILE, self.debug_mint_pickle_file)
            dump_config_value(DEBUG_DEBUGGING, self.debug_debugging)
            dump_config_value(DEBUG_COPY_ADMIN, self.debug_copy_admin)

            # paid from block
            dump_config_value(PAID_FROM_TITLE)
            for paid_from in self.paid_from:
                for pf in paid_from:
                    dump_config_value(pf, paid_from[pf])

            # balance warnings block
            dump_config_value(BALANCE_WARNINGS_TITLE)
            for warning in self.balance_warnings:
                warning.dump()

            # colors block
            dump_config_value(COLORS_TITLE)
            for color in self.color_tags:
                dump_config_value(str(color), str(self.color_tags[color]))

            # account_types block
            dump_config_value(ACCOUNT_TYPES_TITLE)
            dump_config_value(ACCOUNT_TYPES_BANK_FG, self.account_type_bank_fg)
            dump_config_value(ACCOUNT_TYPES_CREDIT_FG, self.account_type_credit_fg)

            # past_due block
            dump_config_value(PAST_DUE_TITLE)
            dump_config_value(PAST_DUE_DAYS_BEFORE, self.past_due_days_before)
            dump_config_value(PAST_DUE_FOREGROUND_COLOR, self.past_due_fg_color)

            # locale block
            dump_config_value(LOCALE_TITLE)
            for locale_val in self.locale_vals:
                if platform.system() == locale_val:
                    dump_config_value(locale_val, self.locale_vals[locale_val] + " *")
                else:
                    dump_config_value(locale_val, self.locale_vals[locale_val])

            # email connection block
            dump_config_value(EmailConnection.TITLE)
            dump_config_value(EmailConnection.USERNAME, self.email_connection.username)
            dump_config_value(EmailConnection.PASSWORD, self.email_connection.password)
            dump_config_value(EmailConnection.FROM, self.email_connection.from_user)
            email_sender = EmailSender(self.email_connection)

            # user blocks
            for user in self.users:
                user.dump()
                if test_email:
                    for email in user.email:
                        logger.debug("Sending test email to " + user.name)
                        email_sender.send(email, user.subject, "This is a test message from Mint Checker")

        if create:
            cfg_mgr.write(out_file)

    @staticmethod
    def next_date_from_day(day):
        today = datetime.datetime.now()
        if day > today.day:
            next_date = today.replace(day=day)
        else:
            next_date = today.replace(day=day) + relativedelta(months=1)
        return next_date

    @staticmethod
    def get_next_payment_date(next_date):
        if next_date == "":
            next_date = None
        if next_date is not None and type(next_date) is str:
            next_date = dateutil.parser.parse(next_date)
        return next_date


def main():
    write = True
    logging.config.fileConfig('logging.ini')
    if write:
        out_file_name = "home_out.ini"
    else:
        out_file_name = None
    MintConfigFile("home.ini", validate=False, test_email=False, out_file=out_file_name)


if __name__ == "__main__":
    main()
