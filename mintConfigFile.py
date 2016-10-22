import ConfigParser
import ast
MINT_TITLE = "Mint Connection"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
MINT_COOKIE = "cookie"
MINT_REMOVE_DUPLICATES ="remove_duplicates"
WARNING_KEYWORDS =  "warning_keywords"

EMAIL_TITLE = "Email Connection"
EMAIL_USER_USERNAME = "username"
EMAIL_USER_PASSWORD = "password"
EMAIL_USER_FROM = "from"

SKIP_TITLES = [MINT_TITLE, EMAIL_TITLE]

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACCOUNTS = "accounts"
RENAME_ACCOUNT = "rename_account"
RENAME_INSTITUTION = "rename_institution"

class MintUser:
    def __init__(self, name, email, subject, accounts_str, rename_accounts_str, rename_institutions_str):
        self.name = name
        self.email = email
        self.subject = subject
        self.rename_accounts = {}
        if rename_accounts_str is not None:
            self.rename_accounts = ast.literal_eval("{" + rename_accounts_str + "}")
        self.rename_institutions = {}
        if rename_institutions_str is not None:
            self.rename_institutions = ast.literal_eval("{" + rename_institutions_str + "}")
        self.accounts = ast.literal_eval(accounts_str)


class MintConfigFile:
    def __init__(self, config_file):
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        self.mint_username = config.get(MINT_TITLE, MINT_USER_USERNAME)
        self.mint_password = config.get(MINT_TITLE, MINT_USER_PASSWORD)
        self.mint_cookie = config.get(MINT_TITLE, MINT_COOKIE)
        self.mint_remove_duplicates = config.get(MINT_TITLE, MINT_REMOVE_DUPLICATES)
        self.warning_keywords = ast.literal_eval("[" + config.get(MINT_TITLE, WARNING_KEYWORDS) + "]")

        self.email_username = config.get(EMAIL_TITLE, EMAIL_USER_USERNAME)
        self.email_password = config.get(EMAIL_TITLE, EMAIL_USER_PASSWORD)
        self.email_user_from = config.get(EMAIL_TITLE, EMAIL_USER_FROM)

        self.users = []

        for user in config.sections():
            try:
                rename_accounts = config.get(user, RENAME_ACCOUNT)
            except ConfigParser.NoOptionError:
                rename_accounts = None
            try:
                rename_institutions = config.get(user, RENAME_INSTITUTION)
            except ConfigParser.NoOptionError:
                rename_institutions = None
            if user not in SKIP_TITLES:
                self.users.append(MintUser(user, config.get(user, USER_EMAIL), config.get(user, USER_SUBJECT),
                                           config.get(user, USER_ACCOUNTS), rename_accounts, rename_institutions))

if __name__ == "__main__":
    mint_config = MintConfigFile("laptop-home.ini")