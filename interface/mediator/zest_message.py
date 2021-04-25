#!/usr/bin/env python3

# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Tuple, Literal


from .zbase                         import Test_Message_Base

from veredi.logs                    import log

from veredi.base.context            import UnitTestContext

from veredi.data.codec              import Codec
from veredi.data.serdes.json.serdes import JsonSerdes
from veredi.base.identity           import (MonotonicId,
                                            MonotonicIdGenerator)
from veredi.data.identity           import (UserId,
                                            MockUserIdGenerator,
                                            UserKey,
                                            MockUserKeyGenerator)
from veredi.security                import abac
from veredi.math.d20                import tree
from veredi.math.parser             import MathTree

from .message                       import Message, MsgType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MESSAGE_ENCODED: Dict = {
    'v.codec': 'veredi.interface.mediator.message.message',
    'v.payload': {
        'encoded.type': 'message',
        'entity_id': None,
        'msg_id': 'v.mid:1',
        'payload': {
            'v.codec': 'veredi.math.d20.tree.add',
            'v.payload': {
                'children': [
                    {'v.codec': 'veredi.math.d20.tree.variable',
                     'v.payload': {'children': None,
                                   'dotted': 'veredi.math.d20.tree.variable',
                                   'encoded.type': 'variable',
                                   'milieu': 'strength.score',
                                   'moniker': 'strength.score',
                                   'tags': None,
                                   'type': 'node.type:INVALID|LEAF|VARIABLE',
                                   'value': 30}},
                    {'v.codec': 'veredi.math.d20.tree.constant',
                     'v.payload': {'children': None,
                                   'dotted': 'veredi.math.d20.tree.constant',
                                   'encoded.type': 'constant',
                                   'milieu': None,
                                   'moniker': 4,
                                   'tags': None,
                                   'type': 'node.type:INVALID|LEAF|CONSTANT',
                                   'value': 4}}],
                'dotted': 'veredi.math.d20.tree.add',
                'encoded.type': 'add',
                'milieu': None,
                'moniker': '+',
                'tags': None,
                'type': 'node.type:INVALID|BRANCH|OPERATOR',
                'value': 34}},
        'security': 'attributes.subject:INVALID|BROADCAST',
        'type': 'v.mt:512',
        'user_id': 'uid:147d7414-b7bd-5779-96cb-4cc72b19a514',
        'user_key': None
    }
}
'''
The Codec-encoded Message.
'''


MESSAGE_SERIALIZED: str = '''
{
  "v.codec": "veredi.interface.mediator.message.message",
  "v.payload": {
    "msg_id": "v.mid:1",
    "type": "v.mt:512",
    "entity_id": null,
    "user_id": "uid:147d7414-b7bd-5779-96cb-4cc72b19a514",
    "user_key": null,
    "payload": {
      "v.codec": "veredi.math.d20.tree.add",
      "v.payload": {
        "dotted": "veredi.math.d20.tree.add",
        "moniker": "+",
        "value": 34,
        "milieu": null,
        "children": [
          {
            "v.codec": "veredi.math.d20.tree.variable",
            "v.payload": {
              "dotted": "veredi.math.d20.tree.variable",
              "moniker": "strength.score",
              "value": 30,
              "milieu": "strength.score",
              "children": null,
              "tags": null,
              "type": "node.type:INVALID|LEAF|VARIABLE",
              "encoded.type": "variable"
            }
          },
          {
            "v.codec": "veredi.math.d20.tree.constant",
            "v.payload": {
              "dotted": "veredi.math.d20.tree.constant",
              "moniker": 4,
              "value": 4,
              "milieu": null,
              "children": null,
              "tags": null,
              "type": "node.type:INVALID|LEAF|CONSTANT",
              "encoded.type": "constant"
            }
          }
        ],
        "tags": null,
        "type": "node.type:INVALID|BRANCH|OPERATOR",
        "encoded.type": "add"
      }
    },
    "security": "attributes.subject:INVALID|BROADCAST",
    "encoded.type": "message"
  }
}'''
'''
The Codec-encoded & JsonSerdes-serialized message we're testing.
'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Message(Test_Message_Base):

    def pre_set_up(self,
                   # Ignored params:
                   filename:  Literal[None]  = None,
                   extra:     Literal[Tuple] = (),
                   test_type: Literal[None]  = None) -> None:
        super().pre_set_up(filename=__file__)

    def set_up(self):
        super().set_up(None,
                       MESSAGE_ENCODED,
                       MESSAGE_SERIALIZED)

    def tear_down(self):
        self.serdes        = None
        self.codec         = None
        self.encoded       = None
        self.serialized    = None
        self._msg_id_gen   = None
        self._user_id_gen  = None
        self._uname        = None
        self._uid          = None
        self._user_key_gen = None
        self._ukey         = None

    def make_payload(self, payload=None):
        # ------------------------------
        # Message Payload
        # ------------------------------
        # Set up payload - a math expression...
        strength = tree.Variable("strength.score", "strength.score")
        strength.value = 30
        constant = tree.Constant(4)
        payload = tree.OperatorAdd([
            strength,
            constant,
        ])
        # Fill in payload's value.
        payload.eval()
        # OperatorAdd's value after evaluation should just be the sum of its
        # children's values.
        self.assertEqual(payload.value, strength.value + constant.value)

        # ------------------------------
        # Let parent do their thing to it now; will end up in `self.payload`.
        # ------------------------------
        return super().make_payload(payload=payload)

    # -------------------------------------------------------------------------
    # Helpers: Math Payload Asserts
    # -------------------------------------------------------------------------

    def assertTreeNodeEqual(self,
                            expected: MathTree,
                            test:     MathTree) -> None:
        '''
        Asserts `test` node is a MathTree node that matches `expected`.

        Does not check that all children match each other; just checks that
        they have the same number of them.
        '''
        self.assertIsInstance(test, MathTree)
        self.assertIsInstance(expected, MathTree)
        self.assertIsInstance(test, type(expected))
        self.assertEqual(expected.type, test.type)
        self.assertEqual(expected.moniker, test.moniker)
        self.assertEqual(expected.value, test.value)
        self.assertEqual(expected.milieu, test.milieu)

    def assertMathTreeEqual(self,
                            expected: MathTree,
                            payload:  MathTree) -> None:
        '''
        Asserts `payload` is a MathTree that matches `expected`.
        '''
        self.assertEqual(bool(expected), bool(payload))
        self.assertIsInstance(expected, MathTree)
        self.assertIsInstance(payload, MathTree)

        # ------------------------------
        # Check: Root
        # ------------------------------
        self.assertIsInstance(expected, tree.OperatorAdd)
        self.assertTreeNodeEqual(expected, payload)

        # ------------------------------
        # Check: Children
        # ------------------------------
        self.assertEqual(len(expected.children), len(payload.children))
        payload_child_types = set()
        for i in range(len(expected.children)):
            child_expected = expected.children[i]
            child_payload = payload.children[i]
            self.assertTreeNodeEqual(child_expected, child_payload)
            payload_child_types.add(type(child_payload))

        self.assertEqual(set((tree.Constant, tree.Variable)),
                         payload_child_types)

    def assertPayloadEqual(self, expected, payload):
        super().assertPayloadEqual(expected, payload)
        self.assertMathTreeEqual(expected, payload)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self) -> None:
        self.do_test_init()

    def test_encode(self):
        self.do_test_encode()

    def test_decode(self) -> None:
        self.do_test_decode()

    def test_serialize(self) -> None:
        self.do_test_serialize()

    def test_deserialize(self):
        self.do_test_deserialize()


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi test interface/mediator/zest_message.py

if __name__ == '__main__':
    import unittest
    unittest.main()
