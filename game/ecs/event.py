# coding: utf-8

'''
Event Manager. Pub/Sub style. Subscribe to events by class type.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Callable, Type, Any, Dict, List)
if TYPE_CHECKING:
    from .const import SystemTick
    from .time import TimeManager

import enum

from veredi.logger             import log
from veredi.base.context       import VerediContext
from veredi.base.const         import VerediHealth
from veredi.data.config.config import Configuration

from .manager                  import EcsManager
from .base.identity            import MonotonicId
from .exceptions               import EventError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Manager Interface Subclass
# -----------------------------------------------------------------------------

class EcsManagerWithEvents(EcsManager):
    # TODO: init that pulls in event_manager to self._event_manager?

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        self._event_manager = event_manager

        return VerediHealth.HEALTHY

    def _event_create(self,
                      event_class:                Type['Event'],
                      owner_id:                   int,
                      type:                       Union[int, enum.Enum],
                      context:                    Optional[VerediContext],
                      requires_immediate_publish: bool) -> None:
        '''
        Calls self._event_manager.create() if self._event_manager is not none.
        '''
        if not self._event_manager:
            return
        self._event_manager.create(event_class,
                                   owner_id,
                                   type,
                                   context,
                                   requires_immediate_publish)

    def _event_notify(self,
                      event:                      'Event',
                      requires_immediate_publish: bool) -> None:
        '''
        Calls self._event_manager.notify() if self._event_manager is not none.
        '''
        if not self._event_manager:
            return
        self._event_manager.notify(event,
                                   requires_immediate_publish)


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Event:
    TYPE_NONE = 0
    '''A "Don't care" for the event.type field.'''

    def __init__(self,
                 id: Union[int, MonotonicId],
                 type: Union[int, enum.Enum],
                 context: Optional[VerediContext] = None) -> None:
        self.set(id, type, context)

    def set(self,
            id: Union[int, MonotonicId],
            type: Union[int, enum.Enum],
            context: VerediContext) -> None:
        self._id      = id
        self._type    = type
        self._context = context

        # Don't have a requirement for context right now.
        # if not self._context:
        #     raise exceptions.EventError(
        #         "Need a context for event. None provided."
        #         f"{self._context}. Also just found:"
        #         f"{each}.",
        #         None,
        #         self._context)

    def reset(self) -> None:
        self._id      = None
        self._type    = None
        self._context = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def type(self) -> Union[int, enum.Enum]:
        return self._type

    @property
    def context(self) -> int:
        return self._context

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type}]"

    def _pretty(self):
        from veredi.logger import pretty
        return (f"{self._str_name()}:\n  context:\n" +
                pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return f"{self._str_name()}: {str(self._context)}"

    def __repr_name__(self):
        return self.__class__.__name__

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"{repr(self._context)}>")


# ----------------------------"Party Coordinator"?-----------------------------
# --                   "Event Manager" seems so formal...                    --
# --------------------------------(oh well...)---------------------------------

class EventManager(EcsManager):

    def _define_vars(self) -> None:
        super()._define_vars()

        self._subscriptions: Dict[Type[Event], Callable[[Any], None]] = {}
        '''Our subscribers. Event types to functions dictionary.'''

        self._events:        List[Event]                              = []
        '''FIFO queue of events that came in, if saving up.'''

    def __init__(self,
                 config: Optional[Configuration]) -> None:
        super().__init__()

        # Pool for event objects?

    def subscribe(self,
                  target_class: Type[Any],
                  handler_fn: Callable[[Any], None]) -> None:
        '''
        Subscribe to all events triggered for `target_class` and any of its
        sub-classes.
        '''
        log.debug("Adding subscriber {} for event {}.",
                  handler_fn, target_class)
        subs = self._subscriptions.setdefault(target_class, set())
        if handler_fn in subs:
            raise log.exception(None,
                                EventError,
                                "Subscriber is trying to re-register."
                                "subscriber: {}, event: {}",
                                handler_fn, target_class)
        subs.add(handler_fn)

    def create(self,
               event_class:                Type[Event],
               owner_id:                   int,
               type:                       Union[int, enum.Enum],
               context:                    Optional[VerediContext],
               requires_immediate_publish: bool) -> None:
        '''
        Creates a managed Event from parameters, then calls notify().
        '''
        event = event_class(owner_id, type, context)
        self.notify(event, requires_immediate_publish)

    def notify(self,
               event: Any,
               requires_immediate_publish: bool = False) -> None:
        '''
        Called when an entity, component, system, or whatever wants to notify
        potential subscribers of an event that just happened.

        If `requires_immediate_publish` is set to True, the EventManager will
        immediately publish the event to all subscribers. Otherwise it will
        queue it up until the next `publish` happens.

        Try not to `requires_immediate_publish` too much... it interrupts game
        flow/timing/whatever.

        Note: you are turning over lifecycle management of the event to
        EventManager.
        '''
        log.debug("Received {} for publishing {}.",
                  event,
                  "IMMEDIATELY" if requires_immediate_publish else "later")
        if requires_immediate_publish:
            self._push(event)
            return
        self._events.append(event)

    def _push(self, event: Any) -> None:
        '''
        Pushes one event to all of its subscribers.
        '''
        # Push for each class, parent classes, multiple inheritance stuff, etc.
        has_subs = False
        for push_type in event.__class__.__mro__:
            subs = self._subscriptions.get(push_type, ())
            if subs:
                log.debug("Pushing {} to its {} subcribers: {}",
                          event, push_type, subs)
            for notice in subs:
                has_subs = True
                notice(event)

        if not has_subs:
            log.debug("Tried to push {}, but it has no subscribers.",
                      event)

    def publish(self) -> int:
        '''
        Publishes all queued up events to any subscribers.

        Returns number published.
        '''
        publishing = len(self._events)
        log.debug("Publishing {} events...",
                  publishing)

        for each in self._events:
            self._push(each)
        self._events.clear()

        return publishing

    def update(self, tick: 'SystemTick', time: 'TimeManager') -> int:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # Publish whatever we've built up and return however many that is.
        return self.publish()

    def apoptosis(self, time: 'TimeManager') -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        health = VerediHealth.APOPTOSIS
        # If we published nothing, then systems and such are probably done...
        # So guess that we're successful.
        #
        # If stuff isn't done and it was just a lull, they will say they're not
        # and next round of apoptosis we'll be back here again anyways.
        if self.publish() == 0:
            health = VerediHealth.APOPTOSIS_SUCCESSFUL
        return health

    # -------------------------------------------------------------------------
    # Unit Test Functions
    # -------------------------------------------------------------------------

    def _ut_clear_events(self) -> None:
        '''
        Replace our event queue with a fresh queue (basically, clear out all
        our queued events).

        Returns the old event queue with whatever was or wasn't in it.
        '''
        queued_events = self._events
        self._events = []
        return queued_events

    def _ut_clear_subs(self) -> None:
        '''
        Replace our subscriptions with a fresh dictionary (basically, clear
        them all out).

        Returns the old subs dict with whatever was in it.
        '''
        prev_subs = self._subscriptions
        self._subscriptions = {}
        return prev_subs
