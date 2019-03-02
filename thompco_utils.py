import logging
import inspect
import os
import logging


def get_logger():
    stack = inspect.stack()
    if len(stack) == 2:
        file_name = os.path.basename(stack[1][1]).split(".")[0]
    else:
        file_name = os.path.basename(stack[2][1]).split(".")[0]
    the_function = stack[1][3]
    # noinspection PyBroadException
    try:
        if len(stack[1][0].f_locals) > 0:
            the_class = str(stack[1][0].f_locals["self"].__class__.__name__) + "."
        else:
            the_class = ""
    except Exception:
        the_class = ""
    logger_name = "{}.{}{}".format(file_name, the_class, the_function)
    return logging.getLogger(logger_name)


def get_log_file_name():
    for handler in logging.root.handlers:
        if handler.baseFilename is not None:
            return handler.baseFilename
    return None

