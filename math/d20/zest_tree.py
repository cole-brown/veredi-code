# coding: utf-8

'''
Unit tests for:
  veredi/roll/d20/tree.py
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

from veredi.zest.base.unit import ZestBase
from veredi.zest.zpath     import TestType
from veredi.logs           import log

from veredi.base.strings   import labeler
from veredi.data.codec     import EncodedComplex, Codec

from .                     import tree
from ..parser              import NodeType


# -----------------------------------------------------------------------------
# Mock Classes
# -----------------------------------------------------------------------------

class MockNode(tree.Node,
               name_dotted='veredi.math.d20.tree.zest-tree.mock-node',
               name_string='mock-node'):

    def __init__(self, type, value=None):
        super().__init__(type,
                         value=value)

    def _eval(self) -> None:
        pass

    def encode_complex(self, codec: Codec):
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        raise NotImplementedError

    @classmethod
    def decode_complex(klass: 'MockNode',
                       data:  EncodedComplex,
                       codec: Codec,
                       instance: Optional['MockNode'] = None):
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        raise NotImplementedError


class MockLeaf(tree.Leaf,
               name_dotted='veredi.math.d20.tree.zest-tree.mock-leaf',
               name_string='mock-leaf'):

    def __init__(self, type, value=None):
        super().__init__(type,
                         value=value)

    def _eval(self) -> None:
        '''
        Internal method for evaluating this dice node (roll dice, sum result)
        and saving results internally.
        '''
        raise NotImplementedError

    def encode_complex(self, codec: Codec):
        '''
        Encode ourself as an EncodedComplex, return that value.
        '''
        raise NotImplementedError

    @classmethod
    def decode_complex(klass: 'MockLeaf',
                       data:  EncodedComplex,
                       codec: Codec,
                       instance: Optional['MockLeaf'] = None):
        '''
        Decode ourself as an EncodedComplex, return a new instance of `klass`
        as the result of the decoding.
        '''
        raise NotImplementedError


# ------------------------------------Tree-------------------------------------
# --                          Abstract / Base Class                          --
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Test::Node (The OG Tree)
# -----------------------------------------------------------------------------

class Test_Node(ZestBase):

     def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'node')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.node0 = MockNode(NodeType.enum.INVALID)
        self.value0 = 42

        self.node1 = MockNode(NodeType.enum.INVALID)
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

    def tear_down(self):
        self.node0 = None
        self.node1 = None

        self.value0 = None
        self.value1 = None

    # -------------------------------------------------------------------------
    # Misc
    # -------------------------------------------------------------------------

    def test_value(self):
        self.assertIsNone(self.node0.value)
        self.assertEqual(self.node0._value, self.node0.value)

        # Turn off log for this exception we expect.
        with log.LoggingManager.disabled(), self.assertRaises(AttributeError):
            self.node1.value = 1
        # self.assertEqual(str(context.exception), "can't set attribute")

    # -------------------------------------------------------------------------
    # Comparison
    # -------------------------------------------------------------------------

    def test_node_equal(self):
        # Make equivalent strings
        # (but not the same string by 2 different names)
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

        # Ok, nodes set up to have non-equivalent values now.
        # Check != operator.
        self.assertNotEqual(self.node0.value, self.node1.value)
        self.assertNotEqual(self.node0,       self.node1)
        self.assertTrue(self.node0 != self.node1)

    def test_node_less_than(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value0 < self.value1)

        # Ok, nodes set up to have non-equivalent values now.
        # Check < operator.
        self.assertTrue(self.node0.value < self.node1.value)
        self.assertTrue(self.node0       < self.node1)

    def test_node_greater_than(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value1 > self.value0)

        # Ok, nodes set up to have non-equivalent values now.
        # Check > operator.
        self.assertTrue(self.node1.value > self.node0.value)
        self.assertTrue(self.node1       > self.node0)

    def test_node_less_than_equal(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value0 <= self.value1)

        # Ok, nodes set up to have non-equivalent values now.
        # Check <= operator.
        self.assertTrue(self.node0.value <= self.node1.value)
        self.assertTrue(self.node0       <= self.node1)

    def test_node_greater_than_equal(self):
        self.set_values()
        self.assert_node_values()

        self.assertTrue(self.value1 >= self.value0)

        # Ok, nodes set up to have non-equivalent values now.
        # Check >= operator.
        self.assertTrue(self.node1.value >= self.node0.value)
        self.assertTrue(self.node1       >= self.node0)

    # -------------------------------------------------------------------------
    # Mathing
    # -------------------------------------------------------------------------
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


# ------------------------------------Tree-------------------------------------
# --                            Leaf Node Classes                            --
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Test::Leaf (of Node)
# -----------------------------------------------------------------------------

class Test_Leaf(ZestBase):

     def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'leaf')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.leaf0 = MockLeaf(NodeType.enum.INVALID)
        self.value0 = 42

        self.leaf1 = MockLeaf(NodeType.enum.INVALID)
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

    def tear_down(self):
        self.leaf0 = None
        self.leaf1 = None

        self.value0 = None
        self.value1 = None

    # -------------------------------------------------------------------------
    # Mathamagics
    # -------------------------------------------------------------------------

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

class Test_Dice(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'dice')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.dice0 = tree.Dice(1, 20)

        self.dice1 = tree.Dice(3, 6)

    def tear_down(self):
        self.dice0 = None
        self.dice1 = None

    # -------------------------------------------------------------------------
    # Roll 'em
    # -------------------------------------------------------------------------

    def test_roll_dice(self):
        self.dice0._eval()
        self.dice1.eval()

        # They both rolled something and saved it to .roll?
        self.assertTrue(self.dice0.roll)
        self.assertTrue(self.dice1.roll)

        # They both rolled the correct number of dice?
        self.assertEqual(len(self.dice0.roll), self.dice0.dice)
        self.assertEqual(len(self.dice1.roll), self.dice1.dice)

    def test_roll_and_value(self):
        self.dice0._eval()
        self.dice1.eval()

        # They both rolled something and saved it to .roll?
        self.assertTrue(self.dice0.roll)
        self.assertTrue(self.dice1.roll)

        # They both saved the correct total to .value?
        self.assertEqual(self.dice0.value, sum(self.dice0.roll))
        self.assertEqual(self.dice1.value, sum(self.dice1.roll))


# -----------------------------------------------------------------------------
# Test::Constant (of Leaf of Node)
# -----------------------------------------------------------------------------

class Test_Constant(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'constant')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.const0 = tree.Constant(self.value0)
        self.value1 = 9001
        self.const1 = tree.Constant(self.value1)

    def tear_down(self):
        self.const0 = None
        self.const1 = None

        self.value0 = None
        self.value1 = None

    # -------------------------------------------------------------------------
    # Test that nothing happens in a specific way...
    # -------------------------------------------------------------------------

    def test_roll_const(self):
        # Constants should already have their value assigned after creation, as
        # they are... constant.
        self.assertEqual(self.value0, self.const0.value)
        self.assertEqual(self.value1, self.const1.value)
        self.assertEqual(self.value0, self.const0)
        self.assertEqual(self.value1, self.const1)

        self.const0._eval()
        self.const1.eval()

        # Nothing should have changed after evaluation, as they are...
        # constant.
        self.assertEqual(self.value0, self.const0.value)
        self.assertEqual(self.value1, self.const1.value)
        self.assertEqual(self.value0, self.const0)
        self.assertEqual(self.value1, self.const1)


# -----------------------------------------------------------------------------
# Test::Variable (of Leaf of Node)
# -----------------------------------------------------------------------------

class Test_Variable(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'variable')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.name0 = "$jeff-mod"
        self.value0 = 3
        self.var0 = tree.Variable(self.name0)
        self.name1 = "$jeff"
        self.value1 = 1336
        self.var1 = tree.Variable(self.name1)

    def tear_down(self):
        self.var0 = None
        self.var1 = None

        self.name0 = None
        self.name1 = None

        self.value0 = None
        self.value1 = None

    # -------------------------------------------------------------------------
    # Test... the placeholder holds its place?
    # -------------------------------------------------------------------------

    def test_roll_var(self):
        # Variables should just be a name until we know what to do with
        # that name...
        # So they shouldn't have a value just yet.
        self.assertEqual(None, self.var0.value)
        self.assertEqual(None, self.var1.value)
        with self.assertRaises(ValueError):
            self.assertEqual(None, self.var0)
        with self.assertRaises(ValueError):
            self.assertEqual(None, self.var1)
        self.assertNotEqual(self.value0, self.var0.value)
        self.assertNotEqual(self.value1, self.var1.value)
        with self.assertRaises(ValueError):
            self.assertNotEqual(self.value0, self.var0)
        with self.assertRaises(ValueError):
            self.assertNotEqual(self.value1, self.var1)

        # But they should have their name.
        self.assertEqual(self.name0, self.var0.name)
        self.assertEqual(self.name1, self.var1.name)

        # Variables get their values filled in from outside systems in normal
        # cases. But this is a test and there is no outside, so... pretend.
        outside0 = 99
        outside1 = 999
        self.var0.value = outside0
        self.var1.value = outside1
        self.assertEqual(outside0, self.var0.value)
        self.assertEqual(outside1, self.var1.value)
        self.assertEqual(outside0, self.var0)
        self.assertEqual(outside1, self.var1)

        self.var0._eval()
        self.var1.eval()

        # Values should still be set; eval should do nothing
        self.assertEqual(outside0, self.var0.value)
        self.assertEqual(outside1, self.var1.value)
        self.assertEqual(outside0, self.var0)
        self.assertEqual(outside1, self.var1)
        self.assertNotEqual(self.value0, self.var0.value)
        self.assertNotEqual(self.value1, self.var1.value)
        self.assertNotEqual(self.value0, self.var0)
        self.assertNotEqual(self.value1, self.var1)


# ------------------------------------Tree-------------------------------------
# --                             Branch Classes                              --
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Test::Branch (of Node)
# -----------------------------------------------------------------------------

class Test_Branch(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'branch')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def test_eval(self):
        # Branch base class shouldn't be able to eval successfully... It
        # shouldn't even be able to instantiate itself now, since it's
        # abstract.

        # So expect a TypeError now on init.
        with self.assertRaises(TypeError):
            # Branch base class shouldn't be able to eval successfully... It
            # shouldn't even be able to instantiate itself now, since it's
            # abstract.
            tree.Branch(None, NodeType.enum.INVALID, 'jeff')

        # And no more expecting an AttributeError on eval().
        # with self.assertRaises(AttributeError):
        #     branch = tree.Branch(None, NodeType.enum.INVALID, 'jeff')
        #     branch.eval()


# -----------------------------------------------------------------------------
# Test::OperatorMath (of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorMath(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'math')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def test_eval(self):
        with self.assertRaises(TypeError):
            # OperatorMath base class shouldn't be able to eval successfully...
            branch = tree.OperatorMath(None,
                                       NodeType.enum.OPERATOR,
                                       None,
                                       None)
            branch.eval()


# -----------------------------------------------------------------------------
# Test::OperatorAdd (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorAdd(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'add')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.add = tree.OperatorAdd(self.children)

    def tear_down(self):
        self.add = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_add(self):
        self.assertIsNone(self.add.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.add)

        self.add.eval()

        expected = self.value0 + self.value1
        self.assertEqual(expected, self.add.value)
        self.assertEqual(expected, self.add)


# -----------------------------------------------------------------------------
# Test::OperatorSub (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorSub(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'sub')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.sub = tree.OperatorSub(self.children)

    def tear_down(self):
        self.sub = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_sub(self):
        self.assertEqual(None, self.sub.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.sub)

        self.sub.eval()

        expected = self.value0 - self.value1
        self.assertEqual(expected, self.sub.value)
        self.assertEqual(expected, self.sub)


# -----------------------------------------------------------------------------
# Test::OperatorMult (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorMult(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'mult')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.mult = tree.OperatorMult(self.children)

    def tear_down(self):
        self.mult = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_mult(self):
        self.assertEqual(None, self.mult.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.mult)

        self.mult.eval()

        expected = self.value0 * self.value1
        self.assertEqual(expected, self.mult.value)
        self.assertEqual(expected, self.mult)


# -----------------------------------------------------------------------------
# Test::OperatorDiv (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorDiv(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'div')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.div = tree.OperatorDiv(self.children)

    def tear_down(self):
        self.div = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_div(self):
        self.assertEqual(None, self.div.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.div)

        self.div.eval()

        expected = self.value0 / self.value1
        self.assertEqual(expected, self.div.value)
        self.assertEqual(expected, self.div)


# -----------------------------------------------------------------------------
# Test::OperatorMod (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorMod(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'mod')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.mod = tree.OperatorMod(self.children)

    def tear_down(self):
        self.mod = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_mod(self):
        self.assertEqual(None, self.mod.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.mod)

        self.mod.eval()

        expected = self.value0 % self.value1
        self.assertEqual(expected, self.mod.value)
        self.assertEqual(expected, self.mod)


# -----------------------------------------------------------------------------
# Test::OperatorPow (of OperatorMath of Branch of Node)
# -----------------------------------------------------------------------------

class Test_OperatorPow(ZestBase):

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'operator', 'pow')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.value0 = 42
        self.value1 = 9001
        self.children = [
            tree.Constant(self.value0),
            tree.Constant(self.value1),
        ]
        self.pow = tree.OperatorPow(self.children)

    def tear_down(self):
        self.pow = None
        self.children = None

        self.value0 = None
        self.value1 = None

    def test_pow(self):
        self.assertEqual(None, self.pow.value)
        with self.assertRaises(ValueError):
            # raises an error before it's eval'd
            self.assertEqual(0, self.pow)

        self.pow.eval()

        expected = self.value0 ** self.value1
        self.assertEqual(expected, self.pow.value)
        self.assertEqual(expected, self.pow)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.math.d20.zest_tree

if __name__ == '__main__':
    import unittest
    unittest.main()
