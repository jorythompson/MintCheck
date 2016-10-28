import ConfigParser
import ast
import logging
import logging.handlers
from emailSender import EmailConnection
import locale
import platform
import sys
from emailSender import EmailSender

# mint connection block
MINT_TITLE = "Mint Connection"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
MINT_COOKIE = "ius_cookie"
MINT_REMOVE_DUPLICATES ="remove_duplicates"
MINT_WARNING_KEYWORDS = "warning_keywords"

# general block
GENERAL_TITLE = "General"
GENERAL_WEEK_START = "week_start"
GENERAL_DEV_ONLY = "dev_only"
GENERAL_LOG_LEVEL = "log_level"
GENERAL_LOG_FILE = "log_file"
GENERAL_LOG_CONSOLE = "log_console"
GENERAL_ADMIN_EMAIL = "admin_email"

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACTIVE_ACCOUNTS = "active_accounts"
USER_ACCOUNT_TOTALS = "account_totals"
USER_FREQUENCY = "frequency" # daily, weekly, monthly
USER_RENAME_ACCOUNT = "rename_account"
USER_RENAME_INSTITUTION = "rename_institution"

LOCALE_TITLE = "locale"
DEBIAN_LOCALE = "debian"
WINDOWS_LOCALE = "windows"

SKIP_TITLES = [MINT_TITLE, GENERAL_TITLE, EmailConnection.TITLE, LOCALE_TITLE]


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
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        try:
            self.mint_username = config.get(MINT_TITLE, MINT_USER_USERNAME)
        except Exception:
            print MINT_USER_USERNAME + " must be set under " + MINT_TITLE
            sys.exit()
        try:
            self.mint_password = config.get(MINT_TITLE, MINT_USER_PASSWORD)
        except Exception:
            print MINT_USER_PASSWORD + " must be set under " + MINT_TITLE
            sys.exit()
        try:
            self.mint_cookie = config.get(MINT_TITLE, MINT_COOKIE)
        except Exception:
            print MINT_COOKIE + " must be set under " + MINT_TITLE
            sys.exit()
        self.mint_remove_duplicates = config.get(MINT_TITLE, MINT_REMOVE_DUPLICATES)
        self.mint_warning_keywords = ast.literal_eval("[" + config.get(MINT_TITLE, MINT_WARNING_KEYWORDS) + "]")
        self.general_week_start = config.get(GENERAL_TITLE, GENERAL_WEEK_START)
        self.logger = logging.getLogger("mintConfig")
        try:
            locale_val = config.get(LOCALE_TITLE, platform.system())
            locale.setlocale(locale.LC_ALL, locale_val)
        except Exception:
            print "\"" + platform.system() + "\" must be set under [" + LOCALE_TITLE + "] in the configuration settings"
            sys.exit()
        try:
            self.general_admin_email = config.get(GENERAL_TITLE, GENERAL_ADMIN_EMAIL)
        except Exception:
            print GENERAL_ADMIN_EMAIL + " must be set under " + GENERAL_TITLE
            sys.exit()
        try:
            self.log_file = config.get(GENERAL_TITLE, GENERAL_LOG_FILE)
        except Exception:
            self.log_file = "log.txt"
        try:
            level = config.get(GENERAL_TITLE, GENERAL_LOG_LEVEL)
        except Exception:
            level = logging.WARN
        try:
            self.general_dev_only = config.getboolean(GENERAL_TITLE, GENERAL_DEV_ONLY)
        except Exception:
            self.general_week_dev_only = False
        try:
            log_console = config.getboolean(GENERAL_TITLE, GENERAL_LOG_CONSOLE)
        except Exception:
            log_console = False
        self.logger.setLevel(level)
        file_handler = logging.handlers.RotatingFileHandler(self.log_file, mode='a', maxBytes=10000, backupCount=5)
        file_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        if log_console:
            consoleHandler = logging.StreamHandler()
            consoleHandler.setFormatter(formatter)
            self.logger.addHandler(consoleHandler)
        self.logger.debug("Starting session")
        self.email_connection = EmailConnection(config)
        self.users = []
        for user in config.sections():
            if user not in SKIP_TITLES:
                self.users.append(MintUser(user, config))

        if validate or test_email:
            dump_config_value(MINT_TITLE)
            dump_config_value(MINT_USER_USERNAME,self.mint_username)
            dump_config_value(MINT_USER_PASSWORD, self.mint_password)
            dump_config_value(MINT_COOKIE, self.mint_cookie)
            dump_config_value(MINT_REMOVE_DUPLICATES, self.mint_remove_duplicates)
            dump_config_value(MINT_WARNING_KEYWORDS, self.mint_warning_keywords)
            dump_config_value(GENERAL_TITLE)
            dump_config_value(GENERAL_WEEK_START, self.general_week_start)
            dump_config_value(GENERAL_DEV_ONLY, self.general_dev_only)
            dump_config_value(GENERAL_LOG_LEVEL, level)
            dump_config_value(GENERAL_LOG_FILE, log_file)
            dump_config_value(GENERAL_LOG_CONSOLE, log_console)
            dump_config_value(LOCALE_TITLE)
            dump_config_value(platform.system(), locale_val)
            dump_config_value(EmailConnection.TITLE)
            dump_config_value(EmailConnection.USERNAME, self.email_connection.username)
            dump_config_value(EmailConnection.PASSWORD, self.email_connection.password)
            dump_config_value(EmailConnection.FROM, self.email_connection.from_user)
            email_sender = EmailSender(self.email_connection, self.logger)
            for user in self.users:
                user.dump()
                if test_email:
                    for email in user.email:
                        self.logger.debug("Sending test email to " + user.name)
                        email_sender.send(email, user.subject, "This is a test message from MintCheck")
            sys.exit()

if __name__ == "__main__":
    mint_config = MintConfigFile("home.ini", validate=True, test_email=True)
    mint_config.logger.info("Done")