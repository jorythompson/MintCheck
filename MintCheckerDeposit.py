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
import inspect

class MintCheckerDeposit:
    def __init__(self):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        self.now = datetime.datetime.combine(datetime.date.today(), datetime.time())
        self.args = self._get_args()
        self.config = MintConfigFile(self.args.config, test_email=self.args.validate_emails,
                                     validate=self.args.validate_ini)
        logger.debug("Today is " + self.now.strftime('%m/%d/%Y at %H:%M:%S'))
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.config.sheets_json_file, MintSheet.scope)
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
        parser.add_argument('--deposit-account', required=True,
                            help='Account to apply this deposit to')
        parser.add_argument('--date', required=False, default=self.now.strftime("%m/%d/%Y"),
                            help='Date to use for this deposit')
        parser.add_argument('--validate_ini', action="store_true", default=False,
                            help='Validates the input configuration file')
        parser.add_argument('--validate_emails',  action="store_true", default=False,
                            help='Validates sending emails to all users in the configuration file')
        return parser.parse_args()

    def update_sheet(self):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        try:
            logger.debug("config file is '" + self.args.config + "'")
            logger.debug("sheet is '" + self.args.sheet + "'")
            notes = ast.literal_eval(str(self.args.notes))
            amounts = self.args.amounts
            while ",," in amounts:
                amounts = amounts.replace(",,", ",None,")
            amounts = ast.literal_eval(amounts)
            if len(amounts) != len(notes):
                raise RuntimeError("Number of elements in payors and amounts should be the same")
            logger.debug("notes are " + str(notes))
            logger.debug("amounts are " + str(amounts))
            logger.debug("account is '" + self.args.deposit_account + "'")
            logger.debug("date is '" + self.args.date + "'")
            logger.debug("validate ini is '" + str(self.args.validate_ini) + "'")
            logger.debug("validate emails is '" + str(self.args.validate_emails) + "'")
            self.now = parser.parse(self.args.date)
            for sheet in self.config.google_sheets:
                if sheet.deposit_account == self.args.deposit_account:
                    logger.debug("found tab as " + self.args.deposit_account)
                    worksheet = MintSheet.get_sheet(self.g_spread, sheet.sheet_name, sheet.tab_name,
                                                    self.config.general_admin_email)
                    list_of_lists = worksheet.get_all_values()
                    row_count = sheet.start_row - 1
                    while True:
                        row_count += 1
                        deposit_amount, deposit_date = \
                            MintSheet.get_row(row_count, sheet.amount_col, sheet.date_col, list_of_lists,
                                              sheet.sheet_name, self.args.deposit_account)
                        if deposit_date is None and deposit_amount is None:  # both are None
                            for entry in range(0, len(amounts)):
                                if amounts[entry] is not None:
                                    val = locale.currency(amounts[entry], grouping=True)
                                    logger.debug("setting cell(" + sheet.amount_col + str(row_count) + ") to " + val)
                                    worksheet.update_cell(row=row_count, col=MintSheet.col2num(sheet.amount_col),
                                                          val=val)
                                    val = notes[entry]
                                    logger.debug("setting cell(" + sheet.notes_col + str(row_count) + ") to " + val)
                                    worksheet.update_cell(row=row_count, col=MintSheet.col2num(sheet.notes_col),
                                                          val=val)
                                    row_count += 1
                                if entry == len(amounts)-1:
                                    val = self.now.strftime("%m/%d/%Y")
                                    logger.debug("setting cell(" + sheet.date_col + str(row_count-1) + ") to " + val)
                                    worksheet.update_cell(row=row_count-1, col=MintSheet.col2num(sheet.date_col),
                                                          val=val)
                                    row_count += 1
                            break
        except Exception as e:
            logger.exception("Caught an exception in " + __file__)


def main():
    mcd = MintCheckerDeposit()
    mcd.update_sheet()

if __name__ == "__main__":
    logging.config.fileConfig('logging.conf')
    main()
