# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Type, Callable,
                    Mapping, MutableMapping, Iterable, Dict, List)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext


# ------------------------------
# Imports for helping others do type hinting
# ------------------------------
from logging import Logger as PyLogType  # noqa


# ------------------------------
# Imports to Do Stuff
# ------------------------------
import logging
import datetime
import math
import enum
from types import TracebackType

from veredi.base.null       import Null, Nullable, NullNoneOr, null_or_none
from veredi.base            import label
from veredi.base.exceptions import VerediError

from . import pretty


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LogLvlConversion = NewType('', NullNoneOr[Union['Level', int]])


_FMT_DATETIME = '%Y-%m-%d %H:%M:%S.{msecs:03d}%z'  # Yeah, this is fun.

# Could use logging.Formatter and set like so:
# _FMT_DATETIME = '%Y-%m-%d %H:%M:%S'
# _FMT_MSEC = '%s.%03d'
#     ...
#     formatter = logging.Formatter(fmt=_FMT_LINE_HUMAN,
#                             datefmt=_FMT_DATETIME,
#                             style=_STYLE)
#     formatter.default_time_format = _FMT_DATETIME
#     formatter.default_msec_format = _FMT_MSEC
#     ...
# But that would miss out on being able to stuff our msecs inside of the
# datetime str like I want...


_STYLE = '{'


# https://docs.python.org/3/library/logging.html#logrecord-attributes
_FMT_LINE_HUMAN = (
    '{asctime:s} - {name:s} - {levelname:8s} - '
    '{module:s}.{funcName:s}{message:s}'
)
'''
Having no space between Python logging variables and `message` will allow
for nicer formatting of e.g. GROUP logging.
'''


@enum.unique
class MessageType(enum.Enum):
    DEFAULT = enum.auto()
    NO_FMT  = enum.auto()
    GROUP   = enum.auto()


_FMT_MESSAGE_HUMAN  = {
    MessageType.DEFAULT: ': {message:s}',
    MessageType.NO_FMT:  '{message:s}',
    MessageType.GROUP:   ' - GROUP[{group:s}, {dotted:s}]: {message:s}',
}
'''
Formatting options for `message` in `_FMT_LINE_HUMAN`.
'''


@enum.unique
class SuccessType(enum.Enum):
    '''
    Success/failure into easier/more consistent strings to see in logs.
    '''
    # ------------------------------
    # Values
    # ------------------------------

    IGNORE = None
    '''Becomes the empty string.'''

    # ---
    # Standard
    # ---
    BLANK = '    '

    FAILURE = 'FAIL'

    SUCCESS = 'OK'

    NEUTRAL = '----'

    # ---
    # Dry Run?
    # ---
    _DRY_BLANK   = '____'
    '''Use `BLANK` and `resolve()` to this, please.'''

    _DRY_NEUTRAL = '_--_'  # (*shrug*)
    '''Use `NEUTRAL` and `resolve()` to this, please.'''

    _DRY_FAILURE = '_F__'  # F(ail)
    '''Use `FAILURE` and `resolve()` to this, please.'''

    _DRY_SUCCESS = '__K_'  # (O)k
    '''Use `SUCCESS` and `resolve()` to this, please.'''

    # ------------------------------
    # Functions
    # ------------------------------

    def resolve(self, dry_run: bool) -> 'SuccessType':
        '''
        Converts a standard value to Dry-Run if `is_dry_run`.
        '''
        if (self is SuccessType.IGNORE
                or not dry_run):
            return self

        # Expect the naming scheme to always hold true.
        return SuccessType['_DRY_' + self.name]

    def __format__(self, format_spec: str) -> str:
        '''
        Check for our None value, then have string formatted.
        '''
        # Center ourself on a 6 char wide string:
        #    1: '['
        #  2-5: self.value
        #    6: ']'
        # Or, if value is None, just make a 6 char wide string (no brackets).
        value = '{:^6s}'.format(
            self.value
            if self.value is not None else
            '')
        return value.__format__(format_spec)

    def __str__(self) -> str:
        '''
        Returns value string of enum formatted into e.g.:
          [ OK ]
          [_F__]
        '''
        return '{:^6s}'.format(self)


_FMT_SUCCESS_HUMAN = '{success:s}: {message:s}'
'''Format for combining string'd success and log message.'''


_CONTEXT_INDENT_AMT = 4


_ULTRA_MEGA_DEBUG_BT = '!~'
_ULTRA_MEGA_DEBUG_TB = '~!'
_ULTRA_MEGA_DEBUG_DBG = (
    _ULTRA_MEGA_DEBUG_BT
    + 'DEBUG'
    + _ULTRA_MEGA_DEBUG_TB
)
_ULTRA_MEGA_DEBUG_FMT = (
    '\n'
    + _ULTRA_MEGA_DEBUG_DBG + (_ULTRA_MEGA_DEBUG_TB * 30) + '\n'
    + ('v' * 69) + '\n\n'
    + '{output}' + '\n\n'
    + ('^' * 69) + '\n'
    + _ULTRA_MEGA_DEBUG_DBG + (_ULTRA_MEGA_DEBUG_TB * 30) + '\n'
    + '\n\n'
)


_ULTRA_HYPER_DEBUG = 'U-L-T-R-A = H-Y-P-E-R = D-E-B-U-G = L-O-G'
_ULTRA_HYPER_SYMBOL = '☢'
_ULTRA_HYPER_INDENT_AMT = 4
_ULTRA_HYPER_DEBUG_FMT = (
    '\n'
    + '---\n'
    + '-----\n'
    + '-= ' + _ULTRA_HYPER_DEBUG + ' =-\n'
    + '{output}\n'
    + '-= ' + _ULTRA_HYPER_DEBUG + ' =-\n'
    + '-----\n'
    + '---\n\n'
)


# ------------------------------
# Log Levels
# ------------------------------

@enum.unique
class Level(enum.IntEnum):
    '''
    Log level enum. Values are python's logging module log level ints.
    '''

    NOTSET   = logging.NOTSET
    DEBUG    = logging.DEBUG
    INFO     = logging.INFO
    WARNING  = logging.WARNING
    ERROR    = logging.ERROR
    CRITICAL = logging.CRITICAL

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def valid(lvl: Union['Level', int]) -> bool:
        for known in Level:
            if lvl == known:
                return True
        return False

    @staticmethod
    def to_logging(lvl: LogLvlConversion) -> int:
        if null_or_none(lvl):
            lvl = Level.NOTSET
        return int(lvl)

    @staticmethod
    def from_logging(lvl: LogLvlConversion) -> 'Level':
        if null_or_none(lvl):
            return Level.NOTSET
        return Level(lvl)

    @staticmethod
    def most_verbose(lvl_a: Union['Level', int, None],
                     lvl_b: Union['Level', int, None],
                     ignore_notset: bool = True) -> 'Level':
        '''
        Returns whichever of `a` or `b` is the most verbose logging level.

        Converts 'None' to Level.NOTSET.

        if `ignore_notset` is True, this will try to get the most verbose and
        return 'the other one' if one is logging level NOTSET. Otherwise, this
        will consider logging level NOTSET as the MOST verbose level.

        NOTSET actually means "use the parent's logging level", so take care.
        '''
        lvl_a = Level.to_logging(lvl_a)
        lvl_b = Level.to_logging(lvl_b)

        # If we're ignoring NOTSET, check for it and return 'the other one' if
        # found. If 'the other one' is also NOTSET, well... we tried.
        if ignore_notset:
            if lvl_a == Level.NOTSET.value:
                return Level.from_logging(lvl_b)
            if lvl_b == Level.NOTSET.value:
                return Level.from_logging(lvl_a)

        # The logging levels are:
        #   NOTSET:    0
        #   DEBUG:    10
        #   ...
        #   CRITICAL: 50
        # So for the most verbose, we want the minimum. NOTSET was addressed
        # above in the 'ignore_notset' check, so here we just assume NOTSET is
        # the most verbose.
        lvl = min(lvl_a, lvl_b)
        return lvl

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        return self.__class__.__name__ + '.' + self.name

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        return self.__class__.__name__ + '.' + self.name


DEFAULT_LEVEL = Level.INFO
'''Veredi's default logging level.'''


# ------------------------------
# Logging "Groups"
# ------------------------------

@enum.unique
class Group(enum.Enum):
    '''
    A logging group is for relating certain logs to a log.Level indirectly.

    E.g. log.Group.SECURITY can be set to Level.WARNING, or turned down to
    Level.DEBUG, and all log.Group.SECURITY logs will dynamically log out at
    the current level for the group.
    '''

    # ------------------------------
    # Values
    # ------------------------------

    START_UP = 'start-up'
    '''Logs related to start up of Veredi, the game, etc.'''

    SECURITY = 'security'
    '''veredi.security.* logs, and related logs.'''

    # TODO: more groups

    # ------------------------------
    # Functions
    # ------------------------------

    def __str__(self) -> str:
        '''
        Returns value string of enum.
        '''
        return self.value


_GROUP_LEVELS: Dict[Group, Level] = {
    Group.SECURITY: Level.WARNING,
    Group.START_UP: Level.DEBUG,
}


# ------------------------------
# Logger Names
# ------------------------------

@enum.unique
class LogName(enum.Enum):
    ROOT = label.join('veredi')
    '''
    The default/root veredi logger.
    '''

    MULTIPROC = label.join(ROOT, 'multiproc')
    '''
    multiproc's logger for setting up/tearing down sub-processes.
    '''

    # TODO [2020-09-12]: More logger names. Some formats?

    def _make(*name: str) -> str:
        '''
        Make **ANY** LogName from `*name` strings.

        Should use `rooted()` unless you're special.
        '''
        return label.join(*name)

    def rooted(self, *name: str) -> str:
        '''
        Make a LogName rooted from LogName enum called from.
        Examples:
          LogName.ROOT.rooted('jeff')
            -> 'veredi.jeff'
          LogName.MULTIPROC.rooted('server', 'jeff')
            -> 'veredi.multiproc.server.jeff'
        '''
        return label.join(str(self), *name)

    def __str__(self) -> str:
        '''
        Returns value string of enum.
        '''
        return self.value


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

__initialized: bool = False

logger: logging.Logger = None
'''Our main/default logger.'''

__handlers: List[logging.Handler] = []
'''Our main/default logger's main/default handler(s).'''

_unit_test_callback: Callable = Null()


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

def init(level:        LogLvlConversion            = DEFAULT_LEVEL,
         handler:      Optional[logging.Handler]   = None,
         formatter:    Optional[logging.Formatter] = None,
         reinitialize: Optional[bool]              = None,
         debug:        Optional[Any]               = None) -> None:
    '''
    Initializes our root logger.

    `debug` purely here for debugging log_server, log_client setting up their
    loggers.
    '''
    # ------------------------------
    # No Re-Init.
    # ------------------------------
    global __initialized
    if __initialized and not reinitialize:
        return
    __initialized = True

    # ------------------------------
    # Logger
    # ------------------------------
    global logger
    logger = init_logger(str(LogName.ROOT), level, formatter)

    # ------------------------------
    # Root Logger's Handler(s)
    # ------------------------------

    # Only let the root logger have special handlers.

    # Either got supplied a handler or we'll be making one. Either way, we want
    # to get rid of any of ours it has.
    global __handlers
    if __handlers:
        for handle in __handlers:
            logger.removeHandler(handle)
        __handlers = []

    # Get rid of any of its own handlers if we've got ones to give it.
    if handler is not None:
        for handle in list(logger.handlers):
            logger.removeHandler(handler)

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
        formatter = BestTimeFmt(fmt=_FMT_LINE_HUMAN,
                                datefmt=_FMT_DATETIME,
                                style=_STYLE)
        handler.setFormatter(formatter)

    # Now set it in our collection and on the logger.
    __handlers.append(handler)
    logger.addHandler(handler)


def init_logger(logger_name: str,
                level:       LogLvlConversion            = DEFAULT_LEVEL,
                formatter:   Optional[logging.Formatter] = None
                ) -> logging.Logger:
    '''
    Initializes and returns a logger with the supplied name.
    '''
    # Create our logger at our default output level.
    logger = logging.getLogger(logger_name)
    logger.setLevel(Level.to_logging(level))
    logger.debug(f"logger initialized at level {level}")

    return logger


# -----------------------------------------------------------------------------
# Logger Helpers
# -----------------------------------------------------------------------------

def remove_handler(handler:     logging.Handler,
                   logger:      Optional[logging.Logger] = None,
                   logger_name: Optional[str]            = None) -> None:
    '''
    Look in log.__handlers for `handler`. If it finds a match, removes it from
    log.__handlers.

    Calls `removeHandler()` on supplied (or default) logger regardless.
    '''
    if __handlers and handler in __handlers:
        __handlers.remove(handler)

    if logger:
        logger.removeHandler(handler)

    if logger_name:
        logging.getLogger(logger_name).removeHandler(handler)


def get_logger(*names:        str,
               min_log_level: LogLvlConversion = None
               ) -> logging.Logger:
    '''
    Get a logger by name. Names should be module name, or module and
    class name. ...Or dotted name? Not sure.

    Ignores any 'Falsy' values in `names` when building a name from parts.

    If `min_log_level` is an int or Level, this will check the logger's level
    and set it if it doesn't meet the requirement.

    E.g.:
      get_logger(__name__, self.__class__.__name__)
      get_logger(__name__)
      get_logger(self.dotted(), min_log_level=log.Level.DEBUG)
      get_logger(self.dotted(), 'client', '{:02d}'.format(client_num))
    '''
    # Ignore any Falsy values in names
    logger_name = '.'.join([each for each in names if each])

    named_logger = logging.getLogger(logger_name)

    # Do we need to adjust the level?
    if min_log_level:
        current = get_level(named_logger)
        desired = Level.to_logging(min_log_level)
        if desired != current:
            set_level(Level.most_verbose(current, desired),
                      named_logger)

    return named_logger


def _logger(veredi_logger: NullNoneOr[logging.Logger] = None
            ) -> logging.Logger:
    '''
    Returns `veredi_logger` if it is Truthy.
    Returns the default veredi logger if not.
    '''
    return (veredi_logger
            if veredi_logger else
            logger)


# -----------------------------------------------------------------------------
# Log Output Levels
# -----------------------------------------------------------------------------

def get_level(veredi_logger: NullNoneOr[logging.Logger] = None) -> Level:
    '''Returns current log level of logger, translated into Level enum.'''
    this = _logger(veredi_logger)
    level = Level(this.level)
    return level


def set_level(level:         LogLvlConversion           = DEFAULT_LEVEL,
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


def will_output(level:         LogLvlConversion,
                veredi_logger: NullNoneOr[logging.Logger] = None) -> bool:
    '''
    Returns true if supplied `level` is high enough to output a log.
    '''
    if isinstance(level, Level):
        level = Level.to_logging(level)
    this = _logger(veredi_logger)
    return level >= this.level


# -----------------------------------------------------------------------------
# Log Output Formatting
# -----------------------------------------------------------------------------

class BestTimeFmt(logging.Formatter):
    converter = datetime.datetime.fromtimestamp

    def formatTime(self,
                   record: logging.LogRecord,
                   fmt_date: str = None) -> str:
        converted = self.converter(record.created)
        if fmt_date:
            time_str = converted.strftime(fmt_date)
            string = time_str.format(msecs=math.floor(record.msecs))
        else:
            time_str = converted.strftime("%Y-%m-%d %H:%M:%S")
            string = "{:s}.{:03d}".format(time_str, math.floor(record.msecs))
        return string


def brace_message(fmt_msg:      str,
                  *args:        Any,
                  context:      Optional['VerediContext'] = None,
                  log_fmt_type: Optional[MessageType]     = None,
                  log_group:    Optional[Group]           = None,
                  log_dotted:   Optional[str]             = None,
                  log_success:  Optional[SuccessType]     = None,
                  log_dry_run:  Optional[bool]            = False,
                  **kwargs:     Mapping[str, Any]) -> str:
    '''
    `fmt_msg` is the user's message, which may have brace formatting to act on.
    Can handle case where no formatting needs be done (no args/kwargs
    supplied).

    Otherwise use '.format()' brace formatting on `fmt_msg` string.

    If `context` exists, it will be formatted by `pretty.indented()`, then
    appended to the log as such:
      <log_line(s)>
      context:
          <indented, formatted context>

    If `log_success` enum is supplied, will prefix formatted user's message
    with the `log_success` formatted to string. `log_dry_run` will be used to
    resolve `log_success` into actual vs dry-run strings.

    `log_fmt_type` will be applied to the final result just before returning.
    It is expected for things like group logging. If None supplied, uses
    MessageType.DEFAULT.

    `log_group` is only necessary for MessageType.GROUP.
    `log_dotted` is only necessary for MessageType.GROUP (currently).
    '''
    # ---
    # Apply `context`.
    # ---
    ctx_msg = ''
    if context:
        ctx_formatted = pretty.indented(context,
                                        indent_amount=_CONTEXT_INDENT_AMT)
        ctx_msg = '\ncontext:\n' + ctx_formatted

    # ---
    # Apply formatting for user.
    # ---
    if args or kwargs:
        try:
            output_msg = fmt_msg.format(*args, **kwargs) + ctx_msg
        except IndexError as error:
            output_msg = ("FORMAT ERROR FOR: "
                          + fmt_msg
                          + ".format(): "
                          + "args: " + str(args) + ", "
                          + "kwargs: " + str(kwargs) + " -> "
                          + str(error))

    else:
        output_msg = fmt_msg + ctx_msg

    if log_success:
        output_msg = _FMT_SUCCESS_HUMAN.format(
            # Resolve success into dry_run vs actual.
            success=str(log_success.resolve(bool(log_dry_run))),
            message=output_msg
        )

    # ---
    # Apply formatting for log line.
    # ---
    log_fmt_type = log_fmt_type or MessageType.DEFAULT
    log_fmt = _FMT_MESSAGE_HUMAN[log_fmt_type]
    return log_fmt.format(message=output_msg,
                          group=log_group,
                          dotted=log_dotted)


# -----------------------------------------------------------------------------
# Log Keyword Args Helpers
# -----------------------------------------------------------------------------

def incr_stack_level(
        kwargs: Optional[MutableMapping[str, Any]],
        amount: Optional[int] = 1) -> MutableMapping[str, Any]:
    '''
    Adds `amount` to existing 'stacklevel' in kwargs, or sets it to `amount` if
    non-existing.
    '''
    if not kwargs:
        kwargs = {}
    stacklevel = kwargs.pop('stacklevel', 0)
    stacklevel += amount
    kwargs['stacklevel'] = stacklevel
    return kwargs


def pop_log_kwargs(kwargs: Mapping[str, Any]) -> int:
    '''
    Pops kwargs intended for logger out of `kwargs`. Leaves the rest for the
    message formatter.

    Returns a new dictionary with the popped args in it, if any.
    '''
    log_args = {}

    # Do we have anything to work with?
    if kwargs:
        # Check for, pop anything of interest.

        if 'stacklevel' in kwargs:
            log_args['stacklevel'] = kwargs.pop('stacklevel', False)

        # Turns out this isn't at thing for logs cuz sensibly they always
        # flush.
        # if 'flush' in kwargs:
        #     log_args['flush'] = kwargs.pop('flush', False)

    # Return dict of log's kwargs. NOT the input kwargs!!
    return log_args


# -----------------------------------------------------------------------------
# Logger Crazy Debug Functions
# -----------------------------------------------------------------------------

def ultra_mega_debug(msg:           str,
                     *args:         Any,
                     veredi_logger: NullNoneOr[logging.Logger] = None,
                     context:       'VerediContext' = None,
                     **kwargs:      Any) -> None:
    '''
    Logs at Level.CRITICAL using either passed in logger or logger named:
      'veredi.debug.DEBUG.!!!DEBUG!!!'

    All logs start with a newline character.

    All logs are prepended with a row starting with '!~DEBUG~!' and
    then repeating '~!'.
    All logs are prepended with a row of 'v'.

    All logs are appended with a row of '^'.
    All logs are appended with a row starting with '!~DEBUG~!' and
    then repeating '~!'.

    All logs end with two newlines characters.

    In other words, a log.ultra_mega_debug('test') is this:

      <log line prefix output>
      !~DEBUG~!~!~!~!~!~!~!~!~!....
      vvvvvvvvvvvvvvvvvvvvvvvvv....

      test

      ^^^^^^^^^^^^^^^^^^^^^^^^^....
      !~DEBUG~!~!~!~!~!~!~!~!~!....


    '''
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           log_fmt_type=MessageType.NO_FMT,
                           **kwargs)
    if not ut_call(Level.CRITICAL, output):
        this = (veredi_logger
                or get_logger('veredi.debug.DEBUG.!!!DEBUG!!!'))
        log_out = _ULTRA_MEGA_DEBUG_FMT.format(output=output)
        this.critical(log_out,
                      **log_kwargs)


def ultra_hyper_debug(msg:           str,
                      *args:         Any,
                      format_str:    bool                       = True,
                      add_type:      bool                       = False,
                      title:         Optional[str]              = None,
                      veredi_logger: NullNoneOr[logging.Logger] = None,
                      context:       'VerediContext' = None,
                      **kwargs:      Any) -> None:
    '''
    Logs at Level.CRITICAL using either passed in logger or logger named:
      'veredi.debug.DEBUG.☢☢DEBUG☢☢'

    If `msg` is a str and `format_str` is True, this acts like other log
    functions (calls `brace_message()` to get a formatted output message).

    If `msg` is not a str, this will pass the `msg` object to
    `pretty.indented()` so as to get a prettily formatted dict, list, or
    whatever.

    If `add_type` is True or if `msg` is not a str: this will prepend "type:
    <type str>" to the output message.

    If `add_title` is not None, it will be prepended as "title: {add_title}" on
    its own line to front of output message.

    All logs start with a newline character.

    All logs end with two newlines characters.

    Basically, a log.ultra_hyper_debug('test', add_title='jeff') is this:

      <log line prefix output>
      ---
      -----
      --U-L-T-R-A-=-H-Y-P-E-R-=-D-E-B-U-G-=-L-O-G--
          title: jeff

          test
      --U-L-T-R-A-=-H-Y-P-E-R-=-D-E-B-U-G-=-L-O-G--
      ---
      -----
    '''
    log_kwargs = pop_log_kwargs(kwargs)
    # Do normal {} string formatting if we have a message string... but let
    # non-strings through so pretty.indented() can work better with dicts, etc.
    output = msg
    if isinstance(msg, str) and format_str:
        output = brace_message(msg,
                               # Add context to string output.
                               context=context,
                               log_fmt_type=MessageType.NO_FMT,
                               *args, **kwargs)

    # Indent output message before printing.
    output = pretty.indented(output,
                             indent_amount=_ULTRA_HYPER_INDENT_AMT)

    # And one more thing: if msg wasn't a string (or they asked us to), let's
    # say what it is:
    if not isinstance(msg, str) or add_type:
        output = (pretty.indented(f"type: {type(msg)}")
                  + "\n\n"
                  + output)
        # Add context to non-string output.
        if context:
            output += ("\n\ncontext:\n"
                       + pretty.indented(context))

    # And one more thing: if they want us to add a title, we will do that:
    if title:
        output = (pretty.indented(f"title: {title}")
                  + "\n\n"
                  + output)

    # Now output the log message.
    if not ut_call(Level.CRITICAL, output):
        this = (veredi_logger
                or get_logger('veredi.debug.DEBUG.☢☢DEBUG☢☢'))
        log_out = _ULTRA_HYPER_DEBUG_FMT.format(output=output)
        this.critical(log_out,
                      **log_kwargs)


# -----------------------------------------------------------------------------
# Logger Normal Functions
# -----------------------------------------------------------------------------

def debug(msg:           str,
          *args:         Any,
          veredi_logger: NullNoneOr[logging.Logger] = None,
          context:       'VerediContext' = None,
          **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           **kwargs)
    if not ut_call(Level.DEBUG, output):
        this = _logger(veredi_logger)
        this.debug(output,
                   **log_kwargs)


def info(msg:           str,
         *args:         Any,
         veredi_logger: NullNoneOr[logging.Logger] = None,
         context:       'VerediContext' = None,
         **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           **kwargs)
    if not ut_call(Level.INFO, output):
        this = _logger(veredi_logger)
        this.info(output,
                  **log_kwargs)


def warning(msg:           str,
            *args:         Any,
            veredi_logger: NullNoneOr[logging.Logger] = None,
            context:       'VerediContext' = None,
            **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           **kwargs)
    if not ut_call(Level.WARNING, output):
        this = _logger(veredi_logger)
        this.warning(output,
                     **log_kwargs)


def error(msg:           str,
          *args:         Any,
          veredi_logger: NullNoneOr[logging.Logger] = None,
          context:       'VerediContext' = None,
          **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           **kwargs)
    if not ut_call(Level.ERROR, output):
        this = _logger(veredi_logger)
        this.error(output,
                   **log_kwargs)


def _except_type(error_or_type: Union[Exception, Type[Exception]]) -> bool:
    '''
    Given `error_or_type`, this will return:
      - `error_or_type` if it is a VerediError (or sub-classes) type/class.
      - True if it is any other type/class.
      - False otherwise (it is an instance already).
    '''
    if isinstance(error_or_type, Exception):
        return False

    # Ok; error_or_type is a type. Return based on whether it's from
    # VerediError or not.

    type_of_error = (error_or_type  # Actual Type for VerediErrors
                     if issubclass(error_or_type, VerediError) else
                     True)  # Just True for others.
    return type_of_error


def _except_msg(message:      str,
                error_type:   Type[Exception],
                error_string: str,
                *args:        Any,
                context:      Optional['VerediContext'] = None,
                **kwargs:     Any) -> str:
    '''
    Build the log message for `exception()`.

    If no `message`, creates a simple default. Otherwise appends basically the
    same info (slightly different format) to the message generated by
    `brace_message(message, *args, context=context, **kwargs)`.

    `error_string` and `error_type` are allowed to have curly brackets when
    string'd and are not passed to `brace_message`.

    Returns the exception log message string.
    '''
    msg_append = []

    # ---
    # Create a default message.
    # ---
    if not message:
        msg_append.append("Exception caught. ")
        comma = False

        if error_type:
            msg_append.append("type: ")
            msg_append.append(error_type.__name__)
            comma = True

        if error_string:
            if comma:
                msg_append.append(", ")
            msg_append.append("str: ")
            msg_append.append(error_string)
            comma = True

        # No message to print these, so just include if they exist.
        if args:
            if comma:
                msg_append.append(", ")
            msg_append.append(f"args: {args}")
            comma = True

        if kwargs:
            if comma:
                msg_append.append(", ")
            msg_append.append(f"kwargs: {kwargs}")
            comma = True

    # ---
    # Message provided; append to it.
    # ---
    else:
        # Start with their message...
        msg_append.append(brace_message(message,
                                        *args,
                                        context=context,
                                        **kwargs))

        # ...Now add whatever useful stuff we think of.
        if error_type or error_string:
            msg_append.append(' (Exception ')

        if error_type:
            msg_append.append("type: ")
            msg_append.append(error_type.__name__)

            if error_string:
                msg_append.append(", ")

        if error_string:
            msg_append.append("str: ")
            msg_append.append(error_string)

        if error_type or error_string:
            msg_append.append(')')

    # ---
    # Done; join whatever string(s) we created.
    # ---
    return ''.join(msg_append)


def exception(err_or_class:  Union[Exception, Type[Exception]],
              msg:           Optional[str],
              *args:         Any,
              context:       Optional['VerediContext'] = None,
              veredi_logger: NullNoneOr[logging.Logger] = None,
              error_data:    Optional[Dict[Any, Any]] = None,
              **kwargs:      Any) -> None:
    '''
    Log the exception at ERROR level.

    If `err_or_class` is a type, this will create and return an instance by
    constructing: `err_or_class(log_msg_output_str)`
      - If optional `error_data` is not None, it will be supplied to the
        created error as the `data` parameter in the constructor.
        - It will be ignored if `err_or_class` is an instance already.

    If `err_or_class` is Falsy, this logs at CRITICAL level instead.

    If no `msg` supplied, will use:
        msg = "Exception caught. type: {}, str: {}"
        args = [type(err_or_class), str(err_or_class)]

    Otherwise error info will be tacked onto end.
      msg += " (Exception type: {err_type}, str: {err_str})"
      kwargs['err_type'] = type(err_or_class)
      kwargs['err_type'] = str(err_or_class)

    Finially, this returns the `err_or_class` supplied. This way you can do
    something like:
      except SomeError as error:
          other_error = OtherError(...)
          raise log.exception(
              other_error,
              "Cannot frobnicate {} from {}. {} instead.",
              source, target, nonFrobMunger,
              context=self.context
          ) from error
    '''
    # ---
    # Why would you log an exception with no exception supplied?
    # Log critically. And judge them. Critically.
    # ---
    if not err_or_class:
        critical(msg, *args,
                 context=context,
                 veredi_logger=veredi_logger,
                 **kwargs)
        return err_or_class

    # ---
    # Did we get an instance or a type?
    # ---
    make_instance = _except_type(err_or_class)
    log_msg_err_type = None
    log_msg_err_str = None
    if make_instance:
        log_msg_err_type = err_or_class
        # We have no `log_msg_err_str`, really... Let `_except_msg()` make it
        # for us.
    else:
        log_msg_err_type = type(err_or_class)
        # This can have curly brackets, so take care with _except_msg!
        log_msg_err_str = str(err_or_class)

    # ---
    # Create log msg.
    # ---
    # Get kwargs for actual python logger call.
    log_kwargs = pop_log_kwargs(kwargs)
    # Now `kwargs` is our message's kwargs.
    log_message = _except_msg(msg,
                              log_msg_err_type,
                              log_msg_err_str,
                              *args,
                              context=context,
                              **kwargs)

    # And now - finally - log it.
    _logger(veredi_logger).error(log_message, **log_kwargs)

    # ---
    # Return the Exception instance.
    # ---
    return_exception = err_or_class
    # Can finally make it if needed now that message is resolved.
    if (not isinstance(make_instance, bool)
            and (issubclass(make_instance, VerediError)
                 or make_instance is VerediError)):
        # Get the error's extra data ready with something about how we
        # ctor'd this here.
        data = None
        if error_data:
            data = error_data
            data['log'] = 'Instantiated by log.exception'
        else:
            data = {
                'log': 'Auto-created by log.exception',
            }

        # Make the VerediError.
        return_exception = err_or_class(
            log_message,
            context=context,
            data=data)

    elif make_instance is True:
        # Make the Python Exception.
        return_exception = err_or_class(log_message)

    # else it's an instance already - leave as-is.
    return return_exception


def critical(msg:           str,
             *args:         Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
             context:       'VerediContext' = None,
             **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = brace_message(msg,
                           *args,
                           context=context,
                           **kwargs)
    if not ut_call(Level.CRITICAL, output):
        this = _logger(veredi_logger)
        this.critical(output,
                      **log_kwargs)


def at_level(level:         'Level',
             msg:           str,
             *args:         Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
             context:       'VerediContext' = None,
             **kwargs:      Any) -> None:
    kwargs = incr_stack_level(kwargs)
    log_fn = None
    if level == Level.NOTSET:
        exception(ValueError("Cannot log at NOTSET level.",
                             msg, args, kwargs),
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

    log_fn(msg, *args,
           veredi_logger=veredi_logger,
           context=context,
           **kwargs)


# -----------------------------------------------------------------------------
# Logging Groups
# -----------------------------------------------------------------------------

def group(group:         'Group',
          dotted:        str,
          msg:           str,
          *args:         Any,
          veredi_logger: NullNoneOr[logging.Logger] = None,
          context:       'VerediContext' = None,
          log_success:   Optional[SuccessType] = None,
          log_dry_run:   Optional[bool] = False,
          **kwargs:      Any) -> None:
    '''
    Log at `group` log.Level, whatever it's set to right now.

    If `log_success` is supplied, will become a SuccessType string prepending
    log message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.
    '''

    # ------------------------------
    # Get level from group.
    # ------------------------------
    level = _GROUP_LEVELS[group]

    # ------------------------------
    # Prep log output w/ group info.
    # ------------------------------
    log_kwargs = pop_log_kwargs(kwargs)

    # Format, with group options
    output = brace_message(msg,
                           *args,
                           context=context,
                           log_fmt_type=MessageType.GROUP,
                           log_group=group,
                           log_dotted=dotted,
                           log_success=log_success,
                           log_dry_run=log_dry_run,
                           **kwargs)
    # Is a unit test eating this log?
    if ut_call(level, output):
        return

    # ------------------------------
    # Translate level to logging function.
    # ------------------------------
    logger = _logger(veredi_logger)
    log_fn = None
    if level == Level.NOTSET:
        exception(ValueError("Cannot group log at NOTSET level.",
                             msg, args, kwargs),
                  msg,
                  args,
                  kwargs)
    elif level == Level.DEBUG:
        log_fn = logger.debug
    elif level == Level.INFO:
        log_fn = logger.info
    elif level == Level.WARNING:
        log_fn = logger.warning
    elif level == Level.ERROR:
        log_fn = logger.error
    elif level == Level.CRITICAL:
        log_fn = logger.critical

    # ------------------------------
    # And log out w/ correct logger at correct level.
    # ------------------------------
    log_fn(output,
           **log_kwargs)


def set_group_level(group: 'Group',
                    level: 'Level') -> None:
    '''
    Updated `group` to logging `level`.
    '''
    global _GROUP_LEVELS
    _GROUP_LEVELS[group] = level


def security(dotted:        str,
             msg:           str,
             *args:         Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
             context:       'VerediContext'            = None,
             log_success:   Optional[SuccessType]      = None,
             log_dry_run:   Optional[bool] = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.SECURITY log.Level, whatever it's set to right now.

    If `log_success` is supplied, will become a SuccessType string prepending
    log message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.
    '''
    kwargs = incr_stack_level(kwargs)
    group(Group.SECURITY,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def start_up(dotted:        str,
             msg:           str,
             *args:         Any,
             veredi_logger: NullNoneOr[logging.Logger] = None,
             context:       'VerediContext'            = None,
             log_success:   Optional[SuccessType]      = None,
             log_dry_run:   Optional[bool] = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.START_UP log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.
    '''
    kwargs = incr_stack_level(kwargs)
    group(Group.START_UP,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


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
    def __init__(self, level: Level, no_op: bool = False) -> None:
        self._desired = level
        self._original = get_level()
        self._do_nothing = no_op

    def __enter__(self):
        if self._do_nothing:
            return

        self._original = get_level()
        set_level(self._desired)

    def __exit__(self,
                 type:      Optional[Type[BaseException]] = None,
                 value:     Optional[BaseException]       = None,
                 traceback: Optional[TracebackType]       = None) -> bool:
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
