# coding: utf-8

'''
EBNF Grammar for Veredi's roll parser.

Some code used from Lark's calc example:
   https://github.com/lark-parser/lark/blob/master/examples/calc.py
'''

# TODO: pythonic logging

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Dice Grammer Parser
import lark  # Lark, Transformer, Visitor, v_args

# Veredi
from . import tree

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# EBNF Grammar
# -----------------------------------------------------------------------------

grammar = '''
// Lark needs either start node in grammar or explicit start in costructor.
?start: sum
      | NAME "=" sum            -> assign_var

// Lowest priority maths first.
?sum: product
      | sum "+" product         -> add
      | sum "-" product         -> sub

?product: factor
        | product "*" factor    -> mul
        | product "/" factor    -> div
        | product "%" factor    -> mod
        | product "^" factor    -> pow

?factor: primary
       | "-" factor             -> neg
       | "+" factor             -> pos

?primary: roll
        | var
        | INT                   -> int
        | NUMBER                -> number
        | "(" sum ")"
        | func

// function is func name and list of params (one or more)
func: NAME "(" [sum ("," sum)*] ")"

var: "$" NAME
   | "${" NAME "}"

// Alias out to die/dice instead of optional amount
// Lets me know more explicitly which is which.
?roll: ("d"|"D") INT            -> die
     | INT ("d"|"D") INT        -> dice

%import common.CNAME            -> NAME
%import common.ESCAPED_STRING   -> STRING
%import common.NUMBER
%import common.INT

%import common.WS_INLINE
%ignore WS_INLINE

'''


# -----------------------------------------------------------------------------
# Text -> Lark Tree
# -----------------------------------------------------------------------------

class Parser:
    # LALR parser doesn't like the ambiguity between INTs and dice... It thinks
    # that "1d12" is the number 1 and wtf is "d". I do not know enough
    # EBNF/LALR/whatever to fix it or know if it's possible to fix...
    #
    # Maybe this to fix ambiguity?
    # https://github.com/lark-parser/lark/blob/master/docs/grammar.md#priority
    parser = lark.Lark(grammar)

    @classmethod
    def parse(cls, text):
        return cls.parser.parse(text)

    @classmethod
    def format(cls, parsed):
        return parsed.pretty()


# -----------------------------------------------------------------------------
# Lark Tree -> Veredi d20 Tree
# -----------------------------------------------------------------------------

# v_args: inline=True:
#   Methods given *args instead of a list by Lark.
#   So I can do:
#     assign_var(self, name, value)
#   Instead of:
#     assign_vars(self, items)
# NOTE: Should not be used for large lists of args. But all of mine are just
# one or two items.
# @lark.v_args(inline=True)
class Transformer(lark.Transformer):
    '''Transforms a lexed/parsed tree into a Veredi roll tree.'''

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------

    def __init__(self):
        self.vars = {}

    # -------------------------------------------------------------------------
    # Leaves
    # -------------------------------------------------------------------------

    # Replace leaf nodes with their classes.

    # ---
    # Variables
    # ---
    @lark.v_args(inline=True)
    def assign_var(self, name, value):
        self.vars[name] = value

        return value

    @lark.v_args(inline=True)
    def var(self, name):
        # name is Token class
        if name in self.vars:
            return self.vars[name]

        return tree.Variable(name)

    # ---
    # Dice
    # ---
    @lark.v_args(inline=True)
    def die(self, faces):
        return tree.Dice(1, int(faces))

    @lark.v_args(inline=True)
    def dice(self, amount, faces):
        return tree.Dice(int(amount), int(faces))

    # ---
    # Constants
    # ---
    @lark.v_args(inline=True)
    def int(self, value):
        return tree.Constant(int(value))

    @lark.v_args(inline=True)
    def number(self, value):
        return tree.Constant(float(value))

    # -------------------------------------------------------------------------
    # Operators: Unary
    # -------------------------------------------------------------------------

    # Replace Unary nodes with their leaf (acted on by the unary operator).

    @lark.v_args(inline=True)
    def neg(self, value):
        value.neg()
        return value

    @lark.v_args(inline=True)
    def pos(self, value):
        value.pos()
        return value

    # -------------------------------------------------------------------------
    # Operators: Binary
    # -------------------------------------------------------------------------

    # Replace these branches with our branch nodes.

    def add(self, children):
        return tree.OperatorAdd(children)

    def sub(self, children):
        return tree.OperatorSub(children)

    def mul(self, children):
        return tree.OperatorMult(children)

    def div(self, children):
        return tree.OperatorDiv(children)

    def mod(self, children):
        return tree.OperatorMod(children)

    def pow(self, children):
        return tree.OperatorPow(children)


# -----------------------------------Veredi------------------------------------
# --                     Main Command Line Entry Point                       --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # text = "-d20 + 3d20 + 10 - 1 - 1d1"
    # parser = Lark(grammar, start='expression')
    # out = parser.parse(text)

    text = "-d20 + 3d20 + 10 - 1 - 1d1 + $hello"
    # text = "3d20"
    ast = Parser.parse(text)
    print("Lark input:\n   ", text)
    print("\nLark output:")
    print("   ", ast)
    print("\nLark output, pretty:")
    print(Parser.format(ast))

    xform = Transformer()
    roll_tree = xform.transform(ast)
    print("\nTransformed:")
    print(roll_tree)
    print("\nTransformed, pretty:")
    print(roll_tree.pretty())
