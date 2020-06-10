# coding: utf-8

'''
Manager interface for ECS managers.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .time import TimeManager
    from .event import EventManager

from veredi.base.const import VerediHealth


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class EcsManager:
    '''
    Interface for ECS Managers.
    '''

    def apoptosis(self, time: 'TimeManager') -> VerediHealth:
        '''
        Game is ending gracefully. Do graceful end-of-the-world stuff...
        '''
        return VerediHealth.APOPTOSIS

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        raise NotImplementedError
