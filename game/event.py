# coding: utf-8

'''
Event Manager. Pub/Sub style.


'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Type, Any


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# TODO THIS
#   - Make a ComponentManager! Have Components have ComponentIds!
#
# https://www.gamasutra.com/blogs/TobiasStein/20171122/310172/The_EntityComponentSystem__An_awesome_gamedesign_pattern_in_C_Part_1.php
#
# https://stackoverflow.com/questions/1092531/event-system-in-python/28479007#28479007


# TODO
#  - Do I need a SystemManager? Or is Game good enough for it?
#
#  - Events should be published... when? Just after STANDARD tick?
#    - After LIFE(so PRE?), STANDARD(so POST?), DEATH(so.......FINAL?)?
#    - Heavily suggest systems stick to PRE/STANDARD/POST ticks?
#  -

class EventManager:
    def __init__(self) -> None:
        subscriptions = {}
        events = []  # FIFO queue of events that came in, if saving up.

    def subscriber(self,
                   target_class: Type[Any],
                   handler_fn: Callable[[Any], None]) -> None:
        '''
        Subscribe to all events triggered for `target_class` and any of its
        sub-classes.
        '''
        subs = subscriptions.setdefault(target_class, [])
        subs.append(handler_fn)

    def notify(self,
               event: Any,
               requires_immediate_publish: bool = False) -> None:
        '''
        Called when an entity, component, system, or whatever wants to notify
        potential subscribers of an event that just happened.

        If `requires_immediate_publish` is set to True, the EventManager will
        immediately publish the event to all subscribers. Otherwise it will
        queue it up until the next `publish` happens.
        '''
        if requires_immediate_publish:
            self._push(event)
            return
        events.append(event)

    def _push(self, event: Any) -> None:
        '''
        Pushes one event to any of its subscribers.
        '''
        # Push for each class, parent classes, multiple inheritance stuff, etc.
        for push_type in event.__class__.__mro__:
            for notice in subscriptions.get(push_type, ()):
                notice(event)

    def publish(self) -> None:
        '''
        Publishes all queued up events to any subscribers.
        '''
        for each in events:
            self.push(each)
        events.clear()
