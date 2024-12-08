import logging
import sys
from datetime import datetime

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and timestamps"""
    
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - WARNING - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - ERROR - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - CRITICAL - %(message)s" + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logging():
    """Setup logging with colors and proper formatting"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter())
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    ) 