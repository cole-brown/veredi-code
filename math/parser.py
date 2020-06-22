# coding: utf-8

'''
Parser interface for turning input strings into Veredi Math Trees.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, NewType, Protocol, Iterable
from abc import ABC, abstractmethod

from collections import deque
# If we need threading, switch to:
# from queue import Queue, LifoQueue
import enum


from veredi.logger import log
from veredi.base.context import VerediContext
from veredi.data.exceptions import ConfigError

from .exceptions import MathError

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


# ---
# Command Invocation Signature
# ---

class TreeWalkerPredicate(Protocol):
    '''
    Protocol class for defining what the MathTree.walk() function takes as its
    node filter predicate.

    It will keep/return nodes that the predicate returns True/Truthy for.
    '''

    def __call__(self, node: 'MathTree') -> bool:
        ...


@enum.unique
class NodeType(enum.Flag):
    '''
    Simpler and more flexable than checking instance types maybe?
    '''

    # ---
    # General Types
    # ---
    INVALID   = 0
    '''A leaf node in the tree.'''

    LEAF   = enum.auto()
    '''A leaf node in the tree.'''

    BRANCH = enum.auto()
    '''A branch node in the tree.'''

    # ---
    # Specific Types
    # ---
    VARIABLE = enum.auto()
    '''Variable parsed as a string.'''

    CONSTANT = enum.auto()
    '''Just some number.'''

    RANDOM   = enum.auto()
    '''Some node that will be a number after randomness happens. e.g. Dice.'''

    OPERATOR = enum.auto()
    '''Math operator like '+', '-', etc.'''

    FUNCTION = enum.auto()
    '''Math function like 'max()', 'min()', etc.'''

    def all(self, flag: 'NodeType'):
        '''Returns true if this NodeType has all the flags specified.'''
        return ((self & flag) == flag)

    def any(self, *flags: 'NodeType'):
        '''
        Returns true if this NodeType has any of the flags specified.
        Can still require multiple by OR'ing e.g.:
          type.any(NodeType.VARIABLE | NodeType.BRANCH, NodeType.CONSTANT)
        That will look for either a BRANCH that is a VARIABLE, or a CONSTANT.
        '''
        for each in flags:
            if self.all(each):
                return True
        return False


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

    _SET_VALUE_ALLOWED = (NodeType.VARIABLE, NodeType.RANDOM)

    def __init__(self, type, tags: VTags = None) -> None:
        self._value: Any = None
        # tags, traits, whatever
        self._tags:      VTags      = tags
        self._children:  'MathTree' = None
        self._node_type: 'NodeType' = type

    def __repr__(self) -> str:
        return str(self)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def type(self) -> Any:
        return self._node_type

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value):
        '''
        Set value if allowed by NodeType.
        Raise MathError if not allowed.
        '''
        if not self._node_type.any(*self._SET_VALUE_ALLOWED):
            msg = ("Node is not allowed to set value; wrong type. "
                   "type: {}, allowed: {}").format(self.type,
                                                   self._SET_VALUE_ALLOWED)
            error = AttributeError(msg)
            raise log.exception(error, None, msg)

        self._value = new_value

    @property
    def tags(self) -> VTags:
        return self._tags

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    @abstractmethod
    def eval(self) -> Any:
        '''
        Evaluate this tree node (roll dice, add children together, whatever).
        '''
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Tree Walker for variables.
    # -------------------------------------------------------------------------

    @staticmethod
    def _predicate_exists(node: 'MathTree') -> bool:
        '''
        Predicate for walk. Returns true if node is Truthy.
        '''
        return bool(node)

    @staticmethod
    def _predicate_variable_nodes(node: 'MathTree') -> bool:
        '''
        Predicate for walk. Returns true if node is Truthy.
        '''
        return bool(node) and node.type.all(NodeType.VARIABLE)

    @staticmethod
    def walk(root, predicate=None):
        '''
        Generator that walks the tree, yielding each node in
        depth-first manner.

        If `predicate` is supplied, it should be:
          predicate(node: MathTree) -> bool
        '''
        predicate = predicate or MathTree._predicate_exists
        visited = set()
        # FIFO queue of nodes to be procecssed still
        queue = [root]

        # LIFO stack of nodes that will be evaluated after processing step is
        # completed.
        nodes = deque()

        # ---
        # Walk tree from root for processing nodes into queue.
        # ---
        while queue:
            subtree = queue.pop()
            # Does this node look familiar? Should we bother with it?
            # (Are there even roll trees with loops or clones?)
            if id(subtree) in visited:
                continue

            # Process our subtree.
            # Allow all nodes in tree, regardless of type.
            nodes.append(subtree)
            visited.add(id(subtree))
            # But only delve down into the branches.
            if subtree._children:
                queue.extend(subtree._children)

        # ---
        # Depth-first yielding of the nodes we've walked.
        # ---
        seen = set()
        while nodes:
            each = nodes.pop()
            if id(each) not in seen:
                if predicate(each):
                    yield each
                seen.add(id(each))

    def each_var(self):
        '''
        Generator for walking variables in tree. Yields each variable node it
        comes across.
        '''
        return self.walk(self, self._predicate_variable_nodes)

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
