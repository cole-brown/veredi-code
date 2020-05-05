# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import logging
import datetime
import math

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
FMT_DATETIME = '%Y-%m-%d %H:%M:%S.{msecs:03d}%z'  # Yeah, this is fun.
STYLE = '{'

# https://docs.python.org/3/library/logging.html#logrecord-attributes
FMT_LINE_HUMAN = (
    '{asctime:s} - {name:s} - {levelname:8s} - '
    '{module:s}.{funcName:s}:{message:s}'
)

LOGGER_NAME = "veredi"

DEFAULT_LEVEL=logging.DEBUG

# ------------------------------------------------------------------------------
# Variables
# ------------------------------------------------------------------------------

initialized = False

logger = None


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def init(level=DEFAULT_LEVEL):
    global initialized
    if initialized:
        return

    global logger

    # Create our logger at our default output level.
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Console Handler, same level.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Set up our format.
    formatter = BestTimeFmt(fmt=FMT_LINE_HUMAN,
                            datefmt=FMT_DATETIME,
                            style=STYLE)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    initialized = True


class BestTimeFmt(logging.Formatter):
    converter = datetime.datetime.fromtimestamp

    def formatTime(self, record, fmt_date=None):
        converted = self.converter(record.created)
        if fmt_date:
            time_str = converted.strftime(fmt_date)
            string = time_str.format(msecs=math.floor(record.msecs))
        else:
            time_str = converted.strftime("%Y-%m-%d %H:%M:%S")
            string = "{:s}.{:03d}".format(time_str, math.floor(record.msecs))
        return string


def brace_message(fmt, *args, **kwargs):
    return fmt.format(*args, **kwargs)

# def fmt_msg(cls, method, msg):
#     if isinstance(cls, str):
#         return f"{cls}.{method}: msg"
#     return f"{cls.__class__.__name__}.{method}: msg"


def debug(msg, *args, **kwargs):
    logger.debug(
        brace_message(
            msg,
            *args, **kwargs))


def info(msg, *args, **kwargs):
    logger.info(
        brace_message(
            msg,
            *args, **kwargs))


def warning(msg, *args, **kwargs):
    logger.warning(
        brace_message(
            msg,
            *args, **kwargs))


def error(msg, *args, **kwargs):
    logger.error(
        brace_message(
            msg,
            *args, **kwargs))


def critical(msg, *args, **kwargs):
    logger.critical(
        brace_message(
            msg,
            *args, **kwargs))


# ------------------------------------------------------------------------------
# Module Setup
# ------------------------------------------------------------------------------

if not initialized:
    init()
