# coding: utf-8

'''
Interface for a Queue of something on a Component.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Generic, TypeVar
from veredi.base.null import Null, Nullable, NullNoneOr

from abc import ABC, abstractmethod


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

QType = TypeVar('QType')


# -----------------------------------------------------------------------------
# Just Imagine You're British and Enjoy a Good Queueing...
# -----------------------------------------------------------------------------

class IQueueComponent(ABC, Generic[QType]):
    '''
    Component interface for a component with a queue of some sort.
    '''

    @abstractmethod
    def _init_queue(self) -> None:
        '''
        Init the queue's member variables.
        '''
        ...

    # -------------------------------------------------------------------------
    # Queue Properties / Methods
    # -------------------------------------------------------------------------

    @property
    def is_queued(self) -> bool:
        '''True if something is queued up.'''
        ...

    @property
    @abstractmethod
    def queued(self) -> Nullable[QType]:
        '''Peek at upcoming queued thing.'''
        ...

    @property
    @abstractmethod
    def dequeue(self) -> Nullable[QType]:
        '''Pop and return queued thing.'''
        ...

    @queued.setter
    @abstractmethod
    def enqueue(self, value: NullNoneOr[QType]):
        '''Set or add queued thing.'''
        ...


class IQueueSingle(IQueueComponent, Generic[QType]):
    '''
    Component interface for a component with a queue that is only one deep -
    queueing something when an item already exists in the queue will overwrite
    the queued item with the new one.
    '''

    def _init_queue(self) -> None:
        '''
        Init the queue's member variables.
        '''
        self._queue = None

    # -------------------------------------------------------------------------
    # Queue Properties / Methods
    # -------------------------------------------------------------------------

    @property
    def is_queued(self) -> bool:
        return bool(self._queued)

    @property
    def queued(self) -> Nullable[QType]:
        '''Peek at queued attack/whetever.'''
        return self._queued if self._queued else Null()

    @property
    def dequeue(self) -> QType:
        '''Pop and return queued attack/whetever.'''
        retval = self._queued or Null()
        self._queued = None
        return retval

    @queued.setter
    def enqueue(self, value: NullNoneOr[QType]) -> None:
        '''Set queued attack/whetever.'''
        self._queued = value


class IQueueList(IQueueComponent, Generic[QType]):
    '''
    Component interface for a component with a queue that is flexably deep. New
    items get appended to end and it is as long as needs to be...
    '''

    def _init_queue(self) -> None:
        '''
        Init the queue's member variables.
        '''
        self._queue = []

    # -------------------------------------------------------------------------
    # Queue Properties / Methods
    # -------------------------------------------------------------------------

    @property
    def is_queued(self) -> bool:
        return bool(self._queued)

    @property
    def queued(self)  -> Nullable[QType]:
        '''Peek at queued attack/whetever.'''
        return self._queued[0] if len(self._queued) > 1 else Null()

    @property
    def dequeue(self) -> Nullable[QType]:
        '''Pop and return queued attack/whetever.'''
        retval = self._queued.pop(0) if len(self._queued) > 1 else Null()
        return retval

    @queued.setter
    def enqueue(self, value) -> None:
        '''Set queued attack/whetever.'''
        self._queued.append(value)
