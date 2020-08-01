# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Callable,
                    Mapping, MutableMapping, Iterable)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext
    from veredi.base.exceptions import VerediError

import logging
import datetime
import math
import enum


from veredi.base.null import Null, Nullable, NullNoneOr


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

_unit_test_callback = Null()


# -----------------------------------------------------------------------------
# Logger Code
# -----------------------------------------------------------------------------

def init(level: Union[Level, int] = DEFAULT_LEVEL,
         handler: Optional[logging.Handler] = None,
         formatter: Optional[logging.Formatter] = None) -> None:
    '''
    Initializes our root logger.
    '''
    global __initialized
    if __initialized:
        return

    global logger

    # Create our logger at our default output level.
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(Level.to_logging(level))

    if not handler:
        # Console Handler, same level.
        handler = logging.StreamHandler()
        # leave as NOTSET - this will let logger control log level
        # handler.setLevel(Level.to_logging(level))

        # Set up our formatter, but only if handler was not specified. For e.g.
        # log client/server, we don't want a formatter on this (client) side.
        #
        # Docs: "Don't bother with a formatter, since a socket handler sends
        # the event as an unformatted pickle."
        #   - https://docs.python.org/3/howto/logging-cookbook.html#network-logging
        #   - [2020-07-19]
        formatter = BestTimeFmt(fmt=FMT_LINE_HUMAN,
                                datefmt=FMT_DATETIME,
                                style=STYLE)
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    __initialized = True


def get_logger(*names: str) -> logging.Logger:
    '''
    Get a logger by name. Names should be module name, or module and
    class name. ...Or dotted name? Not sure.

    Ignores any 'Falsy' values in `names` when building a name from parts.

    E.g.:
      get_logger(__name__, self.__class__.__name__)
      get_logger(__name__)
      ???
        get_logger(self.dotted)
      ???
    '''
    # Ignore any Falsy values in names
    logger_name = '.'.join([each for each in names if each])
    return logging.getLogger(logger_name)


def _logger(veredi_logger: NullNoneOr[logging.Logger] = None
            ) -> logging.Logger:
    '''
    Returns `veredi_logger` if it is Truthy.
    Returns the default veredi logger if not.
    '''
    return (veredi_logger
            if veredi_logger else
            logger)


def get_level(veredi_logger: NullNoneOr[logging.Logger] = None) -> Level:
    '''Returns current log level of logger, translated into Level enum.'''
    this = _logger(veredi_logger)
    level = Level(this.level)
    return level


def set_level(level: Union[Level, int] = DEFAULT_LEVEL,
              veredi_logger: NullNoneOr[logging.Logger] = None) -> None:
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

    this = _logger(veredi_logger)
    this.setLevel(Level.to_logging(level))


def will_output(level: Union[Level, int],
                veredi_logger: NullNoneOr[logging.Logger] = None) -> bool:
    '''
    Returns true if supplied `level` is high enough to output a log.
    '''
    if isinstance(level, Level):
        level = Level.to_logging(level)
    this = _logger(veredi_logger)
    return level >= this.level


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
                  *args: Any,
                  context: Optional['VerediContext'] = None,
                  **kwargs: Mapping[str, Any]) -> str:
    '''
    Pass-through `fmt` if no args/kwargs.

    Otherwise use '.format()' brace formatting on `fmt` string.
    '''
    # print(f"bm:: fmt: {fmt}, args: {args}, kwa: {kwargs}")
    ctx_msg = ''
    if context:
        ctx_msg = f' context: {context}'
    if not args and not kwargs:
        return fmt + ctx_msg
    return fmt.format(*args, **kwargs) + ctx_msg


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
          veredi_logger: NullNoneOr[logging.Logger] = None,
          **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    output = brace_message(msg,
                           *args, **kwargs)
    if not ut_call(Level.DEBUG, output):
        this = _logger(veredi_logger)
        this.debug(output,
                   stacklevel=stacklevel)


def info(msg: str,
         *args: Any,
         veredi_logger: NullNoneOr[logging.Logger] = None,
         **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    output = brace_message(msg,
                           *args, **kwargs)
    if not ut_call(Level.INFO, output):
        this = _logger(veredi_logger)
        this.info(output,
                  stacklevel=stacklevel)


def warning(msg: str,
            *args: Any,
            veredi_logger: NullNoneOr[logging.Logger] = None,
            **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    output = brace_message(msg,
                           *args, **kwargs)
    if not ut_call(Level.WARNING, output):
        this = _logger(veredi_logger)
        this.warning(output,
                     stacklevel=stacklevel)


def error(msg: str,
          *args: Any,
          veredi_logger: NullNoneOr[logging.Logger] = None,
          **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    output = brace_message(msg,
                           *args, **kwargs)
    if not ut_call(Level.ERROR, output):
        this = _logger(veredi_logger)
        this.error(output,
                   stacklevel=stacklevel)


def exception(err: Exception,
              wrap_type: Optional[Type['VerediError']],
              msg:       Optional[str],
              *args:     Any,
              context:   Optional['VerediContext'] = None,
              associate: Optional[Union[Any, Iterable[Any]]] = None,
              veredi_logger: NullNoneOr[logging.Logger] = None,
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

    If something is supplied as 'associate' kwarg, it will go into the
    'associated' value of the veredi wrapping exception.

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

    log_msg = brace_message(msg, *args, context=context, **kwargs)
    this = _logger(veredi_logger)
    this.error(log_msg,
               stacklevel=stacklevel)

    if wrap_type:
        return wrap_type(log_msg, err,
                         context=context,
                         associated=associate)
    return err


def critical(msg: str,
             *args: Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
             **kwargs: Any) -> None:
    stacklevel = pop_stack_level(kwargs)
    output = brace_message(msg,
                           *args, **kwargs)
    if not ut_call(Level.CRITICAL, output):
        this = _logger(veredi_logger)
        this.critical(output,
                      stacklevel=stacklevel)


def at_level(level: 'Level',
             msg: str,
             *args: Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
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

    log_fn(msg, *args, veredi_logger=veredi_logger, **kwargs)


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
    def on_or_off(enabled: bool, bookends: bool = False) -> 'LoggingManager':
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
# Unit Testing
# -----------------------------------------------------------------------------

def ut_call(level: 'Level',
            output: str) -> bool:
    '''
    Call this; it will figure out if it needs to do any of the unit-test
    callback stuff.

    Returns bool:
      - True if _unit_test_callback wants to eat the log.
      - False if no callback or it doesn't want to eat the log.
    '''
    if not _unit_test_callback or not callable(_unit_test_callback):
        return False

    return _unit_test_callback(level, output)


def ut_set_up(callback: Nullable[Callable[['Level', str], bool]]) -> None:
    '''
    Set up for unit testing.

    `callback` will be call for every log output function with log level and
    final output string. It should return a bool: true for when it wants to eat
    the log and not let it be logged out, False otherwise (tee message to it
    and logger).
    '''
    global _unit_test_callback
    _unit_test_callback = callback


def ut_tear_down() -> None:
    '''
    Tear down for unit testing.

    Reset things that were set in ut_set_up().
    '''
    global _unit_test_callback
    _unit_test_callback = Null()


# -----------------------------------------------------------------------------
# Module Setup
# -----------------------------------------------------------------------------

if not __initialized:
    init()
