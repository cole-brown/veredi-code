# coding: utf-8

'''Background Context!

                                      ---
                            - Background Context -
                                     -----

The "Cosmic Microwave Backgroud" version of a VerediContext: a module
that (hopefully) duck-types as a VerediContext. To make sure/force the
"There Can Be Only One" aspect of this one.

Overarching, "always" stuff goes here. Game config, things registered,
systems created, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any,
                    Type, NewType,
                    Mapping, MutableMapping, List, Tuple)
if TYPE_CHECKING:
    from veredi.base.const                 import VerediHealth
    from veredi.base.context               import VerediContext
    from veredi.game.ecs.meeting           import Meeting
    from veredi.game.ecs.time              import TimeManager
    from veredi.game.ecs.event             import EventManager
    from veredi.game.ecs.component         import ComponentManager
    from veredi.game.ecs.entity            import EntityManager
    from veredi.game.ecs.system            import SystemManager
    from veredi.game.data.manager          import DataManager
    from veredi.game.data.identity.manager import IdentityManager

    from veredi.game.ecs.base.system       import System, SystemLifeCycle

    from veredi.interface.input.parse      import Parcel
    from .config                           import Configuration
    from veredi.data.codec.codec           import Codec

    from veredi.game.ecs.base.identity     import EntityId
    from veredi.data.identity              import UserId, UserKey
    from veredi.interface.mediator.context import UserConnToken
    from veredi.interface.user             import UserPassport

import enum
import pathlib
import copy

from veredi.logs            import log

from veredi.base.null       import Null, Nullable, NullNoneOr
from .exceptions            import ConfigError
from veredi.base.exceptions import ContextError
from veredi.base.dicts      import DoubleIndexDict
from veredi.base.strings    import label


# TODO [2020-06-23]: methods for: contains, [], others...?


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

ContextMap = NewType('ContextMap',
                     Mapping[Union[str, enum.Enum], Any])
'''Generally expect Mapping[str, str], but some things can be
Mapping[enum, JeffObject].'''

ContextMutableMap = NewType('ContextMap',
                            MutableMapping[Union[str, enum.Enum], Any])
'''Generally expect MutableMapping[str, str], but some things can be
MutableMapping[enum, JeffObject].'''


# -----------------------------------------------------------------------------
# Context Layout
# -----------------------------------------------------------------------------

# ------------------------------
# All our stuff will be namespaced under this:
# ------------------------------

_ROOT = 'veredi'
'''Veredi's background context will all be in here.'''


# ------------------------------
# Set-Up Stuff
# ------------------------------

_REGISTRY = 'registry'
'''Registration by Veredi's Registries will be placed under this key.'''

_REGISTRARS = 'registrars'
'''Veredi's Registrars/Registries will be listed under this key.'''

_REGISTREES = 'registrees'
'''Veredi's Registry will be listed under this key.'''

_CONFIG = 'configuration'
'''Configuration data will be placed under this key.'''


# ------------------------------
# Game Stuff
# ------------------------------
_GAME = 'game'
'''
Game and game systems' root key.
'''

_MANAGER = 'manager'
'''
Game's Meeting object with all managers.
'''

_SYSTEM = 'system'
'''
SystemManager uses this for e.g. Meeting link. It is also a place where
systems that get created will be registered as running or having been run
here.
'''
_SYS_VITALS = 'vitals'
'''A list of dicts of info about a system's vital records: creation, etc...'''


# ------------------------------
# Interface Stuff (IO)
# ------------------------------

_INTERFACE = 'interface'
'''Input, output, mediator, etc. root key.'''

_USERS = 'users'
'''All users for the game.'''

_USERS_CONNECTED = 'connected'
'''All currently connected users for the game.'''

_USERS_KNOWN = 'known'
'''
All known users for the game. Previously connected, currently connected,
whatever.
'''

_USERS_SUPER = 'super'
'''
Game superusers. Game owner, GMs, etc.
'''

_OUTPUT = 'output'
'''OutputSystem and other output stuff should be placed under this key.'''

_INPUT = 'input'
'''InputSystem and other input stuff should be placed under this key.'''

_COMMAND = 'command'
'''InputSystem's Commander uses this.'''

_CMDS_EXISTING = 'commands'
'''
A list where info about command names registered to InputSystem's Commander
should be placed when registered in Commander.
'''

_MEDIATOR = 'mediator'
'''InputSystem and other input stuff should be placed under this key.'''


# ------------------------------
# Testing Stuff
# ------------------------------

_TESTING = 'testing'
'''Unit/integration/system tests can store things here.'''

# ------------------------------
# ==============================
# The Background Context
# ==============================
# ------------------------------

_CONTEXT_LAYOUT = {
    _ROOT: {
        _CONFIG: {},
        _REGISTRY: {
            _REGISTRARS: {},
            _REGISTREES: {},
        },
        _GAME: {
            _MANAGER: {},
            _SYSTEM: {
                _SYS_VITALS: [],
            },
        },
        _INTERFACE: {
            _USERS: {
                # _USERS_CONNECTED: None,  # Initialized by users._init_dict().
                # _USERS_KNOWN: None,      # Initialized by users._init_dict().
                # _USERS_SUPER: None,      # Initialized by users._init_dict().
            },
            _INPUT: {
                _COMMAND: {
                    _CMDS_EXISTING: [],
                },
            },
            _OUTPUT: {},
            _MEDIATOR: {},
        },
        _TESTING: {}
    },
}
'''
Unit tests don't get the background cleaned up automatically, so split out
the context from its layout to help them reset as needed.
'''

_CONTEXT = None
'''The actual background context.'''

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.context.background'


@enum.unique
class Name(enum.Enum):
    DOTTED  = 'dotted'
    TYPE    = 'type'

    REPO    = 'repository'
    PATH    = 'path'

    SERDES  = 'serdes'

    CODEC   = 'codec'

    SYS     = 'system'
    CONFIG  = 'configuration'

    @property
    def key(self):
        '''
        Return enum value for use as key in dict.
        '''
        return str(self)

    def __str__(self):
        '''
        These are just for nicer context node names. We only want the string.
        '''
        return self.value


@enum.unique
class Ownership(enum.Enum):
    '''
    Things that put data into the background context should indicate whether we
    need to make a deep copy. They use this.
    '''

    SHARE = enum.auto()
    '''
    Context data is safe/preferred to take by reference. Some systems may need
    to fill in data later than init so may prefer this.
    '''

    COPY = enum.auto()
    '''
    Context data must be (deep) copied. E.g. system is using it for
    EphemerealContexts after they set themselves up in the background context.
    '''


# -----------------------------------------------------------------------------
# Setter that obeys Ownership
# -----------------------------------------------------------------------------

def _set(subctx: ContextMutableMap,
         key: Union[str, enum.Enum],
         value: Any,
         ownership: Ownership) -> None:
    '''
    NOTE!: If key should be a string but isn't, call str(key) yourself or
    otherwise translate it.

    Sets supplied `value` into the background context - either by just setting
    or by deep copying (depending on `ownership`).
    '''

    if Ownership.SHARE:
        subctx[key] = value
    elif Ownership.COPY:
        subctx[key] = copy.deepcopy(value)
    else:
        log.exception(
            ContextError,
            "Cannot set data into background context. Don't know what to "
            "do with Ownership type {}. sub-context: {}, key: {}, data: {},",
            ownership, subctx, key, value)


# -------------------------------------------------------------------------
# Veredi Namespace
# -------------------------------------------------------------------------

class veredi:

    @classmethod
    def get(klass: Type['veredi']) -> Nullable[ContextMutableMap]:
        '''
        Get Veredi's root of the background context. Anything else in the
        background context is assumed to be other's (e.g. plugin's?).
        '''
        global _CONTEXT, _ROOT
        if _CONTEXT is None:
            from copy import deepcopy
            _CONTEXT = deepcopy(_CONTEXT_LAYOUT)
        return _CONTEXT.get(_ROOT, Null())


# -------------------------------------------------------------------------
# Configuration Namespace
# -------------------------------------------------------------------------

class ConfigMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''
    @property
    def path(klass: Type['config']) -> Nullable[pathlib.Path]:
        '''
        Checks for a PATH link in config's spot in this context.
        '''
        ctx = klass._get()
        retval = ctx.get(klass.Link.PATH, Null())
        return retval


class config(metaclass=ConfigMeta):

    @enum.unique
    class Link(enum.Enum):
        CONFIG = enum.auto()
        '''The Configuration object.'''

        # KEYCHAIN = enum.auto()
        # '''
        # Iterable of keys into something in the Configuration object that is
        # important to the receiver of a context, probably.
        # '''

        PATH = enum.auto()
        '''A pathlib.Path to somewhere.'''

    @classmethod
    def init(klass: Type['config'],
             path:        pathlib.Path,
             back_link:   'Configuration') -> None:
        '''
        Initialize the background with some config data.
        '''
        # Make sure the path is a directory.
        if path is None:
            raise log.exception(
                ConfigError,
                "Background needs a path to __init__ properly.")
        elif path is False:
            # Current way of allowing a NoFileConfig...
            # TODO [2020-06-16]: Better way?
            pass
        else:
            path = path if path.is_dir() else path.parent
            klass.link_set(klass.Link.PATH, path)

        klass.link_set(klass.Link.CONFIG, back_link)

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['config']) -> Nullable[Any]:
        '''
        Get config's sub-context from background context.
        '''
        global _CONFIG
        return veredi.get().get(_CONFIG, Null())

    @classmethod
    def config(klass:          Type['config'],
               caller_name:    str,
               caller_dotted:  label.DotStr,
               caller_context: Optional['VerediContext'],
               raises_error:   Optional[bool] = True,
               ) -> Nullable['Configuration']:
        '''
        Checks for a CONFIG link in config's spot in this context. Returns it
        if it exists.

        If it doesn't exist use `raises_error` to either:
          - Throw an error via this class's `exception()`.
          - Just return Null().
        '''
        # Get it.
        ctx = klass._get()
        cfg_obj = ctx.get(klass.Link.CONFIG, Null())

        # Error on it or return it?
        if not cfg_obj:
            if raises_error:
                msg = ("No Configuration present in the background "
                       "context; cannot get config setting for {} ({}) "
                       "without it.")
                raise klass.exception(
                    caller_context,
                    msg,
                    caller_name, caller_dotted)
            else:
                # Esure it's null as opposed to Null, None, or Falsy.
                cfg_obj = Null()
        return cfg_obj

    @classmethod
    def link_set(klass: Type['config'], link: Link, entry: Any) -> None:
        klass._get()[link] = entry

    @classmethod
    def link(klass: Type['config'], link: Link) -> Nullable[Any]:
        return klass._get().get(link, Null())

    @classmethod
    def set(klass: Type['config'],
            name:      Name,
            data:      ContextMap,
            ownership: Ownership) -> None:
        '''
        Repo and Serdes have to be created and want to register some data into
        the background context.

        Makes a deep copy of inputs if ownership wants.
        '''
        context = klass._get()
        _set(context, str(name), data, ownership)

    # -------------------------------------------------------------------------
    # More Specific Getters
    # -------------------------------------------------------------------------

    # Provided by ConfigMeta:
    # @classmethod
    # def config(klass: Type['config']) -> Nullable['Configuration']:
    #     '''
    #     Checks for a CONFIG link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.CONFIG, Null())
    #     return retval

    # Provided by ConfigMeta:
    # @classmethod
    # def path(klass: Type['config']) -> Nullable[pathlib.Path]:
    #     '''
    #     Checks for a PATH link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.PATH, Null())
    #     return retval

    # -------------------------------------------------------------------------
    # Helper?
    # -------------------------------------------------------------------------

    @classmethod
    def exception(klass:      Type['config'],
                  context:    Optional['VerediContext'],
                  msg:        Optional[str],
                  *args:      Any,
                  error_data: Optional[Mapping[Any, Any]] = None,
                  **kwargs:   Any) -> None:
        '''
        Calls log.exception() to raise a ConfigError with message built from
        msg, args, kwargs and with supplied context.

        NOTE: If no context is supplied, WILL NOT LOG ANY! Provide
        config.make_config_context() if you are using it as your default!

        Sets stack level one more than usual so that caller of this should be
        the stacktrace of the exception.

        If optional `error_data` is not None, it will be supplied to the
        created ConfigError as the `data` parameter in the constructor.
        '''
        kwargs = log.incr_stack_level(kwargs)
        # If we raised instead of returned, we could add an extra stacklevel to
        # get the log back to whoever called us...
        #                             amount=2)

        # Let a generic ConfigError be made.
        return log.exception(
            ConfigError,
            msg, *args, **kwargs,
            error_data=error_data,
            context=context)

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def ut_inject(self,
                  path:   NullNoneOr[pathlib.Path]    = None,
                  config: NullNoneOr['Configuration'] = None) -> None:
        '''
        Unit testing injection of config (if not None).
        '''
        config_data = self._get().get(self.KEY, {})
        if path:
            config_data[self.Link.PATH] = path
        if config:
            config_data[self.Link.CONFIG] = config
        # if keychain:
        #     config_data[self.Link.KEYCHAIN] = keychain


# -------------------------------------------------------------------------
# Registry Namespace
# -------------------------------------------------------------------------

class registry:

    @classmethod
    def _get(klass: Type['registry'], key: str) -> Nullable[ContextMutableMap]:
        '''
        Get registry's full sub-context from background context.
        '''
        global _REGISTRY
        registry_entry = veredi.get().get(_REGISTRY, Null())
        sub_entry = registry_entry.get(key, Null())
        return sub_entry

    @classmethod
    def registrar(klass:     Type['registry'],
                  register:  label.DotStr,
                  data:      ContextMap,
                  ownership: Ownership) -> None:
        '''
        Adds `register`'s dotted label and background data to the background's
        registrars.
        '''
        # Add to list of registrars known.
        context = klass._get(_REGISTRARS)
        _set(context, register, data, ownership)

        # And make it a default entry for its registrees list.
        registrees = klass._get(_REGISTREES)
        registrees[register] = {}

    @classmethod
    def registry(klass:          Type['registry'],
                 registrar_name: label.DotStr) -> Nullable[ContextMutableMap]:
        '''
        Get registry's sub-context for a specific registrar from background
        context. Creates an empty one if none exists.
        '''
        all_registries = klass._get(_REGISTREES)
        registrar_registry = all_registries.setdefault(registrar_name, {})
        return registrar_registry

    # ------------------------------
    # Note:
    # ------------------------------
    # Registrars handle their own dictionary after obtianing with `get()`.
    # They keep the background in sync with their full reg info dict.


# -------------------------------------------------------------------------
# Game Namespace
# -------------------------------------------------------------------------

class game:

    @classmethod
    def get(klass: Type['game']) -> Nullable[ContextMutableMap]:
        '''
        Get game's sub-context from background context.
        '''
        global _GAME
        return veredi.get().get(_GAME, Null())


# -------------------------------------------------------------------------
# Manager Namespace
# -------------------------------------------------------------------------

class ManagerMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''

    # -------------------------------------------------------------------------
    # Properties: The Whole Meeting of Managers
    # -------------------------------------------------------------------------

    @property
    def meeting(klass: Type['manager']) -> Nullable['Meeting']:
        '''
        Returns the Meeting of managers. Meeting has helper functions and maybe
        you want to access several managers from it?
        '''
        ctx = klass._get()
        retval = ctx.get(klass.Link.MEETING, Null())
        return retval

    # -------------------------------------------------------------------------
    # Properties: Specific Manager Accessors
    # -------------------------------------------------------------------------

    @property
    def time(klass: Type['manager']) -> Nullable['TimeManager']:
        '''
        Helper for getting at Meeting's TimeManager directly.
        '''
        return klass.meeting.time

    @property
    def event(klass: Type['manager']) -> Nullable['EventManager']:
        '''
        Helper for getting at Meeting's EventManager directly.
        '''
        return klass.meeting.event

    @property
    def component(klass: Type['manager']) -> Nullable['ComponentManager']:
        '''
        Helper for getting at Meeting's ComponentManager directly.
        '''
        return klass.meeting.component

    @property
    def entity(klass: Type['manager']) -> Nullable['EntityManager']:
        '''
        Helper for getting at Meeting's EntityManager directly.
        '''
        return klass.meeting.entity

    @property
    def system(klass: Type['manager']) -> Nullable['SystemManager']:
        '''
        Helper for getting at Meeting's SystemManager directly.
        '''
        return klass.meeting.system

    @property
    def data(klass: Type['manager']) -> Nullable['DataManager']:
        '''
        Helper for getting at Meeting's DataManager directly.
        '''
        return klass.meeting.data

    @property
    def identity(klass: Type['manager']) -> Nullable['IdentityManager']:
        '''
        Helper for getting at Meeting's IdentityManager directly.
        '''
        return klass.meeting.identity


class manager(metaclass=ManagerMeta):
    '''
    Background stuff for ECS's Meeting of Managers.

    Has class properties for getting at meeting or a manager directly.
    For example, TimeManager:
      background.manager.time
    '''

    @enum.unique
    class Link(enum.Enum):
        MEETING = enum.auto()
        '''
        The Meeting of Managers.
        '''

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['manager']) -> Nullable[ContextMutableMap]:
        '''
        Get manager's sub-context from background context.
        '''
        global _MANAGER
        return game.get().get(_MANAGER, Null())

    @classmethod
    def set(klass:       Type['manager'],
            dotted_name: str,
            managers:    'Meeting',
            data:        ContextMap,
            ownership:   Ownership) -> None:
        '''
        Set a created manager's entry in background with `data`. Also sets the
        managers into their proper place.
        '''
        context = klass._get()
        _set(context, dotted_name, data, ownership)
        context[klass.Link.MEETING] = managers

    # -------------------------------------------------------------------------
    # Properties: Manager Accessors
    # -------------------------------------------------------------------------

    # Getters are in ManagerMeta class.


# -------------------------------------------------------------------------
# System Namespace
# -------------------------------------------------------------------------

class system:

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['system']) -> Nullable[ContextMutableMap]:
        '''
        Get system's sub-context from background context.
        '''
        global _SYSTEM
        return game.get().get(_SYSTEM, Null())

    @classmethod
    def set(klass:       Type['system'],
            dotted_name: str,
            data:        ContextMap,
            ownership:   Ownership) -> None:
        '''
        Update a created system's entry with `data`.
        '''
        context = klass._get()
        _set(context, dotted_name, data, ownership)

    # -------------------------------------------------------------------------
    # Vitals
    # -------------------------------------------------------------------------

    @classmethod
    def life_cycle(klass: Type['system'],
                   sys:   'System',
                   cycle: 'SystemLifeCycle',
                   health: 'VerediHealth') -> None:
        '''
        Add a system's life-cycle state change to the records.
        '''
        subctx = klass._get()
        vital_records = subctx.setdefault(_SYS_VITALS, [])
        entry = {
            'dotted': sys.dotted,
            'time':   manager.time.machine.stamp_to_str(),
            'cycle':  cycle.name,
            'health': health.name,
        }
        vital_records.append(entry)


# -------------------------------------------------------------------------
# Interface Namespace
# -------------------------------------------------------------------------

class interface:

    @classmethod
    def get(klass: Type['interface']) -> Nullable[ContextMutableMap]:
        '''
        Get interface's sub-context from background context.
        '''
        global _INTERFACE
        return veredi.get().get(_INTERFACE, Null())


# -------------------------------------------------------------------------
# Users Namespace
# -------------------------------------------------------------------------

class users:

    UserIdTypes = NewType('UserIdTypes',
                          Union['EntityId',
                                'UserId', 'UserKey',
                                'UserConnToken'])
    '''
    Can check for, get Users via `UserId`, `UserKey`, `EntityId`,
    `UserConnToken`, or a Falsy value (None). This is the definition of all
    acceptable types but the Falsy thing.
    '''

    UserRmTypes = NewType('UserRmTypes',
                          Union['UserId', 'UserConnToken'])
    '''Users can be removed via `User` object, `UserId`, or `UserConnToken`.'''

    # -------------------------------------------------------------------------
    # users dictionaries
    # -------------------------------------------------------------------------

    @classmethod
    def _init_dict(klass: Type['users']) -> DoubleIndexDict:
        '''
        Create a DoubleIndexDict for the collections of users.
        '''
        # Our DoubleIndexDicts will be accessable under:
        #  - dict.user_id[id]
        #  - dict.connection[conn]
        return DoubleIndexDict('user_id', 'connection')

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['users']) -> MutableMapping[str, DoubleIndexDict]:
        '''
        Get users's sub-context from background context.
        '''
        global _USERS
        return interface.get().get(_USERS, Null())

    @classmethod
    def _connected(klass: Type['users']) -> DoubleIndexDict:
        '''
        Get/init 'user.connected' sub-context from background context.
        '''
        return klass._get().setdefault(_USERS_CONNECTED, users._init_dict())

    @classmethod
    def _known(klass: Type['users']) -> DoubleIndexDict:
        '''
        Get/init 'user.known' sub-context from background context.
        '''
        return klass._get().setdefault(_USERS_KNOWN, users._init_dict())

    @classmethod
    def _super(klass: Type['users']) -> DoubleIndexDict:
        '''
        Get/init 'user.super' sub-context from background context.
        '''
        return klass._get().setdefault(_USERS_SUPER, users._init_dict())

    # -------------------------------------------------------------------------
    # More Specific Getters
    # -------------------------------------------------------------------------

    @classmethod
    def _filter_users(klass:     Type['users'],
                      users:     DoubleIndexDict,
                      filter_id: Optional[UserIdTypes]
                      ) -> List['UserPassport']:
        '''
        Takes the `users` dict and filters it based on the `id`.
        '''
        matches = []
        if not filter_id:
            # Push ALL known users into matches set and return.
            matches.extend(users.values())
            return matches

        for uid in users.keys():
            user = users[uid]
            if not user:
                continue
            # Check all the id types we allow in.
            if (user.id == filter_id
                    or user.key == filter_id
                    or user.entity_prime == filter_id
                    or user.connection == filter_id):
                matches.append(user)

        return matches

    @classmethod
    def connected(klass: Type['users'],
                  id:    Optional[UserIdTypes]) -> List['UserPassport']:
        '''
        Returns a UserPassport, if they exist in the connected users
        collection. If `id` is Falsy, returns all connected users.
        '''
        return klass._filter_users(klass._connected(), id)

    @classmethod
    def known(klass: Type['users'],
              id:    Optional[UserIdTypes]) -> List['UserPassport']:
        '''
        Returns a UserPassport, if they exist in the known users collection.
        If `id` is Falsy, returns all known users.
        '''
        return klass._filter_users(klass._known(), id)

    @classmethod
    def super(klass: Type['users'],
              id:    Optional[UserIdTypes]) -> List['UserPassport']:
        '''
        Returns all matched superuser ids found in the super users collection.
        If `id` is Falsy, returns all GMs.
        '''
        return klass._filter_users(klass._super(), id)

    @classmethod
    def gm(klass: Type['users'],
           id:    Optional[UserIdTypes]) -> List['UserPassport']:
        '''
        Returns all matched GM ids found in the super users collection.
        If `id` is Falsy, returns all GMs.

        TODO: Distinguish GMs from other superusers.
        TODO: Have other superuser types. Debugger, Assistant (to the) GM...
        '''
        return klass._filter_users(klass._super(), id)

    # -------------------------------------------------------------------------
    # Adding Users
    # -------------------------------------------------------------------------

    @classmethod
    def add_connected(klass: Type['users'],
                      user:  'UserPassport') -> None:
        '''
        Adds user to 'connected' (user) collection.

        If `user` already exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this will overwrite
        it.
        '''
        connected = klass._connected()
        connected.set(user.id, user.connection, user)
        # TODO: call add_super() as well if user is superuser?

        # For now, add to known users. Though eventually those should come from
        # the repository when the game loads.
        klass.add_known(user)

    @classmethod
    def add_known(klass: Type['users'],
                  user:  'UserPassport') -> None:
        '''
        Adds user to 'known' (user) collection.

        If `user` already exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this will overwrite
        it.
        '''
        known = klass._known()
        known.set(user.id, user.connection, user)

    @classmethod
    def add_super(klass: Type['users'],
                  user:  'UserPassport') -> None:
        '''
        Adds user to 'super' (user) collection.

        If `user` already exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this will overwrite
        it.
        '''
        super_users = klass._super()
        super_users.set(user.id, user.connection, user)

    # -------------------------------------------------------------------------
    # Removing Users
    # -------------------------------------------------------------------------

    @classmethod
    def remove_connected(klass:    Type['users'],
                         rm_user:  UserRmTypes) -> None:
        '''
        Removes `rm_user` (which can be a id or a UserPassport object) from
        'connected' (user) collection.

        If `user` doesn't exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this does nothing.
        '''
        connected = klass._connected()
        del connected[rm_user]

        # TODO: call remove_super() as well if user is superuser?

    @classmethod
    def remove_known(klass: Type['users'],
                     user:  UserRmTypes) -> None:
        '''
        Removes user from 'known' (user) collection.

        If `user` doesn't exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this does nothing.
        '''
        known = klass._known()
        known.discard(user)

    @classmethod
    def remove_super(klass: Type['users'],
                     user:  UserRmTypes) -> None:
        '''
        Removes user from 'super' (user) collection.

        If `user` doesn't exists in the collection (as defined by Python's
        set() functionality and UserPassport.__hash__()), this does nothing.
        '''
        super_users = klass._super()
        super_users.discard(user)


# -------------------------------------------------------------------------
# Input Namespace
# -------------------------------------------------------------------------

class InputMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''
    @property
    def parsers(klass: Type['input']) -> Nullable['Parcel']:
        '''
        Checks for a CONFIG link in config's spot in this context.
        '''
        ctx = klass._get()
        retval = ctx.get(klass.Link.PARSERS, Null())
        return retval


class input(metaclass=InputMeta):

    @enum.unique
    class Link(enum.Enum):
        PARSERS = enum.auto()
        '''The Parser object(s).'''

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['input']) -> Nullable[ContextMutableMap]:
        '''
        Get input's sub-context from background context.
        '''
        global _INPUT
        return interface.get().get(_INPUT, Null())

    @classmethod
    def set(klass:       Type['input'],
            dotted_name: str,
            parsers:     'Parcel',
            data:        NullNoneOr[ContextMap],
            ownership:   Ownership) -> None:
        '''
        Update a created system's entry with `data` and `parsers`.
        '''
        ctx = klass._get()
        # Set data provided, then set parser (don't want parser overwritten by
        # data entry).
        _set(ctx, dotted_name, data, ownership)
        ctx[klass.Link.PARSERS] = parsers

    # -------------------------------------------------------------------------
    # More Specific Getters
    # -------------------------------------------------------------------------

    # Provided by InputMeta:
    # @classmethod
    # def parsers(klass: Type['input']) -> Nullable['Parcel']:
    #     '''
    #     Checks for a CONFIG link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.PARSERS, Null())
    #     return retval


class command:
    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['command']) -> Nullable[ContextMutableMap]:
        '''
        Get command's sub-context from background context.
        '''
        global _COMMAND
        return input._get().get(_COMMAND, Null())

    @classmethod
    def _get_cmds(klass: Type['command']) -> Nullable[ContextMutableMap]:
        '''
        Get command's registered commands sub-context from background context.
        '''
        global _CMDS_EXISTING
        return klass._get().get(_CMDS_EXISTING, Null())

    @classmethod
    def registered(klass:        Type['command'],
                   source_name:  str,
                   command_name: str) -> None:
        '''
        Add a system's life-cycle state change to the records.
        '''
        infos = klass._get_cmds()
        entry = {
            'source': source_name,
            'name': command_name,
            'time': manager.time.machine.stamp_to_str(),
        }
        infos.append(entry)


# -------------------------------------------------------------------------
# Output Namespace
# -------------------------------------------------------------------------

class OutputMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''
    pass

    # @property
    # def parsers(klass: Type['output']) -> Nullable['Parcel']:
    #     '''
    #     Checks for a CONFIG link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.PARSERS, Null())
    #     return retval


class output(metaclass=OutputMeta):

    # @enum.unique
    # class Link(enum.Enum):
    #     PARSERS = enum.auto()
    #     '''The Parser object(s).'''

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['output']) -> Nullable[ContextMutableMap]:
        '''
        Get output's sub-context from background context.
        '''
        global _OUTPUT
        return interface.get().get(_OUTPUT, Null())

    @classmethod
    def set(klass:       Type['output'],
            dotted_name: str,
            data:        NullNoneOr[ContextMap],
            ownership:   Ownership) -> None:
        '''
        Update output system's entry with `data`.
        '''
        ctx = klass._get()
        # Set data provided.
        _set(ctx, dotted_name, data, ownership)

    # -------------------------------------------------------------------------
    # More Specific Getters
    # -------------------------------------------------------------------------

    # Provided by OutputMeta:
    # @classmethod
    # def parsers(klass: Type['output']) -> Nullable['Parcel']:
    #     '''
    #     Checks for a CONFIG link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.PARSERS, Null())
    #     return retval


# -------------------------------------------------------------------------
# Mediator Namespace
# -------------------------------------------------------------------------

class mediator:

    # -------------------------------------------------------------------------
    # Getters / Setters
    # -------------------------------------------------------------------------

    @classmethod
    def _get(klass: Type['mediator']) -> Nullable[ContextMutableMap]:
        '''
        Get mediator's sub-context from background context.
        '''
        global _MEDIATOR
        return interface.get().get(_MEDIATOR, Null())

    @classmethod
    def set(klass:     Type['mediator'],
            name:      str,
            data:      NullNoneOr[ContextMap],
            ownership: Ownership) -> None:
        '''
        Update mediator system's entry with `data`.
        '''
        ctx = klass._get()
        # Set data provided.
        _set(ctx, name, data, ownership)


# -------------------------------------------------------------------------
# Unit Testing
# -------------------------------------------------------------------------

class testing:
    '''
    Whatever's needed for unit/integration/functional tests.
    '''

    _CLEAN_IGNORE_KEYS = set((_REGISTRY, ))
    '''
    Ignore these keys in the background when checking `is_clean()`.
    '''

    @classmethod
    def _get(klass: Type['testing']) -> Nullable[ContextMutableMap]:
        '''
        Get testing's sub-context from background context.
        '''
        global _TESTING
        return veredi.get().get(_TESTING, Null())

    @classmethod
    def set(klass: Type['testing'], key: str, value: str) -> None:
        '''
        Store a key/value pair into the testing background context.
        '''
        ctx = klass._get()
        ctx[key] = value

    @classmethod
    def get(klass: Type['testing'], key: str) -> Nullable[str]:
        '''
        Get a key's value from the testing background context.
        '''
        ctx = klass._get()
        return ctx.get(key, Null())

    @classmethod
    def pop(klass: Type['testing'], key: str) -> Optional[str]:
        '''
        Get a key's value from the testing background context.
        '''
        value = klass.get(key)
        # Check if we have it. Otherwise have to try catch del's KeyError.
        if value:
            # Have it; remove from dict.
            ctx = klass._get()
            del ctx[key]

        return value

    @classmethod
    def set_unit_testing(klass: Type['testing'],
                         value: Optional[bool]) -> None:
        '''
        Sets unit_testing background flag. Pops it if `value` is none, which
        /should/ be the same as setting false, except it makes for a cleaner
        full background output.
        '''
        ctx = klass._get()
        if value is None:
            ctx.pop('unit_testing', None)
        else:
            ctx['unit_testing'] = value

    @classmethod
    def get_unit_testing(klass: Type['testing']) -> bool:
        '''
        Returns True/False for whether we've been flagged up for
        unit-testing mode.
        '''
        ctx = klass._get()
        return ctx.get('unit_testing', False)

    @classmethod
    def clear(klass: Type['testing']) -> None:
        '''
        Deletes all of testing's things, but leaves rest of background context
        alone.
        '''
        try:
            ctx = veredi.get()
            del ctx['testing']
            ctx[_TESTING] = {}
        except KeyError:
            pass

    @classmethod
    def nuke(klass: Type['testing']) -> None:
        '''
        Reset context for unit tests.
        '''
        global _CONTEXT
        _CONTEXT = None

    @classmethod
    def is_clean(klass: Type['testing']) -> Tuple[bool, Optional[str]]:
        '''
        Returns a 2-tuple of (<clean bool>, <dirty reason).
        Clean:
          - True if background context is uninitialized (None).
          - True if background is initialized but has nothing in any of the
            fields not in IGNORE_KEYS.
          - False otherwise (background has a non-ignored key with data in the
            field).
        '''
        # The simple case:
        if _CONTEXT is None:
            return True, None

        # ---
        # Care!
        # ---
        #   1) Need to allow once-per-all-tests registrations to remain in the
        #      background.
        #
        #   2) Need to be nice to things that register via decorator - they
        #      could have been imported already and we don't want to clear them
        #      out.
        #
        # So basically, don't clear out the registration stuff.
        # ---

        # Walk the background and make sure that nothing besides the registry
        # is filled in yet.
        nodes = [(None, _CONTEXT)]  # Start at root.
        while len(nodes) > 0:
            key, node = nodes.pop()
            # Should we ignore this node?
            if key in klass._CLEAN_IGNORE_KEYS:
                continue

            # Is this a dictionary we should traverse into?
            if isinstance(node, dict):
                # Add each key/value pair to our nodes-to-check.
                for kvp in node.items():
                    nodes.append(kvp)
                continue

            # Else, make sure the node is empty.
            if node:
                return (False,
                        f"'{key}' in background context has data: {node}")

        # Clean.
        return (True, None)


# -------------------------------------------------------------------------
# To String
# -------------------------------------------------------------------------

# TODO [2020-06-23]: string, repr for this

def to_str() -> str:
    from veredi.base.strings import pretty
    return "Veredi Backgroud Context:\n" + pretty.indented(_CONTEXT)


def to_repr() -> str:
    return repr(_CONTEXT)


def __str__() -> str:
    return to_str()


def __repr__() -> str:
    return to_repr()
