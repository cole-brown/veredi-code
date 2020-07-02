# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, MutableMapping

from veredi.data.config.registry    import register

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

        'identity': [
            # Required:
            'name',
            'group',

            # Optional:
            # 'display-name',
            # 'player',
            # 'user',
            # 'owner',
        ],
    }

    # -------------------------------------------------------------------------
    # Init Stuff
    # -------------------------------------------------------------------------

    def _from_data(self, data: MutableMapping[str, Any] = None) -> None:
        '''
        Configure our data into whatever it needs to be for runtime.
        '''
        actual_data = data['identity']
        super()._from_data(actual_data)

    # -------------------------------------------------------------------------
    # Properties: General Entity Names
    # -------------------------------------------------------------------------

    @property
    def display(self) -> Optional[str]:
        '''
        Returns our entity's display name.
        '''
        # TODO [2020-06-11]: Options for, like, full vs short/formal vs
        # informal vs nickname?
        name = (self._persistent.get('display-name', None) or
                self._persistent.get('name', None))
        return name

    @property
    def name(self) -> Optional[str]:
        '''
        Returns our entity's non-display name.
        '''
        return self._persistent.get('name', None)

    @property
    def group(self) -> Optional[str]:
        '''
        Returns our entity's group or owner name.
        '''
        name = (self._persistent.get('group', None) or
                self._persistent.get('owner', None))
        return name

    # -------------------------------------------------------------------------
    # Properties: Player-Specific Names
    # -------------------------------------------------------------------------

    @property
    def user(self) -> Optional[str]:
        '''
        Returns username if a PC and it has one, else None.

        NOTE: this is user currently in control of Entity. May not be the usual
        person playing the character (that is, the player's 'owner').
        '''
        return self._persistent.get('user', None)

    @property
    def player(self) -> Optional[str]:
        '''
        Returns player's name if a PC and it has one, else None.
        '''
        return self._persistent.get('player', None)

    @property
    def owner(self) -> Optional[str]:
        '''
        Returns our entity's owner name (username of main player if PC) if
        it has one, else None.
        '''
        name = self._persistent.get('owner', None)
        return name

    @property
    def log_player(self) -> Optional[str]:
        '''
        Returns: player if exists, else name.
        '''
        return self.player or self.name

    @property
    def log_user(self) -> Optional[str]:
        '''
        Returns: user if exists, else owner, else name.
        '''
        return self.user or self.owner or self.name
