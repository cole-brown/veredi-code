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

import lark  # Lark, Transformer, Visitor, v_args

from veredi.logger               import log
from veredi.data.config.registry import register

from ..parser                    import MathParser, MathTree

from .                           import tree

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# EBNF Grammar
# -----------------------------------------------------------------------------

grammar = '''
// Lark needs either start node in grammar or explicit start in costructor.
?start: sum
      | NAME_LAX "=" sum            -> assign_var

// ---
// Maths
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

// ---
// Funcs & Vars
// Function is func name and list of params (one or more).
func: NAME_FUNC "(" [sum ("," sum)*] ")"

var: "$" NAME_STRICT
   | "${" NAME_LAX "}"

// ---
// Alias out to die/dice instead of optional amount.
// Lets me know more explicitly which is which.
?roll: ("d"|"D") INT            -> die
     | INT ("d"|"D") INT        -> dice

// ---
// Names:
//  - Strict can exist more on their own.
//  - Lark's CNAMEs are used for functions (allows names like C functions).
//  - Lax Names have to be folded into another something (e.g. ${a-b})

NAME_LAX: LETTER (LETTER | DIGIT | " " | ":" | "(" | "_" | "-")* (LETTER | ")")

NAME_STRICT: WORD

NAME_FUNC: CNAME


// ---
// Lark imports and ignores
%import common.LETTER
%import common.DIGIT
%import common.WORD
%import common.CNAME
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


# -----------------------------------------------------------------------------
# Input String -> Veredi d20 Tree
# -----------------------------------------------------------------------------

@register('veredi', 'math', 'd20', 'parser')
class D20Parser(MathParser):
    '''
    MathParser interface implementation. Wraps up the lark parsing and
    tranformation operations for getting from a string to some valid d20 math
    tree.
    '''

    # Nothing to do for __init__/_configure. We don't even need an instance of
    # ourselves to do anything right now, though that could change.

    def parse(self, string: str) -> MathTree:
        '''
        Parse input `string` and return the resultant MathTree, or None if
        parsing/transforming failed at some point.
        '''
        log.debug("parse input: '{}'", string)

        syntax_tree = Parser.parse(string)
        log.debug("Parser (lark) output: \n{}",
                  Parser.format(syntax_tree))

        # §-TODO-§ [2020-06-13]: Do we want transformer to hold onto vars
        # like it does or try to make a static class like Parser?

        # Make a new transformer for each parse run as it holds on to
        # var names?
        xform = Transformer()
        math_tree = xform.transform(syntax_tree)
        log.debug("Math Tree: \n{}",
                  math_tree.pretty())

        # Return parsed, transformed, un-evaluated math tree.
        return math_tree


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
