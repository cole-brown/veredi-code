# coding: utf-8

'''
Unit tests for:
  veredi/roll/d20/tree.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import unittest

# Framework

# Veredi
from . import tree

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test::Node (The OG Tree)
# -----------------------------------------------------------------------------

class Test_Node(unittest.TestCase):

    def setUp(self):
        self.node0 = tree.Node()
        self.value0 = 42

        self.node1 = tree.Node()
        self.value1 = 9001

    def set_values(self, value0=42, value1=9001):
        self.value0 = value0
        self.value1 = value1

        self.node0._value = self.value0
        self.node1._value = self.value1

    def assert_node_values(self):
        self.assertEqual(self.node0.value, self.value0)
        self.assertEqual(self.node0,       self.node0.value)

        self.assertEqual(self.node1.value, self.value1)
        self.assertEqual(self.node1,       self.node1.value)

    def tearDown(self):
        self.node0 = None
        self.node1 = None

        self.value0 = None
        self.value1 = None

    # --------------------------------------------------------------------------
    # Misc
    # --------------------------------------------------------------------------

    def test_value(self):
        self.assertEqual(self.node0.value, 0)
        self.assertEqual(self.node0._value, self.node0.value)

        with self.assertRaises(AttributeError) as context:
            self.node1.value = 1
        # self.assertEqual(str(context.exception), "can't set attribute")

    # --------------------------------------------------------------------------
    # Comparison
    # --------------------------------------------------------------------------

    def test_node_equal(self):
        # Make equivalent strings (but not the same string by 2 different names)
        self.set_values("a string",
                        "a {}".format("string"))
        self.assertEqual(self.value0, self.value1)
        self.assertIsNot(self.value0, self.value1)

        self.assertEqual(self.node0.value, self.value0)
        self.assertEqual(self.node1.value, self.value1)

        # Ok, nodes set up to have equivalent strings now. Check == operator.
        self.assertEqual(self.node0,       self.node0.value)
        self.assertEqual(self.node1,       self.node1.value)
        self.assertEqual(self.node0.value, self.node1.value)
        self.assertEqual(self.node0,       self.node1)
        self.assertTrue(self.node0 == self.node1)

    def test_node_not_equal(self):
        self.set_values(42,
                        42.0001)
        self.assert_node_values()

        self.assertNotEqual(self.value0, self.value1)

        # Ok, nodes set up to have non-equivalent values now. Check != operator.
        self.assertNotEqual(self.node0.value, self.node1.value)
        self.assertNotEqual(self.node0,       self.node1)
        self.assertTrue(self.node0 != self.node1)

    def test_node_less_than(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value0 < self.value1)

        # Ok, nodes set up to have non-equivalent values now. Check != operator.
        self.assertTrue(self.node0.value < self.node1.value)
        self.assertTrue(self.node0       < self.node1)

    def test_node_greater_than(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value1 > self.value0)

        # Ok, nodes set up to have non-equivalent values now. Check != operator.
        self.assertTrue(self.node1.value > self.node0.value)
        self.assertTrue(self.node1       > self.node0)

    def test_node_less_than_equal(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value0 <= self.value1)

        # Ok, nodes set up to have non-equivalent values now. Check != operator.
        self.assertTrue(self.node0.value <= self.node1.value)
        self.assertTrue(self.node0       <= self.node1)

    def test_node_greater_than_equal(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value1 >= self.value0)

        # Ok, nodes set up to have non-equivalent values now. Check != operator.
        self.assertTrue(self.node1.value >= self.node0.value)
        self.assertTrue(self.node1       >= self.node0)

    # --------------------------------------------------------------------------
    # Mathing
    # --------------------------------------------------------------------------
    def test_node_add(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 + self.value1

        self.assertEqual(expected, self.node0.value + self.node1.value)
        self.assertEqual(expected, self.node0 + self.node1)

    def test_node_sub(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 - self.value1

        self.assertEqual(expected, self.node0.value - self.node1.value)
        self.assertEqual(expected, self.node0 - self.node1)

    def test_node_mul(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 * self.value1

        self.assertEqual(expected, self.node0.value * self.node1.value)
        self.assertEqual(expected, self.node0 * self.node1)

    def test_node_truediv(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 / self.value1

        self.assertEqual(expected, self.node0.value / self.node1.value)
        self.assertEqual(expected, self.node0 / self.node1)

    def test_node_floordiv(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 // self.value1

        self.assertEqual(expected, self.node0.value // self.node1.value)
        self.assertEqual(expected, self.node0 // self.node1)

    def test_node_mod(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 % self.value1

        self.assertEqual(expected, self.node0.value % self.node1.value)
        self.assertEqual(expected, self.node0 % self.node1)

    def test_node_pow(self):
        self.set_values()
        self.assert_node_values()

        expected = self.value0 ** self.value1

        self.assertEqual(expected, self.node0.value ** self.node1.value)
        self.assertEqual(expected, self.node0 ** self.node1)


# -----------------------------------------------------------------------------
# Test::Leaf (of Node)
# -----------------------------------------------------------------------------

class Test_Leaf(unittest.TestCase):

    def setUp(self):
        self.leaf0 = tree.Leaf()
        self.value0 = 42

        self.leaf1 = tree.Leaf()
        self.value1 = 9001

    def set_values(self, value0=42, value1=9001):
        self.value0 = value0
        self.value1 = value1

        self.leaf0._value = self.value0
        self.leaf1._value = self.value1

    def assert_leaf_values(self):
        self.assertEqual(self.leaf0.value, self.value0)
        self.assertEqual(self.leaf0,       self.leaf0.value)

        self.assertEqual(self.leaf1.value, self.value1)
        self.assertEqual(self.leaf1,       self.leaf1.value)

    def tearDown(self):
        self.leaf0 = None
        self.leaf1 = None

        self.value0 = None
        self.value1 = None

    # --------------------------------------------------------------------------
    # Mathamagics
    # --------------------------------------------------------------------------

    def test_neg(self):
        self.set_values()
        self.assert_leaf_values()

        self.assertEqual(self.leaf0._sign, 1)
        self.assertEqual(self.leaf0._sign, self.leaf1._sign)

        self.leaf0.neg()
        self.assertEqual(self.leaf0._sign, -1)
        self.assertNotEqual(self.leaf0._sign, self.leaf1._sign)

        # back around to the positive
        self.leaf0.neg()
        self.assertEqual(self.leaf0._sign, 1)
        self.assertEqual(self.leaf0._sign, self.leaf1._sign)

    def test_pos(self):
        self.set_values()
        self.assert_leaf_values()

        self.assertEqual(self.leaf0._sign, 1)
        self.assertEqual(self.leaf0._sign, self.leaf1._sign)

        # This does nothing, really. No really... nothing.
        self.leaf0.pos()
        self.assertEqual(self.leaf0._sign, 1)
        self.assertEqual(self.leaf0._sign, self.leaf1._sign)


# -----------------------------------------------------------------------------
# Test::Dice (of Leaf of Node)
# -----------------------------------------------------------------------------

class Test_Dice(unittest.TestCase):

    def setUp(self):
        self.dice0 = tree.Dice(1, 20)

        self.dice1 = tree.Dice(3, 6)

    def assert_dice_values(self):
        self.assertEqual(self.dice0.value, self.value0)
        self.assertEqual(self.dice0,       self.dice0.value)

        self.assertEqual(self.dice1.value, self.value1)
        self.assertEqual(self.dice1,       self.dice1.value)

    def tearDown(self):
        self.dice0 = None
        self.dice1 = None

        self.value0 = None
        self.value1 = None

    # --------------------------------------------------------------------------
    # Roll 'em
    # --------------------------------------------------------------------------

    def test_roll(self):
        self.dice0._eval()
        self.dice1.eval()

        # They both rolled something and saved it to .roll?
        self.assertTrue(self.dice0.roll)
        self.assertTrue(self.dice1.roll)

        # They both saved the correct total to .value?
        self.assertEqual(self.dice0.value, sum(self.dice0.roll))
        self.assertEqual(self.dice1.value, sum(self.dice1.roll))

#         self.assertEqual(self.dice0._sign, 1)
#         self.assertEqual(self.dice0._sign, self.dice1._sign)
#
#         self.dice0.neg()
#         self.assertEqual(self.dice0._sign, -1)
#         self.assertNotEqual(self.dice0._sign, self.dice1._sign)
#
#         # back around to the positive
#         self.dice0.neg()
#         self.assertEqual(self.dice0._sign, 1)
#         self.assertEqual(self.dice0._sign, self.dice1._sign)


# --------------------------------Unit Testing----------------------------------
# --                      Main Command Line Entry Point                       --
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
