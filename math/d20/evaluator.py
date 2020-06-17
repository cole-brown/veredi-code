# coding: utf-8

'''
Evaluator for a Veredi Roll Tree.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
from collections import deque
# If we need threading, switch to:
# from queue import Queue, LifoQueue

# Framework

# Our Stuff
from . import tree
from .const import FormatOptions

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Veredi d20 tree -> evaluate all nodes -> Veredi d20 tree w/ values/total
# -----------------------------------------------------------------------------

class Evaluator:
    @staticmethod
    def _walk(root):
        '''
        Generator that walks the tree, yielding each node in
        depth-first manner.
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
            # Does this node look familiar? Should we bother with it?
            # (Are there even roll trees with loops or clones?)
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

    @staticmethod
    def eval(root):
        '''Walk tree, evaluate each node, and return total result.

        '''
        total = 0
        for each in Evaluator._walk(root):
            total = each.eval()

        # TODO [2020-04-24]: here you are  - test this?
        return total


# -----------------------------------------------------------------------------
# Veredi -> Text
# -----------------------------------------------------------------------------

class Outputter:
    @staticmethod
    def _walk(root, branch_only=True):
        '''
        Generator that walks the tree, yielding each node in
        depth-first manner.
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
            # Does this node look familiar? Should we bother with it?
            # (Are there even roll trees with loops or clones?)
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

    @staticmethod
    def string(root, options=FormatOptions.ALL):
        if isinstance(root, tree.Leaf):
            return root.expr_str(options)

        # Each branch node is, approximately:
        #   str(children[0]) + str(branch) + str(children[1])
        #
        # But also want to put in parenthesis some things for, e.g.:
        #   d20 * (2d4 + 3)
        #
        # Also we aren't restricting our children to a max of 2.
        branch_finals = {}
        last = None
        for branch in Outputter._walk(root):
            operator = branch.expr_str(options)
            branch_output = []
            # §-TODO-§ [2020-04-27]: hm... need a dict or something for the
            # strings? Like for saving a branch, then getting it back next step
            # to fold into the final output? Or can I just walk and push
            # things?
            for child in branch.children:
                if branch_output:
                    branch_output.append(operator)
                string = None
                if isinstance(child, tree.Branch):
                    string = branch_finals[id(child)]
                else:
                    string = child.expr_str(options)
                branch_output.append(string)

            last = ' '.join(branch_output)
            branch_finals[id(branch)] = last

        return last + " = " + str(root.value)


# -----------------------------------Veredi------------------------------------
# --                             Text -> Veredi                              --
# -----------------------------------------------------------------------------

# def parse_input(input):
#     ast = Parser.parse(input)
#     xform = Transformer()
#     roll_tree = xform.transform(ast)
#     # return roll_tree
#
#     evaluator = Evaluator()
#     # return evaluator.eval(roll_tree)
#     evaluator.eval(roll_tree)
#     return Outputter.string(roll_tree)
