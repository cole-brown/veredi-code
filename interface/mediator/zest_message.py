#!/usr/bin/env python3

# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Tuple, Literal


from datetime import datetime, timezone


from veredi.logs                    import log

from veredi.zest.base.unit          import ZestBase
from veredi.zest.zpath              import TestType
from veredi.base.context            import UnitTestContext

from veredi.base.strings            import label
from veredi.data.codec              import Codec
from veredi.data.serdes.json.serdes import JsonSerdes
from veredi.data.context            import DataAction
from veredi.base.identity           import (MonotonicId,
                                            MonotonicIdGenerator)
from veredi.data                    import background
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


MESSAGE_SERIALIZED_GOOD: str = '''
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


MESSAGE_SERIALIZED_BAD: str = '''
{
    "msg_id": "v.mid:1",
    "type": "v.mt:512",
    "entity_id": null,
    "user_id": "uid:a58fef0f-3604-52d2-a88d-4d74803c031d",
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
}'''
'''
The Codec-encoded & JsonSerdes-serialized message we're testing.
'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Message(ZestBase):

    def pre_set_up(self,
                   # Ignored params:
                   filename:  Literal[None]  = None,
                   extra:     Literal[Tuple] = (),
                   test_type: Literal[None]  = None) -> None:
        super().pre_set_up(filename=__file__)

    def set_up(self):
        self.serdes = JsonSerdes()
        self.codec = Codec()
        self.encoded = MESSAGE_ENCODED
        self.serialized = MESSAGE_SERIALIZED_GOOD

        self._msg_id_gen: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_id_gen: MockUserIdGenerator = UserId.generator(
            unit_testing=True
        )
        '''Generates repeatable user ids for use in testing.'''

        self._uname = 'Tester Jeff'
        '''A user display name for UserID generation.'''

        self._user_id_gen.ut_set_up({
            self._uname: int(
                # Some random UserId value from a run of this test.
                "147d7414-b7bd-5779-96cb-4cc72b19a514".replace('-', ''),
                16),
            })

        self._uid: UserId = self._user_id_gen.next(self._uname)
        '''A user id to use.'''

        self._user_key_gen: MockUserKeyGenerator = UserKey.generator(
            unit_testing=True
        )
        '''Generates repeatable user keys for use in testing.'''
        # TODO: eventually: use a UserKey too.
        # self._user_key_gen.ut_set_up({
        #     self._ukey: int(
        #         # Some random UserKey value from a run of this test.
        #         "TODO: this value".replace('-', ''),
        #         16),
        #     })

        # TODO: eventually: use a UserKey too.
        # self._ukey: UserKey = self._user_key_gen.next(???)
        self._ukey: Optional[UserKey] = None
        '''A user key to use.'''

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

    def make_context(self, test_name: str) -> UnitTestContext:
        context = UnitTestContext(self, test_name=test_name)
        return context

    def fingerprint_string(self, string: str) -> int:
        '''
        Converts string into an integer for testing equality without caring
        about dictionary ordering.

        Sums up the int value of each character.
        '''
        value = 0
        for each in string:
            if each in (' ', '\t', '\n'):
                # Allow for our pretty-printed string vs serialized output's
                # compact string.
                continue
            # Turn the char into an int.
            value += ord(each)
        return value

    def make_message_math(self) -> Message:
        '''
        Create the Message object to use for serialization test.
        '''
        # ------------------------------
        # Unique Message ID
        # ------------------------------
        mid = self._msg_id_gen.next()

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
        # Create/Return Actual Message.
        # ------------------------------
        # Create message with the math payload.
        message = Message(mid, MsgType.ENCODED,
                          payload=payload,
                          user_id=self._uid,
                          user_key=self._ukey,
                          subject=abac.Subject.BROADCAST)
        # str(message):
        #   Message[MonotonicId:001,
        #           MsgType.ENCODED,
        #           UserId:70375a0b-5703-5553-bb7e-c3cda7917c79,
        #           None]
        #   (
        #    <class 'veredi.math.d20.tree.OperatorAdd'>:
        #        OperatorAdd(
        #            Variable(strength.score, 'strength.score'),
        #            Constant(4)
        #        )==34
        #   )

        return message

    def test_init(self):
        self.assertTrue(self.serdes)
        self.assertTrue(self.codec)
        self.assertTrue(self.encoded)

    def test_encode(self):

        # ------------------------------
        # Create the message to be encoded.
        # ------------------------------
        message = self.make_message_math()

        # ------------------------------
        # Encode the message.
        # ------------------------------
        encoded = self.codec.encode(message)

        # ------------------------------
        # Compare encoded.
        # ------------------------------

        # Dict is pretty big; just remove max for this assert so the failure
        # message is more helpful.
        old_max = self.maxDiff
        self.maxDiff = None
        self.assertDictEqual(encoded,
                             self.encoded)
        self.maxDiff = old_max

    def assertMessageEqual(self,
                           expected: Message,
                           message:  Message) -> None:
        '''
        Asserts message fields (except payload) to verify `decoded` matches
        `expected`.

        NOTE: DOES NOT CHECK message.payload CONTENTS!
        '''
        # ------------------------------
        # Do they exist equally?
        # ------------------------------
        exists_expected = bool(expected)
        exists_message = bool(message)
        self.assertEqual(exists_expected, exists_message)

        if expected is None or message is None:
            # Getting here means both are none, since we've asserted they're
            # equal when boolean'd. So this is fine.
            return

        # ------------------------------
        # Do their contents match?
        # ------------------------------
        self.assertEqual(expected.msg_id, message.msg_id)
        self.assertEqual(expected.entity_id, message.entity_id)
        self.assertEqual(expected.user_id, message.user_id)
        self.assertEqual(expected.user_key, message.user_key)
        self.assertEqual(expected.security_subject, message.security_subject)

        # ------------------------------
        # Payload...
        # ------------------------------
        # Can't really do generic check, since payload can be anything.
        self.assertEqual(bool(expected.payload), bool(message.payload))

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

    def test_decode(self):

        # ------------------------------
        # Create the message to compare against.
        # ------------------------------
        # Must exactly match what we will decode!
        expected = self.make_message_math()

        # ------------------------------
        # Decode message.
        # ------------------------------
        decoded = self.codec.decode(
            # We should be able to decode only with the data dictionary.
            None,
            self.encoded)

        self.assertTrue(decoded)

        # ------------------------------
        # Compare.
        # ------------------------------
        self.assertMessageEqual(expected, decoded)
        self.assertMathTreeEqual(expected.payload, decoded.payload)

    def test_serialize(self):

        # ------------------------------
        # Create the message to be serialized.
        # ------------------------------
        message = self.make_message_math()

        # ------------------------------
        # Serialize the message.
        # ------------------------------
        context = self.make_context('test_serialize')
        serialized_stream = self.serdes.serialize(message, self.codec, context)
        serialized = serialized_stream.getvalue()

        # Dict is pretty big; just remove max for this assert so the failure
        # message is more helpful.
        old_max = self.maxDiff
        self.maxDiff = None
        # This probably won't work. We don't order dicts before printing, I
        # don't think...
        self.assertEqual(self.fingerprint_string(serialized),
                         self.fingerprint_string(self.serialized))
        self.maxDiff = old_max

    def test_deserialize(self):

        # ------------------------------
        # Create the message to compare against.
        # ------------------------------
        # Must exactly match what we will decode!
        expected = self.make_message_math()

        # ------------------------------
        # Deserialize message.
        # ------------------------------
        decoded = self.serdes.deserialize(
            self.serialized,
            self.codec,
            self.make_context('test_deserialize'))

        self.assertTrue(decoded)

        # ------------------------------
        # Compare.
        # ------------------------------
        self.assertMessageEqual(expected, decoded)
        self.assertMathTreeEqual(expected.payload, decoded.payload)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi test interface/mediator/zest_message.py

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
