from oauth2client.service_account import ServiceAccountCredentials
import datetime
import argparse
from mintConfigFile import MintConfigFile
import gspread
from mintSheets import MintSheet
import locale
from dateutil import parser
import ast
import logging


class MintCheckerDeposit:
    def __init__(self):
        self.now = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.args = self._get_args()
        self.config = MintConfigFile(self.args.config, test_email=self.args.validate_emails,
                                     validate=self.args.validate_ini)
        self.logger = self.config.logger
        self.logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.config.sheets_json_file, scope)
        self.g_spread = gspread.authorize(credentials)

    def _get_args(self):
        parser = argparse.ArgumentParser(description='Read Information from Mint')
        parser.add_argument('--config', required=True,
                            help='Configuration file containing your username, password, and mint cookie')
        parser.add_argument('--sheet', required=True,
                            help='Google Sheet name to update')
        parser.add_argument('--notes', required=True,
                            help='List of notes to add to the google sheet')
        parser.add_argument('--amounts', required=True,
                            help='List of values to add to the google sheet')
        parser.add_argument('--account', required=True,
                            help='Account to apply this deposit to')
        parser.add_argument('--date', required=False, default=self.now.strftime("%m/%d/%Y"),
                            help='Date to use for this deposit')
        parser.add_argument('--validate_ini', action="store_true", default=False,
                            help='Validates the input configuration file')
        parser.add_argument('--validate_emails',  action="store_true", default=False,
                            help='Validates sending emails to all users in the configuration file')
        return parser.parse_args()

    def update_sheet(self):
        try:
            self.logger.debug("config file is '" + self.args.config + "'")
            self.logger.debug("sheet is '" + self.args.sheet + "'")
            notes = ast.literal_eval(str(self.args.notes))
            amounts = self.args.amounts
            while ",," in amounts:
                amounts = amounts.replace(",,", ",None,")
            amounts = ast.literal_eval(amounts)
            if len(amounts) != len(notes):
                raise RuntimeError("Number of elements in payors and amounts should be the same")
            self.logger.debug("notes are " + str(notes))
            self.logger.debug("amounts are " + str(amounts))
            self.logger.debug("account is '" + self.args.account + "'")
            self.logger.debug("date is '" + self.args.date + "'")
            self.logger.debug("validate ini is '" + str(self.args.validate_ini) + "'")
            self.logger.debug("validate emails is '" + str(self.args.validate_emails) + "'")
            self.now = parser.parse(self.args.date)
            for sheet in self.config.google_sheets:
                if sheet.billing_account == self.args.account:
                    self.logger.debug("found tab as " + self.args.account)
                    worksheet = self.g_spread.open(self.args.sheet).worksheet(sheet.tab_names[0])
                    row_count = sheet.start_row - 1
                    while True:
                        row_count += 1
                        deposit_amount, deposit_date = \
                            MintSheet.get_row(self.logger, row_count, sheet.amount_col, sheet.date_col, worksheet)
                        if deposit_date is None and deposit_amount is None:  # both are None
                            for entry in range(0, len(amounts)):
                                if amounts[entry] is not None:
                                    worksheet.update_cell(row=row_count, col=MintSheet.col2num(sheet.amount_col),
                                                          val=locale.currency(amounts[entry], grouping=True))
                                    worksheet.update_cell(row=row_count, col=MintSheet.col2num(sheet.notes_col),
                                                          val=notes[entry])
                                    row_count += 1
                                if entry == len(amounts)-1:
                                    worksheet.update_cell(row=row_count-1, col=MintSheet.col2num(sheet.date_col),
                                                          val=self.now.strftime("%m/%d/%Y"))
                                    row_count += 1
                            break
        except Exception as e:
            self.logger.exception("Caught an exception in " + __file__)


def main():
    mcd = MintCheckerDeposit()
    mcd.update_sheet()

if __name__ == "__main__":
    main()
