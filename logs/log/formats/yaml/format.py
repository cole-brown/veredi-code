# coding: utf-8

'''
YAML log line format for Veredi Logger.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING, Dict)
if TYPE_CHECKING:
    from veredi.base.context       import VerediContext


import logging
import datetime
import math


from veredi.base.strings import label

from ...                 import const as const_l
from .record             import LogRecordYaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# The Record Formatter
# -----------------------------------------------------------------------------

class FormatYaml(logging.Formatter):
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

        # General Stuff...
        self._record_fmt.timestamp(record.asctime)
        self._record_fmt.level(const_l.Level.from_logging(record.levelno))
        self._record_fmt.logger_dotted(record.name)

        # Group Stuff
        if hasattr(record, 'group'):
            self._record_fmt.group(record.group.group,
                                   record.group.dotted)

        # Success Stuff
        if hasattr(record, 'success'):
            self._record_fmt.success(record.success.normalized,
                                     record.success.verbatim,
                                     record.success.dry_run)

        # The Actual Main Thing and its buddy.
        self._record_fmt.message(record.message)
        if hasattr(record, 'context'):
            self._record_fmt.context(record.context)

        # Python Stuff
        self._record_fmt.module(record.module)
        self._record_fmt.path(record.filename)
        self._record_fmt.function(record.funcName)
        self._record_fmt.process_id(record.process)
        self._record_fmt.process_name(record.processName)
        self._record_fmt.thread_id(record.thread)
        self._record_fmt.thread_name(record.threadName)

        # Error Stuff
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
