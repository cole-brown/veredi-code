# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, Iterable)
# if TYPE_CHECKING:
#     from .config import Configuration

import enum
# import pathlib

from veredi.logger import log

from veredi.base.exceptions import ContextError
from veredi.base.context import (VerediContext,
                                 EphemerealContext,
                                 PersistentContext)

from .parse import Parcel, Mather


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


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

    def __init__(self, name: str, key: str, full_input_safe: str) -> None:
        super().__init__(name, key)

        # Init our input str into place.
        InputSystemContext._set_input(self, full_input_safe)


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

    @enum.unique
    class Link(enum.Enum):
        PARSERS = enum.auto()
        '''The Parser object(s).'''

        INPUT_SAFE = enum.auto()
        '''
        The full input string, after sanitizing/validating. Includes command
        name.
        '''

        # KEYCHAIN = enum.auto()
        # '''
        # Iterable of keys into something in the Configuration object that is
        # important to the receiver of a context, probably.
        # '''

        # PATH = enum.auto()
        # '''A pathlib.Path to somewhere.'''

    def __init__(self,
                 parsers: Parcel,
                 name:    Optional[str] = None,
                 ) -> None:
        name = name or self.NAME
        super().__init__(name, self.KEY)

        # Make sure the path is a directory.
        self.add(self.Link.PARSERS, parsers)

    # -------------------------------------------------------------------------
    # Spawn a Context for an Input Event
    # -------------------------------------------------------------------------

    def clone(self, full_input_safe):
        '''
        Make an InputUserContext for this specific `full_input_safe` user input
        that contains all the context of this InputSystemContext.
        '''
        return self.spawn(InputUserContext,
                          InputUserContext.NAME,
                          InputUserContext.KEY,
                          full_input_safe)

    # -------------------------------------------------------------------------
    # Input/Command-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def _set_input(klass: Type['InputSystemContext'],
                   context: InputUserContext,
                   input_safe: str) -> None:
        '''
        Set input str into `context` where InputSystemContext wants it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_ctx[klass.Link.INPUT_SAFE] = input_safe

    @classmethod
    def input(klass: Type['InputSystemContext'],
              context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns input string (sanitized/validated).
        Includes the command name.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_str = input_ctx.get(klass.Link.INPUT_SAFE, None)
        return input_str

    @classmethod
    def parsers(klass: Type['InputSystemContext'],
                context: VerediContext) -> Optional[Parcel]:
        '''
        Checks for & returns parsers Parcel object from context, if there.
        Returns None if not there.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        parcel = input_ctx.get(klass.Link.PARSERS, None)
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
    #         config_data[self.Link.PATH] = path
    #     if config is not None:
    #         config_data[self.Link.CONFIG] = config
    #     if keychain is not None:
    #         config_data[self.Link.KEYCHAIN] = keychain

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'InCtx'
