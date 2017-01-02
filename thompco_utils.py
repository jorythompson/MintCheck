import logging


def get_log_file_name():
    for handler in logging.root.handlers:
        if handler.baseFilename is not None:
            return handler.baseFilename
    return None

