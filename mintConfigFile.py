import ConfigParser
import ast
import logging
import logging.handlers
from emailSender import EmailConnection
import locale
import platform
import sys
from emailSender import EmailSender
import datetime
from dateutil.relativedelta import relativedelta
import os

# mint connection block
MINT_TITLE = "mint connection"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
MINT_COOKIE = "ius_cookie"
MINT_COOKIE_2 = "thx_guid"
MINT_REMOVE_DUPLICATES ="remove_duplicates"
MINT_IGNORE_ACCOUNTS = "ignore_accounts_containing"

# general block
GENERAL_TITLE = "general"
GENERAL_WEEK_START = "week_start"
GENERAL_LOG_LEVEL = "log_level"
GENERAL_LOG_FILE = "log_file"
GENERAL_LOG_CONSOLE = "log_console"
GENERAL_ADMIN_EMAIL = "admin_email"
GENERAL_USERS = "users"
GENERAL_MAX_SLEEP = "max_sleep"
GENERAL_EXCEPTIONS_TO = "exceptions_to"

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACTIVE_ACCOUNTS = "active_accounts"
USER_ACCOUNT_TOTALS = "account_totals"
ALLOWED_USER_FREQUENCIES = ["daily", "weekly", "monthly"]
USER_FREQUENCY = "frequency"
USER_RENAME_ACCOUNT = "rename_account"
USER_RENAME_INSTITUTION = "rename_institution"

LOCALE_TITLE = "locale"
DEBIAN_LOCALE = "debian"
WINDOWS_LOCALE = "windows"

DEBUG_TITLE = "debug"
DEBUG_DOWNLOAD = "download"
DEBUG_PICKLE_FILE = "pickle_file"
DEBUG_DEBUGGING = "debugging"
DEBUG_COPY_ADMIN = "copy_admin"
DEBUG_SAVE_HTML = "save_html"
DEBUG_SEND_EMAIL = "send_email"

COLORS_TITLE = "colors"
ACCOUNT_TYPES_TITLE = "account_types"
ACCOUNT_TYPES_BANK_FG = "bank_fg_color"
ACCOUNT_TYPES_BANK_BG = "bank_bg_color"
ACCOUNT_TYPES_CREDIT_FG = "credit_fg_color"
ACCOUNT_TYPES_CREDIT_BG = "credit_bg_color"

PAST_DUE_TITLE = "past_due"
PAST_DUE_DAYS_BEFORE = "days_before"
PAST_DUE_FOREGROUND_COLOR = "fg_color"
PAST_DUE_BACKGROUND_COLOR = "bg_color"

BALANCE_WARNINGS_TITLE = "balance warnings"
BILL_DATES_TITLE = "bill dates"
PAID_FROM_TITLE = "paid from"

SKIP_TITLES = [MINT_TITLE, GENERAL_TITLE, EmailConnection.TITLE, LOCALE_TITLE, DEBUG_TITLE, COLORS_TITLE,
               ACCOUNT_TYPES_TITLE, PAST_DUE_TITLE, BALANCE_WARNINGS_TITLE, BILL_DATES_TITLE, PAID_FROM_TITLE]


class BalanceWarning:
    def __init__(self, key, val):
        self.account_name = key
        for comparator in [">", "<", "="]:
            if comparator in val:
                self.amount = float(val.replace(comparator, "").replace("$", "").replace(",", ""))
                self.comparator = comparator


class MintUser:
    def __init__(self, name, config):
        self.name = name
        self.email = ast.literal_eval("[" + config.get(name, USER_EMAIL) + "]")
        try:
            self.subject = config.get(name, USER_SUBJECT)
        except Exception:
            self.subject = "Hello from Mint!"
        try:
            self.frequency = ast.literal_eval("[" + config.get(name, USER_FREQUENCY) + "]")
            for freq in self.frequency:
                if freq not in ALLOWED_USER_FREQUENCIES:
                    config.logger.warn("only values in " + str(ALLOWED_USER_FREQUENCIES) + " are permitted for " +
                                       USER_FREQUENCY)
                    raise Exception("invalid user frequency")
        except Exception:
            self.frequency = "weekly"
        try:
            self.rename_accounts = ast.literal_eval("{" + config.get(name, USER_RENAME_ACCOUNT) + "}")
        except Exception:
            self.rename_accounts = {}
        try:
            self.rename_institutions = ast.literal_eval("{" + config.get(name, USER_RENAME_INSTITUTION) + "}")
        except Exception:
            self.rename_institutions = {}
        try:
            self.account_totals = ast.literal_eval("[" + config.get(name, USER_ACCOUNT_TOTALS) + "]")
        except Exception:
            self.account_totals = {}
        self.active_accounts = ast.literal_eval("[" + config.get(name, USER_ACTIVE_ACCOUNTS) + "]")

    def dump(self):
        dump_config_value(self.name)
        dump_config_value(USER_EMAIL, self.email)
        dump_config_value(USER_SUBJECT, self.subject)
        dump_config_value(USER_ACTIVE_ACCOUNTS, self.active_accounts)
        dump_config_value(USER_ACCOUNT_TOTALS, self.account_totals)
        dump_config_value(USER_FREQUENCY, self.frequency)
        dump_config_value(USER_RENAME_ACCOUNT, self.rename_accounts)
        dump_config_value(USER_RENAME_INSTITUTION, self.rename_institutions)


def dump_config_value(key, value=None):
    if value is None:
        print
        print "[" + key + "]"
    else:
        print key + ":" + str(value)


class MintConfigFile:
    def __init__(self, config_file, validate=False, test_email=False):
        self.config_file = config_file
        self.config = ConfigParser.ConfigParser()
        self.config.optionxform = str
        self.config.read(config_file)

        # MINT section
        try:
            self.mint_username = self.config.get(MINT_TITLE, MINT_USER_USERNAME)
        except Exception:
            print MINT_USER_USERNAME + " must be set under " + MINT_TITLE
            sys.exit()
        try:
            self.mint_password = self.config.get(MINT_TITLE, MINT_USER_PASSWORD)
        except Exception:
            print MINT_USER_PASSWORD + " must be set under " + MINT_TITLE
            sys.exit()
        try:
            self.mint_cookie = self.config.get(MINT_TITLE, MINT_COOKIE)
        except Exception:
            print MINT_COOKIE + " must be set under " + MINT_TITLE
            sys.exit()
        try:
            self.mint_cookie_2 = self.config.get(MINT_TITLE, MINT_COOKIE_2)
        except Exception:
            print MINT_COOKIE_2 + " must be set under " + MINT_TITLE
            sys.exit()

        try:
            self.mint_ignore_accounts = self.config.get(MINT_TITLE, MINT_IGNORE_ACCOUNTS)
        except Exception:
            self.mint_ignore_accounts = None

        self.mint_remove_duplicates = self.config.get(MINT_TITLE, MINT_REMOVE_DUPLICATES)
        colors = self.config.items(COLORS_TITLE)
        self.color_tags = {}
        for color in colors:
            self.color_tags[color[0]] = ast.literal_eval("[" + color[1].lower() + "]")
        self.general_week_start = self.config.get(GENERAL_TITLE, GENERAL_WEEK_START)
        self.logger = logging.getLogger("mintConfig")

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
        try:
            self.locale_val = self.config.get(LOCALE_TITLE, platform.system())
            locale.setlocale(locale.LC_ALL, self.locale_val)
        except Exception:
            print "\"" + platform.system() + "\" must be set under [" + LOCALE_TITLE + "] in the configuration settings"
            sys.exit()

        # GENERAL section
        try:
            self.general_admin_email = self.config.get(GENERAL_TITLE, GENERAL_ADMIN_EMAIL)
        except Exception:
            print GENERAL_ADMIN_EMAIL + " must be set under " + GENERAL_TITLE
            sys.exit()
        try:
            self.general_users = ast.literal_eval("[" + self.config.get(GENERAL_TITLE, GENERAL_USERS) + "]")
        except Exception:
            self.general_users = ["all"]
        try:
            level = self.config.get(GENERAL_TITLE, GENERAL_LOG_LEVEL)
        except Exception:
            level = logging.WARN
        try:
            level = self.config.get(GENERAL_TITLE, GENERAL_LOG_LEVEL)
        except Exception:
            level = logging.WARN
        try:
            self.general_sleep = int(self.config.get(GENERAL_TITLE, GENERAL_MAX_SLEEP))
        except Exception:
            self.general_sleep = 10
        try:
            self.general_log_file = self.config.get(GENERAL_TITLE, GENERAL_LOG_FILE)
            file_path = os.path.dirname(__file__)
            self.general_log_file = os.path.join(file_path, self.general_log_file)
        except Exception:
            self.general_log_file = "MintCheck.log"
        try:
            log_console = self.config.getboolean(GENERAL_TITLE, GENERAL_LOG_CONSOLE)
        except Exception:
            log_console = False

        # DEBUG section
        try:
            self.debug_download = self.config.getboolean(DEBUG_TITLE, DEBUG_DOWNLOAD)
        except Exception:
            self.debug_download = True
        try:
            self.debug_save_html = self.config.get(DEBUG_TITLE, DEBUG_SAVE_HTML)
        except Exception:
            self.debug_save_html = None
        try:
            self.debug_send_email = self.config.getboolean(DEBUG_TITLE, DEBUG_SEND_EMAIL)
        except Exception:
            self.debug_send_email = True
        try:
            self.debug_pickle_file = self.config.get(DEBUG_TITLE, DEBUG_PICKLE_FILE)
            file_path = os.path.dirname(__file__)
            self.debug_pickle_file = os.path.join(file_path, self.debug_pickle_file)
        except Exception:
            self.debug_pickle_file = None
        try:
            self.debug_debugging = self.config.getboolean(DEBUG_TITLE, DEBUG_DEBUGGING)
        except Exception:
            self.debug_debugging = False
        try:
            self.general_exceptions_to =  ast.literal_eval("[" + self.config.get(GENERAL_TITLE, GENERAL_EXCEPTIONS_TO) + "]")
        except Exception:
            self.general_exceptions_to = [self.general_admin_email]
        try:
            self.debug_copy_admin = self.config.getboolean(DEBUG_TITLE, DEBUG_COPY_ADMIN)
        except Exception:
            self.debug_copy_admin = False
        try:
            self.account_type_credit_fg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_CREDIT_FG)
        except Exception:
            self.account_type_credit_fg = "black"
        try:
            self.account_type_credit_bg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_CREDIT_BG)
        except Exception:
            self.account_type_credit_bg = "white"
        try:
            self.account_type_bank_fg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_BANK_FG)
        except Exception:
            self.account_type_bank_fg = "black"
        try:
            self.account_type_bank_bg = self.config.get(ACCOUNT_TYPES_TITLE, ACCOUNT_TYPES_BANK_BG)
        except Exception:
            self.account_type_bank_bg = "white"

        try:
            self.past_due_days_before = self.config.getint(PAST_DUE_TITLE, PAST_DUE_DAYS_BEFORE)
        except Exception:
            self.past_due_days_before = 0
        try:
            self.past_due_fg_color = self.config.get(PAST_DUE_TITLE, PAST_DUE_FOREGROUND_COLOR)
        except Exception:
            self.past_due_fg_color = "red"
        try:
            self.past_due_bg_color = self.config.get(PAST_DUE_TITLE, PAST_DUE_BACKGROUND_COLOR)
        except Exception:
            self.past_due_bg_color = "white"

        self.logger.setLevel(level)
        file_handler = logging.handlers.RotatingFileHandler(self.general_log_file, mode='a', maxBytes=10000, backupCount=5)
        file_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        if log_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        self.logger.debug("Starting session")
        self.email_connection = EmailConnection(self.config)
        self.users = []
        for user in self.config.sections():
            if user not in SKIP_TITLES:
                self.users.append(MintUser(user, self.config))

        if validate or test_email:
            # mint connection block
            dump_config_value(MINT_TITLE)
            dump_config_value(MINT_USER_USERNAME,self.mint_username)
            dump_config_value(MINT_USER_PASSWORD, self.mint_password)
            dump_config_value(MINT_COOKIE, self.mint_cookie)
            dump_config_value(MINT_REMOVE_DUPLICATES, self.mint_remove_duplicates)

            # general block
            dump_config_value(GENERAL_TITLE)
            dump_config_value(GENERAL_WEEK_START, self.general_week_start)
            dump_config_value(GENERAL_LOG_LEVEL, level)
            dump_config_value(GENERAL_LOG_FILE, self.general_log_file)
            dump_config_value(GENERAL_LOG_CONSOLE, log_console)
            dump_config_value(GENERAL_ADMIN_EMAIL, self.general_admin_email)
            dump_config_value(GENERAL_USERS, self.general_users)
            dump_config_value(GENERAL_MAX_SLEEP, self.general_sleep)
            dump_config_value(GENERAL_EXCEPTIONS_TO, self.general_exceptions_to)

            # colors block
            dump_config_value(COLORS_TITLE)
            for color in self.color_tags:
                dump_config_value(str(color), str(self.color_tags[color]))

            # account_types block
            dump_config_value(ACCOUNT_TYPES_TITLE)
            dump_config_value(ACCOUNT_TYPES_BANK_FG, self.account_type_bank_fg)
            dump_config_value(ACCOUNT_TYPES_BANK_BG, self.account_type_bank_bg)
            dump_config_value(ACCOUNT_TYPES_CREDIT_FG, self.account_type_credit_fg)
            dump_config_value(ACCOUNT_TYPES_CREDIT_BG, self.account_type_credit_bg)

            # past_due block
            dump_config_value(PAST_DUE_TITLE)
            dump_config_value(PAST_DUE_DAYS_BEFORE, self.past_due_days_before)
            dump_config_value(PAST_DUE_FOREGROUND_COLOR, self.past_due_fg_color)
            dump_config_value(PAST_DUE_BACKGROUND_COLOR, self.past_due_bg_color)

            # debug block
            dump_config_value(DEBUG_TITLE)
            dump_config_value(DEBUG_DOWNLOAD, self.debug_download)
            dump_config_value(DEBUG_PICKLE_FILE, self.debug_pickle_file)
            dump_config_value(DEBUG_DEBUGGING, self.debug_debugging)
            dump_config_value(DEBUG_COPY_ADMIN, self.debug_copy_admin)

            # locale block
            dump_config_value(LOCALE_TITLE)
            dump_config_value(platform.system(), self.locale_val)

            # email connection block
            dump_config_value(EmailConnection.TITLE)
            dump_config_value(EmailConnection.USERNAME, self.email_connection.username)
            dump_config_value(EmailConnection.PASSWORD, self.email_connection.password)
            dump_config_value(EmailConnection.FROM, self.email_connection.from_user)
            email_sender = EmailSender(self.email_connection, self.logger)

            # user blocks
            for user in self.users:
                user.dump()
                if test_email:
                    for email in user.email:
                        self.logger.debug("Sending test email to " + user.name)
                        email_sender.send(email, user.subject, "This is a test message from MintCheck")

    @staticmethod
    def next_date_from_day(day):
        today = datetime.datetime.now()
        if day > today.day:
            next_date = today.replace(day=day)
        else:
            next_date = today.replace(day=day) + relativedelta(months=1)
        return next_date

    def get_next_payment_date(self, account_name, next_date):
        try:
            config_file = "payment_dates_" + self.config_file
            config = ConfigParser.ConfigParser()
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
                except ConfigParser.DuplicateSectionError:
                    pass
                config.set(BILL_DATES_TITLE, account_name, next_date.day)
                config_file = open(config_file, "w")
                config.write(config_file)
                config_file.close()
                return next_date
        except:
            return next_date

if __name__ == "__main__":
    mint_config = MintConfigFile("home.ini", validate=True, test_email=False)
    now = datetime.datetime.now()
    import os
    os.remove("payment_dates_" + mint_config.config_file)
    print mint_config.get_next_payment_date("test", None)
    print mint_config.get_next_payment_date("test", now + relativedelta(days=-2))
    print mint_config.get_next_payment_date("test", None)
    print mint_config.get_next_payment_date("test", now + relativedelta(days=-2))
    print mint_config.get_next_payment_date("test", None)
    print mint_config.get_next_payment_date("test", now + relativedelta(days=2))
    print mint_config.get_next_payment_date("test", None)
    print mint_config.get_next_payment_date("test", now + relativedelta(days=2))
    print mint_config.logger.info("Done")
