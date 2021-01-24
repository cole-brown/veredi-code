# coding: utf-8

'''
Event Manager. Pub/Sub style. Subscribe to events by class type.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Callable, Any, Type, NewType, Dict, List)
if TYPE_CHECKING:
    from .time import TimeManager

from veredi.base.null import Null, NullNoneOr


import enum


from veredi.logger             import log
from veredi.base.context       import VerediContext
from veredi.base.const         import VerediHealth
from veredi.data               import background
from veredi.data.config.config import Configuration
from veredi.base.exceptions    import VerediError
from veredi.debug.const        import DebugFlag

from .const                    import SystemTick
from .manager                  import EcsManager
from .base.identity            import MonotonicId
from .exceptions               import EventError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EventNotifyFn = NewType('EventNotifyFn', Callable[['Event'], None])


# -----------------------------------------------------------------------------
# Manager Interface Subclass
# -----------------------------------------------------------------------------

class EcsManagerWithEvents(EcsManager):

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._event: EventManager = None
        '''
        Link to the EventManager
        '''

    def __init__(self,
                 event_manager: NullNoneOr['EventManager'],
                 debug_flags:   NullNoneOr[DebugFlag]) -> None:
        super().__init__(debug_flags)

        self._event = event_manager or Null()

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        self._event = event_manager

        return VerediHealth.HEALTHY

    def _event_create(self,
                      event_class:                Type['Event'],
                      owner_id:                   int,
                      type:                       Union[int, enum.Enum],
                      context:                    Optional[VerediContext],
                      requires_immediate_publish: bool) -> None:
        '''
        Calls EventManager.create() if we have an EventManager.
        '''
        if not self._event:
            return
        self._event.create(event_class,
                           owner_id,
                           type,
                           context,
                           requires_immediate_publish)

    def _event_notify(self,
                      event:                      'Event',
                      requires_immediate_publish: bool) -> None:
        '''
        Calls EventManager.notify() if we have an EventManager.
        '''
        if not self._event:
            return
        self._event.notify(event,
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

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type}]"

    def _pretty(self):
        from veredi.logger import pretty
        return (f"{self.__str_name__()}:\n  context:\n" +
                pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return f"{self.__str_name__()}: {str(self._context)}"

    def __repr_name__(self):
        return self.__class__.__name__

    def __repr__(self):
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                f"{repr(self._context)}>")


# ----------------------------"Party Coordinator"?-----------------------------
# --                   "Event Manager" seems so formal...                    --
# --------------------------------(oh well...)---------------------------------

class EventManager(EcsManager):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        self._subscriptions: Dict[Type[Event], EventNotifyFn] = {}
        '''Our subscribers. Event types to functions dictionary.'''

        self._events:        List[Event]                      = []
        '''FIFO queue of events that came in, if saving up.'''

    def __init__(self,
                 config:      Optional[Configuration],
                 debug_flags: NullNoneOr[DebugFlag]) -> None:
        super().__init__(debug_flags)

        # Pool for event objects?

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'EventManager') -> str:
        '''
        The dotted name this Manager has.
        '''
        return 'veredi.game.ecs.manager.event'

    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        return {
            background.Name.DOTTED.key: self.dotted(),
        }

    # -------------------------------------------------------------------------
    # Debug Stuff
    # -------------------------------------------------------------------------

    def debug_flagged(self, desired) -> bool:
        '''
        Returns true if Engine's debug flags are set to something and that
        something has the desired flag. Returns false otherwise.
        '''
        return self._debug and self._debug.has(desired)

    @property
    def debug(self) -> DebugFlag:
        '''Returns current debug flags.'''
        return self._debug

    @debug.setter
    def debug(self, value: DebugFlag) -> None:
        '''
        Set current debug flags. No error/sanity checks.
        Universe could explode; use wisely.
        '''
        self._debug = value

    def _error_maybe_raise(self,
                           error:      Exception,
                           msg:        Optional[str],
                           *args:      Any,
                           context:    Optional['VerediContext'] = None,
                           **kwargs:   Any):
        '''
        Log an error, and raise it if `self.debug_flagged` to do so.
        '''
        kwargs = kwargs or {}
        kwargs = self._log_stack(**kwargs)
        if self.debug_flagged(DebugFlag.RAISE_ERRORS):
            raise self._log_exception(
                error,
                msg,
                *args,
                context=context,
                **kwargs
            ) from error
        else:
            self._log_exception(
                error,
                msg,
                *args,
                context=context,
                **kwargs)

    # -------------------------------------------------------------------------
    # Subscribing
    # -------------------------------------------------------------------------
    def subscribe(self,
                  target_class: Type[Any],
                  handler_fn:   EventNotifyFn) -> None:
        '''
        Subscribe to all events triggered for `target_class` and any of its
        sub-classes.

        Raises EventError if `handler_fn` is already a subscriber to
        `target_class`.
        '''
        if self.is_subscribed(target_class, handler_fn):
            error = EventError("Subscriber is trying to re-register."
                               "subscriber: {}, event: {}")
            raise self._log_exception(EventError,
                                      "Subscriber is trying to re-register."
                                      "subscriber: {}, event: {}",
                                      handler_fn, target_class)

        self._log_debug("Adding subscriber {} for event {}.",
                        handler_fn, target_class)
        subs = self._subscriptions.setdefault(target_class, set())
        subs.add(handler_fn)

    def is_subscribed(self,
                      target_class: Type[Any],
                      handler_fn:   EventNotifyFn) -> None:
        '''
        Returns true if `handler_fn` is already in our subscriptions for
        `target_class`.
        '''
        return handler_fn in self._subscriptions.get(target_class, set())

    # -------------------------------------------------------------------------
    # Event Helpers
    # -------------------------------------------------------------------------

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

    def _drop_events(self) -> None:
        '''
        Clears events out of our queue.
        '''
        self._events.clear()

    # -------------------------------------------------------------------------
    # Event Publishing / Notification
    # -------------------------------------------------------------------------

    @property
    def has_queued(self) -> bool:
        '''
        Returns True if our events queue has anything in it, False otherwise.
        '''
        return len(self._events) > 0

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
        self._log_debug("Received {} for publishing {}.",
                        event,
                        ("IMMEDIATELY"
                         if requires_immediate_publish else
                         "later"))
        if requires_immediate_publish:
            self._push(event)
            return
        self._events.append(event)

    def _call_catch(self,
                    notice: EventNotifyFn,
                    event:  Event) -> None:
        '''
        Call an event notification function, catching exceptions.

        Logs, reraises, or both, depending on DebugFlags.
        '''
        try:
            notice(event)

        # ------------------------------
        # Veredi Exceptions: Specific -> Generic
        # ------------------------------
        except EventError as error:
            self.health = VerediHealth.UNHEALTHY
            # Plow on ahead anyways or raise due to debug flags.
            # TODO: add notice, event to error
            self._error_maybe_raise(
                error,
                "EventManager tried to notify a subscriber about an event, "
                "but got an EventError of type '{}'.",
                type(error))

        # Most generic of our exceptions.
        except VerediError as error:
            self.health = VerediHealth.UNHEALTHY
            # TODO: add notice, event to error
            # Plow on ahead anyways or raise due to debug flags.
            self._error_maybe_raise(
                error,
                "EventManager tried to notify a subscriber about an event, "
                "but got an error of type '{}'.",
                type(error))

        # ------------------------------
        # Python Exceptions
        # ------------------------------
        except AttributeError as error:
            self.health = VerediHealth.UNHEALTHY
            # TODO: add notice, event to error
            # Plow on ahead anyways or raise due to debug flags.
            self._error_maybe_raise(
                error,
                "EventManager tried to notify a subscriber about an event, "
                "but got an error of type '{}'.",
                type(error))

        # Most generic python exception.
        except Exception as error:
            self.health = VerediHealth.UNHEALTHY
            # TODO: add notice, event to error
            # Plow on ahead anyways or raise due to debug flags.
            self._error_maybe_raise(
                error,
                "EventManager tried to notify a subscriber about an event, "
                "but got an error of type '{}'.",
                type(error))
            raise

        except:  # noqa E722
            self.health = VerediHealth.FATAL

            # TODO: add notice, event to error
            # Always log in catch-all?
            # For now anyways.
            self._log_exception(
                VerediError,
                "EventManager tried to notify a subscriber about an event, "
                "but got a _very_ unknown exception.")
            # Always re-raise in catch-all.
            raise

    def _push(self, event: Any) -> None:
        '''
        Pushes one event to all of its subscribers.
        '''
        # Push for each class, parent classes, multiple inheritance stuff, etc.
        has_subs = False
        for push_type in event.__class__.__mro__:
            subs = self._subscriptions.get(push_type, ())
            if subs:
                self._log_debug("Pushing {} to its {} subcribers: {}",
                                event, push_type, subs)
            for notice in subs:
                has_subs = True
                self._call_catch(notice, event)

        if not has_subs:
            self._log_debug("Tried to push {}, but it has no subscribers.",
                            event)

    def publish(self) -> int:
        '''
        Publishes all queued up events to any subscribers.

        Returns number published.
        '''
        publishing = len(self._events)
        self._log_debug("Publishing {} events...",
                        publishing)

        for each in self._events:
            self._push(each)
        self._events.clear()

        return publishing

    # -------------------------------------------------------------------------
    # Engine Ticks
    # -------------------------------------------------------------------------

    def update(self, tick: SystemTick, time: 'TimeManager') -> int:
        '''
        Engine calls us for each update tick, and we'll call all our
        game systems.
        '''
        # For the starting and running ticks, just publish.
        if SystemTick.TICKS_START.has(tick) or SystemTick.TICKS_RUN.has(tick):
            return self.publish()

        # For the ending ticks, bit more complicated -
        # call the function for them.
        if SystemTick.TICKS_END.has(tick):
            return self._update_ticks_end(tick)

        # ---
        # Error!
        # ---
        # For other ticks... WTF - should be no others.
        msg = f"EventManager doesn't know what to do for update tick: {tick}"
        error = ValueError(msg, tick)
        raise self._log_exception(error, msg)

    def _update_ticks_end(self, tick: SystemTick) -> int:
        '''
        Game is ending gracefully.

        Set our health to APOPTOSIS_SUCCESSFUL on ticks we don't publish
        any events.

        Set our health to APOPTOSIS (in progress) on ticks we do publish
        events.

        Return should mirror self.update().

        Returns: Number of events published.
        '''
        published = 0
        if tick == SystemTick.APOPTOSIS:
            # If we published nothing, then systems and such are probably done?
            # So guess that we're successful.
            #
            # If stuff isn't done and it was just a lull, they will say they're
            # not and next round of apoptosis we'll be back here again anyways.
            health = VerediHealth.APOPTOSIS
            published = self.publish()
            if published == 0:
                health = VerediHealth.APOPTOSIS_SUCCESSFUL

        elif tick == SystemTick.APOCALYPSE:
            # Most systems should be dead now. But we need to still do our
            # thing because we are a manager and cannot die until THE_END.
            health = VerediHealth.APOCALYPSE
            published = self.publish()
            if published == 0:
                health = VerediHealth.APOCALYPSE_DONE

        elif tick == SystemTick.THE_END or tick == SystemTick.FUNERAL:
            # Just drop and ignore all events we might have.
            health = VerediHealth.THE_END
            self._drop_events()

        else:
            # Should not have another tick?
            # There is 'FUNERAL', but that should not ever tick.
            health = VerediHealth.FATAL
            self.health = health

            msg = ("EventManager doesn't know what to do for ending "
                   f"update tick: {tick}")
            error = ValueError(msg, tick)
            raise self._log_exception(error, msg)

        self.health = health
        return published

    # -------------------------------------------------------------------------
    # Unit Test Functions
    # -------------------------------------------------------------------------

    def _ut_clear_events(self) -> List[Event]:
        '''
        Replace our event queue with a fresh queue (basically, clear out all
        our queued events).

        Returns the old event queue with whatever was or wasn't in it.
        '''
        queued_events = self._events
        self._events = []
        return queued_events

    def _ut_clear_subs(self) -> Dict[Type[Event], EventNotifyFn]:
        '''
        Replace our subscriptions with a fresh dictionary (basically, clear
        them all out).

        Returns the old subs dict with whatever was in it.
        '''
        prev_subs = self._subscriptions
        self._subscriptions = {}
        return prev_subs
