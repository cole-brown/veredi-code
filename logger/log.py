# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Type, Optional, Any, Mapping
import logging
import datetime
import math
import sys
import os
import enum


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

FMT_DATETIME = '%Y-%m-%d %H:%M:%S.{msecs:03d}%z'  # Yeah, this is fun.

# Could use logging.Formatter and set like so:
# FMT_DATETIME = '%Y-%m-%d %H:%M:%S'
# FMT_MSEC = '%s.%03d'
#     ...
#     formatter = logging.Formatter(fmt=FMT_LINE_HUMAN,
#                             datefmt=FMT_DATETIME,
#                             style=STYLE)
#     formatter.default_time_format = FMT_DATETIME
#     formatter.default_msec_format = FMT_MSEC
#     ...
# But that would miss out on being able to stuff our msecs inside of the
# datetime str like I want...

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
    def valid(lvl: Union['Level', int]) -> bool:
        for known in Level:
            if lvl == known:
                return True
        return False

    @staticmethod
    def to_logging(lvl: Union['Level', int]) -> int:
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

def init(level: Union[Level, int] = DEFAULT_LEVEL) -> None:
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


def set_level(level: Union[Level, int] = DEFAULT_LEVEL) -> None:
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


def will_output(level: Union[Level, int]) -> bool:
    '''
    Returns true if supplied `level` is high enough to output a log.
    '''
    if isinstance(level, Level):
        level = Level.to_logging(level)
    return level >= logger.level


class BestTimeFmt(logging.Formatter):
    converter = datetime.datetime.fromtimestamp

    def formatTime(self,
                   record: logging.LogRecord,
                   fmt_date: str = None):
        converted = self.converter(record.created)
        if fmt_date:
            time_str = converted.strftime(fmt_date)
            string = time_str.format(msecs=math.floor(record.msecs))
        else:
            time_str = converted.strftime("%Y-%m-%d %H:%M:%S")
            string = "{:s}.{:03d}".format(time_str, math.floor(record.msecs))
        return string


def brace_message(fmt: str,
                  *args: Any, **kwargs: Mapping[str, Any]) -> str:
    # print(f"bm:: fmt: {fmt}, args: {args}, kwa: {kwargs}")
    return fmt.format(*args, **kwargs)


def get_stack_level(kwargs: Mapping[str, Any]) -> int:
    '''
    Returns kwargs['stacklevel'] if it exists, or default (of 2).
    '''
    retval = 2
    if kwargs:
        retval = kwargs.pop('stacklevel', 2)
    return retval


def debug(msg: str,
          *args: Any,
          **kwargs: Any) -> None:
    stacklevel = get_stack_level(kwargs)
    logger.debug(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def info(msg: str,
          *args: Any,
          **kwargs: Any) -> None:
    stacklevel = get_stack_level(kwargs)
    logger.info(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def warning(msg: str,
            *args: Any,
            **kwargs: Any) -> None:
    stacklevel = get_stack_level(kwargs)
    logger.warning(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def error(msg: str,
          *args: Any,
          **kwargs: Any) -> None:
    stacklevel = get_stack_level(kwargs)
    logger.error(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def exception(err: Exception,
              wrap_type: Optional[Type['VerediError']],
              msg:       Optional[str],
              *args:     Any,
              context:   Optional['VerediContext'] = None,
              **kwargs:  Any) -> None:
    '''
    The exception this logs is:
      - if err is not None
           err
        else
           wrap_type(<our log msg pre logging.Formatter>,
                    None,
                    context)

    Log the exception at ERROR level. If no `msg` supplied, will use:
        msg = "Exception caught. type: {}, str: {}"
        args = [type(err), str(err)]
    Otherwise error info will be tacked onto end.
      msg += " (Exception type: {err_type}, str: {err_str})"
      kwargs['err_type'] = type(err)
      kwargs['err_type'] = str(err)

    can piggy-back easier.
    Then returns either:
      - if wrap_type is None:
          err (the input error)
      - else:
          wrap_type(<our log msg pre logging.Formatter>,
                    err,
                    context)
    This way you can:
    except SomeError as error:
        raise log.exception(
            error,
            SomeVerediError,
            "Cannot frobnicate {} from {}. {} instead.",
            source, target, nonFrobMunger,
            context=self.context
        ) from error
    '''
    log_msg_err_type = None
    log_msg_err_str = None
    if err is not None:
        log_msg_err_type = type(err)
        log_msg_err_str = str(err)
    else:
        log_msg_err_type = wrap_type
        log_msg_err_str = None

    stacklevel = get_stack_level(kwargs)
    if not msg:
        msg = "Exception caught. type: {}, str: {}"
        args = [log_msg_err_type, log_msg_err_str]
    else:
        msg += " (Exception type: {err_type}, str: {err_str})"
        kwargs['err_type'] = log_msg_err_type
        kwargs['err_str'] = log_msg_err_str

    log_msg = brace_message(msg, *args, **kwargs),
    logger.error(log_msg,
                 stacklevel=stacklevel)

    if wrap_type:
        return wrap_type(log_msg, err, context)
    return err


def critical(msg: str,
             *args: Any,
             **kwargs: Any) -> None:
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
