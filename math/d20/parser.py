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

from typing import (Optional, Any, Type, NewType, Protocol,
                    Iterable, MutableMapping)

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
        | product "/" factor    -> truediv
        | product "//" factor   -> floordiv
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
//  - Lax Names have to be folded into another something (e.g. ${a-b})
//  - Lark's CNAMEs are used for functions (allows names like C functions).
//  - Strict can exist more on their own. So they need to not be
//    confusable with math. But I do need/want period for dotted names.

NAME_LAX: LETTER (LETTER | DIGIT | "." | " " | ":" | "(" | "_" | "-")* (LETTER | ")")

NAME_STRICT: LETTER (LETTER | DIGIT | "." | "_")* (LETTER | DIGIT)

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
    def parse(klass: Type['Parser'], text: str) -> tree.Node:
        '''
        Parse input `text` using Lark EBNF grammar. Fill in resultant tree with
        milieu and return the tree.
        '''
        root = klass.parser.parse(text)
        return root

    @classmethod
    def format(klass: Type['Parser'], parsed: lark.Tree) -> tree.Node:
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
#       one or two items.
# NOTE: Don't do at class level. We want some to be broken out for us and some
#       not, so use the v_args decorator on a per-function basis.
# @lark.v_args(inline=True)
class Transformer(lark.Transformer):
    '''
    Transforms a lexed/parsed tree into a Veredi roll tree.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        '''
        Define our vars, but don't assign them. They'll be set in `set_up()`
        for each transform.
        '''

        self.vars: MutableMapping[lark.Token, tree.Node] = None
        '''
        A collection to hold the name & value of any variables declared in the
        tree.
        '''

        self.milieu: str = None
        '''
        A string to insert into the `milieu` of any tree.Variable returned.
        '''

    def set_up(self,
               vars:   MutableMapping[lark.Token, tree.Node],
               milieu: str) -> None:
        '''
        Sets our vars dict and stuff and things
        '''
        self.vars = vars
        self.milieu = milieu

    # -------------------------------------------------------------------------
    # Leaves
    # -------------------------------------------------------------------------

    # Replace leaf nodes with their classes.

    # ---
    # Variables
    # ---
    @lark.v_args(inline=True)
    def assign_var(self, name: lark.Token, value: tree.Node) -> tree.Node:
        # 'name' is Token class is str class.
        # Get just the str.
        name = str(name)
        self.vars[name] = value

        return value

    @lark.v_args(inline=True)
    def var(self, name: lark.Token) -> tree.Variable:
        # 'name' is Token class is str class.
        # Get just the str.
        name = str(name)
        if name in self.vars:
            return self.vars[name]

        return tree.Variable(name, self.milieu)

    # ---
    # Dice
    # ---
    @lark.v_args(inline=True)
    def die(self, faces: str) -> tree.Dice:
        return tree.Dice(1, int(faces))

    @lark.v_args(inline=True)
    def dice(self, amount: str, faces: str) -> tree.Dice:
        return tree.Dice(int(amount), int(faces))

    # ---
    # Constants
    # ---
    @lark.v_args(inline=True)
    def int(self, value: str) -> tree.Constant:
        return tree.Constant(int(value))

    @lark.v_args(inline=True)
    def number(self, value: str) -> tree.Constant:
        return tree.Constant(float(value))

    # -------------------------------------------------------------------------
    # Operators: Unary
    # -------------------------------------------------------------------------

    # Replace Unary nodes with their leaf (acted on by the unary operator).

    @lark.v_args(inline=True)
    def neg(self, value: tree.Node) -> tree.Node:
        value.neg()
        return value

    @lark.v_args(inline=True)
    def pos(self, value: tree.Node) -> tree.Node:
        value.pos()
        return value

    # -------------------------------------------------------------------------
    # Operators: Binary
    # -------------------------------------------------------------------------

    # Replace these branches with our branch nodes.

    def add(self, children: Iterable[tree.Node]) -> tree.OperatorAdd:
        return tree.OperatorAdd(children)

    def sub(self, children: Iterable[tree.Node]) -> tree.OperatorSub:
        return tree.OperatorSub(children)

    def mul(self, children: Iterable[tree.Node]) -> tree.OperatorMult:
        return tree.OperatorMult(children)

    def truediv(self, children: Iterable[tree.Node]) -> tree.OperatorDiv:
        return tree.OperatorDiv(children, truediv=True)

    def floordiv(self, children: Iterable[tree.Node]) -> tree.OperatorDiv:
        return tree.OperatorDiv(children, truediv=False)

    def mod(self, children: Iterable[tree.Node]) -> tree.OperatorMod:
        return tree.OperatorMod(children)

    def pow(self, children: Iterable[tree.Node]) -> tree.OperatorPow:
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

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._transformer: Transformer = Transformer()
        '''
        Our lark->veredi tree transformer.
        '''

        self._variables: MutableMapping[lark.Token, tree.Node] = {}
        '''
        A collection to hold the name & value of any variables declared in the
        tree.
        '''

        self._milieu: str = None
        '''
        A string to insert into the `milieu` of any tree.Variable returned.
        '''

    def _set_up(self, milieu: Optional[str]) -> None:
        '''
        Initialize/reset/clear/whatever our instance variables in prep for next
        parse & transform.
        '''
        self._milieu = milieu
        self._variables.clear()

        # And set up our transformer.
        self._transformer.set_up(self._variables, self._milieu)

    def parse(self,
              string: str,
              milieu: Optional[str] = None) -> Optional['MathTree']:
        '''
        Parse input `string` and return the resultant MathTree, or None if
        parsing/transforming failed at some point.
        '''
        # Set milieu and clear any old vars, also set up our xformer.
        self._set_up(milieu)

        log.debug("parse input{}: '{}' ",
                  ("(w/ milieu: '" + self._milieu + "')"
                   if self._milieu else
                   ''),
                  string)

        syntax_tree = Parser.parse(string)
        if log.will_output(log.Level.DEBUG):
            # Dont format tree into string unless we're actually logging it.
            log.debug("Parser (lark) output: \n{}",
                      Parser.format(syntax_tree))

        math_tree = self._transformer.transform(syntax_tree)
        if log.will_output(log.Level.DEBUG):
            # Dont format tree into string unless we're actually logging it.
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
