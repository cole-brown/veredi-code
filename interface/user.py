# coding: utf-8

'''
Class to hold User data. UserId, UserKey, username, EntityIds, etc...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Set

from veredi.game.ecs.base.identity import EntityId
from veredi.data.identity          import UserId, UserKey


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class User:
    '''
    Container of user data. UserId, UserKey, username, EntityIds, etc...
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._uid: UserId = UserId.INVALID
        '''User's UserId'''

        self._ukey: UserKey = UserKey.INVALID
        '''User's UserKey'''

        self._entity_prime: EntityId = EntityId.INVALID
        '''
        User's primary EntityId. Most users are just players and this will be
        their player character's EntityId.
        '''

        self._entity_ids: Set[EntityId] = set()
        '''
        The EntityIds for all of the user's current entities (primary
        included).

        For players: Main PC, side-kick, minions, whatever.
        For DM: NPCs, monsters, etc.
        '''

    def __init__(self, user_id: UserId, user_key: UserKey) -> None:
        self._define_vars()

        self._uid = user_id
        self._ukey = user_key

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> UserId:
        '''Returns User's UserId.'''
        return self._uid

    @id.setter
    def id(self, value: UserId) -> None:
        '''Sets User's UserId. Set to UserId.INVALID if 'unset' is desired.'''
        self._uid = value

    @property
    def key(self) -> UserKey:
        '''Returns User's UserKey.'''
        return self._ukey

    @key.setter
    def key(self, value: UserKey) -> None:
        '''
        Sets User's UserKey. Set to UserKey.INVALID if 'unset' is desired.
        '''
        self._ukey = value

    @property
    def entity_prime(self) -> EntityId:
        '''
        Returns User's primary entity's EntityId. Could be EntityId.INVALID.
        '''
        return self._entity_prime

    @entity_prime.setter
    def entity_prime(self, value: EntityId) -> None:
        '''
        Sets User's primary entity's EntityId. Set to EntityId.INVALID if
        'unset' is desired.
        '''
        self._entity_prime = value

    @property
    def entity_ids(self) -> Set[EntityId]:
        '''
        Returns all of User's EntityIds. Could be empty.
        '''
        return self._entity_ids

    @entity_ids.setter
    def entity_ids(self, value: Set[EntityId]) -> None:
        '''
        Sets User's full list of all their EntityIds. Set to an empty set if
        'unset' is desired.
        '''
        self._entity_ids = value

    def add_entity(self,
                   entity_id: EntityId,
                   is_prime:  bool = False) -> None:
        '''
        Add to the user's full set of EntityIds. If 'is_prime' is set,
        overwrites `self._entity_prime` field. Does not remove old entity_prime
        from current set.
        '''
        self._entity_ids.add(entity_id)
        if is_prime:
            self._entity_prime = entity_id

    def remove_entity(self,
                      entity_id: EntityId) -> None:
        '''
        Removes `entity_id` from the user's full set of EntityIds. If
        `entity_id` is `self._entity_prime`, then this also sets
        `self._entity_prime` to EntityId.INVALID.
        '''
        self._entity_ids.discard(entity_id)
        if self._entity_prime == entity_id:
            self._entity_prime = EntityId.INVALID

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __hash__(self) -> int:
        '''
        Returns a hash of the User based on user_id, since a User should be
        tied directly to one client, and UserId is how we talk to/desccribe a
        single user/client.
        '''
        return hash(self._uid)
