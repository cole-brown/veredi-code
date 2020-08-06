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
                    Mapping, MutableMapping)
if TYPE_CHECKING:
    from veredi.base.context          import VerediContext
    from veredi.data.repository.base  import BaseRepository
    from veredi.data.codec.base       import BaseCodec
    from veredi.game.ecs.meeting      import Meeting
    from veredi.game.ecs.base.system  import System, SystemLifeCycle
    from veredi.interface.input.parse import Parcel
    from .config                      import Configuration


import enum
import pathlib
import copy

from veredi.logger          import log

from veredi.base.null       import Null, Nullable, NullNoneOr
from .exceptions            import ConfigError
from veredi.base.exceptions import ContextError


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
'''Registration by Veredi's Registry will be placed under this key.'''

_CONFIG = 'configuration'
'''Configuration data will be placed under this key.'''


# ------------------------------
# Game Stuff
# ------------------------------
_GAME = 'game'
'''Game and game systems' root key.'''

_SYSTEM = 'system'
'''
SystemManager uses this for e.g. Meeting link. It is also a place where
systems that get created will be registered as running or having been run
here.
'''
_SYS_VITALS = 'vitals'
'''A list of dicts of info about a system's vital records: creation, etc...'''

_DATA = 'data'
'''Game data like character saves, system definitions, character definitions,
etc.'''


# ------------------------------
# Interface Stuff (IO)
# ------------------------------

_INTERFACE = 'interface'
'''Input, output, mediator, etc. root key.'''

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
        _REGISTRY: {},
        _GAME: {
            _SYSTEM: {
                _SYS_VITALS: [],
            },
            _DATA: {},
        },
        _INTERFACE: {
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
    REPO = 'repository'
    CODEC = 'codec'
    DATA_SYS = 'system'
    CONFIG = 'configuration'

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
            None,
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
    def config(klass: Type['config']) -> Nullable['Configuration']:
        '''
        Checks for a CONFIG link in config's spot in this context.
        '''
        ctx = klass._get()
        retval = ctx.get(klass.Link.CONFIG, Null())
        return retval

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
                None,
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
        Repo and Codec have to be created and want to register some data into
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
    def exception(klass:     Type['config'],
                  context:   'VerediContext',
                  source:    Optional[Exception],
                  msg:       Optional[str],
                  *args:     Any,
                  **kwargs:  Any) -> None:
        '''
        Calls log.exception() to raise a ConfigError with message built from
        msg, args, kwargs and with supplied context.

        Sets stack level one more than usual so that caller of this should be
        the stacktrace of the exception.
        '''
        return log.exception(
            source,
            ConfigError,
            msg, *args, **kwargs,
            context=context)
        # If we raised instead of returned, we could add an extra stacklevel to
        # get the log back to whoever called us...
        #    stacklevel=3)

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
    def get(klass: Type['registry']) -> Nullable[ContextMutableMap]:
        '''
        Get registry's sub-context from background context.
        '''
        global _REGISTRY
        return veredi.get().get(_REGISTRY, Null())


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
# System Namespace
# -------------------------------------------------------------------------

class SystemMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''
    @property
    def manager(klass: Type['system']) -> Nullable['Meeting']:
        '''
        Checks for the Meeting of Managers link in config's spot
        in this context.
        '''
        return klass.meeting

    @property
    def meeting(klass: Type['system']) -> Nullable['Meeting']:
        '''
        Checks for the Meeting of Managers link in config's spot
        in this context.
        '''
        ctx = klass._get()
        retval = ctx.get(klass.Link.MEETING, Null())
        return retval


class system(metaclass=SystemMeta):

    @enum.unique
    class Link(enum.Enum):
        MEETING = enum.auto()
        '''The Meeting of Managers'''

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
                   cycle: 'SystemLifeCycle') -> None:
        '''
        Add a system's life-cycle state change to the records.
        '''
        subctx = klass._get()
        vital_records = subctx.setdefault(_SYS_VITALS, [])
        entry = {
            'dotted': sys.dotted,
            'time': klass.manager.time.machine.stamp_to_str(),
            'cycle': cycle.name,
        }
        vital_records.append(entry)

    # -------------------------------------------------------------------------
    # Managers
    # -------------------------------------------------------------------------

    @classmethod
    def set_meeting(klass: Type['system'],
                    meeting: NullNoneOr['Meeting']) -> None:
        '''
        Sets our managers.
        '''
        ctx = klass._get()
        ctx[klass.Link.MEETING] = meeting

    # Provided by SystemMeta:
    # @classmethod
    # def manager(klass: Type['system']) -> Nullable['Meeting']:
    #     '''
    #     Checks for a CONFIG link in config's spot in this context.
    #     '''
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.MEETING, Null())
    #     return retval


# -----------------------------------------------------------------------------
# DATA!
# -----------------------------------------------------------------------------

class DataMeta(type):
    '''
    Metaclass shenanigans to make some read-only /class/ property.
    '''
    @property
    def path(klass: Type['data']) -> Nullable[pathlib.Path]:
        ctx = klass._get()
        retval = ctx.get(klass.Link.PATH, Null())
        return retval

    @property
    def repository(klass: Type['data']) -> Nullable['BaseRepository']:
        ctx = klass._get()
        retval = ctx.get(klass.Link.REPO, Null())
        return retval

    @property
    def codec(klass: Type['data']) -> Nullable['BaseCodec']:
        ctx = klass._get()
        retval = ctx.get(klass.Link.CODEC, Null())
        return retval


class data(metaclass=DataMeta):

    @enum.unique
    class Link(enum.Enum):
        PATH = enum.auto()
        '''A pathlib.Path to somewhere.'''

        REPO = enum.auto()
        '''
        A Repository for the Game Data. Should not be used - the
        DataSystem/RepositorySystem/etc should be used instead.
        '''

        CODEC = enum.auto()
        '''
        A Codec for the Game Data. Should not be used - the
        DataSystem/CodecSystem/etc should be used instead.
        '''

    @classmethod
    def _get(klass: Type['data']):
        '''
        Get data's sub-context from background context.
        '''
        global _DATA
        return game.get().get(_DATA, Null())

    @classmethod
    def set(klass: Type['data'],
            name:      Name,
            data:      ContextMap,
            ownership: Ownership) -> None:
        '''
        Someone wants to add to background's data context.

        Makes a deep copy of inputs if ownership wants.
        '''
        context = klass._get()
        if name is Name.REPO and 'path' in data:
            context[klass.Link.PATH] = data['path']

        _set(context, str(name), data, ownership)

    @classmethod
    def link_set(klass: Type['data'], link: Link, entry: Any) -> None:
        klass._get()[link] = entry

    @classmethod
    def link(klass: Type['data'], link: Link) -> None:
        return klass._get()[link]

    # Provided by DataMeta:
    # @classmethod
    # def path(klass: Type['data']) -> Nullable[pathlib.Path]:
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.PATH, Null())
    #     return retval

    # Provided by DataMeta:
    # @classmethod
    # def repository(klass: Type['data']) -> Nullable['BaseRepository']:
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.REPO, Null())
    #     return retval

    # Provided by DataMeta:
    # @classmethod
    # def codec(klass: Type['data']) -> Nullable['BaseCodec']:
    #     ctx = klass._get()
    #     retval = ctx.get(klass.Link.CODEC, Null())
    #     return retval


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
            'time': system.manager.time.machine.stamp_to_str(),
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
    def set(klass:       Type['mediator'],
            dotted_name: str,
            data:        NullNoneOr[ContextMap],
            ownership:   Ownership) -> None:
        '''
        Update mediator system's entry with `data`.
        '''
        ctx = klass._get()
        # Set data provided.
        _set(ctx, dotted_name, data, ownership)


# -------------------------------------------------------------------------
# Unit Testing
# -------------------------------------------------------------------------

class testing:
    '''
    Whatever's needed for unit/integration/functional tests.
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


# -------------------------------------------------------------------------
# To String
# -------------------------------------------------------------------------

# TODO [2020-06-23]: string, repr for this

def to_str() -> str:
    from veredi.logger import pretty
    return "Veredi Backgroud Context:\n" + pretty.indented(_CONTEXT)


def to_repr() -> str:
    return repr(_CONTEXT)


def __str__() -> str:
    return to_str()


def __repr__() -> str:
    return to_repr()
