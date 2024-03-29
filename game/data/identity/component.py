# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, MutableMapping, Literal)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


from veredi.logs                 import log
from veredi.base.strings         import label
from veredi.data.identity        import UserId, UserKey

from ..component                 import DataComponent


# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------

# ---
# Names And Naming:
# ---
# Player Names:
#   - 'name' - ???
#       - No longer exists (in code)!
#       - Don't use in order to avoid confusion. 'name' is generic and already
#         used all over so it's a bit unclear what it really means.
#       - Still exists in data as it just makes more sense as a field name for
#         users to fill out (if filling in e.g. YAML file templates by hand).
#   - 'designation' - display name
#       - character's full 'display-name' or 'name' field.
#   - 'namelog' - name for logging things about the entity
#   - 'dotted' - 'veredi.dotted.name' - not used for entities
#
# Future use?:
#   - 'moniker' - 'familiar' name or 'nickname' of entity
#   - 'cognomen' or 'surname' - 'the Doomed'
#   - 'title' - 'Lord Emperor <name> of This Puddle'
#
# User Names:
#   - 'owner' - name of user who owns the player.
#   - 'allonym'
#       - definition: "name of someone else that is assumed by an author"
#       - our use is: users controlling PCs they don't own
#   - 'controller': Whoever's in control of player right now.
#       - 'allonym' if player is not being run by owner right now.
#       - 'owner' if player is.


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Identity Component
# -----------------------------------------------------------------------------


class IdentityComponent(DataComponent,
                        name_dotted='veredi.game.data.identity.component',
                        name_string='component.identity'):
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
            'owner',

            # Optional:
            # 'display-name',
            # 'log-name',
            # 'allonym',

            # Derived:
            # 'controller',
        ],
    }

    # -------------------------------------------------------------------------
    # Init Stuff
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Set up our vars with type hinting, docstrs.
        '''
        super()._define_vars()

        self._user_id:  Optional[UserId]  = None
        '''
        User Identity of user that should be communicated with about this
        specific entity. E.g. a player-character should have the UserId of the
        user controlling that character this session.
        '''

        self._user_key: Optional[UserKey] = None
        '''
        User Key of user that should be communicated with about this specific
        entity. E.g. a player-character should have the UserKey of the user
        controlling that character this session.
        '''

        self._prime_entity: bool = False
        '''
        Set to true if this is the user's primary entity. Or only entity.
        '''

    def _verify(self,
                data: Union[MutableMapping[str, Any], Literal[False]],
                requirements: MutableMapping[str, Any]) -> None:
        '''
        Verifies our `data` against a template/requirements data set provided
        by `requirements`.

        If `data` is False, we allow it through as verified. Otherwise we only
        accept valid data.

        Raises:
          - DataNotPresentError (VerediError)
          - DataRestrictedError (VerediError)
          - NotImplementedError - temporarily
        '''

        # If no data, allow an empty identity, otherwise require valid data.
        if data is False:
            return

        super()._verify(data, requirements)
        for key in self._REQ_KEYS:
            self._verify_key(key, data, self._REQ_KEYS[key])

    def _from_data(self, data: MutableMapping[str, Any] = None) -> None:
        '''
        Configure our data into whatever it needs to be for runtime.
        '''

        actual_data = data['identity']
        super()._from_data(actual_data)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _join(self, *args: str) -> Optional[str]:
        '''
        Join names together into a name, ignoring any nulls, nones,
        empty strings, etc.
        '''
        names = []
        for each in args:
            if each:
                names.append(each)

        if not names:
            return None
        return ' '.join(names)

    # -------------------------------------------------------------------------
    # Property: User <-> Entity
    # -------------------------------------------------------------------------

    @property
    def entity_prime(self) -> bool:
        '''
        Returns True if this is the primary entity for its UserId.
        '''
        return self._entity_prime

    @entity_prime.setter
    def entity_prime(self, value: bool) -> None:
        '''
        Set 'primary entity' flag for this entity/user.
        '''
        self._entity_prime = value

    # -------------------------------------------------------------------------
    # Properties: General Entity Names
    # -------------------------------------------------------------------------

    @property
    def designation(self) -> Optional[str]:
        '''
        Returns our entity's display name.
        '''
        # TODO [2020-06-11]: Options for, like, full vs short/formal vs
        # informal vs nickname?
        name = (self._persistent.get('display-name', None) or
                self._persistent.get('name', None))
        return name

    # TODO: Do we want all these names or is it too much?
    # @property
    # def moniker(self) -> Optional[str]:
    #     '''
    #     Returns our entity's display name on the 'familiar' or
    #     'nickname' level?
    #     '''
    #     return self._persistent.get('moniker', None)
    #
    # @property
    # def cognomen(self) -> Optional[str]:
    #     '''
    #     Returns our entity's display name with any titular surnames...
    #     e.g. "Jeff the Green".
    #     '''
    #     return self._join(self.designation,
    #                       self.cognomen)
    #
    # @property
    # def title(self) -> Optional[str]:
    #     '''
    #     Returns our entity's display name with any full titles.
    #     e.g. "Lord Emperor Jeff the Green".
    #     '''
    #     return self._join(self._persistent.get('title', None),
    #                       self.designation,
    #                       self.cognomen)

    # -------------------------------------------------------------------------
    # Properties: General Entity Super-Names
    # -------------------------------------------------------------------------

    @property
    def log_name(self) -> Optional[str]:
        '''
        Returns our entity's non-display-for-logging-purporses name.
        Or their 'designation' if we don't have the log-name.
        '''
        return self._persistent.get('log-name',
                                    self.designation)

    @property
    def log_extra(self) -> Optional[str]:
        '''
        For PCs: returns 'controller'.
        For others: returns 'group'.
        '''
        return (self.controller or self.group)

    # -------------------------------------------------------------------------
    # Properties: General Entity Super-Names
    # -------------------------------------------------------------------------

    @property
    def group(self) -> Optional[str]:
        '''
        Returns our entity's group name.
        Groups are classifications like 'monster', 'player', 'npc', etc.
        '''
        name = self._persistent.get('group', None)
        return name

    # -------------------------------------------------------------------------
    # Properties: Player-Character Names
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

    # -------------------------------------------------------------------------
    # Properties: User Names
    # -------------------------------------------------------------------------

    @property
    def owner(self) -> Optional[str]:
        '''
        Returns our entity's owner name (username of main player if PC) if
        it has one, else None.
        '''
        name = self._persistent.get('owner', None)
        return name

    @property
    def allonym(self) -> Optional[str]:
        '''
        Returns our entity's user's name if not being controlled by owner.
        '''
        name = self._persistent.get('owner', None)
        return name

    @property
    def controller(self) -> Optional[str]:
        '''
        Returns entity's owner's name if they are in control; else returns
        entity's allonym - name of user who is in control instead.
        '''
        return (self._persistent.get('allonym', None)
                or self._persistent.get('owner', None))

    # -------------------------------------------------------------------------
    # User Identity: UserId & UserKey
    # -------------------------------------------------------------------------

    @property
    def user_id(self) -> Optional[UserId]:
        '''
        Returns UserId or None.
        '''
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[UserId]) -> None:
        '''
        Set this entity's UserId. Set to 'None' to unset.
        '''
        self._user_id = value

    @property
    def user_key(self) -> Optional[UserKey]:
        '''
        Returns UserKey or None.
        '''
        return self._user_key

    @user_key.setter
    def user_key(self, value: Optional[UserKey]) -> None:
        '''
        Set this entity's UserKey. Set to 'None' to unset.
        '''
        self._user_key = value
