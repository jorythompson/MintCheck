import gspread
import datetime
import locale
from dateutil import parser
from mintConfigFile import MintConfigFile
from oauth2client.service_account import ServiceAccountCredentials


class MintSpread:
    date_col = "A"
    amount_col = "B"
    account_col = "C"
    deposit_date = "date"
    deposit_amount = "amount"
    deposit_account = "account"

    def __init__(self, config):
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(config.sheets_json_file, scope)
        self.g_spread = gspread.authorize(credentials)
        self.worksheet = self.g_spread.open(config.sheets_sheet_name).sheet1
        self.logger = config.logger
        self.sheet_name = config.sheets_sheet_name

    def get_row(self, row):
        cell_list = self.worksheet.range(MintSpread.date_col + str(row) + ":" + MintSpread.account_col + str(row))
        try:
            deposit_date = parser.parse(cell_list[0].value)
        except:
            deposit_date = None
        try:
            deposit_amount = locale.atof(cell_list[1].value[1:])
            return {MintSpread.deposit_date:deposit_date,
                    MintSpread.deposit_amount:deposit_amount,
                    MintSpread.deposit_account:cell_list[2].value}
        except:
            self.logger.critical("Could not parse " + str(cell_list) + " from Google sheet '" +
                                 self.sheet_name + "'")
        return None

    def get_data(self, start_date):
        data = []
        if self.worksheet.acell(MintSpread.date_col + "1").value == "Date" and \
                        self.worksheet.acell(MintSpread.amount_col + "1").value == "Amount" and \
                        self.worksheet.acell(MintSpread.account_col + "1").value == "Account":
            row_count = 2
            row = self.get_row(row_count)
            while row is not None:
                if start_date <= row[MintSpread.deposit_date] <= datetime.datetime.now():
                    data.append(row)
                row_count += 1
                row = self.get_row(row_count)
        return data


def main():
    config = MintConfigFile("home.ini")
    mint_spread = MintSpread(config)
    start_date = datetime.datetime.strptime('02122016', "%d%m%Y")
    mint_spread.get_data(start_date)


if __name__ == "__main__":
    main()
