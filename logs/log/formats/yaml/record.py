# coding: utf-8

'''
Veredi's customized logging record for additional info about groups, context,
etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, NewType, Tuple)
if TYPE_CHECKING:
    from veredi.base.context       import VerediContext
    from veredi.base.numbers.const import NumberTypes
# For creating TracebackTupleType
from types import TracebackType


import logging
import yaml as py_yaml

from collections import OrderedDict
from io import StringIO
from traceback import print_exception


from veredi.base.strings     import label, convert
from veredi.base.paths.utils import to_str as path_to_str
from veredi.base.paths.const import PathType

from ...                     import const as const_l

# ---
# Need to get LiteralString, OrderedDict, etc. registered with Python YAML.
# ---
from veredi.base import yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

TracebackTupleType = NewType(
    'TracebackTupleType',
    Tuple[Type[BaseException], BaseException, TracebackType]
)


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
    #   success:
    #     normalized: '[_OK_]'
    #     verbatim: '[ OK ]'
    #     dry-run: true
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

        self._dict_success: OrderedDict = OrderedDict()
        '''
        Ordered Dictionary of record elements in the 'success' sub-dictionary.
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

        # YAML setup happens in our __init__.py now.
        # # We have the record tag, but for now just say to deserialize it as a
        # # dictionary.
        # yaml.construct(self._DOC_TYPE_TAG,
        #                py_yaml.SafeLoader.construct_mapping,
        #                __file__)
        #
        # # Let YAML know how we want our log enums serialized. Use an enum value
        # # that is the correct type (e.g. SuccessType - don't use IGNORE).
        # yaml.represent(const_l.Group,
        #                yaml.enum_representer(const_l.Group),
        #                __file__)
        # yaml.represent(const_l.SuccessType,
        #                # Use to-string to get the SuccessType formatting.
        #                yaml.enum_to_string_representer,
        #                __file__)

    @classmethod
    def yaml_tag(klass: 'LogRecordYaml') -> str:
        '''
        This class's yaml tag.
        '''
        return klass._DOC_TYPE_TAG

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
        self._dict_success.clear()
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
        self._dict_record['success'] = self._dict_success
        self._dict_record['context'] = None
        self._dict_record['message'] = None
        self._dict_record['error'] = self._dict_error

    def filter(self) -> None:
        '''
        Filters out optional, and currently empty, entries in preparation for
        outputting.
        '''
        # # ---
        # # Fiter down to just a few fields during buggy unit tests?
        # # ---
        # TODO: What flag to check?
        # TODO: How to set?
        # if xxx is not None:
        #     return self._filter_ut()

        # ---
        # Filter the empty entries.
        # ---
        if not self._dict_record.get('python', None):
            self._dict_record.pop('python', None)
        elif not self._dict_py.get('process', None):
            self._dict_py.pop('process', None)
        elif not self._dict_process.get('thread', None):
            self._dict_process.pop('thread', None)

        if not self._dict_record.get('group', None):
            self._dict_record.pop('group', None)

        if not self._dict_record.get('success', None):
            self._dict_record.pop('success', None)

        if not self._dict_record.get('context', None):
            self._dict_record.pop('context', None)

        if not self._dict_record.get('error', None):
            self._dict_record.pop('error', None)

    def _filter_ut(self) -> None:
        '''
        Filters out most of the record, leaving a much smaller log.
        '''
        time = self._dict_record['timestamp']
        message = self._dict_record['message']
        error = self._dict_record['error']

        self._dict_record.clear()

        if time:
            self._dict_record['timestamp'] = time
        if message:
            self._dict_record['message'] = message
        if error:
            self._dict_record['error'] = error

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
        # For Python's fields, only ignore keys. Allow Falsy values.
        if not key:
            return

        # Make sure python dict is in the entries, then add this kvp.
        self._dict_record['python'] = self._dict_py
        self._dict_py[key] = value

    def _group(self, key: str, value: str) -> None:
        '''
        Add a key/value pair to the 'group' sub-dictionary.
        '''
        # Groups should always have key and value.
        if not key or not value:
            return

        # Make sure group dict is in the entries, then add this kvp.
        self._dict_record['group'] = self._dict_group
        self._dict_group[key] = value

    def _success(self, key: str, value: [str, bool]) -> None:
        '''
        Add a key/value pair to the 'success' sub-dictionary.
        '''
        # Success fields should (currently) always have key and value.
        if not key or not value:
            # NOTE: 'dry-run' is a success field which is a bool. Currently
            # [2021-03-03] it is ignored when False.
            return

        # Make sure success dict is in the entries, then add this kvp.
        self._dict_record['success'] = self._dict_success
        self._dict_success[key] = value

    def _error(self, key: str, value: Any) -> None:
        '''
        Add a key/value pair to the 'error' sub-dictionary.
        '''
        # For Error fields, only ignore keys. Allow Falsy values.
        if not key:
            return

        # Make sure error dict is in the entries, then add this kvp.
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

    def level(self, level: const_l.Level) -> None:
        '''
        Set the level field.
        '''
        log_level = const_l.Level.to_logging(level)
        self._dict_level['name'] = logging.getLevelName(log_level)
        self._dict_level['id'] = log_level
        self._dict_record['level'] = self._dict_level

    def logger_dotted(self, dotted: label.DotStr) -> None:
        '''
        Set the dotted field.
        '''
        self._dict_record['dotted'] = dotted

    def group(self, name: str, dotted: label.DotStr) -> None:
        '''
        Set the group's name and dotted field.
        '''
        self._group('name', name)
        self._group('dotted', dotted)

    def success(self,
                normalized: const_l.SuccessType,
                verbatim: const_l.SuccessType,
                dry_run: bool) -> None:
        '''
        Set the success fields.

        Only sets `normalized`, `verbatim` if they are not IGNORE.

        Only sets `dry_run` if it is Truthy.
        '''
        if const_l.SuccessType.valid(normalized):
            self._success('normalized', normalized)
        if const_l.SuccessType.valid(verbatim):
            self._success('verbatim', verbatim)
        if dry_run:
            self._success('dry-run', dry_run)

    def message(self, message: str) -> None:
        '''
        Set the message field.
        '''
        self._dict_record['message'] = yaml.LiteralString(message)

    def context(self, context: 'VerediContext') -> None:
        '''
        Take the context, pretty print it, and set the context field.
        '''
        # Not sure what might be in the context, so convert its values
        # to just strings.
        data = convert.to_str(context.data)
        self._dict_record['context'] = {
            context.klass: data,
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
                  exception_info: Optional[TracebackTupleType] = None,
                  exception:      Optional[Exception] = None) -> None:
        '''
        Format, set exception stuff into record.
        '''
        if exception_info:
            stream = self._stream
            print_exception(exception_info[0],
                            exception_info[1],
                            exception_info[2],
                            None,
                            stream)
            self._error('exception-python', yaml.LiteralString(stream.getvalue()))

        if exception:
            self._error('exception', yaml.LiteralString(str(exception)))

    def stack(self,
              stack_info: Optional[str] = None,
              stack:      Optional[str] = None) -> None:
        '''
        Set the stack trace data.
        '''
        if stack_info:
            self._error('stack-python', yaml.LiteralString(stack_info))

        if stack:
            self._error('stack', yaml.LiteralString(stack))

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
                       default_sequence=yaml.SequenceStyle.BLOCK,
                       stream=stream)
        return stream.getvalue()
