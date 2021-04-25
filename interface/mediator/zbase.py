# coding: utf-8

'''
Base class for Message encode/decode unit tests.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Dict


from veredi.logs                    import log

from veredi.zest.base.unit          import ZestBase
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

from .message                       import Message, MsgType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Test_Message_Base(ZestBase):

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp(), before ZestBase.set_up().
        '''
        super()._define_vars()

        # ------------------------------
        # Test ID Generators
        # ------------------------------

        self._msg_id_gen: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_id_gen: MockUserIdGenerator = UserId.generator(
            unit_testing=True
        )
        '''Generates repeatable user ids for use in testing.'''

        self._user_key_gen: MockUserKeyGenerator = UserKey.generator(
            unit_testing=True
        )
        '''Generates repeatable user keys for use in testing.'''

        # ------------------------------
        # Test User
        # ------------------------------

        self._uname: str = 'Tester Jeff'
        '''A user display name for UserID generation.'''

        self._uid: UserId = None
        '''A user id to use.'''

        # TODO: Eventually use a UserKey too.
        # self._ukeygen: str or int or idk = 'something' or 42 or w/e
        # '''An input for user key generation.'''

        self._ukey: Optional[UserKey] = None
        '''A user key to use.'''

        # ------------------------------
        # Serdes / Codec
        # ------------------------------

        self.serdes: JsonSerdes = JsonSerdes()
        '''Serdes to use for testing.'''

        self.codec = Codec()
        '''Codec to use for testing.'''

        # ------------------------------
        # Test Message
        # ------------------------------
        self.payload: Any = None
        '''Payload to use to create `self.message`.'''

        self.message: Message = None
        '''
        Message that should match `self.encoded` and `self.serialized`.
        '''

        self.encoded: Dict = None
        '''
        Encoded dictionary that should match `self.message` and
        `self.serialized`.
        '''

        self.serialized: str = None
        '''
        Serialized string that should match `self.encoded` and
        `self.message`.
        '''

    def set_up(self,
               message_payload:    Any,
               message_encoded:    Dict,
               message_serialized: str,
               user_id:            Optional[str] = None,
               user_key:           Optional[str] = None) -> None:
        '''
        Set up base class with class, encoded, and serialzed versions of the
        same message - for testing serialize/deserialize & encode/decode.
        '''
        # ------------------------------
        # User
        # ------------------------------
        if not user_id:
            # Some random UserId value from a run of this test.
            user_id = "147d7414-b7bd-5779-96cb-4cc72b19a514"

        self._user_id_gen.ut_set_up({
            self._uname: int(user_id.replace('-', ''), 16),
        })
        self._uid = self._user_id_gen.next(self._uname)

        # TODO: eventually: use a UserKey too.
        # if not user_key:
        #     # Some random UserKey value from a run of this test.
        #     user_key = "TODO: this value".replace('-', ''),

        # self._user_key_gen.ut_set_up({
        #     self._ukeygen: int(
        #         # Some random UserKey value from a run of this test.
        #         "TODO: this value".replace('-', ''),
        #         16),
        #     })
        # self._ukey = self._user_key_gen.next(self._ukey)

        # ------------------------------
        # Serdes/Codec
        # ------------------------------
        self.serdes = JsonSerdes()
        self.codec = Codec()

        # ------------------------------
        # Message
        # ------------------------------
        self.payload = message_payload
        self.encoded = message_encoded
        self.serialized = message_serialized

    def tear_down(self):
        self.serdes        = None
        self.codec         = None
        self.message       = None
        self.payload       = None
        self.encoded       = None
        self.serialized    = None
        self._msg_id_gen   = None
        self._user_id_gen  = None
        self._uname        = None
        self._uid          = None
        self._user_key_gen = None
        self._ukey         = None

    # -------------------------------------------------------------------------
    # Helpers: Payload
    # -------------------------------------------------------------------------

    def make_payload(self, payload: Optional[str] = None) -> Any:
        '''
        Default base impl just returns 'self.payload'.

        Override if you need a dynamic payload.
        '''
        payload = payload or self.payload
        self.payload = payload
        self.assertTrue(self.payload)
        return self.payload

    # -------------------------------------------------------------------------
    # Helpers: Message
    # -------------------------------------------------------------------------

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

    def make_message(self) -> Message:
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
        self.make_payload()

        # ------------------------------
        # Create/Return Actual Message.
        # ------------------------------
        # Create message with the math payload.
        self.message = Message(mid, MsgType.ENCODED,
                               payload=self.payload,
                               user_id=self._uid,
                               user_key=self._ukey,
                               subject=abac.Subject.BROADCAST)
        self.assertTrue(self.message)
        return self.message

    def assertPayloadEqual(self,
                           expected: Any,
                           payload:  Any) -> None:
        '''
        Asserts payloads are equal.

        Base implemenation just asserts truthiness are equal. Override if you
        know more about your payloads.
        '''
        # Can't really do generic check, since payload can be anything.
        self.assertEqual(bool(expected), bool(payload))

    def assertMessageEqual(self,
                           expected: Message,
                           message:  Message) -> None:
        '''
        Asserts message fields (except payload) to verify `decoded` matches
        `expected`.

        NOTE: Payloads compared via `self.assertPayloadEqual()`.
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
        self.assertPayloadEqual(expected.payload, message.payload)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def do_test_init(self) -> None:
        '''
        Just assert some stuff exists.
        '''
        self.assertTrue(self._uid)
        # TODO: eventually use a user key too.
        # self.assertTrue(self._ukey)

        self.assertTrue(self.serdes)
        self.assertTrue(self.codec)

        self.assertTrue(self.encoded)
        self.assertTrue(self.serialized)

        self.make_message()
        self.assertTrue(self.payload)
        self.assertTrue(self.message)

    def do_test_encode(self):
        '''
        Encode `self.message` and assert it is equal to our expected output:
        `self.encoded`.
        '''
        # ------------------------------
        # Create the message to be encoded.
        # ------------------------------
        self.make_message()

        # ------------------------------
        # Encode the message.
        # ------------------------------
        encoded = self.codec.encode(self.message)

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

    def do_test_decode(self) -> None:
        '''
        Decode `self.encoded` and assert it is equal to our expected output:
        `self.message`.
        '''
        # ------------------------------
        # Create the message to compare against.
        # ------------------------------
        # Must exactly match what we will decode!
        expected = self.make_message()

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

    def do_test_serialize(self) -> None:
        '''
        Serialize `self.message` and assert it is equal to our expected output:
        `self.serialized`.
        '''
        # ------------------------------
        # Create the message to be serialized.
        # ------------------------------
        message = self.make_message()

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

    def do_test_deserialize(self):
        '''
        Deserialize `self.serialized` and assert it is equal to our expected
        output: `self.message`.
        '''
        # ------------------------------
        # Create the message to compare against.
        # ------------------------------
        # Must exactly match what we will decode!
        expected = self.make_message()

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
