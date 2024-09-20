#!/usr/local/bin python3
import logging
import sys

logger = logging.getLogger()

class MyFormatter(logging.Formatter):

    COLORS = {
        logging.DEBUG: "\x1b[38;21m", # gray
        logging.INFO: "\x1b[38;5;39m", # blue
        logging.WARNING: "\x1b[38;5;3m", # yellow
        logging.ERROR: "\x1b[38;5;196m", # red
        logging.CRITICAL: "\x1b[31;1m", # bold red
    }
    COLORRESET = "\x1b[0m"

    def __init__(self):
        super().__init__()
        self.datefmt = "%m/%d %H:%M:%S"

    def format(self, record):
        log_fmt = "%(asctime)s " + self.COLORS.get(record.levelno) + "[%(levelname)s]" + self.COLORRESET + " %(message)s"
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(MyFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
