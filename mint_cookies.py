import ConfigParser
import browsercookie


class MintCookies:
    def __init__(self):
        self.cookies = [{"url": "accounts.intuit.com", "cookie": "ius_session", "value": None},
                        {"url": "pf.intuit.com", "cookie": "thx_guid", "value": None}]
        self.cookie_jar = browsercookie.chrome()

    def find_cookie(self, url, cookie):
        for c in self.cookie_jar._cookies:
            if c == unicode(url):
                c = self.cookie_jar._cookies[c]
                val = c[unicode("/")]
                try:
                    val = val[unicode(cookie)]
                except KeyError:
                    return None
                return val.value
        return None

    def find_cookies(self):
        for c in self.cookies:
            c["value"] = self.find_cookie(c["url"], c["cookie"])
        return self.cookies

    @staticmethod
    def replace_value(config_file, key, value):
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        config.read(config_file)
        old_value = config.get("mint connection", key)
        f = open(config_file)
        contents = f.read()
        f.close()
        contents = contents.replace(key + ":" + old_value, key + ":" + value)
        f = open(config_file, "w")
        f.write(contents)
        print "changing {} to {}".format(old_value, value)


def main():
    mc = MintCookies()
    cookies = mc.find_cookies()
    for c in cookies:
        MintCookies.replace_value("home.ini", c["cookie"] + "_cookie", c["value"])


if __name__ == "__main__":
    main()
