import datetime
import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from colorama import init, Fore, Style, Back
init(autoreset=True)

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
PATH = Path(__file__).parent.parent

log_folder = os.path.join(PATH, ".runtime/log/")
Path(log_folder).mkdir(parents=True, exist_ok=True)
LOG_FILE =  os.path.join(log_folder, f"decidra_{str(datetime.date.today())}.log")


class ColorFormatter(logging.Formatter):
    # Change this dictionary to suit your coloring needs!
    COLORS = {
        "WARNING": Fore.RED,
        "ERROR": Fore.RED + Back.WHITE,
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "CRITICAL": Fore.RED + Back.WHITE
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.name = color + record.name
            record.levelname = color + record.levelname
            record.msg = color + record.msg
        return logging.Formatter.format(self, record)


class ColorLogger(logging.Logger):
    def __init__(self, name):
        logging.Logger.__init__(self, name, logging.DEBUG)
        color_formatter = ColorFormatter("%(name)-10s %(levelname)-18s %(message)s")
        console = logging.StreamHandler()
        console.setFormatter(color_formatter)
        self.addHandler(console)
        file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
        file_handler.setFormatter(FORMATTER)
        self.addHandler(file_handler)
        self.propagate = False

def get_logger(logger_name):
    return ColorLogger(logger_name)

def setup_logger(logger_name=__name__):
    return ColorLogger(logger_name)