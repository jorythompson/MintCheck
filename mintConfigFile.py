from configparser import ConfigParser, DuplicateSectionError
import ast
import logging.config
import logging.handlers
from emailSender import EmailConnection
import locale
import platform
import sys
from emailSender import EmailSender
import datetime
import dateutil
from dateutil.relativedelta import relativedelta
import thompco_utils
import os

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
GENERAL_POST_CONNECT_SLEEP="post_connect_sleep"

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
BILL_DATES_TITLE = "bill dates"
PAID_FROM_TITLE = "paid from"

SKIP_TITLES = [MINT_TITLE, GENERAL_TITLE, EmailConnection.TITLE, LOCALE_TITLE, DEBUG_TITLE, COLORS_TITLE,
               ACCOUNT_TYPES_TITLE, PAST_DUE_TITLE, BALANCE_WARNINGS_TITLE, BILL_DATES_TITLE, PAID_FROM_TITLE,
               SHEETS_TITLE]


def missing_entry(section, entry, file_name, default_value=None):
    logger = thompco_utils.get_logger()
    logger.debug("starting")
    if default_value is None:
        log_fn = logger.critical
        message = "Required entry"
        default_value = ""
    else:
        log_fn = logger.debug
        message = "Entry"
        if default_value == "":
            default_value = "Ignoring."
        else:
            default_value = "Using default value of (" + str(default_value) + ")"
    log_fn(message + " \"" + entry + "\" in section [" + section + "] in file: " + file_name
           + " is malformed or missing.  " + default_value)
    if default_value == "":
        log_fn("Exiting now")
        sys.exit()


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
    def __init__(self, section, default_day_error, config):
        self.billing_account = section
        self.sheet_name = config.config.get(section, SHEETS_NAME)
        self.amount_col = config.config.get(section, SHEETS_AMOUNT_COL)
        self.notes_col = config.config.get(section, SHEETS_NOTES_COL)
        self.date_col = config.config.get(section, SHEETS_DATE_COL)
        self.start_row = config.config.getint(section, SHEETS_START_ROW)
        self.deposit_account = config.config.get(section, SHEETS_DEPOSIT_ACCOUNT)
        try:
            self.tab_name = config.config.get(section, SHEETS_TAB_NAME)
        except:
            missing_entry(section, SHEETS_TAB_NAME, config.file_name)
        try:
            self.day_error = config.config.getint(section, SHEETS_DAY_ERROR)
        except:
            missing_entry(section, SHEETS_DAY_ERROR, config.file_name, default_day_error)
            self.day_error = default_day_error

    def dump(self):
        dump_config_value(SHEETS_TITLE)
        dump_config_value(SHEETS_TITLE, self.billing_account)
        dump_config_value(SHEETS_NAME, self.sheet_name)
        dump_config_value(SHEETS_AMOUNT_COL, self.amount_col)
        dump_config_value(SHEETS_NOTES_COL, self.notes)
        dump_config_value(SHEETS_DATE_COL, self.date_col)
        dump_config_value(SHEETS_START_ROW, self.start_row)
        dump_config_value(SHEETS_DEPOSIT_ACCOUNT, self.deposit_account)
        dump_config_value(SHEETS_TAB_NAME, self.tab_name)
        dump_config_value(SHEETS_DAY_ERROR, self.day_error)


class MintUser:
    # Throws an exception if email and active_accounts are not set
    def __init__(self, name, config):
        logger = thompco_utils.get_logger()
        self.name = name
        self.email = ast.literal_eval("[" + config.config.get(name, USER_EMAIL) + "]")
        try:
            self.subject = config.config.get(name, USER_SUBJECT)
        except Exception:
            self.subject = "Hello from Mint!"
        try:
            self.frequency = ast.literal_eval("[" + config.config.get(name, USER_FREQUENCY) + "]")
            for freq in self.frequency:
                if freq not in ALLOWED_USER_FREQUENCIES:
                    logger.warn("only values in " + str(ALLOWED_USER_FREQUENCIES) + " are permitted for "
                                + USER_FREQUENCY)
                    raise Exception("invalid user frequency")
        except Exception:
            missing_entry(name, USER_FREQUENCY, config.file_name)
            self.frequency = "weekly"
        try:
            self.rename_accounts = ast.literal_eval("{" + config.config.get(name, USER_RENAME_ACCOUNT) + "}")
        except Exception:
            missing_entry(name, USER_RENAME_ACCOUNT, config.file_name, "")
            self.rename_accounts = {}
        try:
            self.rename_institutions = ast.literal_eval("{" + config.config.get(name, USER_RENAME_INSTITUTION) + "}")
        except Exception:
            missing_entry(name, USER_RENAME_INSTITUTION, config.file_name, "")
            self.rename_institutions = {}
        self.active_accounts = ast.literal_eval("[" + config.config.get(name, USER_ACTIVE_ACCOUNTS) + "]")

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
        print
        print("[" + key + "]")
    else:
        print(key + ":" + str(value))


class MintConfigFile:
    def __init__(self, file_name, validate=False, test_email=False):
        logger = thompco_utils.get_logger()
        self.file_name = file_name
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(file_name)
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info("Starting session")

        # MINT section
        try:
            self.mint_username = self.config.get(MINT_TITLE, MINT_USER_USERNAME)
        except Exception:
            missing_entry(MINT_TITLE, MINT_USER_USERNAME, self.file_name)
        try:
            self.mint_password = self.config.get(MINT_TITLE, MINT_USER_PASSWORD)
        except Exception:
            missing_entry(MINT_TITLE, MINT_USER_PASSWORD, file_name)
        try:
            self.headless = self.config.getboolean(MINT_TITLE, HEADLESS)
        except Exception:
            missing_entry(MINT_TITLE, HEADLESS, file_name)
        try:
            self.mint_ignore_accounts = self.config.get(MINT_TITLE, MINT_IGNORE_ACCOUNTS)
        except Exception:
            missing_entry(MINT_TITLE, MINT_IGNORE_ACCOUNTS, file_name, default_value="")
            self.mint_ignore_accounts = None
        self.mint_remove_duplicates = self.config.get(MINT_TITLE, MINT_REMOVE_DUPLICATES)
        colors = self.config.items(COLORS_TITLE)
        self.color_tags = {}
        for color in colors:
            self.color_tags[color[0]] = ast.literal_eval("[" + color[1].lower() + "]")
        self.general_week_start = self.config.get(GENERAL_TITLE, GENERAL_WEEK_START)
        self.general_month_start = self.config.getint(GENERAL_TITLE, GENERAL_MONTH_START)

        # Balance Warnings section
        self.balance_warnings = []
        for (key, val) in self.config.items(BALANCE_WARNINGS_TITLE):
            try:
                balance_warning = BalanceWarning(key, val)
                if balance_warning.account_name == "credit":
                    self.balance_warning_credit = balance_warning
                elif balance_warning.account_name == "bank":
                    self.balance_warning_bank = balance_warning
                else:
                    self.balance_warnings.append(balance_warning)
            except:
                pass

        # Paid from section
        self.paid_from = []
        for (key, val) in self.config.items(PAID_FROM_TITLE):
            temp = dict()
            temp["credit account"] = key
            temp["debit account"] = val
            self.paid_from.append(temp)

        # LOCALE section
        self.locale_vals = []
        for (key, val) in self.config.items(LOCALE_TITLE):
            temp = dict()
            temp[key] = val
            self.locale_vals.append(temp)

        try:
            self.locale_val = self.config.get(LOCALE_TITLE, platform.system())
            locale.setlocale(locale.LC_ALL, self.locale_val)
        except Exception:
            missing_entry(LOCALE_TITLE, platform.system(), file_name)

        # GENERAL section
        try:
            self.general_admin_email = self.config.get(GENERAL_TITLE, GENERAL_ADMIN_EMAIL)
        except Exception:
            missing_entry(GENERAL_TITLE, GENERAL_ADMIN_EMAIL, file_name)
        try:
            self.general_users = ast.literal_eval("[" + self.config.get(GENERAL_TITLE, GENERAL_USERS) + "]")
        except Exception:
            self.general_users = "all"
            missing_entry(GENERAL_TITLE, GENERAL_USERS, file_name, default_value=self.general_users)
        try:
            self.general_google_sheets = \
                ast.literal_eval("[" + self.config.get(GENERAL_TITLE, GENERAL_GOOGLE_SHEETS) + "]")
        except Exception:
            self.general_google_sheets = "all"
            missing_entry(GENERAL_TITLE, GENERAL_GOOGLE_SHEETS, file_name, default_value=self.general_google_sheets)
        try:
            self.general_sleep = int(self.config.get(GENERAL_TITLE, GENERAL_MAX_SLEEP))
        except Exception:
            self.general_sleep = 10
            missing_entry(GENERAL_TITLE, GENERAL_MAX_SLEEP, file_name, self.general_sleep)
        try:
            self.general_exceptions_to = ast.literal_eval("[" + self.config.get(GENERAL_TITLE, GENERAL_EXCEPTIONS_TO)
                                                          + "]")
        except Exception:
            self.general_exceptions_to = [self.general_admin_email]
            missing_entry(GENERAL_TITLE, GENERAL_EXCEPTIONS_TO, file_name, self.general_exceptions_to)
        try:
            self.general_pickle_folder = self.config.get(GENERAL_TITLE, GENERAL_PICKLE_FOLDER)
        except Exception:
            self.general_pickle_folder = "pickle"
            missing_entry(GENERAL_TITLE, GENERAL_PICKLE_FOLDER, file_name, self.general_pickle_folder)
        try:
            self.general_html_folder = self.config.get(GENERAL_TITLE, GENERAL_HTML_FOLDER)
        except Exception:
            self.general_html_folder = "html"
            missing_entry(GENERAL_TITLE, GENERAL_HTML_FOLDER, file_name, self.general_html_folder)
        try:
            self.post_connect_sleep = self.config.getfloat(GENERAL_TITLE, GENERAL_POST_CONNECT_SLEEP)
        except Exception:
            self.post_connect_sleep = 5
        self.post_connect_sleep *= 60

        if not os.path.exists(self.general_html_folder):
            os.makedirs(self.general_html_folder)

        # DEBUG section
        try:
            self.debug_mint_download = self.config.getboolean(DEBUG_TITLE, DEBUG_MINT_DOWNLOAD)
        except Exception:
            self.debug_mint_download = True
            missing_entry(DEBUG_TITLE, DEBUG_MINT_DOWNLOAD, file_name, self.debug_mint_download)
        try:
            self.debug_save_html = self.config.get(DEBUG_TITLE, DEBUG_SAVE_HTML)
        except Exception:
            self.debug_save_html = None
            missing_entry(DEBUG_TITLE, DEBUG_SAVE_HTML, file_name, self.debug_save_html)
        try:
            self.debug_send_email = self.config.getboolean(DEBUG_TITLE, DEBUG_SEND_EMAIL)
        except Exception:
            self.debug_send_email = True
            missing_entry(DEBUG_TITLE, DEBUG_SEND_EMAIL, file_name, self.debug_send_email)
        try:
            self.debug_attach_log = self.config.getboolean(DEBUG_TITLE, DEBUG_ATTACH_LOG)
        except Exception:
            self.debug_attach_log = False
            missing_entry(DEBUG_TITLE, DEBUG_ATTACH_LOG, file_name, self.debug_attach_log)
        try:
            self.debug_mint_pickle_file = self.config.get(DEBUG_TITLE, DEBUG_MINT_PICKLE_FILE)
        except Exception:
            self.debug_mint_pickle_file = "mint.pickle"
            missing_entry(DEBUG_TITLE, DEBUG_MINT_PICKLE_FILE, file_name, "")
        try:
            self.previous_accounts_pickle_file = self.config.get(DEBUG_TITLE, ACCOUNTS_PICKLE_FILE)
        except Exception:
            self.previous_accounts_pickle_file = "accounts.pickle"
            missing_entry(DEBUG_TITLE, DEBUG_MINT_PICKLE_FILE, file_name, "")
        pickle_path = os.path.join(self.current_dir, self.general_pickle_folder)
        if not os.path.exists(pickle_path):
            os.makedirs(pickle_path)
        self.debug_mint_pickle_file = os.path.join(pickle_path, self.debug_mint_pickle_file)
        self.previous_accounts_pickle_file = os.path.join(pickle_path, self.previous_accounts_pickle_file)
        try:
            self.debug_debugging = self.config.getboolean(DEBUG_TITLE, DEBUG_DEBUGGING)
        except Exception:
            self.debug_debugging = False
            missing_entry(DEBUG_TITLE, DEBUG_DEBUGGING, file_name, self.debug_debugging)
        try:
            self.debug_sheets_download = self.config.getboolean(DEBUG_TITLE, DEBUG_SHEETS_DOWNLOAD)
        except Exception:
            self.debug_sheets_download = True
            missing_entry(DEBUG_TITLE, DEBUG_SHEETS_DOWNLOAD, file_name, self.debug_sheets_download)
        try:
            self.debug_copy_admin = self.config.getboolean(DEBUG_TITLE, DEBUG_COPY_ADMIN)
        except Exception:
            self.debug_copy_admin = False
            missing_entry(DEBUG_TITLE, DEBUG_COPY_ADMIN, file_name, self.debug_send_email)

        # account_types section
        try:
            self.account_type_credit_fg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_CREDIT_FG)
        except Exception:
            self.account_type_credit_fg = "black"
            missing_entry(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_CREDIT_FG, file_name, self.account_type_credit_fg)
        try:
            self.account_type_bank_fg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_BANK_FG)
        except Exception:
            self.account_type_bank_fg = "black"
            missing_entry(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_BANK_FG, file_name, self.account_type_bank_fg)

        try:
            self.past_due_days_before = self.config.getint(PAST_DUE_TITLE, PAST_DUE_DAYS_BEFORE)
        except Exception:
            self.past_due_days_before = 0
            missing_entry(PAST_DUE_TITLE, PAST_DUE_DAYS_BEFORE, file_name, self.past_due_days_before)
        try:
            self.past_due_fg_color = self.config.get(PAST_DUE_TITLE, PAST_DUE_FOREGROUND_COLOR)
        except Exception:
            self.past_due_fg_color = "red"
            missing_entry(PAST_DUE_TITLE, PAST_DUE_FOREGROUND_COLOR, file_name, self.past_due_fg_color)

        self.email_connection = EmailConnection(self.config)
        try:
            self.sheets_json_file = os.path.join(self.current_dir, self.config.get(SHEETS_TITLE, SHEETS_JSON_FILE))
        except:
            missing_entry(SHEETS_TITLE, SHEETS_JSON_FILE, file_name, "")
            self.sheets_json_file = None
        try:
            self.sheets_day_error = self.config.getint(SHEETS_TITLE, SHEETS_DAY_ERROR)
        except:
            self.sheets_day_error = 3
            missing_entry(SHEETS_TITLE, SHEETS_DAY_ERROR, file_name, self.sheets_day_error)
        try:
            self.sheets_paid_color = self.config.get(SHEETS_TITLE, SHEETS_PAID_COLOR)
        except:
            self.sheets_paid_color = "blue"
            missing_entry(SHEETS_TITLE, SHEETS_PAID_COLOR, file_name, self.sheets_paid_color)
        try:
            self.sheets_unpaid_color = self.config.get(SHEETS_TITLE, SHEETS_UNPAID_COLOR)
        except:
            self.sheets_unpaid_color = "purple"
            missing_entry(SHEETS_TITLE, SHEETS_UNPAID_COLOR, file_name, self.sheets_unpaid_color)
        try:
            self.sheets_day_error = self.config.getint(SHEETS_TITLE, SHEETS_DAY_ERROR)
        except:
            self.sheets_day_error = 3
            missing_entry(SHEETS_TITLE, SHEETS_DAY_ERROR, file_name, self.sheets_day_error)
        self.users = []
        self.google_sheets = []
        self.worst_day_error = 0
        for section in self.config.sections():
            if section not in SKIP_TITLES:
                if section in self.general_users or "all" in self.general_users:
                    try:
                        self.users.append(MintUser(section, self))
                    except:
                        logger.debug("skipping Sheet section " + section + " in configuration file")
                if (section in self.general_google_sheets or "all" in self.general_google_sheets) \
                        and self.sheets_json_file is not None:
                    try:
                        sheet = GoogleSheet(section, self.sheets_day_error, self)
                        if sheet.day_error > self.worst_day_error:
                            self.worst_day_error = sheet.day_error
                        self.google_sheets.append(sheet)
                    except:
                        logger.debug("skipping Sheet section " + section + " in configuration file")

        if validate or test_email:
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
            dump_config_value(GENERAL_MAX_SLEEP, self.general_sleep)
            dump_config_value(GENERAL_EXCEPTIONS_TO, self.general_exceptions_to)

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
                for lc in locale_val:
                    if platform.system() == lc:
                        dump_config_value(lc, locale_val[lc] + " *")
                    else:
                        dump_config_value(lc, locale_val[lc])

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

    @staticmethod
    def next_date_from_day(day):
        today = datetime.datetime.now()
        if day > today.day:
            next_date = today.replace(day=day)
        else:
            next_date = today.replace(day=day) + relativedelta(months=1)
        return next_date

    def get_next_payment_date(self, account_name, next_date):
        if next_date == "":
            next_date = None
        if next_date is not None and type(next_date) is str:
            next_date = dateutil.parser.parse(next_date)
        logger = thompco_utils.get_logger()
        logger.debug("starting")
        try:
            config_file = "payment_dates_" + self.file_name
            config = ConfigParser()
            config.read(config_file)
            if next_date is None:
                try:
                    next_day = config.getint(BILL_DATES_TITLE, account_name)
                    return MintConfigFile.next_date_from_day(next_day)
                except:
                    return None
            else:
                try:
                    config.add_section(BILL_DATES_TITLE)
                except config:
                    pass
                config.set(BILL_DATES_TITLE, account_name, next_date.day)
                config_file = open(config_file, "w")
                config.write(config_file)
                config_file.close()
                return next_date
        except:
            return next_date


if __name__ == "__main__":
    logging.config.fileConfig('logging.conf')
    mint_config = MintConfigFile("home.ini", validate=True, test_email=False)
    now = datetime.datetime.now()
    import os
    try:
        os.remove("payment_dates_" + mint_config.file_name)
    except:
        pass
    print(mint_config.get_next_payment_date("test", None))
    print(mint_config.get_next_payment_date("test", now + relativedelta(days=-2)))
    print(mint_config.get_next_payment_date("test", None))
    print(mint_config.get_next_payment_date("test", now + relativedelta(days=-2)))
    print(mint_config.get_next_payment_date("test", None))
    print(mint_config.get_next_payment_date("test", now + relativedelta(days=2)))
    print(mint_config.get_next_payment_date("test", None))
    print(mint_config.get_next_payment_date("test", now + relativedelta(days=2)))
