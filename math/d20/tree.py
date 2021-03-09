# coding: utf-8

'''
Tree base classes for a d20 roll tree.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING, Optional, Any, Dict, List)
if TYPE_CHECKING:
    import re

from abc import ABC, abstractmethod


from functools import reduce


from veredi.base       import random, numbers
from veredi.data.codec import (Codec,
                               Encodable,
                               EncodedComplex,
                               EncodedSimple)

from ..parser          import MathTree, NodeType, VTags
from .const            import FormatOptions


# TODO [2020-10-28]: Type hinting for this file.


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base-most class for tree (leaves, branches, everything).
# -----------------------------------------------------------------------------

class Node(MathTree, dotted=Encodable._DO_NOT_REGISTER):
    '''Base-most class for tree (leaves, branches, everything).'''

    # Just using MathTree's __init__ at the moment.

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    def eval(self) -> numbers.NumberTypes:
        '''
        Evaluate this tree node (roll dice, add children together, whatever).
        '''
        self._eval()
        return self.value

    # -------------------------------------------------------------------------
    # Single-Line Math/Roll Expression String
    # -------------------------------------------------------------------------

    def expr_str(self, options: FormatOptions = None) -> str:
        '''
        String for this node's math expression representation. No context -
        just this node.
        '''
        return self._expr_str(options)

    # -------------------------------------------------------------------------
    # Maths
    # -------------------------------------------------------------------------

    def __add__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Add nodes.
        '''
        if self._value is None:
            raise ValueError(f"Cannot add; {str(self)} has a value of None.")

        if isinstance(other, Node):
            return self._value + other._value
        return self._value + other

    def __sub__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Subtract nodes.
        '''
        if self._value is None:
            raise ValueError(f"Cannot subtract; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value - other._value
        return self._value - other

    def __mul__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Multiply nodes.
        '''
        if self._value is None:
            raise ValueError(f"Cannot multiply; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value * other._value
        return self._value * other

    def __truediv__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Divide nodes ("true"/float division).
        '''
        if self._value is None:
            raise ValueError(f"Cannot true-divide; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value / other._value
        return self._value / other

    def __floordiv__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Divide nodes ("floor"/int division).
        '''
        if self._value is None:
            raise ValueError(f"Cannot floor-divide; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value // other._value
        return self._value // other

    def __mod__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        Modulo nodes.
        '''
        if self._value is None:
            raise ValueError(f"Cannot modulo; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value % other._value
        return self._value % other

    def __pow__(self, other: 'Node') -> numbers.NumberTypes:
        '''
        By the power of nodes...
        '''
        if self._value is None:
            raise ValueError(f"Cannot power; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value ** other._value
        return self._value ** other

    # -------------------------------------------------------------------------
    # Comparisons
    # -------------------------------------------------------------------------

    # # TODO [2020-04-25]: May need to compare tags and such...

    def __lt__(self, other: 'Node') -> bool:
        '''
        "Less Than" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot less-than; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value < other._value
        return self._value < other

    def __gt__(self, other: 'Node') -> bool:
        '''
        "Greater Than" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot greater-than; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value > other._value
        return self._value > other

    def __le__(self, other: 'Node') -> bool:
        '''
        "Less Than Or Equal To" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot less-than-or-equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value <= other._value
        return self._value <= other

    def __ge__(self, other: 'Node') -> bool:
        '''
        "Greater Than Or Equal To" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot greater-than-or-equal; {str(self)} has "
                             "a value of None.")

        if isinstance(other, Node):
            return self._value >= other._value
        return self._value >= other

    def __eq__(self, other: 'Node') -> bool:
        '''
        "Equal To" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value == other._value
        return self._value == other

    def __ne__(self, other: 'Node') -> bool:
        '''
        "Not Equal To" boolean operator.
        '''
        if self._value is None:
            raise ValueError(f"Cannot not-equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value != other._value
        return self._value != other

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    def encode_simple(self, codec: 'Codec') -> EncodedSimple:
        '''
        Don't support simple by default.
        '''
        msg = (f"{self.__class__.__name__} doesn't support encoding to a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def decode_simple(klass: 'Encodable',
                      data:  EncodedSimple,
                      codec: 'Codec') -> 'Encodable':
        '''
        Don't support simple by default.
        '''
        msg = (f"{klass.__name__} doesn't support decoding from a "
               "simple string.")
        raise NotImplementedError(msg)

    @classmethod
    def _get_decode_str_rx(klass: 'Encodable') -> Optional[str]:
        '''
        We don't support simple encoding.
        '''
        return None

    @classmethod
    def _get_decode_rx(klass: 'Encodable') -> Optional['re.Pattern']:
        '''
        We don't support simple encoding.
        '''
        return None


# -----------------------------------------------------------------------------
# Leaves
# -----------------------------------------------------------------------------

class Leaf(Node, dotted=Encodable._DO_NOT_REGISTER):
    '''Leaf node of parsed tree. Dice, constants, vars, etc.'''

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------

    def __init__(self,
                 type:     'NodeType',
                 value:    Any                  = None,
                 milieu:   str                  = None,
                 name:     str                  = None,
                 tags:     VTags                = None) -> None:
        super().__init__(NodeType.LEAF | type,
                         value=value,
                         milieu=milieu,
                         children=None,
                         name=name,
                         tags=tags)

        # 1 == positive, -1 == negative
        self._sign = 1

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python's str() function.
        '''
        return self.__class__.__name__

    def __repr__(self) -> str:
        '''
        Python's repr() function.
        '''
        return self.__str__()

    def _pretty_name(self) -> str:
        '''
        A pretty string name for this.
        '''
        return str(self)

    # -------------------------------------------------------------------------
    # Unary Operators
    # -------------------------------------------------------------------------

    def neg(self) -> None:
        '''
        Negate this leaf (i.e. flip the sign).
        '''
        self._sign = self._sign * -1

    def pos(self) -> None:
        '''
        Do nothing to this leaf. (Unary '+' operator...)
        '''
        # self._sign = self._sign * 1
        pass


# -----------------------------------------------------------------------------
# Leaf Actuals
# -----------------------------------------------------------------------------

class Dice(Leaf, dotted='veredi.math.d20.tree.dice'):

    _NAME = 'dice'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 dice: int,
                 faces: int,
                 tags: Dict[str, str] = None) -> None:
        super().__init__(NodeType.RANDOM, name='dice', tags=tags)

        self.dice = dice
        self.faces = faces
        self.roll = None

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python's str() function.
        '''
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self.dice}d{self.faces}"
            f"{'=' + str(self.roll) if self.roll is not None else ''}"
            f"{'==' + str(self.value) if self.value is not None else ''}"
            f")"
        )

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _eval(self) -> None:
        '''
        Internal method for evaluating this dice node (roll dice, sum result)
        and saving results internally.
        '''
        # Roll each die, record result.
        self.roll = []
        for i in range(self.dice):
            self.roll.append(random.randint(1, self.faces))

        # Save total as value.
        self._value = sum(self.roll)

    def _expr_str(self, options: FormatOptions = None) -> str:
        '''
        String for this node's math expression representation.
        No context - just this node.
        '''
        if options is FormatOptions.NONE:
            return ''

        output = []
        d20_fmt = options.any(FormatOptions.INITIAL)
        if d20_fmt:
            if self.dice == 0:
                output.append(f'd{self.faces}')
            else:
                output.append(f'{self.dice}d{self.faces}')

        roll_fmt = options.any(FormatOptions.INTERMEDIATE)
        if roll_fmt:
            if d20_fmt:
                output.append("=")
            if self.roll is None:
                output.append(self.NULL_SIGN)
            else:
                output.append(str(self.roll))

        total_fmt = options.any(FormatOptions.FINAL)
        if total_fmt:
            if roll_fmt:
                output.append("=")
            if self.value is None:
                output.append(self.NULL_SIGN)
            else:
                output.append(str(self.value))

        str_out = ''.join(output)
        if len(output) > 1:
            return '(' + str_out + ')'

        return str_out

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'Dice') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # Add our specific Dice data.
        enc_data['dice']  = self.dice
        enc_data['faces'] = self.faces
        enc_data['roll']  = self.roll

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'Dice',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'Dice':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data.
        num_dice = data['dice']
        faces = data['faces']
        roll = data.get('roll', None)

        # And build our instance from the data.
        dice = Dice(num_dice, faces)
        dice.roll = roll

        # Finish building by having our parents do their things.
        klass._decode_super(dice, data)

        return dice


class Constant(Leaf, dotted='veredi.math.d20.tree.constant'):

    _NAME = 'constant'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 constant: numbers.NumberTypes,
                 tags: Dict[str, str] = None) -> None:
        super().__init__(NodeType.CONSTANT,
                         value=constant,
                         name=constant,
                         tags=tags)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python's str() function.
        '''
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self._value}"
            f")"
        )

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _eval(self):
        '''
        Internal method for evaluating this Constant node.
        Constants are constant, so no-op.
        '''
        # We already have our (constant) value and
        # nothing will (should?) change it.
        pass

    def _expr_str(self, options: FormatOptions = None) -> str:
        '''
        String for this node's math expression representation.
        No context - just this node.
        '''
        if options is FormatOptions.NONE:
            return ''

        if self.value is None:
            return self.NULL_SIGN

        return str(self.value)

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'Constant') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # And... we have nothing to add.

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'Constant',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'Constant':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have nothing.

        # And build our instance from the data.
        constant = Constant(None)

        # Finish building by having our parents do their things.
        klass._decode_super(constant, data)

        return constant


class Variable(Leaf, dotted='veredi.math.d20.tree.variable'):

    _NAME = 'variable'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 var: str,
                 milieu: str = None,
                 tags: Dict[str, str] = None):
        super().__init__(NodeType.VARIABLE,
                         milieu=milieu,
                         name=var,
                         tags=tags)

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python's str() function.
        '''
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self.name}"
            f", '{self.milieu if self.milieu else ''}'"
            f")"
        )

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _eval(self) -> None:
        '''
        Variable should have had its value replaced by whatever system or thing
        knows the value of its variable. So we have nothing to do for eval.
        '''
        pass

    def _expr_str(self, options: FormatOptions = None) -> str:
        '''
        String for this node's math expression representation.
        No context - just this node.
        '''
        if options is FormatOptions.NONE:
            return ''

        output = []
        name_fmt = options.any(FormatOptions.INITIAL,
                               FormatOptions.INTERMEDIATE)
        if name_fmt:
            if not self.name:
                output.append(self.NULL_SIGN)
            else:
                # §-TODO-§ [2020-04-27]: 'proper name' instead of input name
                output.append(f'${self.name}')

        total_fmt = options.any(FormatOptions.FINAL)
        if total_fmt:
            if name_fmt:
                output.append("=")
            if self.value is None:
                output.append(self.NULL_SIGN)
            else:
                output.append(str(self.value))

        str_out = ''.join(output)
        if len(output) > 1:
            return '(' + str_out + ')'

        return str_out

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'Variable') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # And... we have nothing to add.

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'Variable',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'Variable':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have nothing.

        # And build our instance from the data.
        variable = Variable(None)

        # Finish building by having our parents do their things.
        klass._decode_super(variable, data)

        return variable


# -----------------------------------------------------------------------------
# Tree Node
# -----------------------------------------------------------------------------

class Branch(Node, ABC, dotted=Encodable._DO_NOT_REGISTER):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 children: List['Node'],
                 type: NodeType,
                 name: str,
                 tags: Dict[str, str] = None):
        super().__init__(NodeType.BRANCH | type,
                         children=children,
                         name=name,
                         tags=tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    @abstractmethod
    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        Do whatever it is the branch should do with its children.
        E.g.: OperatorAdd should add them all together.

        Returns some sort of number... int/float/etc.
        '''
        raise NotImplementedError(
            f"{self.__class__.__name__}._evaluate_children() "
            "is not implemented.")

    @property
    def children(self) -> List['Node']:
        return self._children

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python's str() function.
        '''
        if not self.children:
            raise ValueError(f"Branch class {self.__class__.__name__} has no "
                             f"children?! children: {self._children}", self)

        out = [f"{self.__class__.__name__}",
               "("]
        first = True
        for each in self.children:
            if not first:
                out.append(", ")
            out.append(str(each))
            first = False

        out.append(")")
        if self.value is not None:
            out.append("==")
            out.append(str(self.value))
        return ''.join(out)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _pretty_name(self) -> str:
        '''
        A pretty string name for this.
        '''
        return f"{self.__class__.__name__}"

    def _pretty(self, level: int, indent_str: str) -> str:
        '''
        Returns a line of str fragments to concat into one pretty branch line
        output.
        '''
        # Leaf or junk in our tree. Just print it.
        if (len(self.children) == 1
                and not isinstance(self.children[0], Branch)):
            return [indent_str * level, self._pretty_name(), '\n']

        # Else print me then my children.
        lines = [indent_str * level, self._pretty_name(), '\n']
        for each in self.children:
            if isinstance(each, Branch):
                # Recurse down to this branch.
                lines += each._pretty(level + 1, indent_str)
            else:
                # Print non-branch child at level + 1; don't recurse into it.
                name = None
                try:
                    name = each._pretty_name()
                except AttributeError:
                    name = str(each)

                lines += [indent_str * (level + 1), name, '\n']

        return lines

    def pretty(self, indent_str: str = '- ') -> str:
        return ''.join(self._pretty(0, indent_str))

    def _eval(self) -> None:
        '''
        Branches probably have same evaluation: Do something to children and
        store accumulated result.
        '''
        self._value = reduce(self._evaluate_children, self.children)


# -----------------------------------------------------------------------------
# Mathmatic Operations
# -----------------------------------------------------------------------------

class OperatorMath(Branch, dotted=Encodable._DO_NOT_REGISTER):
    '''Base class for math nodes.'''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 children: List['Node'],
                 op_str: str,
                 tags: Dict[str, str] = None):
        super().__init__(children, NodeType.OPERATOR, op_str, tags)
        self.__operator_str = op_str

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _expr_str(self, options: FormatOptions = None) -> str:
        '''
        String for this node's math expression representation.
        No context - just this node.
        '''
        if options is FormatOptions.NONE:
            return ''

        return self.__operator_str


class OperatorAdd(OperatorMath, dotted='veredi.math.d20.tree.add'):
    STR_ASCII = '+'
    STR_UNICODE = '+'
    # STR_UNICODE = '\u002B'
    # STR_UNICODE = '\N{PLUS SIGN}'

    _NAME = 'Add'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, children: List['Node'], tags: Dict[str, str] = None):
        super().__init__(children,
                         OperatorAdd.STR_UNICODE,
                         tags)

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorAdd will add these two children together.
        '''
        return left + right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorAdd') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorAdd',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorAdd':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        add = OperatorAdd(None)

        # Finish building by having our parents do their things.
        klass._decode_super(add, data)

        return add


class OperatorSub(OperatorMath, dotted='veredi.math.d20.tree.subtract'):
    STR_ASCII = '-'
    STR_UNICODE = '−'
    # STR_UNICODE = '\u2212'
    # STR_UNICODE = '\N{MINUS SIGN}'

    _NAME = 'subtract'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, children: List['Node'], tags: Dict[str, str] = None):
        super().__init__(children,
                         OperatorSub.STR_UNICODE,
                         tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorSub will subtract these two children.
        '''
        return left - right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorSub') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorSub',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorSub':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        sub = OperatorSub(None)

        # Finish building by having our parents do their things.
        klass._decode_super(sub, data)

        return sub


class OperatorMult(OperatorMath, dotted='veredi.math.d20.tree.multiply'):
    STR_ASCII = '*'
    STR_UNICODE = '×'
    # STR_UNICODE = '\u00D7'
    # STR_UNICODE = '\N{MULTIPLICATION SIGN}'

    _NAME = 'multiply'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, children: List['Node'], tags: Dict[str, str] = None):
        super().__init__(children,
                         OperatorMult.STR_UNICODE,
                         tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorMult will multiply these two children.
        '''
        return left * right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorMult') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorMult',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorMult':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        mult = OperatorMult(None)

        # Finish building by having our parents do their things.
        klass._decode_super(mult, data)

        return mult


class OperatorDiv(OperatorMath, dotted='veredi.math.d20.tree.divide'):
    '''
    Covers both truediv (float math) and floor div (int math) operators.
    '''

    # ---
    # True Div
    # ---
    STR_ASCII_TRUE = '/'
    STR_UNICODE_TRUE = '÷'
    # STR_UNICODE = '\u00F7'
    # STR_UNICODE = '\N{DIVISION SIGN}'

    # ---
    # Floor Div
    # ---
    STR_ASCII_FLOOR = '//'
    STR_UNICODE_FLOOR = '÷÷'

    _NAME = 'divide'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 children: List['Node'],
                 truediv: bool = True,
                 tags: Dict[str, str] = None):
        self.truediv = truediv
        div_str = (self.STR_UNICODE_TRUE
                   if truediv else
                   self.STR_UNICODE_FLOOR)

        super().__init__(children,
                         div_str,
                         tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorDiv will divide these two children. It will either use 'true'
        (float) division or 'floor' (int) division, based on self.truediv flag.
        '''
        if self.truediv:
            # True/float division.
            return left / right
        # Else floor/int division.
        return left // right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorDiv') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorDiv',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorDiv':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        div = OperatorDiv(None)

        # Finish building by having our parents do their things.
        klass._decode_super(div, data)

        return div


class OperatorMod(OperatorMath, dotted='veredi.math.d20.tree.modulo'):
    STR_ASCII = '%'
    STR_UNICODE = '%'  # Modulo doesn't have a math symbol...

    _NAME = 'modulo'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, children: List['Node'], tags: Dict[str, str] = None):
        super().__init__(children,
                         OperatorMod.STR_UNICODE,
                         tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorMod will modulo these two children.
        '''
        return left % right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorMod') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorMod',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorMod':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        mod = OperatorMod(None)

        # Finish building by having our parents do their things.
        klass._decode_super(mod, data)

        return mod


class OperatorPow(OperatorMath, dotted='veredi.math.d20.tree.power'):
    STR_ASCII = '^'
    # It would be nice to super-script the 'power-of' component, but
    # that is complicated... maybe?
    STR_UNICODE = '^'

    _NAME = 'power'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self, children: List['Node'], tags: Dict[str, str] = None):
        super().__init__(children,
                         OperatorPow.STR_UNICODE,
                         tags)

    # -------------------------------------------------------------------------
    # Node Functions
    # -------------------------------------------------------------------------

    def _evaluate_children(self,
                           left: 'Node',
                           right: 'Node') -> numbers.NumberTypes:
        '''
        OperatorPow will return `left` to the power of `right`.
        '''
        return left ** right

    # -------------------------------------------------------------------------
    # Encodable
    # -------------------------------------------------------------------------

    @classmethod
    def type_field(klass: 'OperatorPow') -> str:
        '''Encodable type name.'''
        return klass._NAME

    def encode_complex(self, codec: 'Codec') -> EncodedComplex:
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        # Get our parents to do their work.
        enc_data = super().encode_complex()

        # We don't have anything...

        # Done
        return enc_data

    @classmethod
    def decode_complex(klass: 'OperatorPow',
                       data:  EncodedComplex,
                       codec: 'Codec') -> 'OperatorPow':
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        # Get our stuff from the data. We have none.

        # And build our instance from the data.
        pow = OperatorPow(None)

        # Finish building by having our parents do their things.
        klass._decode_super(pow, data)

        return pow
