import ConfigParser
MINT_USER = "Mint User"
MINT_USER_USERNAME = "username"
MINT_USER_PASSWORD = "password"
MINT_COOKIES = "Mint Cookies"
MINT_COOKIES_COOKIE = "cookie"

USER_EMAIL = "email"
USER_SUBJECT = "subject"
USER_ACCOUNTS = "accounts"


class MintUser:
    def __init__(self, name, email, subject, accounts):
        self.name = name
        self.email = email
        self.subject = subject
        self.accounts = accounts.split(",")
        for account in self.accounts:
            account = account.replace('"', "").strip()


def read_config(config_file):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    username = config.get(MINT_USER, MINT_USER_USERNAME)
    password = config.get(MINT_USER, MINT_USER_PASSWORD)
    cookie = config.get(MINT_COOKIES, MINT_COOKIES_COOKIE)
    users = []
    for user in config.sections():
        if user != MINT_COOKIES and user != MINT_USER:
            users.append(MintUser(user, config.get(user, USER_EMAIL), config.get(user, USER_SUBJECT),
                                  config.get(user, USER_ACCOUNTS)))
    return username, password, cookie, users

