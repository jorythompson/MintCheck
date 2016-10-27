import ConfigParser
import ast
import logging
from emailSender import EmailConnection
import locale
import platform
import sys

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


class MintConfigFile:
    def __init__(self, config_file):
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        self.mint_username = config.get(MINT_TITLE, MINT_USER_USERNAME)
        self.mint_password = config.get(MINT_TITLE, MINT_USER_PASSWORD)
        self.mint_cookie = config.get(MINT_TITLE, MINT_COOKIE)
        self.mint_remove_duplicates = config.get(MINT_TITLE, MINT_REMOVE_DUPLICATES)
        self.mint_warning_keywords = ast.literal_eval("[" + config.get(MINT_TITLE, MINT_WARNING_KEYWORDS) + "]")
        self.general_week_start = config.get(GENERAL_TITLE, GENERAL_WEEK_START)
        self.logger = logging.getLogger("mintConfig")
        try:
            locale.setlocale(locale.LC_ALL, config.get(LOCALE_TITLE, platform.system()))
        except Exception:
            print "\"" + platform.system() + "\" must be set under [" + LOCALE_TITLE + "] in the configuration settings"
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
        handler = logging.FileHandler(self.log_file)
        handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
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

if __name__ == "__main__":
    mint_config = MintConfigFile("home.ini")
    mint_config.logger.info("Done")