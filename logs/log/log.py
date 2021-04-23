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


import logging
import pprint
import textwrap
import traceback
import sys

from types import TracebackType


from veredi.base.null       import Null, Nullable
from veredi.base.strings    import label, pretty
from veredi.base.exceptions import VerediError

from . import const
from . import formats
from . import filter


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    'init',
    'init_logger',

    'get_logger',
    'get_level',
    'set_level',

    'will_output',
    'format_pretty',
    'incr_stack_level',

    'ultra_mega_debug',
    'ultra_hyper_debug',

    'debug',
    'info',
    'warning',
    'error',
    'exception',
    'critical',
    'at_level',

    'group',
    'set_group_level',
    'get_group_level',
    'group_multi',
    'security',
    'start_up',
    'shutdown',
    'data_processing',
    'registration',
    'parallel',

    # ------------------------------
    # 'with' context manager
    # ------------------------------
    'LoggingManager',

    # ------------------------------
    # Unit Testing Support
    # ------------------------------
    'ut_call',
    'ut_set_up',
    'ut_tear_down',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

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
# Logging "Groups"
# ------------------------------

_GROUP_LEVELS: Dict[const.Group, const.Level] = {
    const.Group.SECURITY:        const.Level.WARNING,
    const.Group.START_UP:        const.Level.DEBUG,
    const.Group.SHUTDOWN:        const.Level.DEBUG,
    const.Group.DATA_PROCESSING: const.Level.DEBUG,
    const.Group.REGISTRATION:    const.Level.DEBUG,
    const.Group.PARALLEL:        const.Level.DEBUG,
}


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

__initialized: bool = False
'''Re-init protection.'''

logger: logging.Logger = None
'''Our main/default logger.'''

_filter: filter.VerediFilter = None
'''
A LogRecord filter class that adds Veredi data to LogRecords for the formatter.
'''

_unit_test_callback: Callable = Null()
'''Logging callback to consume logs during unit tests.'''


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

def init(level:        const.LogLvlConversion    = const.DEFAULT_LEVEL,
         handler:      Optional[logging.Handler] = None,
         formatter:    formats.FormatInitTypes   = None,
         reinitialize: Optional[bool]            = None,
         debug:        Optional[Any]             = None) -> None:
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
    # Initialize the Logger...
    # ------------------------------
    global logger
    logger = init_logger(str(const.LogName.ROOT), level)

    # ------------------------------
    # Initialize the Filter(s) & Format...
    # ------------------------------
    global _filter
    _filter = filter.init(logger)
    # This is our root logger, so we do allow it to have special handlers.
    formats.init(logger, handler, formatter)


def init_logger(logger_name: str,
                level:       const.LogLvlConversion      = const.DEFAULT_LEVEL,
                formatter:   Optional[logging.Formatter] = None
                ) -> logging.Logger:
    '''
    Initializes and returns a logger with the supplied name.
    '''
    # Create our logger at our default output level.
    logger = logging.getLogger(logger_name)
    logger.setLevel(const.Level.to_logging(level))
    logger.debug(f"Logger '{logger_name}' initialized at level {level}")

    # Non-root loggers should/must use the root's handler/formatter.

    return logger


# -----------------------------------------------------------------------------
# Logger Helpers
# -----------------------------------------------------------------------------


def get_logger(*names:        str,
               min_log_level: const.LogLvlConversion = None
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
      get_logger(self.dotted, min_log_level=log.const.Level.DEBUG)
      get_logger(self.dotted, 'client', '{:02d}'.format(client_num))
    '''
    # Ignore any Falsy values in names
    logger_name = '.'.join([each for each in names if each])

    named_logger = logging.getLogger(logger_name)

    # Do we need to adjust the level?
    if min_log_level:
        current = get_level(named_logger)
        desired = const.Level.to_logging(min_log_level)
        if desired != current:
            set_level(const.Level.most_verbose(current, desired),
                      named_logger)

    return named_logger


def _logger(veredi_logger: const.LoggerInput = None) -> logging.Logger:
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

def get_level(veredi_logger: const.LoggerInput = None) -> const.Level:
    '''Returns current log level of logger, translated into Level enum.'''
    this = _logger(veredi_logger)
    level = const.Level(this.level)
    return level


def set_level(level:         const.LogLvlConversion = const.DEFAULT_LEVEL,
              veredi_logger: const.LoggerInput      = None) -> None:
    '''
    Change logger's log level. Options are:
      - log.CRITICAL
      - log.ERROR
      - log.WARNING
      - log.INFO
      - log.DEBUG
      - log.NOTSET
      - log.DEFAULT_LEVEL

    '''
    if not const.Level.valid(level):
        error("Invalid log level {}. Ignoring.", level)
        return

    this = _logger(veredi_logger)
    this.setLevel(const.Level.to_logging(level))


def will_output(*args:         Union[const.LogLvlConversion, const.Group],
                veredi_logger: const.LoggerInput = None) -> bool:
    '''
    Returns true if any supplied `args` is high enough to output a log.
    '''
    the_logger = _logger(veredi_logger)
    for check in args:
        # ---
        # Convert to a log level int.
        # ---
        if isinstance(check, const.Group):
            check = get_group_level(check)
        if isinstance(check, const.Level):
            check = const.Level.to_logging(check)

        # ---
        # Compare to the logger's output level int.
        # ---
        if check >= the_logger.level:
            return True

    return False


# -----------------------------------------------------------------------------
# Log Output Formatting
# -----------------------------------------------------------------------------

def format_pretty(object:     object,
                  prefix:     Optional[str] = None,
                  indent:     int           = 2,
                  width:      int           = 120,
                  depth:      Optional[int] = None,
                  compact:    bool          = False,
                  sort_dicts: bool          = True) -> str:
    '''
    Pretty print `object` to a string, return the string.

    Calls `pprint.pformat()` with all args except `prefix`
    (`indent` becomes pformat's `indent` arg).

    If `prefix` is positive int, call `textwrap.indent()` with output of
    `pprint.pformat()` and `prefix`.
    '''
    pretty = pprint.pformat(object,
                            indent=indent,
                            width=width,
                            depth=depth,
                            compact=compact,
                            sort_dicts=sort_dicts)
    if prefix and isinstance(prefix, str):
        pretty = textwrap.indent(pretty,
                                 prefix)

    return pretty


# NOTE: Would make sense to puth these in formats/, but log.py owns the filter
# right now so they're here for now.

def _format(msg_fmt:      str,
            *args:        Any,
            context:      Optional['VerediContext']   = None,
            log_group:    Optional[const.Group]       = None,
            log_dotted:   Optional[label.DotStr]      = None,
            log_success:  const.SuccessInput          = None,
            log_dry_run:  Optional[bool]              = False,
            **kwargs:     Mapping[str, Any]) -> str:
    '''
    `fmt_msg` is the user's message, which may have brace formatting to act on.
    Can handle case where no formatting needs be done (no args/kwargs
    supplied).

    Otherwise use '.format()' brace formatting on `fmt_msg` string.

    If `context` exists, it will be added to our filter for later use.

    If group data exists (`log_group`, `log_dotted`), it will be added to our
    filter for later use.

    If success/fail data exists (`log_success`, `log_dry_run`), it will be
    added to our filter for later use.
    '''
    # Squirrel away our contextual data about this log.
    _add_data(context=context,
              log_group=log_group,
              log_dotted=log_dotted,
              log_success=log_success,
              log_dry_run=log_dry_run)

    # And format the message we've been given.
    return _brace_message(msg_fmt, *args, **kwargs)


def _add_data(context:      Optional['VerediContext'] = None,
              log_group:    Optional[const.Group]     = None,
              log_dotted:   Optional[label.DotStr]    = None,
              log_success:  const.SuccessInput        = None,
              log_dry_run:  Optional[bool]            = False) -> None:
    '''
    Add any extra logging data to the filter so that it can add it to the
    LogRecord soon.

    If `log_success` enum is supplied, will use with `log_dry_run` to
    resolve `log_success` into actual vs dry-run value before saving.
    '''
    global _filter
    if not _filter:
        return

    _filter.context(context=context)
    _filter.group(group=log_group,
                  dotted=log_dotted)
    _filter.success(success=log_success,
                    dry_run=log_dry_run)


def _clear_data() -> None:
    '''
    Clears out our special LogRecord saved data.
    '''
    global _filter
    if not _filter:
        return

    _filter.context(clear=True)
    _filter.group(clear=True)
    _filter.success(clear=True)
    _filter.exception(clear=True)


def _add_exception(error: Exception) -> None:
    '''
    Gets stack trace from `log.stack_trace()` and adds it to the filter so that
    it can be added to the log.
    '''
    global _filter
    if not _filter:
        return

    _filter.exception(exception=error,
                      stack=stack_trace())


def stack_trace() -> str:
    '''
    Returns a formatted multi-line string of the stack trace.

    If there is an exception, the stack trace is for that exception.
    Otherwise it is for the caller.
    '''
    exception_type = sys.exc_info()[0]
    if exception_type is not None:
        # Have an exception, so use the exception info's frame to get the stack
        # trace.
        frame = sys.exc_info()[-1].tb_frame.f_back
        stack = traceback.extract_stack(frame)
    else:
        # Trim ourself (`stack_trace()`) out of the stack trace.
        stack = traceback.extract_stack()[:-1]
    title = 'Traceback (most recent call last):\n'
    output = title + ''.join(traceback.format_list(stack))
    if exception_type is not None:
        output += '  ' + traceback.format_exc().lstrip()
    return output


# TODO: Delete this? Logs should be able to format themselves?
def _brace_message(fmt_msg:      str,
                   *args:        Any,
                   **kwargs:     Mapping[str, Any]) -> str:
    '''
    `fmt_msg` is the user's message, which may have brace formatting to act on.
    Can handle case where no formatting needs be done (no args/kwargs
    supplied).

    Otherwise use '.format()' brace formatting on `fmt_msg` string.
    '''
    output_msg = None

    # ---
    # Apply formatting for user?
    # ---
    if args or kwargs:
        try:
            output_msg = fmt_msg.format(*args, **kwargs)

        # We are trying to log something, so...
        # Try to eat errors but still give both log and error info maybe?
        except IndexError as error:
            output_msg = ("FORMAT IndexError FOR: "
                          + fmt_msg
                          + ".format(): "
                          + "args: " + str(args) + ", "
                          + "kwargs: " + str(kwargs) + " -> "
                          + str(error))
        except KeyError as error:
            output_msg = ("FORMAT KeyError FOR: "
                          + fmt_msg
                          + ".format(): "
                          + "args: " + str(args) + ", "
                          + "kwargs: " + str(kwargs) + " -> "
                          + str(error))

    else:
        # Nope; just a string.
        output_msg = fmt_msg

    # ---
    # Apply formatting for log line.
    # ---
    return output_msg


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
                     veredi_logger: const.LoggerInput     = None,
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
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.CRITICAL, output):
        this = (veredi_logger
                or get_logger('veredi.debug.DEBUG.!!!DEBUG!!!'))
        log_out = _ULTRA_MEGA_DEBUG_FMT.format(output=output)
        this.critical(log_out,
                      **log_kwargs)


def ultra_hyper_debug(msg:           str,
                      *args:         Any,
                      format_str:    bool            = True,
                      add_type:      bool            = False,
                      title:         Optional[str]   = None,
                      veredi_logger: const.LoggerInput     = None,
                      context:       'VerediContext' = None,
                      **kwargs:      Any) -> None:
    '''
    Logs at Level.CRITICAL using either passed in logger or logger named:
      'veredi.debug.DEBUG.☢☢DEBUG☢☢'

    If `msg` is a str and `format_str` is True, this acts like other log
    functions (calls `_format()` to get a formatted output message).

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
        output = _format(msg,
                         # Add context to string output.
                         context=context,
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
    if not ut_call(const.Level.CRITICAL, output):
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
          veredi_logger: const.LoggerInput     = None,
          context:       'VerediContext' = None,
          **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.DEBUG, output):
        this = _logger(veredi_logger)
        this.debug(output,
                   **log_kwargs)


def info(msg:           str,
         *args:         Any,
         veredi_logger: const.LoggerInput     = None,
         context:       'VerediContext' = None,
         **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.INFO, output):
        this = _logger(veredi_logger)
        this.info(output,
                  **log_kwargs)


def warning(msg:           str,
            *args:         Any,
            veredi_logger: const.LoggerInput     = None,
            context:       'VerediContext' = None,
            **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.WARNING, output):
        this = _logger(veredi_logger)
        this.warning(output,
                     **log_kwargs)


def error(msg:           str,
          *args:         Any,
          veredi_logger: const.LoggerInput     = None,
          context:       'VerediContext' = None,
          **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.ERROR, output):
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
    `_format(message, *args, context=context, **kwargs)`.

    `error_string` and `error_type` are allowed to have curly brackets when
    string'd and are not passed to `_format`.

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
        msg_append.append(_format(message,
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
              veredi_logger: const.LoggerInput               = None,
              error_data:    Optional[Dict[Any, Any]]  = None,
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
    # ------------------------------
    # Why would you log an exception with no exception supplied?
    # Log critically. And judge them. Critically.
    # ------------------------------
    if not err_or_class:
        critical(msg, *args,
                 context=context,
                 veredi_logger=veredi_logger,
                 **kwargs)
        return err_or_class

    # ------------------------------
    # Did we get an instance or a type?
    # ------------------------------
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

    # ------------------------------
    # Create log msg.
    # ------------------------------
    # Get kwargs for actual python logger call.
    log_kwargs = pop_log_kwargs(kwargs)
    # Now `kwargs` is our message's kwargs.
    log_message = _except_msg(msg,
                              log_msg_err_type,
                              log_msg_err_str,
                              *args,
                              context=context,
                              **kwargs)

    # ------------------------------
    # Ensure the Exception instance.
    # ------------------------------
    exception_instance = err_or_class
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
        exception_instance = err_or_class(
            log_message,
            context=context,
            data=data)

    elif make_instance is True:
        # Make the Python Exception.
        exception_instance = err_or_class(log_message)

    # else it's an instance already - leave as-is.

    # ------------------------------
    # And now - finally - log it and return exception
    # ------------------------------
    _add_exception(exception_instance)
    _logger(veredi_logger).error(log_message, **log_kwargs)

    return exception_instance


def critical(msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput     = None,
             context:       'VerediContext' = None,
             **kwargs:      Any) -> None:
    log_kwargs = pop_log_kwargs(kwargs)
    output = _format(msg,
                     *args,
                     context=context,
                     **kwargs)
    if not ut_call(const.Level.CRITICAL, output):
        this = _logger(veredi_logger)
        this.critical(output,
                      **log_kwargs)


def at_level(level:         'const.Level',
             msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput     = None,
             context:       'VerediContext' = None,
             **kwargs:      Any) -> None:
    kwargs = incr_stack_level(kwargs)
    log_fn = None
    if level == const.Level.NOTSET:
        exception(ValueError("Cannot log at NOTSET level.",
                             msg, args, kwargs),
                  msg,
                  args,
                  kwargs)
    elif level == const.Level.DEBUG:
        log_fn = debug
    elif level == const.Level.INFO:
        log_fn = info
    elif level == const.Level.WARNING:
        log_fn = warning
    elif level == const.Level.ERROR:
        log_fn = error
    elif level == const.Level.CRITICAL:
        log_fn = critical

    log_fn(msg, *args,
           veredi_logger=veredi_logger,
           context=context,
           **kwargs)


# -----------------------------------------------------------------------------
# Logging Groups
# -----------------------------------------------------------------------------

def group(log_group:     'const.Group',
          dotted:        label.DotStr,
          msg:           str,
          *args:         Any,
          veredi_logger: const.LoggerInput            = None,
          context:       'VerediContext'              = None,
          log_minimum:   const.Level                  = None,
          log_success:   Optional[const.SuccessInput] = const.SuccessType.IGNORE,
          log_dry_run:   Optional[bool]               = False,
          **kwargs:      Any) -> None:
    '''
    Log at `group` log.Level, whatever it's set to right now, as long as it's
    above `log_minimum` or `log_minimum` is None.

    If `log_success` is supplied, will become a SuccessType string prepending
    log message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''

    # ------------------------------
    # Get level from group.
    # ------------------------------
    level = _GROUP_LEVELS[log_group]
    # If we have a minimum, make sure this group matches it (NOTSETs treated as
    # failures). Also might as well check that the logger will output it at
    # all.
    if ((log_minimum and not level.will_output_at(log_minimum,
                                                  notset_return=False))
            or not will_output(level,
                               veredi_logger=veredi_logger)):
        # If the group is below the min required by this specific group (or min
        # required to output at all), do not log it.
        return

    # ------------------------------
    # Prep log output w/ group info.
    # ------------------------------
    log_kwargs = pop_log_kwargs(kwargs)

    # Translate bools of lazy typing into full SuccessTypes.
    if log_success is True:
        log_success = const.SuccessType.SUCCESS
    elif log_success is False:
        log_success = const.SuccessType.FAILURE

    # Format, with group options
    output = _format(msg,
                     *args,
                     context=context,
                     log_group=log_group,
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
    if level == const.Level.NOTSET:
        exception(ValueError("Cannot group log at NOTSET level.",
                             msg, args, kwargs),
                  msg,
                  args,
                  kwargs)
    elif level == const.Level.DEBUG:
        log_fn = logger.debug
    elif level == const.Level.INFO:
        log_fn = logger.info
    elif level == const.Level.WARNING:
        log_fn = logger.warning
    elif level == const.Level.ERROR:
        log_fn = logger.error
    elif level == const.Level.CRITICAL:
        log_fn = logger.critical

    # ------------------------------
    # And log out w/ correct logger at correct level.
    # ------------------------------
    log_fn(output,
           **log_kwargs)


def get_group_level(group: 'const.Group') -> 'const.Level':
    '''
    Returns group's current log.Level.
    '''
    global _GROUP_LEVELS
    return _GROUP_LEVELS[group]


def set_group_level(group: 'const.Group',
                    level: 'const.Level') -> None:
    '''
    Updated `group` to logging `level`.
    '''
    global _GROUP_LEVELS
    _GROUP_LEVELS[group] = level


def group_multi(groups:        Iterable['const.Group'],
                dotted:        label.DotStr,
                msg:           str,
                *args:         Any,
                group_resolve: Optional[const.GroupResolve]   = const.GroupResolve.HIGHEST,
                veredi_logger: const.LoggerInput               = None,
                context:       'VerediContext'           = None,
                log_minimum:   const.Level                     = None,
                log_success:   Optional[const.SuccessInput] = const.SuccessType.IGNORE,
                log_dry_run:   Optional[bool]            = False,
                **kwargs:      Any) -> None:
    '''
    Log at `group` log.const.Level, whatever it's set to right now.

    If `log_success` is supplied, will become a SuccessType string prepending
    log message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    if group_resolve is None:
        group_resolve = const.GroupResolve.HIGHEST

    # Resolve the groups based on resolution type, then log to whatever
    # group(s) that is.
    final_groups = group_resolve.resolve(groups, _GROUP_LEVELS)
    for log_group in final_groups:
        group(log_group,
              dotted,
              msg,
              *args,
              veredi_logger=veredi_logger,
              context=context,
              log_minimum=log_minimum,
              log_success=log_success,
              log_dry_run=log_dry_run,
              **kwargs)


def security(dotted:        label.DotStr,
             msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput     = None,
             context:       'VerediContext' = None,
             log_minimum:   const.Level           = None,
             log_success:   const.SuccessInput    = const.SuccessType.IGNORE,
             log_dry_run:   Optional[bool]  = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.SECURITY log.Level, whatever it's set to right now.

    If `log_success` is supplied, will become a SuccessType string prepending
    log message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.SECURITY,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def start_up(dotted:        label.DotStr,
             msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput     = None,
             context:       'VerediContext' = None,
             log_minimum:   const.Level           = None,
             log_success:   const.SuccessInput    = const.SuccessType.IGNORE,
             log_dry_run:   Optional[bool]  = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.START_UP log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.START_UP,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def shutdown(dotted:        label.DotStr,
             msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput     = None,
             context:       'VerediContext' = None,
             log_minimum:   const.Level           = None,
             log_success:   const.SuccessInput    = const.SuccessType.IGNORE,
             log_dry_run:   Optional[bool]  = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.SHUTDOWN log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.SHUTDOWN,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def data_processing(dotted:        label.DotStr,
                    msg:           str,
                    *args:         Any,
                    veredi_logger: const.LoggerInput     = None,
                    context:       'VerediContext' = None,
                    log_minimum:   const.Level           = None,
                    log_success:   const.SuccessInput    = const.SuccessType.IGNORE,
                    log_dry_run:   Optional[bool]  = False,
                    **kwargs:      Any) -> None:
    '''
    Log at Group.DATA_PROCESSING log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.DATA_PROCESSING,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def registration(dotted:        label.DotStr,
                 msg:           str,
                 *args:         Any,
                 veredi_logger: const.LoggerInput  = None,
                 context:       'VerediContext'    = None,
                 log_minimum:   const.Level        = None,
                 log_success:   const.SuccessInput = const.SuccessType.IGNORE,
                 log_dry_run:   Optional[bool]     = False,
                 **kwargs:      Any) -> None:
    '''
    Log at Group.REGISTRATION log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.REGISTRATION,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
          log_success=log_success,
          log_dry_run=log_dry_run,
          **kwargs)


def parallel(dotted:        label.DotStr,
             msg:           str,
             *args:         Any,
             veredi_logger: const.LoggerInput  = None,
             context:       'VerediContext'    = None,
             log_minimum:   const.Level        = None,
             log_success:   const.SuccessInput = const.SuccessType.IGNORE,
             log_dry_run:   Optional[bool]     = False,
             **kwargs:      Any) -> None:
    '''
    Log at Group.PARALLEL log.Level, whatever it's set to right now.

    If `success` is supplied, will become a SuccessType string prepending log
    message. `log_dry_run` will be used to resolve `log_success` into
    actual vs dry-run strings.

    If `log_success` is a bool:
      - True  -> SuccessType.SUCCESS
      - False -> SuccessType.FAILURE
    '''
    kwargs = incr_stack_level(kwargs)
    group(const.Group.PARALLEL,
          dotted,
          msg,
          *args,
          veredi_logger=veredi_logger,
          context=context,
          log_minimum=log_minimum,
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
    def __init__(self, level: const.Level, no_op: bool = False) -> None:
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
        return LoggingManager(const.Level.DEBUG)

    @staticmethod
    def disabled() -> 'LoggingManager':
        '''
        This one sets logging to least verbose level - CRITICAL.
        '''
        # TODO [2020-05-30]: more 'disabled' than this?
        return LoggingManager(const.Level.CRITICAL)

    @staticmethod
    def ignored() -> 'LoggingManager':
        '''
        This one does nothing.
        '''
        return LoggingManager(const.Level.CRITICAL, no_op=True)


# -----------------------------------------------------------------------------
# Unit Testing
# -----------------------------------------------------------------------------

def ut_call(level: 'const.Level',
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


def ut_set_up(callback: Nullable[Callable[['const.Level', str], bool]]) -> None:
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
