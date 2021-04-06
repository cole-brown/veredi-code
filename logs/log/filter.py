# coding: utf-8

'''
"Filter" for Veredi Logger.

...except the cookbook recommends using a filter to impart context information
on to a log instead of a LogRecordFactory... For some performance reason?

So this isn't really a filter. It's an AddVerediData-er.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, NamedTuple)
from veredi.base.null import Null, Nullable, NullNoneOr, is_null
if TYPE_CHECKING:
    from veredi.base.context import VerediContext


import logging
import threading


from veredi.base         import threads
from veredi.base.strings import label, labeler
from .                   import const


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

def init(logger: logging.Logger) -> 'VerediFilter':
    '''
    Create and add the VerediFilter to the provided logger.
    '''
    filter = VerediFilter()

    # Attach it to the logger...
    logger.addFilter(filter)

    # And done.
    return filter

def reset(filter: logging.Filter,
          logger: logging.Logger) -> None:
    '''
    Remove the LogRecord filter.
    '''
    # Remove our filter if we have one initialized...
    if not filter or not logger:
        return
    logger.removeFilter(filter)


# -----------------------------------------------------------------------------
# Veredi Log Info
# -----------------------------------------------------------------------------

class RecordGroup(NamedTuple):
    '''
    Container for info about logging group.
    '''
    group:  const.Group
    '''Group enum value.'''

    dotted: label.DotStr
    '''Dotted string logged specifically for group.'''


class RecordSuccess(NamedTuple):
    '''
    Container for info about success type/dry run.
    '''
    normalized: const.SuccessType
    '''Success normalized with dry-run flag.'''

    verbatim: const.SuccessType
    '''Success value we got passed in as-is.'''

    dry_run: bool
    '''Dry-run flag we got passed in as-is.'''


# -----------------------------------------------------------------------------
# Filter... in some data into the LogRecord?
# -----------------------------------------------------------------------------
# ...doesn't sound like a filter?
# But is recommended...
# https://docs.python.org/3/howto/logging-cookbook.html#filters-contextual


@labeler.dotted('veredi', 'log', 'filter')
class VerediFilter(logging.Filter):
    '''
    For log records with extra fields for Groups, Context, etc.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        # Initialize our fields with Null...
        self._record_storage: threads.Local = threads.Local(context=Null(),
                                                            group=Null(),
                                                            success=Null())
        '''
        An instance of the thread-local data-storage class.

        We'll use it to store context, group, etc info to be filtered into the
        LogRecord soon.
        '''

    def __init__(self) -> None:
        self._define_vars()

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------

    def filter(self, record: logging.LogRecord) -> bool:
        '''
        Method called by Python logging for each LogRecord.

        Returns True if log should be logged; False if log has been filtered
        out and should not be logged.
        '''
        # Run the record through all our data adders...
        self.context_filter(record)
        self.group_filter(record)
        self.success_filter(record)

        # We just add data; always log all records that pass through this
        # 'filter'.
        return True

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------

    def context(self,
                clear:    Optional[bool]              = False,
                context:  NullNoneOr['VerediContext'] = None) -> None:
        '''
        Save context off for injecting into LogRecord on filtering.

        If `clear` is True, saves `Null()` instead.
        '''
        if clear is True:
            context = Null()
        self._record_storage.context = context

    def context_filter(self,
                       record: logging.LogRecord) -> bool:
        '''
        Add a VerediContext data to the LogRecord if we have any.
        '''
        # Do we have a context to add?
        context = self._record_storage.context
        if context:
            # Have data; add to the log.
            record.context = context
            return True
        return False

    def group(self,
              clear:    Optional[bool]                = False,
              group:    NullNoneOr[const.Group]       = None,
              dotted:   NullNoneOr[label.DotStr]      = None) -> None:
        '''
        Save group data off for injecting into LogRecord on filtering.

        If `clear` is True, saves `Null()` instead.
        '''
        rec_group = Null()
        if clear is not True:
            rec_group = RecordGroup(group, dotted)
        self._record_storage.group = rec_group

    def group_filter(self,
                     record: logging.LogRecord) -> bool:
        '''
        Add Group data to the LogRecord if we have any.
        '''
        # Do we have group data to add?
        group = self._record_storage.group
        if group:
            # Have data; add to the log.
            record.group = group
            return True
        return False

    def success(self,
                clear:   Optional[bool]               = False,
                success: Nullable[const.SuccessInput] = None,
                dry_run: Nullable[bool]               = False) -> None:
        '''
        Save success data off for injecting into LogRecord on filtering.

        If `clear` is True, saves `Null()` instead.
        '''
        rec_success = Null()
        if clear is not True:
            dry_run = bool(dry_run)
            # Full success log?
            if (not is_null(success)
                    and success is not const.SuccessType.IGNORE):
                value = const.SuccessType.normalize(success,
                                                    dry_run)
                rec_success = RecordSuccess(value, success, dry_run)

            # Just stick dry-run in on its own?
            elif dry_run:
                rec_success = RecordSuccess(Null(), Null(), dry_run)

        self._record_storage.success = rec_success

    def success_filter(self,
                       record: logging.LogRecord) -> bool:
        '''
        Add Success data to the LogRecord if we have any.
        '''
        # Do we have success data to add?
        success = self._record_storage.success
        if success:
            # Have data; add to the log.
            record.success = success
            return True
        return False
