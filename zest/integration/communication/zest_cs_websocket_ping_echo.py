# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.

Tests ping() and echo().
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .base                             import Test_WebSockets_Base
from veredi.zest.base.multiproc        import ProcTest
from veredi.logs                       import log


# ---
# Mediation
# ---
from veredi.interface.mediator.const   import MsgType
from veredi.interface.mediator.message import Message
from veredi.interface.mediator.context import MessageContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO
'''Test should set this to desired during set_up()'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets_Ping_Echo(Test_WebSockets_Base):

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        self.DISABLED_TESTS = set({
            # Nothing, ideally.

            # # ---
            # # This is cheating.
            # # ---
            # 'test_ignored_tests',

            # # ---
            # # More complex tests.
            # # ---
            # 'test_ping',
            # 'test_echo',
        })

        default_flags_server = ProcTest.NONE  # ProcTest.DNE
        default_flags_client = ProcTest.NONE  # ProcTest.DNE
        super().set_up(LOG_LEVEL,
                       default_flags_server,
                       default_flags_client)

    def tear_down(self):
        super().tear_down(LOG_LEVEL)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    def test_ignored_tests(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_ignored_tests))

    # ------------------------------
    # Test cliets pinging server.
    # ------------------------------

    def do_test_ping(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()
        msg = Message(mid, MsgType.PING,
                      payload=None)
        client.send(msg, self.msg_context(mid))
        recv, ctx = client.recv()
        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        self.assertEqual(msg.msg_id, ctx.id)
        self.assertEqual(mid, recv.msg_id)
        self.assertEqual(msg.msg_id, recv.msg_id)
        self.assertEqual(msg.type, recv.type)

        # I really hope the local ping is between negative nothingish and
        # positive five seconds.
        self.assertIsInstance(recv.payload, float)
        self.assertGreater(recv.payload, -0.0000001)
        self.assertLess(recv.payload, 5)

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_ping(self):
        # No other checks for ping outside do_test_ping.
        self.assert_test_ran(
            self.runner_of_test(self.do_test_ping, *self.proc.clients))

    # ------------------------------
    # Test Clients sending an echo message.
    # ------------------------------

    def do_test_echo(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()
        expected = f"Hello from {client.name}"
        send_payload = Message.payload_basic(expected)
        msg = Message(mid, MsgType.ECHO,
                      payload=send_payload)
        ctx = self.msg_context(mid)
        client.send(msg, ctx)
        self.wait(0.5)
        recv, ctx = client.recv()
        # Make sure we got a message back and it has the same
        # message as we sent.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        # IDs made it around intact.
        self.assertEqual(msg.msg_id, ctx.id)
        self.assertEqual(mid, recv.msg_id)
        self.assertEqual(msg.msg_id, recv.msg_id)
        # Sent echo, got echo-back.
        self.assertEqual(msg.type, MsgType.ECHO)
        self.assertEqual(recv.type, MsgType.ECHO_ECHO)
        # Got what we sent.
        self.assertIsInstance(recv.payload, type(send_payload))
        self.assertEqual(recv.payload.data, expected)

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_echo(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_echo, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run zest/integration/communication/zest_cs_websocket_ping_echo.py

if __name__ == '__main__':
    import unittest
    unittest.main()
