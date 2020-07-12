# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type)
from veredi.base.null import Nullable
if TYPE_CHECKING:
    from veredi.base.identity import MonotonicId

import enum

from veredi.data         import background
from veredi.base.context import (VerediContext,
                                 EphemerealContext)

from .parse              import Parcel, Mather
from .identity           import InputId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Link(enum.Enum):
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

    SOURCE_DESIGNATION = enum.auto()
    '''
    A display name from the input event's source.

    For when entity exists when command tries to execute, but a required
    component is absent.
      "Couldn't find either 'Display Name' or their data."
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
class InputContext(EphemerealContext):
    '''
    Input EphemerealContext for a specific user input with some input &
    command-specific things in very specific places.
    '''
    KEY  = 'input'

    def __init__(self,
                 input_id:           InputId,
                 full_input_safe:    str,
                 source_id:          'MonotonicId',
                 source_designation: str,
                 dotted:             str,
                 key:                Optional[str] = None) -> None:
        key = key or self.KEY
        super().__init__(dotted, key)

        # Init our input str into place.
        self._set_input(input_id, full_input_safe, source_id)
        self._set_names(source_designation)

    def _set_input(self,
                   input_id: InputId,
                   input_safe: str,
                   source_id: 'MonotonicId') -> None:
        '''
        Set input str into `context` where InputContext wants it.
        '''
        input_ctx = self._get().get(self.KEY, {})
        input_ctx[Link.INPUT_ID] = input_id
        input_ctx[Link.INPUT_SAFE] = input_safe
        input_ctx[Link.SOURCE_ID] = source_id

    def _set_names(self,
                   source_designation: str) -> None:
        '''
        Set any names we're give into our context data.
        '''
        input_ctx = self._get().get(self.KEY, {})
        input_ctx[Link.SOURCE_DESIGNATION] = source_designation

    # -------------------------------------------------------------------------
    # Input/Command-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def input_id(klass: Type['InputContext'],
                 context: VerediContext) -> Optional[InputId]:
        '''
        Checks for & returns our Input ID or InputId.INVALID.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_id = input_ctx.get(Link.INPUT_ID, InputId.INVALID)
        return input_id

    @classmethod
    def source_designation(klass: Type['InputContext'],
                           context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns our Input ID or InputId.INVALID.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        designation = input_ctx.get(Link.SOURCE_DESIGNATION, None)
        return designation

    @classmethod
    def source_id(klass: Type['InputContext'],
                  context: VerediContext) -> Union[int, 'MonotonicId']:
        '''
        If there is a source id (EntityId, whatever), get it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        ident = input_ctx.get(Link.SOURCE_ID, None)
        return ident

    @classmethod
    def type(klass: Type['InputContext'],
             context: VerediContext) -> Union[int, enum.Enum]:
        '''
        If there is a type id, get it.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        type_id = input_ctx.get(Link.TYPE, None)
        return type_id

    @classmethod
    def input(klass: Type['InputContext'],
              context: VerediContext) -> Optional[str]:
        '''
        Checks for & returns our input string or None.
        '''
        input_ctx = context._get().get(klass.KEY, {})
        input_id = input_ctx.get(Link.INPUT_SAFE, None)
        return input_id

    # -------------------------------------------------------------------------
    # Input Parsing
    # -------------------------------------------------------------------------

    @classmethod
    def parsers(klass: Type['InputContext'],
                context: VerediContext) -> Nullable[Parcel]:
        '''
        Checks for & returns parsers Parcel object from background context, if
        there. Returns Null() if not there.
        '''
        return background.input.parsers

    @classmethod
    def math(klass: Type['InputContext'],
             context: VerediContext) -> Nullable[Mather]:
        '''
        If there is a parsers Parcel object, get the math parser from it.
        Returns math parser or Null().
        '''
        # Yay null cascading into itself all nice-like.
        return klass.parsers(context).math

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'InCtx'
