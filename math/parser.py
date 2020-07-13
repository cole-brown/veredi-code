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
from decimal import Decimal

from veredi.logger import log
from veredi.base.context import VerediContext
from veredi.base.enum import FlagCheckMixin


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

FINAL_VALUE_TYPES = (int, float, Decimal)
'''
These value types are considered final. If a math tree has a node that
evaluates out to not one of these, we can't actually reduce the tree down to a
final evaluated value.
'''


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
class NodeType(FlagCheckMixin, enum.Flag):
    '''
    Simpler and more flexable than checking instance types maybe?

    has() and any() provided by FlagCheckMixin.
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
        self._configure(context)

    def _configure(self, context: VerediContext) -> None:
        '''
        This is where sub-classes should do any configuration from context, or
        just if they don't want to override __init__()...
        '''
        ...

    @abstractmethod
    def parse(self,
              string: str,
              milieu: Optional[str] = None) -> Optional['MathTree']:
        '''
        Parse input `string` and return the resultant MathTree, or None if
        parsing/transforming failed at some point.

        Optional `milieu` string is a context in the event of any 'this'
        variables.
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
    _SET_NAME_ALLOWED = (NodeType.VARIABLE, )

    def __init__(self,
                 type:     'NodeType',
                 value:    Any                  = None,
                 milieu:   str                  = None,
                 children: Iterable['MathTree'] = None,
                 name:     str                  = None,
                 tags:     VTags                = None) -> None:
        '''
        Base init - optional values for things so children can subclass
        init easy?
        '''

        self._node_type: 'NodeType'           = type
        '''
        Type of math node - used by base classes for checks, mostly.
        This type enum is an enum.Flag class, so they can be combined.
        '''

        self._value:     Any                  = value or None
        '''Final value of math node - use node.value getter property.'''

        self._name:      str                  = name or None
        '''
        Name of node (variable name, math operator sign, etc).
        Use node.name getter property.
        '''

        self._milieu:    Optional[str]        = milieu or None
        '''"context" for value. See veredi.base.milieu module.'''

        self._children:  Iterable['MathTree'] = children or None
        '''Children node of this node for a branch-type node.'''

        self._tags:      VTags                = tags or None
        '''Tags, traits, whatever.'''

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def type(self) -> Any:
        return self._node_type

    @property
    def name_is_shortcut(self) -> bool:
        '''
        Returns true if name has a shortcut in it, like 'this'.
        '''
        # §-TODO-§ [2020-07-13]: 'name_is_alias'? 'name_is_canon'?
        return self._name.find('this') != -1

    @property
    def name(self) -> Any:
        return self._name

    @name.setter
    def name(self, new_name: Any) -> None:
        '''
        Set name if allowed by NodeType.
        Raise AttributeError if not allowed.
        '''
        if not self._node_type.any(*self._SET_NAME_ALLOWED):
            msg = ("Node is not allowed to set name; wrong type. "
                   "type: {}, allowed: {}").format(self.type,
                                                   self._SET_NAME_ALLOWED)
            error = AttributeError(msg)
            raise log.exception(error, None, msg)

        if self._name and not self.name_is_shortcut:
            msg = ("Node is not allowed to change name unless name has "
                   "'this' in it. current name: {}").format(self.name)
            error = ValueError(msg)
            raise log.exception(error, None, msg)

        self._name = new_name

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        '''
        Set value if allowed by NodeType.
        Raise AttributeError if not allowed.
        '''
        if not self._node_type.any(*self._SET_VALUE_ALLOWED):
            msg = ("Node is not allowed to set value; wrong type. "
                   "type: {}, allowed: {}").format(self.type,
                                                   self._SET_VALUE_ALLOWED)
            error = AttributeError(msg)
            raise log.exception(error, None, msg)

        self._value = new_value

    @property
    def milieu(self) -> Any:
        return self._milieu

    @milieu.setter
    def milieu(self, new_milieu: str) -> None:
        '''
        Set milieu if allowed by NodeType.
        Raise AttributeError if not allowed.
        '''
        if not self._node_type.any(*self._SET_VALUE_ALLOWED):
            msg = ("Node is not allowed to set milieu; wrong type. "
                   "type: {}, allowed: {}").format(self.type,
                                                   self._SET_VALUE_ALLOWED)
            error = AttributeError(msg)
            raise log.exception(error, None, msg)

        self._milieu = new_milieu

    @property
    def tags(self) -> VTags:
        return self._tags

    def set(self, new_value: Any, new_milieu: str) -> None:
        '''
        Set value and milieu if allowed by NodeType.
        Raise AttributeError if not allowed.
        '''
        # Let the setters do the sanity checking.
        self.value = new_value
        self.milieu = new_milieu
        if (isinstance(self.value, FINAL_VALUE_TYPES)
                and new_milieu
                and self.name_is_shortcut):
            self.name = new_milieu

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
    def _predicate_setting_allowed(node: 'MathTree') -> bool:
        '''
        True if `node` is allowed to set values.
        That is, if node's type is in `MathTree._SET_VALUE_ALLOWED`.
        '''
        return node.type in MathTree._SET_VALUE_ALLOWED

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
        return bool(node) and node.type.has(NodeType.VARIABLE)

    def walk(self, predicate=None):
        '''
        Generator that walks the tree, yielding each node in
        depth-first manner.

        If `predicate` is supplied, it should be:
          predicate(node: MathTree) -> bool
        '''
        predicate = predicate or MathTree._predicate_exists
        visited = set()
        # FIFO queue of nodes to be procecssed still
        queue = [self]

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
        return self.walk(self._predicate_variable_nodes)

    def replace(self,
                existing:    'MathTree',
                replacement: 'MathTree') -> bool:
        '''
        Find `existing` node in the tree and replace it with `replacement`.

        Returns True if found and replaced exisiting. False otherwise.
        '''
        replaced = False
        visited = set()
        # FIFO queue of nodes to be procecssed still
        queue = [self]

        # ---
        # Walk tree from root for processing nodes into queue.
        # ---
        while queue and not replaced:
            subtree = queue.pop()
            # Does this node look familiar? Should we bother with it?
            # (Are there even math trees with loops or clones?)
            if id(subtree) in visited:
                continue

            # Is this your guy's mom?
            if subtree._children:
                for i in range(len(subtree._children)):
                    if existing is not subtree._children[i]:
                        continue
                    # Found it! Replace it and done.
                    subtree._children[i] = replacement
                    replaced = True
                    break

            # Process our subtree.
            #   - Allow all nodes in tree, regardless of type.
            visited.add(id(subtree))
            #   - Delve down into any children.
            if subtree._children:
                queue.extend(subtree._children)

        return replaced

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

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    # def __str__(self):
    #     '''Too-basic to-string - sub-classes should overwrite.'''
    #     return str(self)

    # def __repr__(self) -> str:
    #     '''Too-basic to-repr-string - sub-classes should overwrite.'''
    #     return repr(self)
