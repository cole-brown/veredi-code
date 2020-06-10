# coding: utf-8

'''
Unit tests for:
  veredi/roll/d20/parser.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest

# Veredi
from . import parser
from . import tree

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------Text -> Lark Tree------------------------------
# --                          Test your grammar...                           --
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test::Parser's Nodes
# -----------------------------------------------------------------------------

class Test_Parser(unittest.TestCase):

    # NOTE!
    #  Don't test Lark itself. Just test some basics so I can know my grammar
    #  becomes something I expect /after/ Lark is done and I'm about to do
    #  something with its output.

    # -------------------------------------------------------------------------
    # Simple Cases
    #   - just test that we can get a certain node type
    # -------------------------------------------------------------------------

    # Lowest on the list is 'roll' (-> 'die' & 'dice'), so test that first.
    def test_die(self):

        lark_tree = parser.Parser.parse("d10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a die token in there?
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "die")
        self.assertEqual(lark_tree.children[0].type, "INT")
        self.assertEqual(lark_tree.children[0].value, "10")

    def test_dice(self):

        lark_tree = parser.Parser.parse("47d3000")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a dice token. And not a die token.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "dice")
        self.assertEqual(lark_tree.children[0].type, "INT")
        self.assertEqual(lark_tree.children[0].value, "47")
        self.assertEqual(lark_tree.children[1].type, "INT")
        self.assertEqual(lark_tree.children[1].value, "3000")

    def test_var(self):

        lark_tree = parser.Parser.parse("${jeff}")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a var token in there?
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "var")
        self.assertEqual(lark_tree.children[0].type, "NAME")
        self.assertEqual(lark_tree.children[0].value, "jeff")

        lark_tree = parser.Parser.parse("$jeff")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a var token in there?
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "var")
        self.assertEqual(lark_tree.children[0].type, "NAME")
        self.assertEqual(lark_tree.children[0].value, "jeff")

    def test_func(self):

        lark_tree = parser.Parser.parse("max(0, 1)")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a var token in there?
        self.assertEqual(3, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "func")
        self.assertEqual(lark_tree.children[0].type, "NAME")
        self.assertEqual(lark_tree.children[0].value, "max")
        self.assertEqual(lark_tree.children[1].data, "int")
        self.assertEqual(lark_tree.children[1].children[0].type, "INT")
        self.assertEqual(lark_tree.children[1].children[0].value, "0")
        self.assertEqual(lark_tree.children[2].data, "int")
        self.assertEqual(lark_tree.children[2].children[0].type, "INT")
        self.assertEqual(lark_tree.children[2].children[0].value, "1")

    def test_int(self):

        lark_tree = parser.Parser.parse("10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a int token in there?
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "int")
        self.assertEqual(lark_tree.children[0].type, "INT")
        self.assertEqual(lark_tree.children[0].value, "10")

    def test_number(self):

        lark_tree = parser.Parser.parse("10.1")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure it's only a number token in there?
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "number")
        self.assertEqual(lark_tree.children[0].type, "NUMBER")
        self.assertEqual(lark_tree.children[0].value, "10.1")

    def test_neg(self):

        lark_tree = parser.Parser.parse("-10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is neg, and has the int below it.
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "neg")
        self.assertEqual(lark_tree.children[0].data, "int")
        self.assertEqual(1, len(lark_tree.children[0].children))
        self.assertEqual(lark_tree.children[0].children[0].type, "INT")
        self.assertEqual(lark_tree.children[0].children[0].value, "10")

    def test_pos(self):

        lark_tree = parser.Parser.parse("+10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is pos, and has the int below it.
        self.assertEqual(1, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "pos")
        self.assertEqual(lark_tree.children[0].data, "int")
        self.assertEqual(1, len(lark_tree.children[0].children))
        self.assertEqual(lark_tree.children[0].children[0].type, "INT")
        self.assertEqual(lark_tree.children[0].children[0].value, "10")

    def test_mul(self):

        lark_tree = parser.Parser.parse("10 * 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "mul")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_div(self):

        lark_tree = parser.Parser.parse("10 / 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "div")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_mod(self):

        lark_tree = parser.Parser.parse("10 % 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "mod")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_pow(self):

        lark_tree = parser.Parser.parse("10 ^ 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "pow")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_add(self):

        lark_tree = parser.Parser.parse("10 + 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "add")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_sub(self):

        lark_tree = parser.Parser.parse("10 - 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our operator, and has the ints below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "sub")
        for each in lark_tree.children:
            self.assertEqual(each.data, "int")
            self.assertEqual(1, len(each.children))
            self.assertEqual(each.children[0].type, "INT")
            self.assertEqual(each.children[0].value, "10")

    def test_assign_var(self):

        lark_tree = parser.Parser.parse("jeff = 10")
        # Make sure we got something.
        self.assertIsNotNone(lark_tree)
        self.assertTrue(lark_tree)

        # Make sure root is our assignment, and has the int below it.
        self.assertEqual(2, len(lark_tree.children))
        self.assertEqual(lark_tree.data, "assign_var")

        self.assertEqual(lark_tree.children[0].type, "NAME")
        self.assertEqual(lark_tree.children[0].value, "jeff")

        self.assertEqual(1, len(lark_tree.children[1].children))
        self.assertEqual(lark_tree.children[1].data, "int")
        self.assertEqual(lark_tree.children[1].children[0].type, "INT")
        self.assertEqual(lark_tree.children[1].children[0].value, "10")


# -----------------------------------------------------------------------------
# Test::Transformer (Lark tree -> Veredi tree Step)
# -----------------------------------------------------------------------------

class Test_Transformer(unittest.TestCase):

    # NOTE!
    #  Don't test Lark. Test my Transformer!

    def str_to_transformed(self, string):
        ast = parser.Parser.parse(string)
        xform = parser.Transformer()
        roll_tree = xform.transform(ast)
        return roll_tree

    # -------------------------------------------------------------------------
    # Simple Cases
    #   - just test that we can get a certain node type
    # -------------------------------------------------------------------------

    # TODO: Get assign_var() working.
    # def test_assign_var(self):
    #     string = "jeff = 10"
    #     roll_tree = self.str_to_transformed(string)
    #     # Make sure we got something.
    #     self.assertIsNotNone(roll_tree)
    #     self.assertTrue(roll_tree)
    #
    #     print(roll_tree)
    #
    #     # Make sure we only have what we input.
    #     self.assertEqual(1, len(roll_tree.children))
    #     self.assertTrue(isinstance(roll_tree, tree.Variable))
    #     self.assertEqual(roll_tree.name, "jeff")

    def test_var(self):
        string = "$jeff"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Variable))
        self.assertEqual(roll_tree.name, "jeff")

    def test_die(self):
        string = "d20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Dice))
        self.assertEqual(roll_tree.dice, 1)
        self.assertEqual(roll_tree.faces, 20)

    def test_dice(self):
        string = "3d20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Dice))
        self.assertEqual(roll_tree.dice, 3)
        self.assertEqual(roll_tree.faces, 20)

    def test_int(self):
        string = "123"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Constant))
        self.assertEqual(roll_tree.value, 123)

    def test_number(self):
        string = "123.456"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Constant))
        self.assertEqual(roll_tree.value, 123.456)

    def test_neg(self):
        string = "-20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Constant))
        self.assertEqual(roll_tree.value, 20)
        self.assertEqual(roll_tree._sign, -1)

    def test_pos(self):
        string = "+20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.Constant))
        self.assertEqual(roll_tree.value, 20)
        self.assertEqual(roll_tree._sign, 1)

    def test_add(self):
        string = "10 + 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorAdd))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)

    def test_sub(self):
        string = "10 - 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorSub))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)

    def test_mul(self):
        string = "10 * 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorMult))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)

    def test_div(self):
        string = "10 / 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorDiv))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)

    def test_mod(self):
        string = "10 % 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorMod))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)

    def test_pow(self):
        string = "10 ^ 20"
        roll_tree = self.str_to_transformed(string)
        # Make sure we got something.
        self.assertIsNotNone(roll_tree)
        self.assertTrue(roll_tree)

        # Make sure we only have what we input.
        self.assertTrue(isinstance(roll_tree, tree.OperatorPow))
        self.assertEqual(len(roll_tree.children), 2)
        self.assertEqual(roll_tree.children[0].value, 10)
        self.assertEqual(roll_tree.children[1].value, 20)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
