# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .base                                  import Test_WebSockets_Base
from veredi.zest.base.multiproc             import ProcTest
from veredi.logs                            import log


# ---
# Mediation
# ---
from veredi.interface.mediator.const        import MsgType
from veredi.interface.mediator.message      import Message
from veredi.interface.mediator.context      import MessageContext
from veredi.interface.mediator.payload.bare import BarePayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO
'''Test should set this to desired during set_up()'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets_Text(Test_WebSockets_Base):

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
            # # Skip actual tests?
            # # ---
            # 'test_text',
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
    # Test Clients sending text messages to server.
    # ------------------------------

    def do_test_text(self, client):
        # Get the connect out of the way.
        self.client_connect(client)

        mid = self._msg_id.next()

        # ---
        # Client -> Server: TEXT
        # ---
        self.log_debug("client to server...")

        expected = f"Hello from {client.name}?"
        send_payload = Message.payload_basic(expected)
        client_send = Message(mid, MsgType.TEXT,
                              payload=send_payload)
        client_send_ctx = self.msg_context(mid)

        client_recv_msg = None
        client_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Have client send, then receive from server.
            client.send(client_send, client_send_ctx)

            # Server automatically sent an ACK_ID, need to check client.
            client_recv_msg, client_recv_ctx = client.recv()

        self.log_debug("client send msg: {}", client_send)
        # Why is this dying when trying to print its payload?!
        # # self.log_ultra_mega_debug(
        # #     "client_recv msg: {client_recv_msg._payload}")
        # ...
        # ...Huh... f-strings and veredi.logger and multiprocessor or
        # log_server or something don't like each other somewhere along
        # the way? This is a-ok:
        self.log_debug("client_recv msg: {}", client_recv_msg._payload)

        # Make sure that the client received the correct thing.
        self.assertIsNotNone(client_recv_msg)
        self.assertIsInstance(client_recv_msg, Message)
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)
        self.assertEqual(mid, client_recv_msg.msg_id)
        self.assertEqual(client_send.msg_id, client_recv_msg.msg_id)
        self.assertEqual(client_recv_msg.type, MsgType.ACK_ID)
        ack_id = client_recv_msg.payload
        self.assertIsInstance(ack_id, type(mid))

        # ---
        # Check: Client -> Server: TEXT
        # ---
        self.log_debug("test_text: server to game...")
        server_recv_msg = None
        server_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Our server should have put the client's packet in its pipe for
            # us... I hope.
            self.log_debug("test_text: game recv from server...")
            server_recv_msg, server_recv_ctx = self.proc.server.recv()

        self.log_debug("client_sent/server_recv: {}", server_recv_msg)
        # Make sure that the server received the correct thing.
        self.assertEqual(mid, server_recv_msg.msg_id)
        self.assertEqual(client_send.msg_id, server_recv_msg.msg_id)
        self.assertEqual(client_send.type, server_recv_msg.type)
        self.assertIsInstance(server_recv_msg.payload, BarePayload)
        self.assertEqual(server_recv_msg.payload.data, expected)
        # Check the Context.
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(server_recv_ctx.id, ack_id)

        # ---
        # Server -> Client: TEXT
        # ---

        self.log_debug("test_text: server_send/client_recv...")
        # Tell our server to send a reply to the client's text.
        recv_txt = f"Hello from {self.proc.server.name}!"
        server_send = Message(server_recv_ctx.id, MsgType.TEXT,
                              user_id=server_recv_msg.user_id,
                              user_key=server_recv_msg.user_key,
                              payload=recv_txt)

        client_recv_msg = None
        client_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Make something for server to send and client to recvive.
            self.log_debug("test_text: server_send...")
            self.log_debug("test_text: pipe to game: {}", server_send)
            self.proc.server.send(server_send, server_recv_ctx)
            self.log_debug("test_text: client_recv...")
            client_recv_msg, client_recv_ctx = client.recv()

        self.log_debug("server_sent/client_recv: {}", client_recv_msg)
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)

        self.assertIsInstance(client_recv_msg, Message)
        self.assertEqual(ack_id, client_recv_msg.msg_id)
        self.assertEqual(server_send.msg_id, client_recv_msg.msg_id)
        self.assertEqual(server_send.type, client_recv_msg.type)
        self.assertIsInstance(client_recv_msg.payload, str)
        self.assertEqual(client_recv_msg.payload, recv_txt)

        # ---
        # Server -> Client: ACK
        # ---

        # Client automatically sent an ACK_ID, need to check server for it.
        server_recv = self.proc.server.recv()

        self.log_debug("server sent msg: {}", server_send)
        self.log_debug("server recv ack: {}", server_recv)
        # Make sure that the server received the correct thing.
        self.assertIsNotNone(server_recv)
        self.assertIsInstance(server_recv, tuple)
        self.assertEqual(len(server_recv), 2)  # Make sure next line is sane...
        server_recv_msg, server_recv_ctx = server_recv
        # Make sure that the server received their ACK_ID.
        self.assertIsNotNone(server_recv_msg)
        self.assertIsInstance(server_recv_msg, Message)
        self.assertIsNotNone(server_recv_ctx)
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(mid, server_recv_msg.msg_id)
        self.assertEqual(server_send.msg_id, server_recv_msg.msg_id)
        self.assertEqual(server_recv_msg.type, MsgType.ACK_ID)
        ack_id = server_recv_msg.payload
        self.assertIsInstance(ack_id, type(mid))

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_text(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_text, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run zest/integration/communication/zest_client_server_websocket

if __name__ == '__main__':
    import unittest
    unittest.main()
