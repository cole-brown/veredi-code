#!/usr/bin/env python3

# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Dict, Tuple, Literal


from .zbase                                    import Test_Message_Base

from veredi.logs                               import log

from veredi.base.context                       import UnitTestContext

from veredi.data.codec                         import Codec
from veredi.data.serdes.json.serdes            import JsonSerdes
from veredi.base.identity                      import (MonotonicId,
                                                       MonotonicIdGenerator)
from veredi.data.identity                      import (UserId,
                                                       MockUserIdGenerator,
                                                       UserKey,
                                                       MockUserKeyGenerator)
from veredi.security                           import abac
from veredi.interface.mediator.payload.logging import (LogPayload,
                                                       LogReply,
                                                       LogField,
                                                       Validity,
                                                       _NC_LEVEL)

from .message                                  import Message, MsgType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MESSAGE_ENCODED: Dict = {
    'v.codec': 'veredi.interface.mediator.message.message',
    'v.payload': {
        'msg_id': 'v.mid:1',
        'type': 'v.mt:8',
        'entity_id': None,
        'user_id': 'uid:147d7414-b7bd-5779-96cb-4cc72b19a514',
        'user_key': None,
        'payload': {
            'v.codec': 'veredi.interface.mediator.payload.log.payload',
            'v.payload': {
                'valid': 'valid:3',
                'data': {
                    'field:REQUEST': {
                        'field:LEVEL': 'log.level:DEBUG',
                    }
                },
                'encoded.type': 'payload.log'
            }
        },
        'security': None,
        'encoded.type': 'message'
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
    "type": "v.mt:8",
    "entity_id": null,
    "user_id": "uid:147d7414-b7bd-5779-96cb-4cc72b19a514",
    "user_key": null,
    "payload": {
      "v.codec": "veredi.interface.mediator.payload.log.payload",
      "v.payload": {
        "valid": "valid:3",
        "data": {
          "field:REQUEST": {
            "field:LEVEL": "log.level:DEBUG"
          }
        },
        "encoded.type": "payload.log"
      }
    },
    "security": null,
    "encoded.type": "message"
  }
}'''
'''
The Codec-encoded & JsonSerdes-serialized logging message we're testing.
'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Message_Logging(Test_Message_Base):

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
        # Make log level DEBUG payload.
        # ------------------------------
        payload = LogPayload()
        payload.request_level(log.Level.DEBUG)

        self.assertTrue(payload)
        log_request = payload.request
        self.assertTrue(log_request)
        self.assertEqual(log_request[LogField.LEVEL], log.Level.DEBUG)

        # ------------------------------
        # Let parent do their thing to it now; will end up in `self.payload`.
        # ------------------------------
        return super().make_payload(payload=payload)

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
        self.message = Message.log(mid,
                                   self._uid,
                                   self._ukey,
                                   self.payload)

        self.assertTrue(self.message)
        return self.message

    # -------------------------------------------------------------------------
    # Helpers: Logging Payload Asserts
    # -------------------------------------------------------------------------

    def assertLogPayloadEqual(self,
                              expected: LogPayload,
                              payload:  LogPayload) -> None:
        '''
        Asserts `payload` is a LogPayload that matches `expected`.
        '''
        self.assertEqual(bool(expected), bool(payload))
        self.assertIsInstance(expected, LogPayload)
        self.assertIsInstance(payload, LogPayload)

        # ------------------------------
        # Check: Request Field
        # ------------------------------
        self.assertTrue(expected.request)
        self.assertTrue(payload.request)

        self.assertIn(LogField.LEVEL, expected.request)
        self.assertIn(LogField.LEVEL, payload.request)

        self.assertEqual(expected.request[LogField.LEVEL],
                         log.Level.DEBUG)
        self.assertEqual(expected.request[LogField.LEVEL],
                         payload.request[LogField.LEVEL])

        # Request's LEVEL should be only field...
        payload.request.pop(LogField.LEVEL)
        self.assertFalse(payload.request)

    def assertPayloadEqual(self, expected, payload):
        super().assertPayloadEqual(expected, payload)
        self.assertLogPayloadEqual(expected, payload)

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
#   doc-veredi test interface/mediator/zest_message_logging.py

if __name__ == '__main__':
    import unittest
    unittest.main()
