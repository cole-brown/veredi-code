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
from .                   import const


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

factory: 'LogRecordFactory' = None
'''
A LogRecord factory class that adds Veredi data to LogRecords for the formatter.
'''

_factory_orig: Callable = None
'''
Save spot for the original factory function.
'''


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

def init() -> 'LogRecordFactory':
    '''
    Create and return the LogRecordFactory.

    Saves off the old factory...
    '''
    # Save original...
    global _factory_orig
    _factory_orig = logging.getLogRecordFactory()

    # Create new...
    global factory
    factory = LogRecordFactory()

    # Attach it to the logger...
    logging.setLogRecordFactory(factory.create)

    # And done.


def reset() -> 'LogRecordFactory':
    '''
    Reset the LogRecord factory to the factory default.
    '''
    global _factory_orig
    if not _factory_orig:
        raise ValueError("veredi.logs.log.factory: Cannot reset the "
                         "LogRecord Factory - have nothing to reset to.",
                         _factory_orig)
    # Reattach original...
    logging.setLogRecordFactory(_factory_orig)


# -----------------------------------------------------------------------------
# Veredi Log Group Info
# -----------------------------------------------------------------------------

class RecordGroup(NamedTuple):
    '''
    Container for info about logging group.
    '''
    name:   str
    dotted: label.DotStr
    status: const.SuccessType


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

    def create(self,
               *args:    Any,
               name:     Optional[str]               = None,
               dotted:   Optional[label.DotStr]      = None,
               status:   Optional[const.SuccessType] = None,
               context:  Optional['VerediContext']   = None,
               **kwargs: Any) -> logging.LogRecord:
        '''
        Generic factory function to start the chain of adding veredi-specific
        data to a LogRecord.

        This adds:
          1) Group data, then
          2) Context data, then
          3) default logging LogRecord data.
        '''
        record = self.group(*args,
                            name=name,
                            dotted=dotted,
                            status=status,
                            context=context,
                            **kwargs)
        return record
