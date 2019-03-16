from configparser import ConfigParser
import ast
import logging.config
import logging.handlers
from emailSender import EmailConnection
import locale
from emailSender import EmailSender
import datetime
import dateutil
from dateutil.relativedelta import relativedelta
import thompco_utils
import os
import config_utils
import platform

# mint connection block
MINT_TITLE = "mint connection"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
HEADLESS = "headless"
MINT_REMOVE_DUPLICATES = "remove_duplicates"
MINT_IGNORE_ACCOUNTS = "ignore_accounts_containing"

# general block
GENERAL_TITLE = "general"
GENERAL_WEEK_START = "week_start"
GENERAL_MONTH_START = "month_start"
GENERAL_ADMIN_EMAIL = "admin_email"
GENERAL_USERS = "users"
GENERAL_GOOGLE_SHEETS = "google_sheets"
GENERAL_MAX_SLEEP = "max_sleep"
GENERAL_EXCEPTIONS_TO = "exceptions_to"
GENERAL_PICKLE_FOLDER = "pickle_folder"
GENERAL_HTML_FOLDER = "html_folder"
GENERAL_POST_CONNECT_SLEEP = "post_connect_sleep"
GENERAL_MAX_RETRIES = "max_retries"

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACTIVE_ACCOUNTS = "active_accounts"
USER_ACCOUNTS = "accounts"
ALLOWED_USER_FREQUENCIES = ["daily", "weekly", "monthly", "biweekly"]
USER_FREQUENCY = "frequency"
USER_RENAME_ACCOUNT = "rename_account"
USER_RENAME_INSTITUTION = "rename_institution"

LOCALE_TITLE = "locale"

DEBUG_TITLE = "debug"
DEBUG_MINT_DOWNLOAD = "download_mint"
DEBUG_SHEETS_DOWNLOAD = "download_sheets"
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

SHEETS_TITLE = "google_sheets"
SHEETS_JSON_FILE = "json_file"
SHEETS_DAY_ERROR = "max_day_error"
SHEETS_NAME = "sheet_name"
SHEETS_AMOUNT_COL = "amount_col"
SHEETS_NOTES_COL = "notes_col"
SHEETS_DATE_COL = "date_col"
SHEETS_START_ROW = "start_row"
SHEETS_DEPOSIT_ACCOUNT = "deposit_account"
SHEETS_TAB_NAME = "tab_name"
SHEETS_PAID_COLOR = "paid_color"
SHEETS_UNPAID_COLOR = "unpaid_color"

BALANCE_WARNINGS_TITLE = "balance warnings"
PAID_FROM_TITLE = "paid from"

SKIP_TITLES = [MINT_TITLE, GENERAL_TITLE, EmailConnection.TITLE, LOCALE_TITLE, DEBUG_TITLE, COLORS_TITLE,
               ACCOUNT_TYPES_TITLE, PAST_DUE_TITLE, BALANCE_WARNINGS_TITLE, PAID_FROM_TITLE,
               SHEETS_TITLE]


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


class GoogleSheet:
    def __init__(self, section, default_day_error, cfg_mgr):
        logger = thompco_utils.get_logger()
        self.billing_account = section
        self.sheet_name = cfg_mgr.config.get(section, SHEETS_NAME)
        self.amount_col = cfg_mgr.config.get(section, SHEETS_AMOUNT_COL)
        self.notes_col = cfg_mgr.config.get(section, SHEETS_NOTES_COL)
        self.date_col = cfg_mgr.config.get(section, SHEETS_DATE_COL)
        self.start_row = cfg_mgr.config.getint(section, SHEETS_START_ROW)
        self.deposit_account = cfg_mgr.config.get(section, SHEETS_DEPOSIT_ACCOUNT)
        try:
            self.tab_name = cfg_mgr.config.get(section, SHEETS_TAB_NAME)
        except Exception as e:
            logger.exception(e)
            config_utils.ConfigManager.missing_entry(section, SHEETS_TAB_NAME, cfg_mgr.file_name)
        try:
            print("section is {}".format(section))
            self.day_error = cfg_mgr.config.getint(section, SHEETS_DAY_ERROR)
        except Exception as e:
            config_utils.ConfigManager.missing_entry(section, SHEETS_DAY_ERROR, cfg_mgr.file_name,
                                                     default_day_error)
            self.day_error = default_day_error

    def dump(self):
        dump_config_value(SHEETS_TITLE)
        dump_config_value(SHEETS_TITLE, self.billing_account)
        dump_config_value(SHEETS_NAME, self.sheet_name)
        dump_config_value(SHEETS_AMOUNT_COL, self.amount_col)
        dump_config_value(SHEETS_DATE_COL, self.date_col)
        dump_config_value(SHEETS_START_ROW, self.start_row)
        dump_config_value(SHEETS_DEPOSIT_ACCOUNT, self.deposit_account)
        dump_config_value(SHEETS_TAB_NAME, self.tab_name)
        dump_config_value(SHEETS_DAY_ERROR, self.day_error)


class MintUser:
    # Throws an exception if email and active_accounts are not set
    def __init__(self, name, cfg_mgr):
        logger = thompco_utils.get_logger()
        self.name = name
        self.email = ast.literal_eval("[" + cfg_mgr.config.get(name, USER_EMAIL) + "]")
        try:
            self.subject = cfg_mgr.config.get(name, USER_SUBJECT)
        except Exception as e:
            logger.exception(e)
            self.subject = "Hello from Mint!"
        try:
            self.frequency = ast.literal_eval("[" + cfg_mgr.config.get(name, USER_FREQUENCY) + "]")
            for freq in self.frequency:
                if freq not in ALLOWED_USER_FREQUENCIES:
                    logger.warn("only values in " + str(ALLOWED_USER_FREQUENCIES) + " are permitted for "
                                + USER_FREQUENCY)
                    raise Exception("invalid user frequency")
        except Exception as e:
            logger.exception(e)
            config_utils.ConfigManager.missing_entry(name, USER_FREQUENCY, cfg_mgr.file_name)
            self.frequency = "weekly"
        try:
            self.rename_accounts = ast.literal_eval("{" + cfg_mgr.config.get(name,
                                                                             USER_RENAME_ACCOUNT) + "}")
        except Exception as e:
            logger.exception(e)
            config_utils.ConfigManager.missing_entry(name, USER_RENAME_ACCOUNT, cfg_mgr.file_name, "")
            self.rename_accounts = {}
        try:
            self.rename_institutions = ast.literal_eval("{" +
                                                        cfg_mgr.config.get(name,
                                                                           USER_RENAME_INSTITUTION) +
                                                        "}")
        except Exception as e:
            logger.exception(e)
            config_utils.ConfigManager.missing_entry(name, USER_RENAME_INSTITUTION,
                                                     cfg_mgr.file_name, "")
            self.rename_institutions = {}
        self.active_accounts = ast.literal_eval("[" + cfg_mgr.config.get(name,
                                                                         USER_ACTIVE_ACCOUNTS) + "]")

    def dump(self):
        dump_config_value(self.name)
        dump_config_value(USER_EMAIL, self.email)
        dump_config_value(USER_SUBJECT, self.subject)
        dump_config_value(USER_ACTIVE_ACCOUNTS, self.active_accounts)
        dump_config_value(USER_FREQUENCY, self.frequency)
        dump_config_value(USER_RENAME_ACCOUNT, self.rename_accounts)
        dump_config_value(USER_RENAME_INSTITUTION, self.rename_institutions)


def dump_config_value(key, value=None):
    if value is None:
        print()
        print("[" + key + "]")
    else:
        print(key + ":" + str(value))


class MintConfigFile:
    def __init__(self, file_name, validate=False, test_email=False, out_file=None):
        logger = thompco_utils.get_logger()
        create = out_file is not None
        cfg_mgr = config_utils.ConfigManager(file_name, create=create)
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info("Starting session")
        self.mint_username = cfg_mgr.read_entry(MINT_TITLE, MINT_USER_USERNAME, "Mint Username", str,
                                                "username to access Mint")
        self.mint_password = cfg_mgr.read_entry(MINT_TITLE, MINT_USER_PASSWORD, "Mint Password", str,
                                                "Password to access Mint")
        self.headless = cfg_mgr.read_entry(MINT_TITLE, HEADLESS, "True", bool,
                                           "True if you don't want chrome browser to display")
        self.mint_ignore_accounts = cfg_mgr.read_entry(MINT_TITLE, MINT_IGNORE_ACCOUNTS,
                                                       "duplicate", str,
                                                       "accounts containing this string will be ignored")
        self.mint_remove_duplicates = cfg_mgr.read_entry(MINT_TITLE, MINT_REMOVE_DUPLICATES, "True", bool,
                                                         "Sometimes Mint will duplicate accounts and transactions,"
                                                         " setting this to True will help prevent this")
        colors = cfg_mgr.read_section(COLORS_TITLE,
                                      {"red": "\"fee, charge\"",
                                       "blue": "\"deposit\""},
                                      "Colors are used to indicate key words are in the transaction")
        self.color_tags = {}
        if colors is not None:
            for color in colors:
                self.color_tags[color] = ast.literal_eval("[" + colors[color].lower() + "]")

        self.general_week_start = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_WEEK_START, "Monday", str,
                                                     "The day of the week that week starts")
        self.general_month_start = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_MONTH_START, 1, int,
                                                      "The day of the month the month starts")
        balance_warnings = cfg_mgr.read_section(BALANCE_WARNINGS_TITLE,
                                                {"Chase Checking": "< 25",
                                                 "Savings": ">= 100"},
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
        from_to = cfg_mgr.read_section(PAID_FROM_TITLE, {"PayPal": "Main Checking",
                                                         "Chase Credit": "Savings"},
                                       "List of debit accounts and the accounts they are paid from")
        self.paid_from = []
        if not create:
            for (key, val) in from_to.items():
                temp = dict()
                temp["credit account"] = key
                temp["debit account"] = val
                self.paid_from.append(temp)
        self.locale_vals = cfg_mgr.read_section(LOCALE_TITLE,
                                                {"Linux": "en_US.utf8",
                                                 "Windows": "us_us",
                                                 "Darwin": "en_US.UTF - 8"})
        if self.locale_vals is not None:
            locale.setlocale(locale.LC_ALL, self.locale_vals[platform.system()])
        self.general_admin_email = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_ADMIN_EMAIL,
                                                      "admin@mydomain.com", str,
                                                      "Google email address of the account mails will be sent from")
        general_users = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_USERS, "\"user 1\", \"user 2\", \"all\"", str,
                                           "List of users to send emails to")
        if general_users is not None:
            self.general_users = ast.literal_eval("[" + general_users + "]")
        google_sheets = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_GOOGLE_SHEETS,
                                           "\"all\", \"my google sheet\"", str,
                                           "list of Google sheets to update")
        if google_sheets is not None:
            self.general_google_sheets = ast.literal_eval("[" + google_sheets + "]")
        self.general_sleep = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_MAX_SLEEP, 10, int,
                                                "Time to sleep before connecting to Mint\n"
                                                "Useful when running this at the same time every day\n"
                                                "(It will not look like a machine is hitting Mint)")
        exceptions_to = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_EXCEPTIONS_TO, "errors@mydomein.com", str,
                                           "email address to send exceptions to (generally an admin)")
        if exceptions_to is not None:
            self.general_exceptions_to = ast.literal_eval("[" + exceptions_to + "]")
        self.general_html_folder = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_HTML_FOLDER, "C:\\temp", str,
                                                      "location of html file (if printed)\nThis is for debugging")
        if self.general_html_folder is not None:
            if not os.path.exists(self.general_html_folder):
                os.makedirs(self.general_html_folder)

        self.post_connect_sleep = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_POST_CONNECT_SLEEP, 5, float,
                                                     "Time to sleep after connecting to Mint.\n"
                                                     "This allows Mint to collect data from your accounts before "
                                                     "grabbing the transactions")
        if self.post_connect_sleep is not None:
            self.post_connect_sleep *= 5
        self.max_retries = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_MAX_RETRIES, 10, int,
                                              "Maximum number of retries to connect to Mint before giving up")
        self.debug_mint_download = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_MINT_DOWNLOAD, False, bool,
                                                      "If False, MintChecker will attempt to use pickle files with "
                                                      "data previously collected.\nThis is for Debugging")
        self.debug_save_html = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_SAVE_HTML, "html.txt", str,
                                                  "If True, the html that is attached to the emails will be saved\n"
                                                  "This is for debugging")
        self.debug_send_email = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_SEND_EMAIL, True, bool,
                                                   "If False, it will prevent MintChecker from sending any emails\n"
                                                   "This is for debugging")
        self.debug_attach_log = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_ATTACH_LOG, True, bool,
                                                   "If True, will attach the log file to the email to the admin\n"
                                                   "This is for debugging")
        debug_mint_pickle_file = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_MINT_PICKLE_FILE, "pickle.pkl", str,
                                                    "The name of the pickle file to store transactions in.\n"
                                                    "This is useful to save time for development and debugging\n"
                                                    "This is for debugging")
        previous_accounts_pickle_file = cfg_mgr.read_entry(DEBUG_TITLE, ACCOUNTS_PICKLE_FILE, "accounts.pickle", str,
                                                           "The name of the pickle file to store accounts in.\n"
                                                           "This is useful to save time for development and "
                                                           "debugging\n"
                                                           "This is for debugging")
        self.general_pickle_folder = cfg_mgr.read_entry(GENERAL_TITLE, GENERAL_PICKLE_FOLDER, "C:\\temp",
                                                        str, "The location (folder) of pickle files")
        if not create:
            pickle_path = os.path.join(self.current_dir, self.general_pickle_folder)
            if not os.path.exists(pickle_path):
                os.makedirs(pickle_path)
            self.debug_mint_pickle_file = os.path.join(pickle_path, debug_mint_pickle_file)
            self.previous_accounts_pickle_file = os.path.join(pickle_path, previous_accounts_pickle_file)

        self.debug_debugging = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_DEBUGGING, False, bool,
                                                  "If True, MintCheck will dump data to the screen")
        self.debug_sheets_download = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_SHEETS_DOWNLOAD, True, bool,
                                                        "If True, MintChecker dumps Google sheet data to the screen")
        self.debug_copy_admin = cfg_mgr.read_entry(DEBUG_TITLE, DEBUG_COPY_ADMIN, False, bool,
                                                   "If True, MintChecker will copy the admin on all debugging")
        self.account_type_credit_fg = cfg_mgr.read_entry(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_CREDIT_FG,
                                                         "green", str,
                                                         "This indicates the color for credit accounts")
        self.account_type_bank_fg = cfg_mgr.read_entry(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_BANK_FG, "blue", str,
                                                       "This indicates the color for bank accounts")
        self.past_due_days_before = cfg_mgr.read_entry(PAST_DUE_TITLE, PAST_DUE_DAYS_BEFORE, 5, int,
                                                       "This indicates the color to present a credit account if it is "
                                                       "due within the number of days")
        self.past_due_fg_color = cfg_mgr.read_entry(PAST_DUE_TITLE, PAST_DUE_FOREGROUND_COLOR, "red", str,
                                                    "This indicates the color to present a credit account if it is "
                                                    "past due")
        self.email_connection = EmailConnection(cfg_mgr, filename=file_name, create=create)
        json_file = cfg_mgr.read_entry(SHEETS_TITLE, SHEETS_JSON_FILE, "sheets.json", str,
                                       "This is the name of the json file for Google sheets\n"
                                       "It is for Debugging")
        if not create:
            self.sheets_json_file = os.path.join(self.current_dir, json_file)
        self.sheets_day_error = cfg_mgr.read_entry(SHEETS_TITLE, SHEETS_DAY_ERROR, 7, int)
        self.sheets_paid_color = cfg_mgr.read_entry(SHEETS_TITLE, SHEETS_PAID_COLOR, "green", str)
        self.sheets_unpaid_color = cfg_mgr.read_entry(SHEETS_TITLE, SHEETS_UNPAID_COLOR, "red", str)
        self.users = []
        self.google_sheets = []
        self.worst_day_error = 0
        if create:
            cfg_mgr.read_section("TD Bank", {SHEETS_NAME: "Mint Checker %%Y",
                                             SHEETS_AMOUNT_COL: "G",
                                             SHEETS_NOTES_COL: "H",
                                             SHEETS_DATE_COL: "I",
                                             SHEETS_START_ROW: "3",
                                             SHEETS_DEPOSIT_ACCOUNT: "TD Bank 1234",
                                             SHEETS_TAB_NAME: "Deposits"},
                                 "This section represents a Google sheet that will be updated")
            cfg_mgr.read_section("Personal", {SHEETS_NAME: "Mint Checker %%Y",
                                              SHEETS_AMOUNT_COL: "G",
                                              SHEETS_NOTES_COL: "H",
                                              SHEETS_DATE_COL: "I",
                                              SHEETS_START_ROW: "3",
                                              SHEETS_DEPOSIT_ACCOUNT: "Personal Checking 4567",
                                              SHEETS_TAB_NAME: "Deposits"})
            cfg_mgr.read_section("user 1", {USER_EMAIL: "user1@somewhere.com",
                                            USER_SUBJECT: "Mail for user 1",
                                            USER_ACTIVE_ACCOUNTS: "all",
                                            USER_FREQUENCY: "\"daily\", \"monthly\", \"weekly\", \"biweekly\"",
                                            USER_RENAME_ACCOUNT: "\"account in mint\":\"account displayed\","
                                                                 " \"mint\":displayed\"",
                                            USER_RENAME_INSTITUTION:
                                                "\"institution in mint\":\"institution displayed\","
                                                " \"mint\":displayed\"",
                                            USER_ACCOUNTS: "all"},
                                 "A user section represents a person who will receive an email\n" +
                                 USER_EMAIL + " is their email address\n" +
                                 USER_SUBJECT + " is the subject of the email\n" +
                                 USER_ACTIVE_ACCOUNTS + " is a list of accounts this user should be notified about\n" +
                                 USER_FREQUENCY + " is the frequency the user should be notified.  \n"
                                                  "This is useful if MintChecker is run autonomously\n" +
                                 USER_RENAME_ACCOUNT + " is used to obfuscate account names\n" +
                                 USER_RENAME_INSTITUTION + " is used to obfuscate instition names\n" +
                                 USER_ACCOUNTS + " is a list of accounts to be collected for this user")
            cfg_mgr.read_section("user 2", {USER_EMAIL: "user2@somewhere.com",
                                            USER_SUBJECT: "Mail for user 1",
                                            USER_ACTIVE_ACCOUNTS: "all",
                                            USER_FREQUENCY: "\"daily\", \"monthly\", \"weekly\", \"biweekly\"",
                                            USER_RENAME_ACCOUNT: "",
                                            USER_RENAME_INSTITUTION: "",
                                            USER_ACCOUNTS: "all"})

        else:
            for section in cfg_mgr.config.sections():
                if section not in SKIP_TITLES:
                    if section in self.general_users or "all" in self.general_users:
                        try:
                            self.users.append(MintUser(section, cfg_mgr))
                        except Exception as e:
                            logger.exception(e)
                            logger.debug("skipping Sheet section " + section + " in configuration file")
                    if (section in self.general_google_sheets or "all" in self.general_google_sheets) \
                            and self.sheets_json_file is not None:
                        try:
                            sheet = GoogleSheet(section, self.sheets_day_error, cfg_mgr)
                            if sheet.day_error > self.worst_day_error:
                                self.worst_day_error = sheet.day_error
                            self.google_sheets.append(sheet)
                        except Exception as e:
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
            dump_config_value(GENERAL_GOOGLE_SHEETS, self.general_google_sheets)
            dump_config_value(GENERAL_EXCEPTIONS_TO, self.general_exceptions_to)
            dump_config_value(GENERAL_MAX_SLEEP, self.general_sleep)
            # sheets block
            dump_config_value(SHEETS_TITLE)
            dump_config_value(SHEETS_TITLE, self.sheets_json_file)
            for sheet in self.google_sheets:
                sheet.dump()

            # debug block
            dump_config_value(DEBUG_TITLE)
            dump_config_value(DEBUG_MINT_DOWNLOAD, self.debug_mint_download)
            dump_config_value(DEBUG_SHEETS_DOWNLOAD, self.debug_sheets_download)
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
    logging.config.fileConfig('logging.conf')
    if write:
        out_file_name = "home_out.ini"
    else:
        out_file_name = None
    MintConfigFile("home.ini", validate=False, test_email=False, out_file=out_file_name)


if __name__ == "__main__":
    main()
