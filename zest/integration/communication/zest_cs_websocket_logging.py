# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .base                                     import Test_WebSockets_Base
from veredi.zest.base.multiproc                import ProcTest
from veredi.logs                               import log


# ---
# Mediation
# ---
from veredi.interface.mediator.const           import MsgType
from veredi.interface.mediator.message         import Message
from veredi.interface.mediator.payload.logging import (LogPayload,
                                                       LogReply,
                                                       LogField,
                                                       Validity,
                                                       _NC_LEVEL)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LOG_LEVEL = log.Level.INFO
'''Test should set this to desired during set_up()'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets_Logging(Test_WebSockets_Base):

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def set_up(self) -> None:
        self.DISABLED_TESTS = set({
            # Nothing, ideally.

            # # ---
            # # Logging tests.
            # # ---
            # 'test_logging',
        })

        default_flags_server = ProcTest.LOG_LEVEL_DELAY
        default_flags_client = ProcTest.LOG_LEVEL_DELAY
        default_flags_logs   = ProcTest.LOG_LEVEL_DELAY
        super().set_up(LOG_LEVEL,
                       default_flags_server,
                       default_flags_client,
                       default_flags_logs)

    def tear_down(self):
        super().tear_down(LOG_LEVEL)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Test Server sending LOGGING to client.
    # ------------------------------

    def _check_ignored_counter(self,
                               assert_eq_value=None,
                               assert_gt_value=None):
        # Check counter if asked.
        if assert_eq_value is not None:
            self.assertEqual(self.proc.log.ignored_counter.value,
                             assert_eq_value)

        if assert_gt_value is not None:
            self.assertGreater(self.proc.log.ignored_counter.value,
                               assert_gt_value)

    def ignore_logging(self,
                       enable,
                       assert_eq_value=None,
                       assert_gt_value=None):
        '''
        Instruct log_server to start or stop ignoring log messages. Will
        assertEqual() or assertGreater() on the ignored_counter if those values
        are not None.

        `enable` should be:
          - True or False to toggle. Asserts before and after values.
          - None to leave alone.
        '''
        if enable is True:
            # Sanity check.
            self.assertFalse(self.proc.log.ignore_logs.is_set())
            was = self.proc.log.ignore_logs.is_set()

            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

            # Start ignoring logs.
            self.proc.log.ignore_logs.set()

            line_pre = '-='
            line_post = '=-'
            line_title = 'logging'
            line_width = 80
            line_padding = line_width - len(line_title)
            line_pad_half = line_padding // 2
            line_titled = ((line_pre * (line_pad_half // len(line_pre)))
                           + line_title
                           + (line_post * (line_pad_half // len(line_post))))
            line_untitled = line_pre * (line_width // 2 - 1) + '-'

            self.log_debug(
                '\n\n'
                + line_titled + '\n'
                + 'IGNORE LOGGING: \n'
                + f'  was    = "{was}" \n'
                + f'  set    = "{self.proc.log.ignore_logs.is_set()}" \n'
                + f'  count  = {self.proc.log.ignored_counter.value} \n'
                + line_untitled
                + '\n\n')

        elif enable is False:
            # Sanity check.
            self.assertTrue(self.proc.log.ignore_logs.is_set())

            # Stop ignoring logs.
            was = self.proc.log.ignore_logs.is_set()
            self.proc.log.ignore_logs.clear()

            line_pre = '-='
            line_post = '=-'
            line_title = 'logging'
            line_width = 80
            line_padding = line_width - len(line_title)
            line_pad_half = line_padding // 2
            line_titled = ((line_pre * (line_pad_half // len(line_pre)))
                           + line_title
                           + (line_post * (line_pad_half // len(line_post))))
            line_untitled = line_pre * (line_width - 1) + '-'

            self.log_debug(
                '\n\n'
                + line_untitled + '\n'
                + 'IGNORE LOGGING: \n'
                + f'  was    = "{was}" \n'
                + f'  set    = "{self.proc.log.ignore_logs.is_set()}" \n'
                + f'  count  = {self.proc.log.ignored_counter.value} \n'
                + line_titled
                + '\n\n')

            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

        elif enable is None:
            # Check counter if asked.
            self._check_ignored_counter(assert_eq_value, assert_gt_value)

        # Um... what?
        else:
            self.fail(f'enabled must be True/False/None. Got: {enable}')

        # Wait a bit so flag propogates to log_server? Maybe? Why isn't
        # this working?
        # It wasn't working because a LogRecordSocketReceiver's 'request' is a
        # whole client, actually, whereas I thought it was a log record.
        self.wait(0.1)

    def do_test_logging(self, client):
        # Get the connect out of the way.
        self.client_connect(client)
        # self.debugging = True

        # ------------------------------
        # NOTE: Unit-Tests Failing?
        # ------------------------------
        # NOTE: Can't figure out why you're getting no logs in here?
        # ---------------
        #   START-NOTE: THIS IS WHY YOUR LOGS ARE MISSING!!!

        if self._ut_is_verbose:
            log.ultra_hyper_debug(
                "YOU ARE NOW IGNORING LOGS!\n"
                "  - This means you can't see what's actually going on now!\n"
                "  - Comment out `ignore_logging` call when debugging!!!")

        # Start ignoring logs.
        self.ignore_logging(True, assert_eq_value=0)

        #   END-NOTE: THIS IS WHY YOUR LOGS ARE MISSING!!!
        # ---------------
        # NOTE: Scoreboard of Embarassment: ||||-
        #       Most Recent Embarassment:   [2021-03-24]
        # ------------------------------

        # Have a client adjust its log level to debug. Should spit out a lot of
        # logs then.
        payload = LogPayload()
        payload.request_level(log.Level.DEBUG)

        mid = self._msg_id.next()
        send_msg = Message.log(mid,
                               client.user_id,
                               client.user_key,
                               payload)

        # self.debugging = True
        with log.LoggingManager.on_or_off(self.debugging):
            send_ctx = self.msg_context(mid)
            # server -> client
            self.proc.server.send(send_msg, send_ctx)
        # self.debugging = False

        # Server should have put client's reply into the unit test pipe so we
        # can check it.
        recv_msg, recv_ctx = self.proc.server._ut_recv()

        # Make sure we got a LOGGING message reply back.
        self.assertTrue(recv_msg)
        self.assertIsInstance(recv_msg, Message)
        # Sent logging... right?
        self.assertEqual(send_msg.type, MsgType.LOGGING)
        # Got logging... right?
        self.assertEqual(recv_msg.type, MsgType.LOGGING)

        # Got logging response?
        self.assertIsInstance(recv_msg.payload, LogPayload)
        report = recv_msg.payload.report
        self.assertIsNotNone(report)
        level = report[LogField.LEVEL]

        # Got reply for our level request?
        self.assertIsInstance(level, LogReply)
        self.assertEqual(level.valid, Validity.VALID)

        # Got /valid/ reply?
        self.assertTrue(LogReply.validity(level.value, _NC_LEVEL),
                        Validity.VALID)

        # Client reports they're now at the level we requested?
        self.assertEqual(level.value, log.Level.DEBUG)

        # Client should have push into the ut_pipe too.
        # Don't really care, at the moment, but we do care to
        # assert_empty_pipes() for other reasons so get this one out.
        recv_msg_client, recv_ctx_client = client._ut_recv()
        self.assertTrue(recv_msg_client)
        self.assertIsInstance(recv_msg_client, Message)
        self.assertEqual(recv_msg_client.type, MsgType.LOGGING)

        self.wait(0.1)

        # Stop ignoring logs and make sure we ignored something, at least,
        # right? Well... either have to tell client to go back to previous
        # logging level or we have to keep ignoring. Clean-up / tear-down has
        # logs too.
        self.ignore_logging(None, assert_gt_value=2)

        if self._ut_is_verbose:
            log.ultra_hyper_debug(
                "YOU ARE DONE IGNORING LOGS!\n"
                "  - This means you just missed a lot of logs...\n"
                "  - Comment out `ignore_logging` call when debugging!!!")

        # Make sure we don't have anything in the queues...
        self.assert_empty_pipes()

    def test_logging(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_logging, *self.proc.clients))


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run zest/integration/communication/zest_client_server_websocket

if __name__ == '__main__':
    import unittest
    unittest.main()
