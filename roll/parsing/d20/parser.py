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
from collections import deque
# If we need threading, switch to:
# from queue import Queue, LifoQueue

# Dice Grammer Parser
from lark import Lark, Transformer, Visitor, v_args

# Veredi
from . import tree
from .utils import FormatOptions

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
    parser = Lark(grammar)

    @classmethod
    def parse(cls, text):
        return cls.parser.parse(text)

    @classmethod
    def format(cls, parsed):
        return parsed.pretty()


# ------------------------------------------------------------------------------
# Lark Tree -> Veredi d20 Tree
# ------------------------------------------------------------------------------

# v_args: inline=True:
#   Methods given *args instead of a list by Lark.
#   So I can do:
#     assign_var(self, name, value)
#   Instead of:
#     assign_vars(self, items)
# NOTE: Should not be used for large lists of args. But all of mine are just
# one or two items.
#@v_args(inline=True)
class D20Transformer(Transformer):
    '''Transforms a lexed/parsed tree into a Veredi roll tree.'''

    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------

    def __init__(self):
        self.vars = {}

    # --------------------------------------------------------------------------
    # Leaves
    # --------------------------------------------------------------------------

    # Replace leaf nodes with their classes.

    # ---
    # Variables
    # ---
    @v_args(inline=True)
    def assign_var(self, name, value):
        self.vars[name] = value

        return value

    @v_args(inline=True)
    def var(self, name):
        # name is Token class
        if name in self.vars:
            return self.vars[name]

        return tree.Variable(name)

    # ---
    # Dice
    # ---
    @v_args(inline=True)
    def die(self, faces):
        return tree.Dice(1, int(faces))

    @v_args(inline=True)
    def dice(self, amount, faces):
        return tree.Dice(int(amount), int(faces))

    # ---
    # Constants
    # ---
    @v_args(inline=True)
    def int(self, value):
        return tree.Constant(int(value))

    @v_args(inline=True)
    def number(self, value):
        return tree.Constant(float(value))

    # --------------------------------------------------------------------------
    # Operators: Unary
    # --------------------------------------------------------------------------

    # Replace Unary nodes with their leaf (acted on by the unary operator).

    @v_args(inline=True)
    def neg(self, value):
        value.neg()
        return value

    @v_args(inline=True)
    def pos(self, value):
        value.pos()
        return value

    # --------------------------------------------------------------------------
    # Operators: Binary
    # --------------------------------------------------------------------------

    # Replace these branches with our branch nodes.

    def add(self, children):
        return tree.OperatorAdd(children)

    def sub(self, children):
        return tree.OperatorSub(children)

    def mul(self, children):
        return tree.OperatorMul(children)

    def div(self, children):
        return tree.OperatorDiv(children)

    def mod(self, children):
        return tree.OperatorMod(children)

    def pow(self, children):
        return tree.OperatorPow(children)


# ------------------------------------------------------------------------------
# Veredi d20 tree -> evaluate all nodes -> Veredi d20 tree w/ values/total
# ------------------------------------------------------------------------------

class Evaluator:
    def _walk(self, root):
        '''
        Generator that walks the tree, yielding each node in depth-first manner.
        '''
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
            # Does this node look familiar? Should we bother with it? (Are there
            # even roll trees with loops or clones?)
            if id(subtree) in visited:
                continue

            # Process our subtree.
            # Allow all nodes in tree, regardless of type.
            nodes.append(subtree)
            visited.add(id(subtree))
            # But only delve down into the branches.
            if isinstance(subtree, tree.Branch):
                queue.extend(subtree.children)

        # ---
        # Depth-first yielding of the nodes we've walked.
        # ---
        seen = set()
        while nodes:
            each = nodes.pop()
            if id(each) not in seen:
                yield each
                seen.add(id(each))

    def eval(self, root):
        '''Walk tree, evaluate each node, and return total result.

        '''
        total = 0
        for each in self._walk(root):
            total = each.eval()

        # TODO [2020-04-24]: here you are  - test this?
        return total


# ------------------------------------------------------------------------------
# Veredi -> Text
# ------------------------------------------------------------------------------

class Outputter:
    @static
    def _walk(root, branch_only=True):
        '''
        Generator that walks the tree, yielding each node in depth-first manner.
        '''
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
            # Does this node look familiar? Should we bother with it? (Are there
            # even roll trees with loops or clones?)
            if id(subtree) in visited:
                continue

            # Process our subtree.
            # Allow all nodes in tree, regardless of type.
            nodes.append(subtree)
            visited.add(id(subtree))
            # But only delve down into the branches.
            if isinstance(subtree, tree.Branch):
                if branch_only:
                    # branch_only: extend the queue with only children who are
                    # also branch nodes.
                    queue.extend([each
                                  for each in subtree.children
                                  if isinstance(each, tree.Branch)])
                else:
                    # extend with all children
                    queue.extend(subtree.children)

        # ---
        # Depth-first yielding of the nodes we've gathered.
        # ---
        seen = set()
        while nodes:
            each = nodes.pop()
            if id(each) not in seen:
                yield each
                seen.add(id(each))

    def string(root, options=FormatOptions.ALL):
        # Each branch node is, approximately:
        #   str(children[0]) + str(branch) + str(children[1])
        #
        # But also want to put in parenthesis some things for, e.g.:
        #   d20 * (2d4 + 3)
        #
        # Also we aren't restricting our children to a max of 2.
        output = []
        for branch in self._walk(root):
            operator = branch.expr_str(options)
            # §-TODO-§ [2020-04-27]: hm... need a dict or something for the
            # strings? Like for saving a branch, then getting it back next step
            # to fold into the final output? Or can I just walk and push things?

        pass

# -----------------------------------Veredi-------------------------------------
# --                             Text -> Veredi                               --
# ------------------------------------------------------------------------------

def parse_input(input):
    ast = Parser.parse(input)
    xform = D20Transformer()
    roll_tree = xform.transform(ast)
    # return roll_tree

    evaluator = Evaluator()
    return evaluator.eval(roll_tree)


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

    xform = D20Transformer()
    roll_tree = xform.transform(ast)
    print("\nTransformed:")
    print(roll_tree)
    print("\nTransformed, pretty:")
    print(roll_tree.pretty())

    evaluator = Evaluator()
    print("Eval'd:", evaluator.eval(roll_tree))
