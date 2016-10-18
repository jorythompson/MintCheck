import ConfigParser
MINT_USER = "Mint User"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"

MINT_CONNECTION = "Mint Connection"
MINT_COOKIES_COOKIE = "cookie"
MINT_REMOVE_DUPLICATES ="remove_duplicates"

# USER block
USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACCOUNTS = "accounts"


class MintUser:
    def __init__(self, name, email, subject, accounts):
        self.name = name
        self.email = email
        self.subject = subject
        self.accounts = accounts.split(",")
        for i in range(0, len(self.accounts)):
            self.accounts[i] = self.accounts[i].replace('"', "").strip()


class MintConfigFile:
    def __init__(self, config_file):
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        self.username = config.get(MINT_USER, MINT_USER_USERNAME)
        self.password = config.get(MINT_USER, MINT_USER_PASSWORD)
        self.cookie = config.get(MINT_CONNECTION, MINT_COOKIES_COOKIE)
        self.remove_duplicates = config.getboolean(MINT_CONNECTION,MINT_REMOVE_DUPLICATES)
        self.users = []
        for user in config.sections():
            if user != MINT_CONNECTION and user != MINT_USER:
                self.users.append(MintUser(user, config.get(user, USER_EMAIL), config.get(user, USER_SUBJECT),
                                           config.get(user, USER_ACCOUNTS)))

