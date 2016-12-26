import logging.handlers
import os


class RelativePathRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, relative_path, file_name, max_bytes=2000, backup_count=100):
        local_path = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(local_path, relative_path)
        if not os.path.isdir(log_path):
            os.mkdir(log_path)
        log_file_name = os.path.join(log_path, file_name)
        super(RelativePathRotatingFileHandler, self).__init__(log_file_name, max_bytes, backup_count)
