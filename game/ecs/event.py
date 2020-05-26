# coding: utf-8

'''
Event Manager. Pub/Sub style. Subscribe to events by class type.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Type, Any, Union, Optional
import enum

from . import exceptions
from .manager import EcsManager
from .const import SystemHealth
from veredi.base.context import VerediContext

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Manager Interface Subclass
# ------------------------------------------------------------------------------

class EcsManagerWithEvents(EcsManager):
    # TODO: init that pulls in event_manager to self._event_manager?

    def subscribe(self, event_manager: 'EventManager') -> SystemHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        return SystemHealth.HEALTY

    def event(self,
              event_manager:              'EventManager',
              event_class:                Type['Event'],
              owner_id:                   int,
              type:                       Union[int, enum.Enum],
              context:                    Optional[VerediContext],
              requires_immediate_publish: bool,
              *args:                      Any,
              **kwargs:                   Any) -> None:
        '''
        Calls event_manager.create() if event_manager is not none.
        '''
        if not event_manager:
            return
        event_manager.create(event_class,
                             owner_id,
                             type,
                             context,
                             requires_immediate_publish,
                             *args,
                             **kwargs)


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Event:
    def __init__(self,
                 id: int,
                 type: Union[int, enum.Enum],
                 *args: Any,
                 context: Optional[VerediContext] = None,
                 **kwargs: Any) -> None:
        self.set(id, type, context, *args, **kwargs)

    def set(self,
            id: int,
            type: Union[int, enum.Enum],
            context: VerediContext,
            *args: Any,
            **kwargs: Any) -> None:
        self._id      = id
        self._type    = type
        self._context = context

        if not self._context:
            for each in args:
                if isinstance(each, VerediContext):
                    if not self._context:
                        self._context = each
                    else:
                        raise exceptions.EventError(
                            "Too many contexts for event. Already found: "
                            f"{self._context}. Also just found:"
                            f"{each}.",
                            None,
                            self._context)

        # Don't have a requirement for context right now.
        # raise exceptions.EventError(
        #     "Too many contexts for event. Already found: "
        #     f"{self._context}. Also just found:"
        #     f"{each}.",
        #     None,
        #     self._context):


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


class EventManager(EcsManager):
    def __init__(self) -> None:
        self._subscriptions = {}
        self._events = []  # FIFO queue of events that came in, if saving up.

        # Pool for event objects?

    def subscribe(self,
                  target_class: Type[Any],
                  handler_fn: Callable[[Any], None]) -> None:
        '''
        Subscribe to all events triggered for `target_class` and any of its
        sub-classes.
        '''
        subs = self._subscriptions.setdefault(target_class, [])
        subs.append(handler_fn)

    def create(self,
               event_class:                Type[Event],
               owner_id:                   int,
               type:                       Union[int, enum.Enum],
               context:                    Optional[VerediContext],
               requires_immediate_publish: bool,
               *args:                      Any,
               **kwargs:                   Any) -> None:
        '''
        Creates a managed Event from parameters, then calls notify().
        '''
        event = event_class(owner_id, type, context, *args, **kwargs)
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
        '''
        if requires_immediate_publish:
            self._push(event)
            return
        self._events.append(event)

    def _push(self, event: Any) -> None:
        '''
        Pushes one event to all of its subscribers.
        '''
        # Push for each class, parent classes, multiple inheritance stuff, etc.
        for push_type in event.__class__.__mro__:
            for notice in self._subscriptions.get(push_type, ()):
                notice(event)

    def publish(self) -> None:
        '''
        Publishes all queued up events to any subscribers.
        '''
        for each in self._events:
            self._push(each)
        self._events.clear()

    def update(self, tick: 'SystemTick', time: 'TimeManager') -> None:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # Publish whatever we've built up.
        self.publish()

    def apoptosis(self, time: 'TimeManager') -> SystemHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        # About all we can do is make sure the event queue is empty.
        self.publish()
        return SystemHealth.APOPTOSIS
