import gspread
import datetime
import cPickle
from dateutil import parser
from mintConfigFile import MintConfigFile
from oauth2client.service_account import ServiceAccountCredentials
import re
import string


class MintSheet:
    numbers = re.compile('\d+(?:\.\d+)?')

    def __init__(self, config, start_date):
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(config.sheets_json_file, scope)
        self.config = config
        self.g_spread = gspread.authorize(credentials)
        self.logger = config.logger
        self.sheet_data = self._get_data(start_date)

    @staticmethod
    def col2num(col):
        num = 0
        for c in col:
            if c in string.ascii_letters:
                num = num * 26 + (ord(c.upper()) - ord('A')) + 1
        return num

    @staticmethod
    def get_row(logger, row, amount_col, date_col, worksheet):
        logger.debug("getting row #" + str(row) + " on tab '" + worksheet.title
                     + "', on sheet '" + worksheet.spreadsheet.title + "'")
        try:
            date_cell = worksheet.acell(date_col + str(row))
            deposit_date = parser.parse(date_cell.value)
        except Exception as e:
            logger.debug("Could not get deposit date from cell [" + date_col + ":" + str(row) + "]"
                         + "in sheet '" + worksheet.spreadsheet.title + "' on tab '" + worksheet.title
                         + "(not necessarily a problem, it could just be end of data)."
                         + "  Exception was:' " + e.message + "'")
            deposit_date = None
        try:
            amount_cell = worksheet.acell(amount_col + str(row))
            deposit_amount = float(MintSheet.numbers.findall(amount_cell.value.replace(",", ""))[0])
        except Exception as e:
            logger.debug("Could not get deposit amount from cell [" + amount_col + ":" + str(row) + "]"
                         + "in sheet '" + worksheet.spreadsheet.title + "' on tab '" + worksheet.title
                         + "(not necessarily a problem, it could just be end of data)."
                         + "  Exception was:'" + e.message + "'")
            deposit_amount = None
        return deposit_amount, deposit_date

    def get_missing_deposits(self, mint_transactions, user):
        rtn = []
        for data in self.sheet_data:
            data["actual_deposit_date"] = None
            rtn.append(data)
            for transaction in mint_transactions.transactions:
                if transaction["account"] == data["deposit_account"] \
                        and transaction["amount"] == data["deposit_amount"] \
                        and ("all" in user.accounts or transaction["account"] in user.accounts):
                    if data["expected_deposit_date"] + datetime.timedelta(data["date_error"]) > transaction["date"] \
                            > data["expected_deposit_date"] - datetime.timedelta(data["date_error"]):
                        data["actual_deposit_date"] = transaction["date"]
                        break
        return rtn

    def _get_data(self, start_date):
        data = []
        if self.config.debug_sheets_download:
            for sheet in self.config.google_sheets:
                for tab_name in sheet.tab_names:
                    self.logger.debug("Connecting to tab '" + tab_name + "', on sheet '" + sheet.sheet_name + "'")
                    try:
                        worksheet = self.g_spread.open(sheet.sheet_name).worksheet(tab_name)
                        row_count = sheet.start_row - 1
                        while True:
                            row_count += 1
                            deposit_amount, deposit_date = \
                                MintSheet.get_row(self.logger, row_count, sheet.amount_col, sheet.date_col, worksheet)
                            if deposit_date is None and deposit_amount is None:  # both are None
                                break
                            elif deposit_date is not None and deposit_amount is not None:  # neither is None
                                if deposit_date > start_date:
                                    data.append({
                                        "billing_account": sheet.billing_account,
                                        "expected_deposit_date": deposit_date,
                                        "date_error": sheet.day_error,
                                        "deposit_amount": deposit_amount,
                                        "deposit_account": sheet.deposit_account,
                                        "sheet_name": sheet.sheet_name,
                                        "row": str(row_count)
                                    })
                    except:
                        self.logger.info("Tab " + tab_name + " on sheet " + sheet.sheet_name
                                         + " does not exist... skipping")
            if self.config.debug_sheets_pickle_file is not None:
                with open(self.config.debug_sheets_pickle_file, 'wb') as handle:
                    cPickle.dump(data, handle)
        else:
            if self.config.debug_sheets_pickle_file is not None:
                with open(self.config.debug_sheets_pickle_file, 'rb') as handle:
                    data = cPickle.load(handle)
        return data


def main():
    config = MintConfigFile("home.ini")
    start_date = datetime.datetime.strptime('08/01/2016', "%d/%m/%Y")
    mint_spread = MintSheet(config, start_date)
    with open(config.debug_mint_pickle_file, 'rb') as handle:
        cPickle.load(handle)
        mint_transactions = cPickle.load(handle)

    for user in config.users:
        if user.name == "Jordan":
            missing_transactions = mint_spread.get_missing_deposits(mint_transactions, user)
            for missing in missing_transactions:
                print missing

if __name__ == "__main__":
    main()
