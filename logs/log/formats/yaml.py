# coding: utf-8

'''
YAML log line format for Veredi Logger.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Callable,
                    Dict, NamedTuple, Tuple)
#                     Optional, Union, Any, NewType, Type, Callable,
#                     Mapping, MutableMapping, Iterable, Dict, List)
if TYPE_CHECKING:
    from types                     import TracebackType
    from veredi.base.context       import VerediContext
    from veredi.base.numbers.const import NumberTypes


import logging
import yaml

import datetime
import math
# import enum
from collections import OrderedDict


# from veredi.base.null       import Null, Nullable, NullNoneOr, null_or_none
from veredi.base.strings       import label, pretty
from veredi.base.paths.utils   import to_str as path_to_str
from veredi.base.paths.const   import PathType
# from veredi.base.exceptions import VerediError

from .. import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# LogRecord Attributes
# -----------------------------------------------------------------------------

# Attribute Name
#   - Format
#   - Description
#
# args
#   - You shouldn’t need to format this yourself.
#   - The tuple of arguments merged into msg to produce message, or a dict
#     whose values are used for the merge (when there is only one argument, and
#     it is a dictionary).
#
# asctime
#   - %(asctime)s
#   - Human-readable time when the LogRecord was created. By default this is of
#     the form ‘2003-07-08 16:49:45,896’ (the numbers after the comma are
#     millisecond portion of the time).
#
# created
#   - %(created)f
#   - Time when the LogRecord was created (as returned by time.time()).
#
# exc_info
#   - You shouldn’t need to format this yourself.
#   - Exception tuple (à la sys.exc_info) or, if no exception has occurred,
#     None.
#
# filename
#   - %(filename)s
#   - Filename portion of pathname.
#
# funcName
#   - %(funcName)s
#   - Name of function containing the logging call.
#
# levelname
#   - %(levelname)s
#   - Text logging level for the message ('DEBUG', 'INFO', 'WARNING', 'ERROR',
#     'CRITICAL').
#
# levelno
#   - %(levelno)s
#   - Numeric logging level for the message (DEBUG, INFO, WARNING, ERROR,
#     CRITICAL).
#
# lineno
#   - %(lineno)d
#   - Source line number where the logging call was issued (if available).
#
# message
#   - %(message)s
#   - The logged message, computed as msg % args. This is set when
#     Formatter.format() is invoked.
#
# module
#   - %(module)s
#   - Module (name portion of filename).
#
# msecs
#   - %(msecs)d
#   - Millisecond portion of the time when the LogRecord was created.
#
# msg
#   - You shouldn’t need to format this yourself.
#   - The format string passed in the original logging call. Merged with args
#     to produce message, or an arbitrary object (see Using arbitrary objects
#     as messages).
#
# name
#   - %(name)s
#   - Name of the logger used to log the call.
#
# pathname
#   - %(pathname)s
#   - Full pathname of the source file where the logging call was issued (if
#     available).
#
# process
#   - %(process)d
#   - Process ID (if available).
#
# processName
#   - %(processName)s
#   - Process name (if available).
#
# relativeCreated
#   - %(relativeCreated)d
#   - Time in milliseconds when the LogRecord was created, relative to the time
#     the logging module was loaded.
#
# stack_info
#   - You shouldn’t need to format this yourself.
#   - Stack frame information (where available) from the bottom of the stack in
#     the current thread, up to and including the stack frame of the logging
#     call which resulted in the creation of this record.
#
# thread
#   - %(thread)d
#   - Thread ID (if available).
#
# threadName
#   - %(threadName)s
#   - Thread name (if available).

# -----------------------------------------------------------------------------
# The Record Itself, now with more Veredi Flavor!
# -----------------------------------------------------------------------------

class RecordGroup(NamedTuple):
    '''
    Container for info about logging group.
    '''
    name:   str
    dotted: label.DotStr
    status: const.SuccessType


class LogRecordFactory:
    '''
    For log records with extra fields for Groups, Context, etc.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DOTTED = label.normalize('veredi', 'log', 'factory')

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._default: Callable = logging.getLogRecordFactory()
        '''
        The original/default log factory. Will be used to generate the log
        record to start with before adding in more data.

        The logging.LogRecord original callable uses parameters:
          args:
            name, level, pathname, lineno, msg, args, exc_info,
          kwargs:
            func  = None
            sinfo = None
        '''

    def __init__(self) -> None:
        self._define_vars()

    # -------------------------------------------------------------------------
    # Lumber Generation
    # -------------------------------------------------------------------------

    def default(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        '''
        Generate a 'default' Veredi version of a logging.LogRecord.
        '''
        record = self._default(*args, **kwargs)
        return record

    def context(self,
                *args:    Any,
                context:  'VerediContext' = None,
                **kwargs: Any) -> logging.LogRecord:
        '''
        Generate a default LogRecord with additional VerediContext data.
        '''
        record = self.default(*args, **kwargs)
        record.context = context
        return record

    def group(self,
              *args:    Any,
              name:     Optional[str]               = None,
              dotted:   Optional[label.DotStr]      = None,
              status:   Optional[const.SuccessType] = None,
              context:  Optional['VerediContext']   = None,
              **kwargs: Any) -> logging.LogRecord:
        '''
        Generate a LogRecord with additional log Group data.
        '''
        record = self.context(*args, context=context, **kwargs)

        # Now add in our fields.
        record.group = RecordGroup(name, dotted, status)
        return record


# -----------------------------------------------------------------------------
# The Record Format Itself
# -----------------------------------------------------------------------------

class LogRecordYaml:
    '''
    A helpful container for building a yaml-formatted log record.
    '''

    # -------------------------------------------------------------------------
    # Layout
    # -------------------------------------------------------------------------
    # Record should become a string formatted approximately like so:
    #   --- !veredi.log.yaml
    #
    #   2021-02-21 21:11:50.146:
    #     level: INFO
    #     dotted: veredi.repository.file-bare
    #     python:
    #       module: log
    #       function: group
    #     group:
    #       name: data-processing
    #       dotted: veredi.repository.file-bare
    #       status:
    #     message: |
    #       Load...
    #     context:
    #       DataBareContext:
    #         configuration:
    #           dotted: veredi.data.repository.file.zest_bare
    #           key: PosixPath('/srv/veredi/veredi/zest/zata/unit/repository/file-bare/config.test-bare.yaml')
    #           action: <DataAction.LOAD: 2>
    #           meta:
    #             dotted: veredi.data.repository.file.zest_bare
    #             test-suite: Test_FileBareRepo
    #             unit-test: test_load
    #           temp: False
    #

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DOC_TYPE = label.normalize('veredi', 'log', 'yaml')
    _DOTTED = _DOC_TYPE

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._dict_record: OrderedDict = OrderedDict()
        '''
        Top-Level Ordered Dictionary of the record.

        Is probably:
          {
            <timestamp str>: <self._dict_entries>
          }
        '''

        self._dict_entries: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements to be formatted/printed for a
        log record.
        '''

        self._dict_py: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'python' sub-dictionary.
        '''

        self._dict_group: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'group' sub-dictionary.
        '''

    def __init__(self) -> None:
        self._define_vars()

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        '''
        Clear out variables in preparation for the next log record.
        '''
        self._dict_record.clear()
        self._dict_entries.clear()
        self._dict_py.clear()
        self._dict_group.clear()

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    # ------------------------------
    # Sub-Entries
    # ------------------------------

    def _python(self, key: str, value: [str, 'NumberTypes']) -> None:
        '''
        Add a key/value pair to the 'python' sub-dictionary.
        '''
        # Make sure python dict is in the entries, then add this kvp.
        self._dict_entries['python'] = self._dict_py
        self._dict_py[key] = value

    def _group(self, key: str, value: [str, 'NumberTypes']) -> None:
        '''
        Add a key/value pair to the 'group' sub-dictionary.
        '''
        # Make sure group dict is in the entries, then add this kvp.
        self._dict_entries['group'] = self._dict_group
        self._dict_group[key] = value

    # ------------------------------
    # Time Info
    # ------------------------------

    def timestamp(self, stamp: str) -> None:
        '''
        Set the timestamp field.
        '''
        self._dict_record[stamp] = self._dict_entries

    # ------------------------------
    # Log Info
    # ------------------------------

    def level(self, level: const.Level) -> None:
        '''
        Set the level field.
        '''
        log_level = const.Level.to_logging(level)
        self._dict_entries['level'] = {
            'name': logging.getLevelName(log_level),
            'id':   log_level,
        }

    def logger_dotted(self, dotted: label.DotStr) -> None:
        '''
        Set the dotted field.
        '''
        self._dict_entries['dotted'] = dotted

    def group_name(self, name: str) -> None:
        '''
        Set the group's name field.
        '''
        self._group('name', name)

    def group_dotted(self, dotted: label.DotStr) -> None:
        '''
        Set the group's dotted field.
        '''
        self._group('dotted', dotted)

    def group_status(self, status: const.SuccessType) -> None:
        '''
        Set the group's status field.
        '''
        self._group('status', status)

    def message(self, message: str) -> None:
        '''
        Set the message field.
        '''
        self._dict_entries['message'] = message

    def context(self, context: 'VerediContext') -> None:
        '''
        Take the context, pretty print it, and set the context field.
        '''
        # Pretty Print!
        self._dict_entries['context'] = {
            context.__class__.__name__: pretty.to_str(context.data),
        }
        # TODO: Make sure flow style is correct?

    # ------------------------------
    # File/Module Info
    # ------------------------------

    def module(self, module: str) -> None:
        '''
        Set the module field.
        '''
        self._python('module', module)

    def file(self, file: str) -> None:
        '''
        Set the file field.
        '''
        self._python('file', file)

    def path(self, path: PathType) -> None:
        '''
        Set the path field.
        '''
        self._python('path', path_to_str(path))

    def function(self, function: str) -> None:
        '''
        Set the function field.
        '''
        self._python('function', function)

    # ------------------------------
    # Process Info
    # ------------------------------

    def process_id(self, process_id: 'NumberTypes') -> None:
        '''
        Set the process_id field.
        '''
        process = self._dict_py.setdefault('process', {})
        process['id'] = process_id

    def process_name(self, process_name: str) -> None:
        '''
        Set the process_name field.
        '''
        process = self._dict_py.setdefault('process', {})
        process['name'] = process_name

    def thread_id(self, thread_id: 'NumberTypes') -> None:
        '''
        Set the thread field.
        '''
        process = self._dict_py.setdefault('process', {})
        thread = process.setdefault('thread', {})
        thread['id'] = thread_id

    def thread_name(self, thread_name: str) -> None:
        '''
        Set the thread_name field.
        '''
        process = self._dict_py.setdefault('process', {})
        thread = process.setdefault('thread', {})
        thread['name'] = thread_name

    # TODO:
    # TODO: Exception
    # TODO: Stack
    # TODO:

    # ------------------------------
    # Process Info
    # ------------------------------

    def __str__(self) -> str:
        '''
        Convert this formatted log record into a string.
        '''
        # TODO: this
        # Can we dump w/ a separator and a doc tag?
        # Or do we just prepend those?
        # yaml.safe_dump(...)
        pass


# -----------------------------------------------------------------------------
# The Record Formatter
# -----------------------------------------------------------------------------

class LogYaml(logging.Formatter):
    '''
    Log to a yaml format.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DOC_TYPE = label.normalize('veredi', 'log', 'formatter', 'yaml')
    _DOTTED = _DOC_TYPE

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._iso_8601_sep: str = ' '
        '''
        Separator to use for datetime.datetime.isoformat()
        '''

        self._iso_8601_spec: str = 'microseconds'
        '''
        Timespec to use for datetime.datetime.isoformat()
        '''

        self._record_fmt: LogRecordYaml = LogRecordYaml()
        '''
        Ordered Collection for help creating our YAML record string of the
        log record.
        '''

    def __init__(self,
                 # TODO: do we use the parent's init params?
                 fmt:      str  = None,
                 datefmt:  str  = None,
                 validate: bool = True) -> None:
        self._define_vars()

        # TODO: Does this get our inputs?
        # Only using '{' style for now...
        style = '{'
        super().__init__(fmt, datefmt, style, validate)

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    def format(self,
               record: Dict  # 'Attribute Dictionary'
               ) -> str:
        '''
        Format a log record into a string for display.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.getMessage(). If the formatting string uses the
        time (as determined by a call to usesTime(), formatTime() is
        called to format the event time. If there is exception information,
        it is formatted using formatException() and appended to the message.
        '''
        # Parent class does this as of 3.8... So I guess we should too?
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        # ---
        # Make YAML Dict entries.
        # ---
        self._record_fmt.clear()

        # Do these in order that they should appear; LogRecordYaml is
        # an ordered collection.
        self._record_fmt.timestamp(record.asctime)
        self._record_fmt.level(const.Level.from_logging(record.level))
        self._record_fmt.logger_dotted(record.name)

        # Group Stuff
        # TODO: Think we also need a LogRecord itself...
        self._record_fmt.group_name()
        self._record_fmt.group_dotted()
        self._record_fmt.group_status()

        # The Actual Main Thing and its buddy.
        self._record_fmt.message()
        self._record_fmt.context()

        # Python Stuff
        self._record_fmt.module()
        self._record_fmt.path()
        self._record_fmt.function()
        self._record_fmt.process_id()
        self._record_fmt.process_name()
        self._record_fmt.thread_id()
        self._record_fmt.thread_name()

        self._record_fmt.exception()
        self._record_fmt.stack()

        # s = self.formatMessage(record)
        # if record.exc_info:
        #     # Cache the traceback text to avoid converting it multiple times
        #     # (it's constant anyway)
        #     if not record.exc_text:
        #         record.exc_text = self.formatException(record.exc_info)
        # if record.exc_text:
        #     if s[-1:] != "\n":
        #         s = s + "\n"
        #     s = s + record.exc_text
        # if record.stack_info:
        #     if s[-1:] != "\n":
        #         s = s + "\n"
        #     s = s + self.formatStack(record.stack_info)
        # return s

        return str(self._record_fmt)

    def formatMessage(self, record):
        '''
        Format the record's message according to our style type.
        '''
        return self._style.format(record)

    def formatTime(self,
                   record: Dict,  # 'Attribute Dictionary'
                   fmt_date: str = None) -> str:
        '''
        Format a timestamp a string for the log record's display.
        '''
        parsed = datetime.datetime.fromtimestamp(record.created)
        string = ""
        if fmt_date:
            # Got passed a formatting string - use it.
            time_str = parsed.strftime(fmt_date)
            string = time_str.format(msecs=math.floor(record.msecs))
        else:
            # No string; use our own to get "ISO-8601-sans-'T'-plus-msec"
            # formatted time string.
            string = datetime.datetime.isoformat(sep=self._iso_8601_sep,
                                                 timespec=self._iso_8601_spec)
            # # old way (sans timezon)
            # time_str = parsed.strftime()
            # string = "{:s}.{:03d}".format(time_str, math.floor(record.msecs))
        return string

    # def formatException(self,
    #                     exc_info: Tuple[Type, Exception, TracebackType]
    #                     ) -> str:
    #     '''
    #     Format an exception's info into a string for the log record's display.
    #     '''
    #     pass

    # def formatStack(self,
    #                 stack_info: str) -> str:
    #     '''
    #     Format the `stack_info` (string from traceback.print_stack().
    #     '''
    #     pass


# -----------------------------------------------------------------------------
# The Packaged Deal
# -----------------------------------------------------------------------------

def init(level:        const.LogLvlConversion      = const.DEFAULT_LEVEL,
         handler:      Optional[logging.Handler]   = None) -> logging.Logger:
    '''
    Set up logging to output Veredi YAML formatted log messages.

    Initializes a logger and returns it.

    `debug` purely here for debugging log_server, log_client setting up their
    loggers.
    '''
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
