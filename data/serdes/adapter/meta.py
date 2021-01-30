# coding: utf-8

'''
Veredi's Adapter classes for interfacing specific serdes backends to
Veredi systems.

E.g. the YAML tag '!grouped' should have a Veredi class to be its face. So when
a DB or JSON comes along they can just implement to the same thing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Tuple
from collections import abc
import enum

from veredi.base.string import text


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-06-26]: Do I need this whole hashable thing? Don't think so?
_MM_HASH = 'MetaTag'


@enum.unique
class MetaType(enum.Enum):
    '''
    Could be Flag Enum if that makes sense. Normal Enum for now.
    '''

    INVALID = 0
    '''Bad.'''

    USER_DEFINED = enum.auto()
    '''User can do things; be very careful.'''

    @classmethod
    def from_str(klass: 'MetaType', string: str) -> 'MetaType':
        '''Either returns a valid value or throws a KeyError.'''
        string = text.normalize(string)
        retval = klass.INVALID
        if string == 'user.defined':
            retval = klass.USER_DEFINED

        return retval


# -----------------------------------------------------------------------------
# Keys
# -----------------------------------------------------------------------------

# ---
# Grouping
# ---

class MetaMarker(abc.Hashable):
    '''
    Used for marking some metadata in the saved data. E.g. this from the
    SkillSystem's definition file:

      !grouped craft:
        !meta user.defined: allow
        !user.defined <name>:
          display-name: !user.defined "Craft (<NAME>)"
          class: false
          ranks: 0

    The '!meta' YAML tag should get turned into a MetaMarker, which should
    allow SkillSystem to know that 'craft' skills are allowed to have any old
    weird user defined name.
    '''

    _ALLOWED_TAGS = frozenset(('user.defined', ))

    def __init__(self, value: str) -> None:
        value = value.lower()
        if value not in self._ALLOWED_TAGS:
            raise ValueError(f"!meta tag '{value}' is not a known meta "
                             "tag value. Allowed are: {self._ALLOWED_TAGS}")

        self._name: str = value
        self._hash: Tuple[str, str] = (_MM_HASH, self._name)
        self._type: 'MetaType' = MetaType.from_str(value)

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    # ---
    # Hashable / Dict/Set Key Interface
    # ---

    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare KeyGroupMarkers to
        KeyGroups and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name})")

    def __repr__(self) -> str:
        return (f"<{type(self).__name__}({self._name})>")
