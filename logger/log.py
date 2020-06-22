# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Union,
                    Type,
                    Optional,
                    Any,
                    Mapping,
                    MutableMapping)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from veredi.base.exceptions import VerediError

import logging
import datetime
import math
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


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

__initialized = False

logger = None


# -----------------------------------------------------------------------------
# Logger Code
# -----------------------------------------------------------------------------

def init(level: Union[Level, int] = DEFAULT_LEVEL) -> None:
    global __initialized
    if __initialized:
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

    __initialized = True


def get_level() -> Level:
    '''Returns current log level of logger, translated into Level enum.'''
    level = Level(logger.level)
    return level


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
        error("Invalid log level {}. Ignoring.", level)
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


def pop_stack_level(kwargs: Mapping[str, Any]) -> int:
    '''
    Returns kwargs['stacklevel'] if it exists, or default (of 2).
    '''
    retval = 2
    if kwargs:
        retval = kwargs.pop('stacklevel', 2)
    return retval


def set_stack_level(
        level: int,
        kwargs: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    '''
    Adds or sets 'stacklevel' in kwargs.
    '''
    if not kwargs:
        kwargs = {}
    kwargs['stacklevel'] = level
    return kwargs


def incr_stack_level(
        kwargs: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    '''
    Adds or sets 'stacklevel' in kwargs.
    '''
    if not kwargs:
        kwargs = {}
    stacklevel = pop_stack_level(kwargs)
    stacklevel += 1
    set_stack_level(stacklevel, kwargs)
    return kwargs


def debug(msg: str,
          *args: Any,
          **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    logger.debug(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def info(msg: str,
         *args: Any,
         **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    logger.info(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def warning(msg: str,
            *args: Any,
            **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    logger.warning(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def error(msg: str,
          *args: Any,
          **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
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

    stacklevel = pop_stack_level(kwargs)
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
    stacklevel = pop_stack_level(kwargs)
    logger.critical(
        brace_message(
            msg,
            *args, **kwargs),
        stacklevel=stacklevel)


def at_level(level: 'Level',
             msg: str,
             *args: Any,
             **kwargs: Any) -> None:
    kwargs = incr_stack_level(kwargs)
    log_fn = None
    if level == Level.NOTSET:
        exception(ValueError("Cannot log at NOTSET level.",
                             msg, args, kwargs),
                  None,
                  msg,
                  args,
                  kwargs)
    elif level == Level.DEBUG:
        log_fn = debug
    elif level == Level.INFO:
        log_fn = info
    elif level == Level.WARNING:
        log_fn = warning
    elif level == Level.ERROR:
        log_fn = error
    elif level == Level.CRITICAL:
        log_fn = critical

    log_fn(msg, *args, **kwargs)


# -----------------------------------------------------------------------------
# Logging Context Manager
# -----------------------------------------------------------------------------
# A context manager for unit testing/debugging that will
# turn up log level then turn it back to where it was when done.
# e.g.:
#   with log.manage.full_blast():
#       something_weird_happening()
# Also:
#   with log.manage.disabled():
#       something_log_spammy_we_dont_care_about_right_now()

class LoggingManager:
    def __init__(self, level: Level, no_op: bool = False):
        self._desired = level
        self._original = get_level()
        self._do_nothing = no_op

    def __enter__(self):
        if self._do_nothing:
            return

        self._original = get_level()
        set_level(self._desired)

    def __exit__(self, type, value, traceback):
        '''We do the same thing, regardless of an exception or not.'''
        if self._do_nothing:
            return

        set_level(self._original)

    def bookend(self, start):
        if start:
            print("\n\n\n")
        print("========================================"
              "========================================")
        print("========================================"
              "========================================")
        print("========================================"
              "========================================")
        if not start:
            print("\n\n\n")

    # ---
    # Specific Manager Types...
    # ---
    @staticmethod
    def on_or_off(enabled: bool) -> 'LoggingManager':
        '''
        Returns either a full_blast() manager or an ignored() manager,
        depending on `enabled`.
        '''
        if enabled:
            return LoggingManager.full_blast()
        return LoggingManager.ignored()

    @staticmethod
    def full_blast() -> 'LoggingManager':
        '''
        This one sets logging to most verbose level - DEBUG.
        '''
        return LoggingManager(Level.DEBUG)

    @staticmethod
    def disabled() -> 'LoggingManager':
        '''
        This one sets logging to least verbose level - CRITICAL.
        '''
        # TODO [2020-05-30]: more 'disabled' than this?
        return LoggingManager(Level.CRITICAL)

    @staticmethod
    def ignored() -> 'LoggingManager':
        '''
        This one does nothing.
        '''
        return LoggingManager(Level.CRITICAL, no_op=True)


# -----------------------------------------------------------------------------
# Module Setup
# -----------------------------------------------------------------------------

if not __initialized:
    init()
