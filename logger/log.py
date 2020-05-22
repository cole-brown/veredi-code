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
import sys
import os
import enum

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
    '{module:s}.{funcName:s}: {message:s}'
)

LOGGER_NAME = "veredi"

# ---
# Log Levels
# ---

@enum.unique
class Level(enum.IntEnum):
    NOTSET   = logging.NOTSET
    DEBUG    = logging.DEBUG
    INFO     = logging.INFO
    WARNING  = logging.WARNING
    ERROR    = logging.ERROR
    CRITICAL = logging.CRITICAL

    @staticmethod
    def valid(lvl):
        for known in Level:
            if lvl == known:
                return True
        return False

    @staticmethod
    def to_logging(lvl):
        return int(lvl)

DEFAULT_LEVEL = Level.INFO


# ------------------------------------------------------------------------------
# Variables
# ------------------------------------------------------------------------------

initialized = False

logger = None


# -----------------------------------------------------------------------------
# Logger Code
# -----------------------------------------------------------------------------

def init(level=DEFAULT_LEVEL):
    global initialized
    if initialized:
        return

    global logger

    # Create our logger at our default output level.
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(Level.to_logging(level))

    # Console Handler, same level.
    console_handler = logging.StreamHandler()
    # leave as NOTSET - this will let logger control log level
    # console_handler.setLevel(Level.to_logging(level))

    # Set up our format.
    formatter = BestTimeFmt(fmt=FMT_LINE_HUMAN,
                            datefmt=FMT_DATETIME,
                            style=STYLE)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    initialized = True

def set_level(level=DEFAULT_LEVEL):
    '''Change logger's log level. Options are:
      - log.CRITICAL
      - log.ERROR
      - log.WARNING
      - log.INFO
      - log.DEBUG
      - log.NOTSET
      - log.DEFAULT_LEVEL

    '''
    if not Level.valid(level):
        log.error("Invalid log level {}. Ignoring.", level)
        return

    logger.setLevel(Level.to_logging(level))


def will_output(level):
    '''
    Returns true if supplied `level` is high enough to output a log.
    '''
    if isinstance(level, Level):
        level = Level.to_logging(level)
    return level >= logger.level


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
    # print(f"bm:: fmt: {fmt}, args: {args}, kwa: {kwargs}")
    return fmt.format(*args, **kwargs)


def get_stack_level(kwargs):
    retval = 2
    if kwargs:
        retval = kwargs.pop('stacklevel', 2)
    return retval


def debug(msg, *args, **kwargs):
    stacklevel = get_stack_level(kwargs)
    logger.debug(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def info(msg, *args, **kwargs):
    stacklevel = get_stack_level(kwargs)
    logger.info(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def warning(msg, *args, **kwargs):
    stacklevel = get_stack_level(kwargs)
    logger.warning(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def error(msg, *args, **kwargs):
    stacklevel = get_stack_level(kwargs)
    logger.error(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def exception(err, msg=None, *args, **kwargs):
    '''
    Log the exception at ERROR level. If no `msg` supplied, will use:
        msg = "Exception caught. type: {}, str: {}"
        args = [type(err), str(err)]
    Otherwise error info will be tacked onto end.
      msg += " (Exception type: {err_type}, str: {err_str})"
      kwargs['err_type'] = type(err)
      kwargs['err_type'] = str(err)
    '''
    stacklevel = get_stack_level(kwargs)
    if not msg:
        "Exception caught. type: {}, str: {}"
        args = [type(err), str(err)]
    else:
        msg += " (Exception type: {err_type}, str: {err_str})"
        kwargs['err_type'] = type(err)
        kwargs['err_str'] = str(err)
    logger.error(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def critical(msg, *args, **kwargs):
    stacklevel = get_stack_level(kwargs)
    logger.critical(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


# ------------------------------------------------------------------------------
# Module Setup
# ------------------------------------------------------------------------------

if not initialized:
    init()
