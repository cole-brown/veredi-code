# coding: utf-8

'''
YAML log line format for Veredi Logger.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Callable, NamedTuple)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext


import logging


from veredi.base.strings import label
from ...                 import const_l


# -----------------------------------------------------------------------------
# Veredi Log Group Info
# -----------------------------------------------------------------------------

class RecordGroup(NamedTuple):
    '''
    Container for info about logging group.
    '''
    name:   str
    dotted: label.DotStr
    status: const_l.SuccessType


# -----------------------------------------------------------------------------
# The Record Itself, now with more Veredi Flavor!
# -----------------------------------------------------------------------------

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
              name:     Optional[str]                 = None,
              dotted:   Optional[label.DotStr]        = None,
              status:   Optional[const_l.SuccessType] = None,
              context:  Optional['VerediContext']     = None,
              **kwargs: Any) -> logging.LogRecord:
        '''
        Generate a LogRecord with additional log Group data.
        '''
        record = self.context(*args, context=context, **kwargs)

        # Now add in our fields.
        record.group = RecordGroup(name, dotted, status)
        return record
