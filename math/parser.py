# coding: utf-8

'''
Parser interface for turning input strings into Veredi Math Trees.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, NewType, Any, Iterable
from abc import ABC, abstractmethod

from veredi.logger import log
from veredi.base.context import VerediContext
from veredi.data.exceptions import ConfigError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

VTags = NewType('VTags', Optional[Iterable[str]])
'''
For tagging tree nodes and data with strings that mean nothing until they're
wanted, then only mean something in context.

E.g. 'fire':
  - On a damage amount, maybe it means that damage is the Fire Damage type.
  - On a light source, maybe it means that source should produce a
    medium/'campfire' amount of light.
  - On a skill roll, maybe it is meaningless and some buff added it
    because it didn't know and just in case.
'''


# -----------------------------------------------------------------------------
# Input String -> Veredi d20 Tree
# -----------------------------------------------------------------------------

class MathParser(ABC):
    '''
    Base MathParser interface.

    For getting from a string to some valid math tree.
    '''

    def __init__(self, context: VerediContext) -> None:
        '''
        Initialize from the context.

        Calls _configure(context) after verifying context exists.
        '''
        if not context:
            raise log.exception(
                None,
                ConfigError,
                'MathParser requires a context to create/configure '
                'its parsers.')

        self._configure(context)

    def _configure(self, context: VerediContext) -> None:
        '''
        This is where sub-classes should do any configuration from context, or
        just if they don't want to override __init__()...
        '''
        pass

    @abstractmethod
    def parse(self, string: str) -> Optional['MathTree']:
        '''
        Parse input `string` and return the resultant MathTree, or None if
        parsing/transforming failed at some point.
        '''
        raise NotImplementedError


# -----------------------------------------------------------------------------
# Veredi Math Operations in Tree Form
# -----------------------------------------------------------------------------

class MathTree(ABC):
    '''
    Base MathTree interface.

    This is a tree of maths. Rest of Veredi will use it to, for example, fill
    in parts of a roll command until MathTree can be evaluated and result
    returned.
    '''

    # NULL_SIGN = '\u2205'
    # NULL_SIGN = '\N{EMPTY SET}'
    NULL_SIGN = '∅'

    def __init__(self, tags: VTags = None) -> None:
        self._value: Any = None
        # tags, traits, whatever
        self._tags: VTags = tags

    def __repr__(self) -> str:
        return str(self)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def value(self) -> Any:
        return self._value

    # @value.setter
    # def value(self, new_value):
    #     self._value = new_value

    @property
    def tags(self) -> VTags:
        return self._tags

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    @abstractmethod
    def eval(self):
        '''
        Evaluate this tree node (roll dice, add children together, whatever).
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Single-Line Math/Roll Expression String
    # -------------------------------------------------------------------------

    def expr_str(self, options=None):
        '''
        String for this node's math expression representation. No context -
        just this node.
        '''
        return self._expr_str(options)

    # -------------------------------------------------------------------------
    # Maths
    # -------------------------------------------------------------------------

    @abstractmethod
    def __add__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __sub__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __mul__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __truediv__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __floordiv__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __mod__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __pow__(self, other):
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Comparisons
    # -------------------------------------------------------------------------

    @abstractmethod
    def __lt__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __gt__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __le__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __ge__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __ne__(self, other):
        raise NotImplementedError
