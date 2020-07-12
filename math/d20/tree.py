# coding: utf-8

'''
Tree base classes for a d20 roll tree.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, NewType, Protocol, Iterable

from functools import reduce

from veredi.base import random

from ..parser import MathTree, NodeType, VTags
from .const import FormatOptions


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base-most class for tree (leaves, branches, everything).
# -----------------------------------------------------------------------------

class Node(MathTree):
    '''Base-most class for tree (leaves, branches, everything).'''

    # Just using MathTree's __init__.

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    def eval(self):
        '''
        Evaluate this tree node (roll dice, add children together, whatever).
        '''
        self._eval()
        return self.value

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

    def __add__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot add; {str(self)} has a value of None.")

        if isinstance(other, Node):
            return self._value + other._value
        return self._value + other

    def __sub__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot subtract; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value - other._value
        return self._value - other

    def __mul__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot multiply; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value * other._value
        return self._value * other

    def __truediv__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot true-divide; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value / other._value
        return self._value / other

    def __floordiv__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot floor-divide; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value // other._value
        return self._value // other

    def __mod__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot modulo; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value % other._value
        return self._value % other

    def __pow__(self, other):
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

    def __lt__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot less-than; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value < other._value
        return self._value < other

    def __gt__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot greater-than; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value > other._value
        return self._value > other

    def __le__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot less-than-or-equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value <= other._value
        return self._value <= other

    def __ge__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot greater-than-or-equal; {str(self)} has "
                             "a value of None.")

        if isinstance(other, Node):
            return self._value >= other._value
        return self._value >= other

    def __eq__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value == other._value
        return self._value == other

    def __ne__(self, other):
        if self._value is None:
            raise ValueError(f"Cannot not-equal; {str(self)} has a "
                             "value of None.")

        if isinstance(other, Node):
            return self._value != other._value
        return self._value != other


# -----------------------------------------------------------------------------
# Leaves
# -----------------------------------------------------------------------------

class Leaf(Node):
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

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()

    def _pretty_name(self):
        return str(self)

    # -------------------------------------------------------------------------
    # Unary Operators
    # -------------------------------------------------------------------------

    def neg(self):
        '''
        Negate this leaf (i.e. flip the sign).
        '''
        self._sign = self._sign * -1

    def pos(self):
        '''
        Do nothing to this leaf. (Unary '+' operator...)
        '''
        # self._sign = self._sign * 1
        pass

    # -------------------------------------------------------------------------
    # To Final Value
    # -------------------------------------------------------------------------
    def _eval(self):
        # TODO [2020-04-23]: make this an abstract base class and force
        # children to implement this
        pass


# -----------------------------------------------------------------------------
# Leaf Actuals
# -----------------------------------------------------------------------------

class Dice(Leaf):

    def __init__(self, dice, faces, tags=None):
        super().__init__(NodeType.RANDOM, name='dice', tags=tags)

        self.dice = dice
        self.faces = faces
        self.roll = None

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self.dice}d{self.faces}"
            f"{'=' + str(self.roll) if self.roll is not None else ''}"
            f"{'==' + str(self.value) if self.value is not None else ''}"
            f")"
        )

    def _eval(self):
        # Roll each die, record result.
        self.roll = []
        for i in range(self.dice):
            self.roll.append(random.randint(1, self.faces))

        # Save total as value.
        self._value = sum(self.roll)

    def _expr_str(self, options=None):
        '''String for this node's math expression representation.
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


class Constant(Leaf):

    def __init__(self, constant, tags=None):
        super().__init__(NodeType.CONSTANT,
                         value=constant,
                         name=constant,
                         tags=tags)

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self._value}"
            f")"
        )

    def _eval(self):
        # We already have our (constant) value and
        # nothing will (should?) change it.
        pass

    def _expr_str(self, options=None):
        '''String for this node's math expression representation.
        No context - just this node.

        '''
        if options is FormatOptions.NONE:
            return ''

        if self.value is None:
            return self.NULL_SIGN

        return str(self.value)


class Variable(Leaf):

    def __init__(self, var, milieu=None, tags=None):
        super().__init__(NodeType.VARIABLE,
                         milieu=milieu,
                         name=var,
                         tags=tags)

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"("
            f"{'-' if self._sign < 0 else ''}"
            f"{self.name}"
            f", '{self.milieu if self.milieu else ''}'"
            f")"
        )

    def _eval(self):
        '''
        Variable should have had its value replaced by whatever system or thing
        knows the value of its variable. So we have nothing to do for eval.
        '''
        pass

    def _expr_str(self, options=None):
        '''String for this node's math expression representation.
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


# -----------------------------------------------------------------------------
# Tree Node
# -----------------------------------------------------------------------------

class Branch(Node):
    def __init__(self, children, type, name, tags=None):
        super().__init__(NodeType.BRANCH | type,
                         children=children,
                         name=name,
                         tags=tags)

    @property
    def children(self):
        return self._children

    def __str__(self):
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

    def _pretty_name(self):
        return f"{self.__class__.__name__}"

    def _pretty(self, level, indent_str):
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

    def pretty(self, indent_str='- '):
        return ''.join(self._pretty(0, indent_str))

    def _eval(self):
        '''
        Branches probably have same evaluation: Do something to children and
        store accumulated result.
        '''
        self._value = reduce(self._act_on_children, self.children)


# -----------------------------------------------------------------------------
# Mathmatic Operations
# -----------------------------------------------------------------------------

class OperatorMath(Branch):
    '''Base class for math nodes.'''

    def __init__(self, children, operator, op_str, tags=None):
        super().__init__(children, NodeType.OPERATOR, op_str, tags)
        self.__operator = operator
        self.__operator_str = op_str

    def _act_on_children(self, left, right):
        return self.__operator(left, right)

    def _expr_str(self, options=None):
        '''String for this node's math expression representation.
        No context - just this node.

        '''
        if options is FormatOptions.NONE:
            return ''

        return self.__operator_str


class OperatorAdd(OperatorMath):
    STR_ASCII = '+'
    STR_UNICODE = '+'
    # STR_UNICODE = '\u002B'
    # STR_UNICODE = '\N{PLUS SIGN}'

    def __init__(self, children, tags=None):
        super().__init__(children,
                         self.__add_children,
                         OperatorAdd.STR_UNICODE,
                         tags)

    def __add_children(self, left, right):
        return left + right


class OperatorSub(OperatorMath):
    STR_ASCII = '-'
    STR_UNICODE = '−'
    # STR_UNICODE = '\u2212'
    # STR_UNICODE = '\N{MINUS SIGN}'

    def __init__(self, children, tags=None):
        super().__init__(children,
                         self.__sub_children,
                         OperatorSub.STR_UNICODE,
                         tags)

    def __sub_children(self, left, right):
        return left - right


class OperatorMult(OperatorMath):
    STR_ASCII = '*'
    STR_UNICODE = '×'
    # STR_UNICODE = '\u00D7'
    # STR_UNICODE = '\N{MULTIPLICATION SIGN}'

    def __init__(self, children, tags=None):
        super().__init__(children,
                         self.__mul_children,
                         OperatorMult.STR_UNICODE,
                         tags)

    def __mul_children(self, left, right):
        return left * right


class OperatorDiv(OperatorMath):
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

    def __init__(self, children, truediv=True, tags=None):
        div_fn = (self.__truediv_children
                  if truediv else
                  self.__floordiv_children)
        div_str = (self.STR_UNICODE_TRUE
                   if truediv else
                   self.STR_UNICODE_FLOOR)

        super().__init__(children,
                         div_fn,
                         div_str,
                         tags)

    def __truediv_children(self, left, right):
        '''"True" division aka float maths.'''
        return left / right

    def __floordiv_children(self, left, right):
        '''"Floor" division aka int maths.'''
        return left // right


class OperatorMod(OperatorMath):
    STR_ASCII = '%'
    STR_UNICODE = '%'  # Modulo doesn't have a math symbol...

    def __init__(self, children, tags=None):
        super().__init__(children,
                         self.__mod_children,
                         OperatorMod.STR_UNICODE,
                         tags)

    def __mod_children(self, left, right):
        return left % right


class OperatorPow(OperatorMath):
    STR_ASCII = '^'
    # It would be nice to super-script the 'power-of' component, but
    # that is complicated... maybe?
    STR_UNICODE = '^'

    def __init__(self, children, tags=None):
        super().__init__(children,
                         self.__pow_children,
                         OperatorPow.STR_UNICODE,
                         tags)

    def __pow_children(self, left, right):
        return left ** right
