# coding: utf-8

'''
Class to hold User data. UserId, UserKey, username, EntityIds, etc...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Callable, Set, Tuple, Iterable)
if TYPE_CHECKING:
    from ..message import Message


import asyncio


from veredi.game.ecs.base.identity import EntityId
from veredi.data.identity          import UserId, UserKey
from .mediator.context             import (MessageContext,
                                           UserConnToken,
                                           USER_CONN_INVALID)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# The basest of the users?
# -----------------------------------------------------------------------------

class BaseUser:
    '''
    Base class of user data like: UserId, UserKey, username, EntityIds, etc...
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

        self._connection: UserConnToken = USER_CONN_INVALID
        '''Token representing a user's connection to the server.'''

        # I'd like this to be a Callable[[str, *Any, **Any], None], but that is
        # impossible. Typing doesn't support *args/**kwargs yet.
        self.debug: Optional[Callable] = None
        '''
        Some callback for testing. We don't care.
        '''

    def __init__(self,
                 user_id:  UserId,
                 user_key: UserKey,
                 conn:     UserConnToken,
                 debug:    Optional[Callable]      = None) -> None:
        self._define_vars()

        self._uid = user_id
        self._ukey = user_key
        self._connection = conn

        self.debug = debug

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

    # 'debug' is just a public variable - no getter/setter properties.

    @property
    def connection(self) -> UserConnToken:
        '''
        User's (socket) connection token.
        '''
        return self._connection

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"<{self.__class__.__name__}: "
            f"id: {self.id}, "
            f"key: {self.key}, "
            f"conn: {self.connection}"
            f"debug: {self.debug}>"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"{self.id}, "
            f"{self.key}, "
            f"{self.connection}, "
            f"debug={self.debug})"
        )

    def __hash__(self) -> int:
        '''
        Returns a hash of the User based on User.hash(), which should not rely
        on memory location or anything - it will hash a user based on identity
        of the user themself.

        In other words: two separate instances of a user that refer to the same
        specific client user must have the same hash.
        '''
        return hash(self._uid)


# -----------------------------------------------------------------------------
# User Connection
# -----------------------------------------------------------------------------

class UserConn(BaseUser):
    '''
    Container of user data for MediatorServer. Includes their tx_queue.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._tx_queue: Optional[asyncio.Queue] = None
        '''
        User's queue of messages to send. Only exists if user is connected.
        '''

    def __init__(self,
                 user_id:  UserId,
                 user_key: UserKey,
                 conn:     UserConnToken,
                 debug:    Optional[Callable]      = None,
                 tx_queue: Optional[asyncio.Queue] = None) -> None:
        super().__init__(user_id, user_key, conn, debug)
        self._tx_queue = tx_queue

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    # 'debug' is just a public variable - no getter/setter properties.

    @property
    def queue(self) -> asyncio.Queue:
        '''
        Queue is for "received-from-game;waiting-to-send-to-user" messages.

        Returns User's Optional[asyncio.Queue]. Don't touch if you're not a
        Mediator.
        '''
        return self._tx_queue

    @queue.setter
    def queue(self, value: Optional[asyncio.Queue]) -> None:
        '''
        Queue is for "received-from-game;waiting-to-send-to-user" messages.

        Sets User's Optional[asyncio.Queue]. Don't touch if you're not a
        Mediator.
        '''
        self._tx_queue = value

    # -------------------------------------------------------------------------
    # Queue Helpers
    # -------------------------------------------------------------------------

    def has_data(self) -> bool:
        '''Returns True if client's queue has data to send them.'''
        # No queue? Then, uh... it has no data.
        if not self._tx_queue:
            return False

        # Have a queue, ask it if it's empty or not.
        return not self._tx_queue.empty()

    def get_data(self) -> Tuple['Message', MessageContext]:
        '''Gets (no wait) data from client's queue for processing/sending.'''
        msg, ctx = self._tx_queue.get_nowait()
        if self.debug:
            self.debug("Got from client's queue for sending to client: "
                       "msg: {}, ctx: {}, client: {}",
                       msg, ctx, self)
        return msg, ctx

    async def put_data(self,
                       msg: 'Message',
                       ctx: MessageContext) -> None:
        '''
        Puts data into client's queue for us to send to this client later.
        '''
        if self.debug:
            self.debug("Putting data into client's queue for sending to "
                       "client: msg: {}, ctx: {}, client: {}",
                       msg, ctx, self)
        await self._tx_queue.put((msg, ctx))

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f"id: {self.id}, "
            f"key: {self.key}, "
            f"conn: {self.connection}, "
            f"queue: {self.queue} "
            f"queue-has-data?: {self.has_data()}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"{self.id}, "
            f"{self.key}, "
            f"{self.connection}, "
            f"tx_queue={self._tx_queue})"
        )


# -----------------------------------------------------------------------------
# User and Entity
# -----------------------------------------------------------------------------

class UserPassport(BaseUser):
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
        super()._define_vars()

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

    def __init__(self,
                 user_id:      UserId,
                 user_key:     UserKey,
                 conn:         UserConnToken,
                 entity_prime: Optional[EntityId]           = None,
                 entity_ids:   Optional[Iterable[EntityId]] = None,
                 debug:        Optional[Callable]           = None) -> None:
        super().__init__(user_id, user_key, conn, debug)

        self._entity_prime = entity_prime
        self._entity_ids = entity_ids

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

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

    # 'debug' is just a public variable - no getter/setter properties.

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f"id: {self.id}, "
            f"key: {self.key}, "
            f"entity_prime: {self.entity_prime}, "
            f"entity_ids: {self.entity_ids}, "
            f"debug: {self.debug}"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"{self.id}, "
            f"{self.key}, "
            f"{self.connection}, "
            f"entity_prime={self.entity_prime}, "
            f"entity_ids={self.entity_ids}, "
            f"debug={self.debug})"
        )
