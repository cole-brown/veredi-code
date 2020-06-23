# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type)
if TYPE_CHECKING:
    from veredi.base.identity import MonotonicId
    from veredi.game.ecs.base.system import Meeting

import enum

from veredi.base.context import (VerediContext,
                                 EphemerealContext,
                                 PersistentContext)

from .parse import Parcel, Mather
from .identity import InputId

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Link(enum.Enum):
    PARSERS = enum.auto()
    '''The Parser object(s).'''

    # TODO [2020-06-21]- CONSTRUCTION ONLY?
    MEETING = enum.auto()
    '''The Meeting of Managers'''

    INPUT_SAFE = enum.auto()
    '''
    The full input string, after sanitizing/validating. Includes command
    name.
    '''

    INPUT_ID = enum.auto()
    '''
    An ID of some sort from whatever caused an InputEvent.
    E.g.: ComponentId, EntityId, SystemId
    '''

    SOURCE_ID = enum.auto()
    '''
    An ID of some sort from whatever caused an InputEvent.
    E.g.: ComponentId, EntityId, SystemId
    '''

    TYPE = enum.auto()
    '''
    A TypeId of some sortfrom whatever caused an InputEvent.
    '''

    # KEYCHAIN = enum.auto()
    # '''
    # Iterable of keys into something in the Configuration object that is
    # important to the receiver of a context, probably.
    # '''

    # PATH = enum.auto()
    # '''A pathlib.Path to somewhere.'''


# -----------------------------------------------------------------------------
# InputSystem's Ephemereal Context
#   - These are for each input event (command, message, whatever, etc...)
#   - Commander is InputSystem's sub-system for commands and uses this too.
# -----------------------------------------------------------------------------
class InputUserContext(EphemerealContext):
    '''
    Input EphemerealContext for a specific user input with some input &
    command-specific things in very specific places.
    '''
    # TODO: should we use different name or key than InputSystemContext?
    NAME = 'input'
    KEY  = 'input'

    def __init__(self,
                 name: str, key: str,
                 input_id: InputId, full_input_safe: str,
                 source_id: 'MonotonicId') -> None:
        super().__init__(name, key)

        # Init our input str into place.
        InputSystemContext._set_input(self,
                                      input_id, full_input_safe,
                                      source_id)

    # -------------------------------------------------------------------------
    # Input/Command-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def input_id(klass: Type['InputSystemContext'],
                 context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns our Input ID or InputId.INVALID.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_id = input_ctx.get(Link.INPUT_ID, InputId.INVALID)
        return input_id

    @classmethod
    def source_id(klass: Type['InputSystemContext'],
                  context: VerediContext) -> Union[int, 'MonotonicId']:
        '''
        If there is a source id (EntityId, whatever), get it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        ident = input_ctx.get(Link.SOURCE_ID, None)
        return ident

    @classmethod
    def type(klass: Type['InputSystemContext'],
             context: VerediContext) -> Union[int, enum.Enum]:
        '''
        If there is a type id, get it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        type_id = input_ctx.get(Link.TYPE, None)
        return type_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'InUsrCtx'


# -----------------------------------------------------------------------------
# InputSystem's Persistent Context
#   - This is for the input system's setup/config/etc.
#   - Commander is InputSystem's sub-system for commands and uses this too.
# -----------------------------------------------------------------------------

class InputSystemContext(PersistentContext):
    '''
    PersistentContext with some input & command-specific things in very
    specific places.
    '''

    NAME = 'input'
    KEY  = 'input'

    def __init__(self,
                 parsers: Parcel,
                 managers: 'Meeting',
                 name:    Optional[str] = None,
                 ) -> None:
        name = name or self.NAME
        super().__init__(name, self.KEY)

        # Make sure the path is a directory.
        self.add(Link.PARSERS, parsers)

        self.add(Link.MEETING, managers)

    # -------------------------------------------------------------------------
    # Spawn a Context for an Input Event
    # -------------------------------------------------------------------------

    def clone(self,
              input_id: InputId,
              full_input_safe: str,
              source_id: 'MonotonicId') -> InputUserContext:
        '''
        Make an InputUserContext for this specific `full_input_safe` user input
        that contains all the context of this InputSystemContext.
        '''
        return self.spawn(InputUserContext,
                          InputUserContext.NAME,
                          InputUserContext.KEY,
                          input_id,
                          full_input_safe,
                          source_id)

    # -------------------------------------------------------------------------
    # Sub-System Config Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def managers(klass: Type['InputSystemContext'],
                 context: VerediContext) -> Optional['Meeting']:
        '''
        Checks for & returns the TimeManager, if in the context.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        managers = input_ctx.get(Link.MEETING, None)
        return managers

    # -------------------------------------------------------------------------
    # Input/Command-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def _set_input(klass: Type['InputSystemContext'],
                   context: InputUserContext,
                   input_id: InputId,
                   input_safe: str,
                   source_id: 'MonotonicId') -> None:
        '''
        Set input str into `context` where InputSystemContext wants it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_ctx[Link.INPUT_ID] = input_id
        input_ctx[Link.INPUT_SAFE] = input_safe
        input_ctx[Link.SOURCE_ID] = source_id

    @classmethod
    def input(klass: Type['InputSystemContext'],
              context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns input string (sanitized/validated).
        Includes the command name.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_str = input_ctx.get(Link.INPUT_SAFE, None)
        return input_str

    @classmethod
    def input_id(klass: Type['InputSystemContext'],
                 context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns our Input ID or InputId.INVALID.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_id = input_ctx.get(Link.INPUT_ID, InputId.INVALID)
        return input_id

    # @classmethod
    # def source_id(klass: Type['InputSystemContext'],
    #               context: VerediContext) -> Union[int, 'MonotonicId']:
    #     '''
    #     If there is a source id (EntityId, whatever), get it.
    #     '''
    #     input_ctx = context._get().get(klass.KEY, {})
    #     ident = input_ctx.get(Link.SOURCE_ID, None)
    #     return ident

    # @classmethod
    # def type(klass: Type['InputSystemContext'],
    #          context: VerediContext) -> Union[int, enum.Enum]:
    #     '''
    #     If there is a type id, get it.
    #     '''
    #     input_ctx = context._get().get(klass.KEY, {})
    #     type_id = input_ctx.get(Link.TYPE, None)
    #     return type_id

    @classmethod
    def parsers(klass: Type['InputSystemContext'],
                context: VerediContext) -> Optional[Parcel]:
        '''
        Checks for & returns parsers Parcel object from context, if there.
        Returns None if not there.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        parcel = input_ctx.get(Link.PARSERS, None)
        return parcel

    @classmethod
    def math(klass: Type['InputSystemContext'],
             context: VerediContext) -> Optional[Mather]:
        '''
        If there is a parsers Parcel object, get the math parser from it.
        Returns math parser or None.
        '''
        parcel = klass.parsers(context)
        if not parcel:
            return None

        return parcel.math

    # @classmethod
    # def exception(klass:     Type['ConfigContext'],
    #               context:   VerediContext,
    #               source:    Optional[Exception],
    #               msg:       Optional[str],
    #               *args:     Any,
    #               **kwargs:  Any) -> None:
    #     '''
    #     Calls log.exception() to raise a ConfigError with message built from
    #     msg, args, kwargs and with supplied context.

    #     Sets stack level one more than usual so that caller of this should be
    #     the stacktrace of the exception.
    #     '''
    #     # An extra stacklevel should get us back to whoever called us...
    #     raise log.exception(
    #         source,
    #         ContextError,
    #         msg, *args, **kwargs,
    #         context=context,
    #         stacklevel=3)

    # # -------------------------------------------------------------------------
    # # Unit Testing
    # # -------------------------------------------------------------------------
    # def ut_inject(self,
    #               path:     Optional[pathlib.Path]    = None,
    #               config:   Optional['Configuration'] = None,
    #               keychain: Optional[Iterable[Any]]   = None) -> None:
    #     '''
    #     Unit testing.

    #     Inject any of these that are not None into their spot in the context.
    #     '''
    #     config_data = self._get().get(self.KEY, {})
    #     if path is not None:
    #         config_data[Link.PATH] = path
    #     if config is not None:
    #         config_data[Link.CONFIG] = config
    #     if keychain is not None:
    #         config_data[Link.KEYCHAIN] = keychain

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'InSysCtx'
