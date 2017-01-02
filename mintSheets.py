import gspread
import datetime
import cPickle
from dateutil import parser
from mintConfigFile import MintConfigFile
from oauth2client.service_account import ServiceAccountCredentials
import string
import os
import logging
import inspect


class MintSheet:
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    def __init__(self, config, start_date):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(config.sheets_json_file, MintSheet.scope)
        self.config = config
        self.g_spread = gspread.authorize(credentials)
        self.sheet_data = self._get_data(start_date)

    @staticmethod
    def col2num(col):
        num = 0
        for c in col:
            if c in string.ascii_letters:
                num = num * 26 + (ord(c.upper()) - ord('A')) + 1
        return num

    @staticmethod
    def get_sheet(g_spread, sheet_name, tab_name, new_owner=None):
        logger = logging.getLogger(inspect.stack()[0][3])
        worksheet = None
        try:
            logger.debug("trying to open sheet '" + sheet_name + "'")
            worksheet = g_spread.open(sheet_name)
        except Exception:
            logger.debug("failed trying to open sheet '" + sheet_name + "'")
            if new_owner is not None:
                try:
                    logger.debug("trying to create sheet '" + sheet_name + "'")
                    worksheet = g_spread.create(sheet_name)
                    worksheet.share(value=new_owner, perm_type="user", role="owner", notify=True,
                                    email_message="Just created this sheet")
                except Exception as e:
                    logging.exception("could not create worksheet '" + sheet_name + "'")
                    raise e
        try:
            logger.debug("trying to get tab '" + tab_name + "' on sheet '" + sheet_name + "'")
            try:  # share this worksheet in case we created it before but had an issue
                permissions = worksheet.list_permissions()
                added = False
                for permission in permissions:
                    if permission["emailAddress"] == new_owner:
                        added = True
                        break
                if not added:
                    worksheet.share(value=new_owner, perm_type="user", role="owner", notify=True,
                                    email_message="Just created this sheet")
            except:
                pass
            try:
                tab = worksheet.worksheet(tab_name)
            except:
                tab = None
            return tab
        except:
            logger.debug("failed trying to open tab '" + tab_name + "' on sheet '" + sheet_name + "'")
            if new_owner is None:
                logging.exception("Could not get tab '" + tab_name + "' on sheet '" + sheet_name + "'")
            else:
                try:
                    logger.debug("trying to create tab '" + tab_name + "'")
                    tab = worksheet.add_worksheet(tab_name, cols=100, rows=100)
                    try:  # remove Sheet1 if it exists
                        worksheet.del_worksheet(worksheet.worksheet("Sheet1"))
                    except:
                        pass
                    return tab
                except Exception as e:
                    logging.exception("could not create tab '" + tab_name + "' on worksheet '" + sheet_name + "'")
                    raise e

    @staticmethod
    def dollars2float(string_in):
        return float(string_in.replace(",", "").replace("$", ""))

    @staticmethod
    def get_row(row, amount_col, date_col, list_of_lists, sheet_name, tab_name):
        logger = logging.getLogger(inspect.stack()[0][3])
        logger.debug("getting row #" + str(row) + " on tab '" + tab_name
                     + "', on sheet '" + sheet_name + "'")
        try:
            deposit_cell = list_of_lists[row - 1][MintSheet.col2num(date_col) - 1]
            logger.debug("Got deposit date string of '" + deposit_cell + "'")
            deposit_date = parser.parse(deposit_cell)
        except Exception as e:
            logger.debug("Could not get deposit date from cell [" + date_col + ":" + str(row) + "]"
                         + "in sheet '" + sheet_name + "' on tab '" + tab_name
                         + "(not necessarily a problem, it could just be end of data)."
                         + "  Exception was:' " + e.message + "'")
            deposit_date = None
        try:
            amount_cell = list_of_lists[row - 1][MintSheet.col2num(amount_col) - 1]
            logger.debug("Got deposit amount string of '" + amount_cell + "'")
            deposit_amount = MintSheet.dollars2float(amount_cell)
        except Exception as e:
            logger.debug("Could not get deposit amount from cell [" + amount_col + ":" + str(row) + "]"
                         + "in sheet '" + sheet_name + "' on tab '" + tab_name
                         + "(not necessarily a problem, it could just be end of data)."
                         + "  Exception was:'" + e.message + "'")
            deposit_amount = None
        return deposit_amount, deposit_date

    def get_missing_deposits(self, mint_transactions, user):
        rtn = []
        for data in self.sheet_data:
            data["actual_deposit_date"] = None
            appended = False
            for transaction in mint_transactions.transactions:
                if "all" in user.accounts or data["deposit_account"] in user.accounts:
                    if not appended:
                        rtn.append(data)
                        appended = True
                    if transaction["account"] == data["deposit_account"] \
                            and transaction["amount"] == data["deposit_amount"]:
                        if data["expected_deposit_date"]\
                                + datetime.timedelta(data["date_error"]) >= transaction["date"] \
                                >= data["expected_deposit_date"] - datetime.timedelta(data["date_error"]):
                            data["actual_deposit_date"] = transaction["date"]
                            break
        return rtn

    def convert_name(self, name):
        names = [datetime.datetime.now().strftime(name)]
        if "%" in name:
            if datetime.datetime.today().day < self.config.worst_day_error:
                new_name = (datetime.datetime.now() - datetime.timedelta(self.config.worst_day_error)).strftime(name)
                if new_name not in names:
                    names.append(new_name)
        return names

    def _get_data(self, start_date):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        data = []
        for sheet in self.config.google_sheets:
            sheet_names = self.convert_name(sheet.sheet_name)
            tab_names = self.convert_name(sheet.tab_name)
            for sheet_name in sheet_names:
                for tab_name in tab_names:
                    logger.debug("Connecting to tab '" + tab_name + "', on sheet '" + sheet_name + "'"
                                 + " for " + sheet.billing_account)
                    try:
                        pickle_file = os.path.join(self.config.general_pickle_folder,
                                                   sheet.sheet_name + "_" + tab_name + ".pickle")
                        if self.config.debug_sheets_download:
                            worksheet = MintSheet.get_sheet(self.g_spread, sheet_name, tab_name)
                            list_of_lists = worksheet.get_all_values()
                            with open(pickle_file, 'wb') as handle:
                                cPickle.dump(list_of_lists, handle)
                        else:
                            with open(pickle_file, 'rb') as handle:
                                list_of_lists = cPickle.load(handle)
                        row_count = sheet.start_row - 1
                        while True:
                            row_count += 1
                            deposit_amount, deposit_date = \
                                MintSheet.get_row(row_count, sheet.amount_col, sheet.date_col,
                                                  list_of_lists, sheet.sheet_name, tab_name)
                            if deposit_date is None and deposit_amount is None:  # both are None
                                break
                            elif deposit_date is not None and deposit_amount is not None:  # neither is None
                                if deposit_date > start_date - datetime.timedelta(sheet.day_error):
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
                        logger.info("Tab " + tab_name + " on sheet " + sheet_name + " does not exist... skipping")
        return data


def main():
    config = MintConfigFile("home.ini")
    start_date = datetime.datetime.strptime('08/01/2016', "%d/%m/%Y")
    mint_spread = MintSheet(config, start_date)
    MintSheet.get_sheet(mint_spread.g_spread, "Transactions for West New Haven Plaza %Y", "test_tab %B")
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
