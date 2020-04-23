'''
EBNF Grammar for Veredi's roll parser.

Some code used from Lark's calc example:
   https://github.com/lark-parser/lark/blob/master/examples/calc.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Dice Grammer Parser
from lark import Lark, Transformer, v_args

# Veredi


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# EBNF Grammar
# -----------------------------------------------------------------------------

grammar = '''

?start: sum
      | NAME "=" sum            -> assign_var

?sum: product
           | sum "+" product    -> add
           | sum "-" product    -> sub

?product: factor
     | product "*" factor       -> mul
     | product "/" factor       -> div
     | product "%" factor       -> mod

?factor: primary
       | "-" factor             -> neg
       | "+" factor             -> pos

?primary: roll
        | var
        | INT                   -> int
        | NUMBER                -> number
        | "(" sum ")"

var: "$" NAME
   | "${" NAME "}"

?roll: ("d"|"D") INT       -> die
     | INT ("d"|"D") INT   -> dice

%import common.CNAME            -> NAME
%import common.ESCAPED_STRING   -> STRING
%import common.NUMBER
%import common.INT

%import common.WS_INLINE
%ignore WS_INLINE

'''


# -----------------------------------------------------------------------------
# Parsed Tree to Roll Object?
# -----------------------------------------------------------------------------

class Leaf:
    # leaf node of parsed tree

    def __init__(self, tags):
        # tags, traits, whatever
        self.tags = tags

        # Parsed Value
        #  Examples:
        #    dice 2d10 == "2d10"
        #    int  10   == "10"
        self.value_initial = None

        # Parsed Value
        #  Examples:
        #    dice 2d10 == (8, 4)
        #    int  10   == 10
        self.value_raw     = None

        # Final Value
        #  Examples:
        #    dice 2d10 == (8, 4) == 14
        #    int  10   == 10
        self.value_total   = None


class Dice(Leaf):

    def __init__(self, dice, tags):
        super().__init__(tags)

        # Parsed Value
        #  Examples:
        #    dice 2d10 == "2d10"
        self.value_initial = dice


class Constant(Leaf):

    def __init__(self, constant, tags):
        super().__init__(tags)

        # Parsed Value
        #  Examples:
        #    int  10   == "10"
        self.value_initial = constant


class Variable(Leaf):

    def __init__(self, var, tags):
        super().__init__(tags)

        # Parsed Value
        #  Examples:
        #    var  str-mod   == "str-mod"
        self.value_initial = var


# @v_args(inline=True)  # Affects the signatures of the methods? *args instead of... whatever
class Calculator(Transformer):
    # # from operator import add, sub, mul, truediv as div, mod, neg
    # # Have to impl our own ops for our dice to be used in.

    # number = float
    # # int = int

    def __init__(self):
        self.vars = {}

    # --------------------------------------------------------------------------
    # Leaves
    # --------------------------------------------------------------------------

    # ---
    # Variables
    # ---
    def assign_var(self, items):
        print("assign_var:", items)
        # self.vars[name] = value
        # return value

    def var(self, items):
        print("var:", items)
        # return self.vars[name]

    # ---
    # Dice
    # ---
    def die(self, items):
        print("die:", items)

    def dice(self, items):
        print("dice:", items)

    # ---
    # Constants
    # ---
    def int(self, items):
        print("int:", items)

    def int(self, items):
        print("number:", items)

    # --------------------------------------------------------------------------
    # Operators: Unary
    # --------------------------------------------------------------------------

#            | sum "+" product    -> add
#            | sum "-" product    -> sub

    # --------------------------------------------------------------------------
    # Operators: Binary

    # --------------------------------------------------------------------------
#      | product "*" factor       -> mul
#      | product "/" factor       -> div
#      | product "%" factor       -> mod
#
#        | "-" factor             -> neg
#        | "+" factor             -> pos



# -----------------------------------------------------------------------------
# d20 Parser
# -----------------------------------------------------------------------------

class Parser:
    # LALR parser doesn't like the ambiguity between INTs and dice... It thinks
    # that "1d12" is the number 1 and wtf is "d". I do not know enough
    # EBNF/LALR/whatever to fix it or know if it's possible to fix...
    parser = Lark(grammar)

    @classmethod
    def parse(cls, text):
        return cls.parser.parse(text)

    @classmethod
    def format(cls, parsed):
        return parsed.pretty()


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # text = "-d20 + 3d20 + 10 - 1 - 1d1"
    # parser = Lark(grammar, start='expression')
    # out = parser.parse(text)

    text = "-d20 + 3d20 + 10 - 1 - 1d1 + $hello"
    # text = "3d20"
    roll = Parser.parse(text)
    pretty = Parser.format(roll)
    print("Lark input:\n   ", text)
    print("\nLark output:")
    print("   ", roll)
    print("\nLark output, pretty:")
    print(pretty)
    print("\nTransformed:")
    print(Calculator().transform(roll))
