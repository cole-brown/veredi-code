# coding: utf-8

'''
YAML log line format for Veredi Logger.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, NewType, Callable,
                    Dict, NamedTuple, Tuple)
if TYPE_CHECKING:
    from veredi.base.context       import VerediContext
    from veredi.base.numbers.const import NumberTypes
# For creating TracebackTupleType
from types import TracebackType


import logging
import yaml

import datetime
import math
# import enum
from collections import OrderedDict
from io import StringIO
from traceback import print_exception


# from veredi.base.null       import Null, Nullable, NullNoneOr, null_or_none
from veredi.base.strings       import label, pretty
from veredi.base.paths.utils   import to_str as path_to_str
from veredi.base.paths.const   import PathType
# from veredi.base.exceptions import VerediError

from .. import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

TracebackTupleType = NewType(
    'TracebackTupleType',
    Tuple[Type[BaseException], BaseException, TracebackType]
)


# -----------------------------------------------------------------------------
# YAML Large String Dumpers
# -----------------------------------------------------------------------------

# TODO: Move to... idk... base.yaml?!
# import yaml

class FoldedString(str):
    '''
    Class just marks this string to be dumped in 'folded' YAML string format.
    '''
    pass


class LiteralString(str):
    '''
    Class just marks this string to be dumped in 'literal' YAML string format.
    '''
    pass


def folded_string_representer(dumper, data):
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='>')


def literal_string_representer(dumper, data):
    '''
    Register FoldedString as the correct style of literal.
    '''
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')


def ordered_dict_representer(dumper, data):
    '''
    Register OrderedDict in order to be able to dump it.
    '''
    return dumper.represent_mapping(u'tag:yaml.org,2002:map',
                                    data.items(),
                                    flow_style=False)  # block flow style


yaml.add_representer(FoldedString,
                     folded_string_representer,
                     Dumper=yaml.SafeDumper)
yaml.add_representer(LiteralString,
                     literal_string_representer,
                     Dumper=yaml.SafeDumper)
yaml.add_representer(OrderedDict,
                     ordered_dict_representer,
                     Dumper=yaml.SafeDumper)


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
    #   timestamp: 2021-02-21 21:11:50.146
    #   level: INFO
    #   dotted: veredi.repository.file-bare
    #   python:
    #     module: log
    #     function: group
    #   group:
    #     name: data-processing
    #     dotted: veredi.repository.file-bare
    #     status:
    #   context:
    #     DataBareContext:
    #       configuration:
    #         dotted: veredi.data.repository.file.zest_bare
    #         key: PosixPath('/srv/veredi/veredi/zest/zata/unit/repository/file-bare/config.test-bare.yaml')
    #         action: <DataAction.LOAD: 2>
    #         meta:
    #           dotted: veredi.data.repository.file.zest_bare
    #           test-suite: Test_FileBareRepo
    #           unit-test: test_load
    #         temp: False
    #   message: |
    #     Load...
    #

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _DOC_TYPE = label.normalize('veredi', 'log', 'yaml')
    _DOTTED = _DOC_TYPE
    _DOC_TYPE_TAG = '!' + _DOC_TYPE

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._stream_io: StringIO = StringIO()
        '''A buffer to use for string formatting.'''

        self._dict_record: OrderedDict = OrderedDict()
        '''
        Top-Level Ordered Dictionary of the record.
        '''

        self._dict_level: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of level data (name, id) to be formatted/printed for
        a log record.
        '''

        self._dict_group: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'group' sub-dictionary.
        '''

        self._dict_py: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'python' sub-dictionary.
        '''

        self._dict_process: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in _dict_py's 'process'
        sub-dictionary.
        '''

        self._dict_thread: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in _dict_process's 'thread'
        sub-dictionary.
        '''

        self._dict_error: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'error' sub-dictionary.
        '''

    def __init__(self) -> None:
        self._define_vars()

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    def reset(self) -> None:
        '''
        Clear out variables in preparation for the next log record.
        '''
        # ---
        # First: Clear
        # ---
        self._dict_record.clear()
        self._dict_level.clear()
        self._dict_group.clear()
        self._dict_py.clear()
        self._dict_process.clear()
        self._dict_thread.clear()
        self._dict_error.clear()

        # ---
        # Last: Try to enforce our own ordering.
        # ---
        self._dict_record['timestamp'] = None
        self._dict_record['level'] = self._dict_level
        self._dict_record['dotted'] = None
        self._dict_record['python'] = self._dict_py

        self._dict_py['module'] = None
        self._dict_py['function'] = None
        self._dict_py['path'] = None
        self._dict_py['process'] = self._dict_process

        self._dict_process['name'] = None
        self._dict_process['id'] = None
        self._dict_process['thread'] = self._dict_thread
        self._dict_thread['name'] = None
        self._dict_thread['id'] = None

        self._dict_record['group'] = self._dict_group
        self._dict_record['context'] = None
        self._dict_record['message'] = None
        self._dict_record['error'] = self._dict_error

    def filter(self) -> None:
        '''
        Filters out optional, and currently empty, entries in preparation for
        outputting.
        '''
        if not self._dict_record.get('python', None):
            self._dict_record.pop('python', None)
        elif not self._dict_py.get('process', None):
            self._dict_py.pop('process', None)
        elif not self._dict_process.get('thread', None):
            self._dict_process.pop('thread', None)

        if not self._dict_record.get('group', None):
            self._dict_record.pop('group', None)

        if not self._dict_record.get('context', None):
            self._dict_record.pop('context', None)

        if not self._dict_record.get('error', None):
            self._dict_record.pop('error', None)

    @property
    def _stream(self) -> StringIO:
        '''
        Returns our `self._stream_io` after clearing and resetting it.
        '''
        self._stream_io.truncate(0)
        self._stream_io.seek(0)
        return self._stream_io

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
        self._dict_record['python'] = self._dict_py
        self._dict_py[key] = value

    def _group(self, key: str, value: [str, 'NumberTypes']) -> None:
        '''
        Add a key/value pair to the 'group' sub-dictionary.
        '''
        # Make sure group dict is in the entries, then add this kvp.
        self._dict_record['group'] = self._dict_group
        self._dict_group[key] = value

    def _error(self, key: str, value: Any) -> None:
        '''
        Add a key/value pair to the 'group' sub-dictionary.
        '''
        # Make sure group dict is in the entries, then add this kvp.
        self._dict_record['error'] = self._dict_error
        self._dict_error[key] = value

    # ------------------------------
    # Time Info
    # ------------------------------

    def timestamp(self, stamp: str) -> None:
        '''
        Set the timestamp field.
        '''
        # Could have a timestamp dict for local and UTC.
        # Just UTC for now.
        self._dict_record['timestamp'] = stamp

    # ------------------------------
    # Log Info
    # ------------------------------

    def level(self, level: const.Level) -> None:
        '''
        Set the level field.
        '''
        log_level = const.Level.to_logging(level)
        self._dict_level['name'] = logging.getLevelName(log_level)
        self._dict_level['id'] = log_level
        self._dict_record['level'] = self._dict_level

    def logger_dotted(self, dotted: label.DotStr) -> None:
        '''
        Set the dotted field.
        '''
        self._dict_record['dotted'] = dotted

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
        self._dict_record['message'] = LiteralString(message)

    def context(self, context: 'VerediContext') -> None:
        '''
        Take the context, pretty print it, and set the context field.
        '''
        # Pretty Print!
        self._dict_record['context'] = {
            context.__class__.__name__: context.data,
            # LiteralString(
            #     pretty.to_str(context.data)
            # ),
        }

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

    # ------------------------------
    # Exceptions & Stack Traces
    # ------------------------------

    def exception(self,
                  exception_info: TracebackTupleType,
                  exception_text: str) -> None:
        '''
        Format, set the exception data.

        Uses, in preference order, `exception_text` or `exception_info` to
        create the exception data string. This imitates Python's way of doing
        it.
        '''
        if exception_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not exception_text:
                stream = self._stream
                print_exception(exception_info[0],
                                exception_info[1],
                                exception_info[2],
                                None,
                                stream)
                exception_text = stream.getvalue()

        if not exception_text:
            return

        self._error('exception', LiteralString(exception_text))

    def stack(self, stack_info: str) -> None:
        '''
        Set the stack trace data.
        '''
        if not stack_info:
            return

        self._error('exception', LiteralString(stack_info))

    # ------------------------------
    # Process Info
    # ------------------------------

    def __str__(self) -> str:
        '''
        Convert this formatted log record into a string.
        '''
        stream = self._stream
        self.filter()

        # Can we dump w/ a separator and a doc tag?
        # Or do we just prepend those?
        stream.write("\n--- ")
        stream.write(self._DOC_TYPE_TAG)
        stream.write("\n\n")

        yaml.safe_dump(self._dict_record,
                       # Always use block formatting.
                       default_flow_style=False,
                       stream=stream)
        return stream.getvalue()


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

    def uses_time(self) -> bool:
        '''
        Returns true if this formatter uses a timestamp.
        '''
        return True

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
        if not self.uses_time():
            raise AttributeError(f"{self.__class__.__name__} requires time "
                                 "for its formatting, but `self.uses_time()` "
                                 "returned False!")
        record.asctime = self.formatTime(record, self.datefmt)

        # ---
        # Make YAML Dict entries.
        # ---
        self._record_fmt.reset()

        # Do these in order that they should appear; LogRecordYaml is
        # an ordered collection.
        self._record_fmt.timestamp(record.asctime)
        self._record_fmt.level(const.Level.from_logging(record.levelno))
        self._record_fmt.logger_dotted(record.name)

        # Group Stuff
        try:
            self._record_fmt.group_name(record.group.name)
            self._record_fmt.group_dotted(record.group.dotted)
            self._record_fmt.group_status(record.group.status)
        except AttributeError:
            # No group data; ok.
            pass

        # The Actual Main Thing and its buddy.
        self._record_fmt.message(record.message)
        try:
            self._record_fmt.context(record.context)
        except AttributeError:
            # No context data; ok.
            pass

        # Python Stuff
        self._record_fmt.module(record.module)
        self._record_fmt.path(record.filename)
        self._record_fmt.function(record.funcName)
        self._record_fmt.process_id(record.process)
        self._record_fmt.process_name(record.processName)
        self._record_fmt.thread_id(record.thread)
        self._record_fmt.thread_name(record.threadName)

        self._record_fmt.exception(record.exc_info, record.exc_text)
        self._record_fmt.stack(record.stack_info)

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
            string = parsed.isoformat(sep=self._iso_8601_sep,
                                      timespec=self._iso_8601_spec)
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
