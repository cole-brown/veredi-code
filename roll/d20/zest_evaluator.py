# coding: utf-8

'''
Unit tests for:
  veredi/roll/d20/evaluator.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest

# Veredi
from . import tree
from . import parser
from . import evaluator

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------Text -> Lark Tree-------------------------------
# --                          Test your grammar...                            --
# ------------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Test::Evaluator
# -----------------------------------------------------------------------------

class Test_Evaluator(unittest.TestCase):

    def str_to_transformed(self, string):
        ast = parser.Parser.parse(string)
        xform = parser.Transformer()
        roll_tree = xform.transform(ast)
        return roll_tree

    # --------------------------------------------------------------------------
    # Simple Cases
    #   - just test that we can get a certain node type
    # --------------------------------------------------------------------------

    def test_eval_roll(self):
        string = "d20 + 13"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure it is not eval'd yet.
        self.assertTrue(isinstance(roll_tree, tree.OperatorAdd))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.value, None)
        self.assertEqual(roll_tree.children[0].value, None)
        self.assertEqual(roll_tree.children[1].value, 13)

        # Eval it; make sure it's eval'd.
        evaluator.Evaluator.eval(roll_tree)

        # Now all the nodes should have values.
        self.assertTrue(isinstance(roll_tree, tree.OperatorAdd))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertTrue(roll_tree.children[0].value >  0)
        self.assertTrue(roll_tree.children[0].value < 21)
        self.assertEqual(roll_tree.children[1].value, 13)
        expected = roll_tree.children[0].value + roll_tree.children[1].value
        self.assertEqual(roll_tree.value, expected)


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
