import gspread
import datetime
import sys
from dateutil import parser
from mintConfigFile import MintConfigFile
from oauth2client.service_account import ServiceAccountCredentials
import re


class MintSpread:
    numbers = re.compile('\d+(?:\.\d+)?')

    def __init__(self, config):
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(config.sheets_json_file, scope)
        self.config = config
        self.g_spread = gspread.authorize(credentials)
        self.logger = config.logger

    def get_row(self, row, amount_col, date_col, worksheet):
        self.logger.debug("getting row #" + str(row) + " on tab '" + worksheet.title
                          + "', on sheet '" + worksheet.spreadsheet.title + "'")
        try:
            date_cell = worksheet.acell(date_col + str(row))
            deposit_date = parser.parse(date_cell.value)
        except Exception as e:
            self.logger.debug("Could not get deposit amount from cell [" + date_col + ":" + str(row) + "]"
                              + "in sheet '" + worksheet.spreadsheet.title + "' on tab '" + worksheet.title
                              + "(not necessarily a problem, it could just be end of data)."
                              + "  Exception was:' " + e.message + "'")
            deposit_date = None
        if deposit_date is None:
            deposit_amount = None
        else:
            try:
                amount_cell = worksheet.acell(amount_col + str(row))
                deposit_amount = float(MintSpread.numbers.findall(amount_cell.value.replace(",", ""))[0])
            except Exception as e:
                self.logger.debug("Could not get deposit amount from cell [" + amount_col + ":" + str(row) + "]"
                                  + "in sheet '" + worksheet.spreadsheet.title + "' on tab '" + worksheet.title
                                  + "(not necessarily a problem, it could just be end of data)."
                                  + "  Exception was:'" + e.message + "'")
                deposit_amount = None
        return deposit_amount, deposit_date

    def get_data(self, start_date):
        data = []
        for sheet in self.config.google_sheets:
            self.logger.debug("Connecting to tab '" + sheet.tab_name + "', on sheet '" + sheet.sheet_name + "'")
            worksheet = self.g_spread.open(sheet.sheet_name).worksheet(sheet.tab_name)
            row_count = sheet.start_row
            deposit_amount, deposit_date = self.get_row(row_count, sheet.amount_col, sheet.date_col, worksheet)
            while deposit_date is not None and deposit_amount is not None:
                if deposit_date > start_date:
                    data.append({
                        "deposit_date":deposit_date,
                        "deposit_amount":deposit_amount,
                        "deposit_account":sheet.deposit_account,
                        "sheet_name":sheet.sheet_name,
                        "row":str(row_count)
                    })
                row_count += 1
                deposit_amount, deposit_date = self.get_row(row_count, sheet.amount_col, sheet.date_col, worksheet)
        return data


def main():
    config = MintConfigFile("home.ini")
    mint_spread = MintSpread(config)
    start_date = datetime.datetime.strptime('02/02/2016', "%d/%m/%Y")
    data = mint_spread.get_data(start_date)
    for d in data:
        config.logger.debug(d)

if __name__ == "__main__":
    main()
