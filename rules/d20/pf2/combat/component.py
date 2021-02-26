# coding: utf-8

'''
Combat Components

AttackComponent
  - a component that has the aggressive side of combat in it.

DefenseComponent
  - a component that has the defensive side of combat in it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional)
if TYPE_CHECKING:
    from veredi.base.context         import VerediContext
    from veredi.data.config.context  import ConfigContext

from veredi.logs                     import log
from veredi.data.config.registry     import register

from veredi.game.data.component      import DataComponent
from veredi.game.interface.component import queue


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# This means war!
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'pf2', 'combat', 'component', 'attack')
class AttackComponent(DataComponent, queue.IQueueSingle[AttackEvent]):
    '''
    Component with offensive/attack numbers, attack action queue, probably
    other stuff...
    '''

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Members
        # ---

        # Set up our queue.
        self._init_queue()

        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.

    # ---
    # Queue Interface
    # ---

    # @property
    # def is_queued(self) -> bool:
    #     ...
    # @property
    # def queued(self) -> Nullable[QType]:
    #     ...
    # @property
    # def dequeue(self) -> QType:
    #     ...
    # @queued.setter
    # def enqueue(self, value: NullNoneOr[QType]) -> None:
    #     ...


# -----------------------------------------------------------------------------
# D-Fence.
# -----------------------------------------------------------------------------

@register('veredi', 'rules', 'd20', 'pf2', 'combat', 'component', 'defense')
class DefenseComponent(DataComponent, queue.IQueueSingle):
    '''
    Component with defense numbers, defense action queue(?), probably other
    stuff...
    '''

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Members
        # ---

        # Set up our queue.
        self._init_queue()

        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.

    # ---
    # Queue Interface
    # ---

    # @property
    # def is_queued(self) -> bool:
    #     ...
    # @property
    # def queued(self) -> Nullable[QType]:
    #     ...
    # @property
    # def dequeue(self) -> QType:
    #     ...
    # @queued.setter
    # def enqueue(self, value: NullNoneOr[QType]) -> None:
    #     ...
