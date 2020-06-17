# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, MutableMapping

from veredi.data.config.registry    import register

# from veredi.base.context            import VerediContext
# from veredi.data.config.context     import ConfigContext

# Data Stuff
from ..component import DataComponent

# from ..ecs.base.identity            import ComponentId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Identity Component
# -----------------------------------------------------------------------------


@register('veredi', 'game', 'identity', 'component')
class IdentityComponent(DataComponent):
    '''
    Component with identity information beyond, the usual EntityId/ComponentId.

    E.g. user names, player names, display names...
    '''

    # TEMP: a way to verify we got something, and to verify we're using the
    # verify() function...
    _REQ_KEYS = {
        # Not sure about layout at all yet...
        'identity': [],
    }

    # -------------------------------------------------------------------------
    # Init Stuff
    # -------------------------------------------------------------------------

    # def _configure(self,
    #                context: Optional[ConfigContext]) -> None:
    #     '''
    #     '''
    #     # ---
    #     # Context Init Section
    #     # ---
    #     # Nothing at the moment?

    #     # ---
    #     # Misc Section
    #     # ---
    #     # Also nothing?
    #     pass

    def _from_data(self, data: MutableMapping[str, Any] = None) -> None:
        '''
        Configure our data into whatever it needs to be for runtime.
        '''
        actual_data = data['identity']
        super()._from_data(actual_data)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def display(self) -> str:
        '''
        Returns our best data for a display name.
        '''
        # §-TODO-§ [2020-06-11]: Options for, like, full vs short/formal vs
        # informal vs nickname?
        name = (self._persistent.get('display-name', None) or
                self._persistent.get('name', None))
        return name

    @property
    def name(self) -> str:
        '''
        Returns our best data for a non-display name.
        '''
        return self._persistent.get('name', None)

    @property
    def user(self) -> str:
        '''
        Returns 'user' (username if a PC) if it has one, else None.
        '''
        return self._persistent.get('user', None)

    @property
    def player(self) -> str:
        '''
        Returns 'player' (player's name if a PC) if it has one, else None.
        '''
        return self._persistent.get('player', None)

    @property
    def log_player(self) -> str:
        '''
        Returns: player if exists, else name.
        '''
        return self.player or self.name

    @property
    def log_user(self) -> str:
        '''
        Returns: user if exists, else name.
        '''
        return self.user or self.name
