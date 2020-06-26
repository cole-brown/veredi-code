# coding: utf-8

'''
Combat Offensive Component
  - a component that has the aggressive side of combat in it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional)
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext

from ..ecs.base.component import Component
from ..ecs.base.identity import ComponentId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Offensive!
# -----------------------------------------------------------------------------

class OffensiveComponent(Component):
    '''
    Component with offensive/attack numbers, attack action queue, probably
    other stuff...
    '''

    def __init__(self,
                 context: Optional['VerediContext'],
                 cid: ComponentId) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''

        # This calls _configure with the context.
        super().__init__(context, cid)

        # Now we'll finish init by setting up our members.
        self._queued = None
        '''Can hold on to next thing Entity wants to attack with here.'''

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.
        pass

    # -------------------------------------------------------------------------
    # Action / Attack / Whatever Queue
    # -------------------------------------------------------------------------
    # §-TODO-§ [2020-06-04]: QueueComponent Interface to inherit from?

    @property
    def has_action(self):
        return bool(self._queued)

    @property
    def queued(self):
        '''Peek at queued attack/whetever.'''
        return self._queued

    @property
    def dequeue(self):
        '''Pop and return queued attack/whetever.'''
        retval = self._queued
        self._queued = None
        return retval

    @queued.setter
    def enqueue(self, value):
        '''Set queued attack/whetever.'''
        self._queued = value


# -----------------------------------------------------------------------------
# D-Fence.
# -----------------------------------------------------------------------------

class DefensiveComponent(Component):
    '''
    Component with defensive numbers, defense action queue(?), probably other
    stuff...
    '''

    def __init__(self,
                 context: Optional['VerediContext'],
                 cid: ComponentId) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''

        # This calls _configure with the context.
        super().__init__(context, cid)

        # Now we'll finish init by setting up our members.
        # §-TODO-§ [2020-06-03]: that.

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.
        pass

#     # -------------------------------------------------------------------------
#     # Action / Attack / Whatever Queue
#     # -------------------------------------------------------------------------
#
#     @property
#     def has_action(self):
#         return bool(self._queued)
#
#     @property
#     def queued(self):
#         '''Peek at queued attack/whetever.'''
#         return self._queued
#
#     @property
#     def dequeue(self):
#         '''Pop and return queued attack/whetever.'''
#         retval = self._queued
#         self._queued = None
#         return retval
#
#     @queued.setter
#     def enqueue(self, value):
#         '''Set queued attack/whetever.'''
#         self._queued = value
