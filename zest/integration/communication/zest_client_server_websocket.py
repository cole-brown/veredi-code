# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Callable, Iterable

import unittest

import multiprocessing
import multiprocessing.connection
import signal
from collections import namedtuple
import time

from veredi.zest import zmake, zpath
from veredi.logger                      import log, log_server, log_client


# ---
# Need these to register...
# ---
from veredi.data.codec.json import codec


# ---
# Delete these?
# ---
from veredi.base.null                       import Null
from veredi.base.context                    import UnitTestContext
from veredi.data.context                    import (DataGameContext,
                                                    DataLoadContext)
from veredi.data.exceptions                 import LoadError
from veredi.time.timer                      import MonotonicTimer
from veredi.base.identity        import MonotonicId

from veredi.game.ecs.const                  import DebugFlag
from veredi.game.ecs.base.identity          import ComponentId
from veredi.game.data.component             import DataComponent

from veredi.game.data.event                 import (DataLoadRequest,
                                                    DataLoadedEvent)

from veredi.interface.input.event           import CommandInputEvent
from veredi.interface.input.context         import InputContext
from veredi.interface.output.system         import OutputSystem
from veredi.interface.output.event          import OutputType

from veredi.rules.d20.pf2.ability.system    import AbilitySystem
from veredi.rules.d20.pf2.ability.event     import AbilityResult
from veredi.rules.d20.pf2.ability.component import AbilityComponent

from veredi.math.system                     import MathSystem
from veredi.game.data.identity.system       import IdentitySystem
from veredi.game.data.identity.component    import IdentityComponent
from veredi.rules.d20.pf2.health.component  import HealthComponent


from veredi.interface.mediator.mediator import Mediator
from veredi.interface.mediator.message  import Message, MsgType
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context           import (MediatorServerContext,
                                                 MessageContext)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ---
# TODO: put these in config?
# -start-
WAIT_SLEEP_TIME_SEC = 0.1
'''Main process will wait/sleep on the game_over flag for this long each go.'''

GRACEFUL_SHUTDOWN_TIME_SEC = 15.0
'''
Main process will give the game/mediator this long to gracefully shutdown.
If they take longer, it will just terminate them.
'''
# -end-
# TODO
# ---

# TODO: this is... ignored?
LOG_LEVEL = log.Level.WARNING
'''Test should set this to desired during setUp()'''

TestProc = namedtuple('TestProc', ['name', 'process', 'pipe'])

StopRetVal = namedtuple('StopRetVal',
                        ['mediator_grace', 'log_grace',
                         'mediator_terminate', 'log_terminate'])


# -----------------------------------------------------------------------------
# Multiprocessing Helper
# -----------------------------------------------------------------------------

def _sigint_ignore() -> None:
    # Child processes will ignore sigint and rely on the main process to
    # tell them to stop.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _sigalrm_start(timeout: float, handler: Callable) -> None:
    '''
    Sets SIGALRM to go off in `timeout` seconds if not cancelled. Will call
    `handler` function if it raises the signal.
    '''
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)


def _sigalrm_end() -> None:
    '''
    Disables SIGALRM.
    '''
    signal.alarm(0)


# -----------------------------------------------------------------------------
# Multiprocessing Runners
# -----------------------------------------------------------------------------

def run_logs(proc_name     = None,
             log_level     = None,
             shutdown_flag = None) -> None:
    '''
    Inits and runs logging server.
    '''
    _sigint_ignore()
    server = log_server.init(shutdown_flag, log_level)

    # TODO: debug level
    lumberjack = log.get_logger(proc_name)
    lumberjack.debug(f"Starting log_server '{proc_name}'...")

    # log_server.run() should never return (until shutdown signaled) - it just
    # listens on the socket connection for logs to process forever.
    log_server.run(server, proc_name)


def run_server(proc_name     = None,
               conn          = None,
               config        = None,
               log_level     = None,
               shutdown_flag = None) -> None:
    '''
    Init and run client/engine IO mediator.
    '''
    _sigint_ignore()
    log_client.init(log_level)

    lumberjack = log.get_logger(proc_name)
    if not conn:
        raise log.exception(
            "Mediator requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not config:
        raise log.exception(
            "Mediator requires a configuration; received None.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            "Mediator requires a default log level (int); received None.",
            veredi_logger=lumberjack)
    if not shutdown_flag:
        raise log.exception(
            "Mediator requires a shutdown flag; received None.",
            veredi_logger=lumberjack)

    # TODO: debug level
    lumberjack.debug(f"Starting WebSocketServer '{proc_name}'...")
    mediator = WebSocketServer(config, conn, shutdown_flag)
    mediator.start()


def run_client(proc_name     = None,
               conn          = None,
               config        = None,
               log_level     = None,
               shutdown_flag = None) -> None:
    '''
    Init and run client/engine IO mediator.
    '''
    _sigint_ignore()
    log_client.init(log_level)

    lumberjack = log.get_logger(proc_name)
    if not conn:
        raise log.exception(
            "Mediator requires a pipe connection; received None.",
            veredi_logger=lumberjack)
    if not config:
        raise log.exception(
            "Mediator requires a configuration; received None.",
            veredi_logger=lumberjack)
    if not log_level:
        raise log.exception(
            "Mediator requires a default log level (int); received None.",
            veredi_logger=lumberjack)
    if not shutdown_flag:
        raise log.exception(
            "Mediator requires a shutdown flag; received None.",
            veredi_logger=lumberjack)

    # TODO: debug level
    lumberjack.debug(f"Starting WebSocketClient '{proc_name}'...")
    mediator = WebSocketClient(config, conn, shutdown_flag)
    mediator.start()


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets(unittest.TestCase):

    PER_TEST_TIMEOUT = 5  # seconds

    # TODO [2020-07-25]: 2 or 4 or something!
    NUM_CLIENTS = 1

    NAME_LOG = 'veredi.test.websockets.log'
    NAME_SERVER = 'veredi.test.websockets.server'
    NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'
    NAME_MAIN = 'veredi.test.websockets.tester'

    # ------------------------------
    # Set-Up & Tear-Down
    # ------------------------------

    def setUp(self):
        self.debug_flags = DebugFlag.UNIT_TESTS
        self.debugging = False

        self._shutdown = multiprocessing.Event()
        self._shutdown_log = multiprocessing.Event()

        self._msg_id = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._log_server: TestProc = None
        '''Our Logging Server process.'''

        self._server: TestProc = None
        '''Our WebSocket Server process and pipe.'''

        self._clients: Iterable[TestProc] = []
        '''Our WebSocket Client processes and pipes in an indexable list.'''

        config = zmake.config(zpath.TestType.INTEGRATION,
                              'config.websocket.yaml')

        self._set_up_log(config)
        self._set_up_server(config)
        self._set_up_clients(config)

    def tearDown(self):
        self._stop_mediators()
        self._tear_down_server()
        self._tear_down_clients()

        self._stop_logs()
        self._tear_down_log()

        self.debug_flags = None
        self._shutdown = None
        self._shutdown_log = None
        self._msg_id = None

    # ---
    # Log Set-Up / Tear-Down
    # ---

    def _set_up_log(self, config):
        name = self.NAME_LOG
        self._log_server = TestProc(
            name,
            multiprocessing.Process(
                target=run_logs,
                name=name,
                kwargs={
                    'proc_name':     name,
                    'log_level':     LOG_LEVEL,
                    'shutdown_flag': self._shutdown_log,
                }),
            None)

    def _tear_down_log(self):
        # Ask log server to stop if we haven't already...
        if not self._shutdown_log.is_set():
            self._stop_logs()

        self._log_server = None

    # ---
    # Server Set-Up / Tear-Down
    # ---

    def _set_up_server(self, config):
        name = self.NAME_SERVER
        mediator_conn, test_conn = multiprocessing.Pipe()
        self._server = TestProc(
            name,
            multiprocessing.Process(
                target=run_server,
                name=name,
                kwargs={
                    'proc_name':     name,
                    'conn':          mediator_conn,
                    'config':        config,
                    'log_level':     LOG_LEVEL,
                    'shutdown_flag': self._shutdown,
                }),
            test_conn)

    def _tear_down_server(self):
        # Ask all mediators to stop if we haven't already...
        if not self._shutdown.is_set():
            self._stop_mediators()

        self._server = None

    # ---
    # Clients Set-Up / Tear-Down
    # ---

    def _set_up_clients(self, config):
        self._clients = []
        for i in range(self.NUM_CLIENTS):
            mediator_conn, test_conn = multiprocessing.Pipe()
            name = self.NAME_CLIENT_FMT.format(i=i)
            self._clients.append(
                TestProc(
                    name,
                    multiprocessing.Process(
                        target=run_client,
                        name=name,
                        kwargs={
                            'proc_name':     name,
                            'conn':          mediator_conn,
                            'config':        config,
                            'log_level':     LOG_LEVEL,
                            'shutdown_flag': self._shutdown,
                        }),
                    test_conn))

    def _tear_down_clients(self):
        # Ask all mediators to stop if we haven't already...
        if not self._shutdown.is_set():
            self._stop_mediators()

        self._clients = None

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def per_test_timeout(self, sig_triggered, frame):
        '''
        Stop our processes and fail test due to timeout.
        '''
        _sigalrm_end()
        self.per_test_tear_down()
        self.fail(f"Test failure due to {signal.Signal(sig_triggered)} "
                  f"timeout. frame: {frame}")

    def per_test_set_up(self):
        # Let it all run and wait for the game to end...
        _sigalrm_start(self.PER_TEST_TIMEOUT, self.per_test_timeout)

        self._log_server.process.start()
        self._server.process.start()
        for client in self._clients:
            client.process.start()

        # Wait for clients, server to settle out.
        self.wait(1)
        _sigalrm_end()

    def per_test_tear_down(self):
        self.stop()

    def runner_of_test(self, body, *args):
        '''
        Runs `per_test_set_up`, then runs function `body` with catch for
        KeyboardInterrupt (aka SIGINT), then finishes off with
        `per_test_tear_down`.

        If `args`, will run `body` with each arg entry (unpacked if tuple).
        '''
        self.per_test_set_up()

        error = False
        sig_int = False

        _sigalrm_start(self.PER_TEST_TIMEOUT, self.per_test_timeout)
        try:
            if args:
                for test_arg in args:
                    # If we have args, call body for each one. Unpack its args
                    # for call if it is a (normal) tuple.
                    if (not isinstance(test_arg, TestProc)
                            and isinstance(test_arg, tuple)):
                        body(*test_arg)
                    else:
                        body(test_arg)
            else:
                # No extra args; just run body arg-less.
                body()
        except KeyboardInterrupt as err:
            sig_int = True
            error = err
        except AssertionError as err:
            # Reraise these - should be unittest assertions.
            raise err
        except Exception as err:
            error = err
        finally:
            _sigalrm_end()
            self.per_test_tear_down()

        return (sig_int, error)

    def assert_test_ran(self, *test_runner_ret_vals):
        got_sig_int = None
        error = None

        # Accept (tuple, values) and ((tuple, values),):
        if len(test_runner_ret_vals) == 1:
            test_runner_ret_vals = test_runner_ret_vals[0]

        self.assertEqual(len(test_runner_ret_vals), 2,
                         "Expecting a 2-tuple for my arg, got: "
                         f"{test_runner_ret_vals}")
        (got_sig_int, error) = test_runner_ret_vals

        if got_sig_int:
            self.assertFalse(error,
                             msg="SIGINT/KeyboardInterrupt raised during test")
        elif error:
            self.assertFalse(error,
                             msg="Exception raised at some point during test.")

    def wait(self,
             wait_timeout,
             loop_timeout=WAIT_SLEEP_TIME_SEC) -> None:
        '''
        Loops waiting on `self._shutdown` flag or Ctrl-C/SIGINT. Each loop it
        will sleep/await the shutdown flag for `loop_timeout` seconds. The
        maximum amount this will wait is `wait_timeout` seconds.

        Does not call self.stop() or do any clean up after waiting.
        '''
        lumberjack = log.get_logger(self.NAME_MAIN)

        # Get rid of None, force timeout into range.
        wait_timeout = wait_timeout or 0
        if (wait_timeout < 0.000001
                or wait_timeout > 5):
            # This is a unit test, so we waint to time out and we want to do it
            # soonish... So timeout between quite soonish to 5 sec.
            wait_timeout = min(max(0.000001, wait_timeout), 5)

        # Get rid of None, force timeout into range.
        loop_timeout = loop_timeout or 0
        if (loop_timeout < 0.000001
                or loop_timeout > 5):
            # This is a unit test, so we waint to time out and we want to do it
            # soonish... So timeout between quite soonish to 5 sec.
            loop_timeout = min(max(0.000001, loop_timeout), 5)

        timer = MonotonicTimer()  # Timer starts timing on creation.
        try:
            # check shutdown flag...
            running = not self._shutdown.wait(timeout=WAIT_SLEEP_TIME_SEC)
            while running and not timer.timed_out(wait_timeout):
                # Do nothing and take naps forever until SIGINT received or
                # game finished.
                running = not self._shutdown.wait(timeout=WAIT_SLEEP_TIME_SEC)

        except KeyboardInterrupt:
            # First, ask for a gentle, graceful shutdown...
            log.debug("Received SIGINT.",
                      veredi_logger=lumberjack)

        else:
            log.debug("wait finished normally.")

    def stop(self):
        # Finally, stop the processes.
        stopped = self._stop()

        # Figure out our exitcode return value.
        exitcode = self._reduce_exitcodes()

        self._assert_stopped(stopped, exitcode)

    def _assert_stopped(self, stop_retval, reduced_exitcode):
        '''
        Asserts that return values from self._stop() and
        self._reduce_exitcodes() are all good return values and indicate
        properly stopped processes.
        '''
        # ---
        # Ok... Now assert stuff.
        # Tried to kill the procs a few ways and gave them some time to die, so
        # assert what we remember about that.
        # ---

        # I really want them to all have died by now...
        self.assertIsNotNone(reduced_exitcode)

        # I don't want to have had to call in the terminators.
        self.assertFalse(stop_retval.log_terminate)
        self.assertFalse(stop_retval.mediator_terminate)

        # I do want the processes to have ended gracefully with their shutdown
        # flag.
        self.assertTrue(stop_retval.log_grace)
        self.assertTrue(stop_retval.mediator_grace)

        # I really want them to have all exited with a successful exit code.
        # self.assertIn(reduced_exitcode, (0, -signal.SIGINT))
        self.assertEqual(reduced_exitcode, 0)
        # -15 is -SIGTERM, fyi...
        #   https://man7.org/linux/man-pages/man7/signal.7.html

    def _stop(self):
        '''
        Stops all processes.

        First asks for a graceful stop via self._stop_<blank>().
        If that fails, asks for a less graceful stop via Process.terminate().

        Returns StopRetVal (named 4-tuple of bools) on how it did.
        '''
        mediators_ok = self._stop_mediators()
        log_ok = self._stop_logs()

        # Give up and ask for the terminator... If necessary.
        mediator_terminator = False
        log_terminator = False
        if self._server.process.exitcode is None:
            # Still not exited; terminate it.
            self._server.process.terminate()
            mediator_terminator = True
        for client in self._clients:
            if client.process.exitcode is None:
                # Still not exited; terminate it.
                client.process.terminate()
                mediator_terminator = True
        if self._log_server.process.exitcode is None:
            # Still not exited; terminate it.
            self._log_server.process.terminate()
            log_terminator = True

        return StopRetVal(mediators_ok, log_ok,
                          mediator_terminator, log_terminator)

    def _reduce_exitcodes(self):
        '''
        Reduced all our child processes' (current) exitcodes down to one.
        Will take worst of (in worst-to-best order):
          - None
          - any non-zero
          - zero
        and return that as the exitcode of choice.

        Zero is only returned when all child processes have exited with a
        successful (0) exitcode.
        '''
        # We 'reduce' the exit code by:
        #   1) Starting off assuming the best (0).
        #   2) Exiting early with `None` if found.
        #   3) Replacing our return value with non-zero if found.

        # Short nap for our kids to clean up...
        time.sleep(0.1)

        # Assume the best... replace with the worst.
        exitcode = 0

        # ---
        # Check server:
        # ---
        if self._server.process.exitcode is None:
            exitcode = None
            return exitcode
        elif self._server.process.exitcode == 0:
            pass
        else:
            exitcode = self._server.process.exitcode

        # ---
        # Check Clients:
        # ---
        for client in self._clients:
            if client.process.exitcode is None:
                exitcode = None
                return exitcode
            elif client.process.exitcode == 0:
                pass
            else:
                exitcode = client.process.exitcode

        # ---
        # Check Log Server:
        # ---
        if self._log_server.process.exitcode is None:
            exitcode = None
            return exitcode
        elif self._log_server.process.exitcode == 0:
            pass
        else:
            exitcode = self._log_server.process.exitcode

        return exitcode

    def _mediators_stopped(self):
        '''
        Did it all shutdown and gave a good exit code?
        '''
        all_good = True
        for client in self._clients:
            all_good = all_good and (client.process.exitcode == 0)
        all_good = all_good and (self._server.process.exitcode == 0)
        return all_good

    def _log_stopped(self):
        '''
        Did log server shutdown and gave a good exit code?
        '''
        return (self._log_server.process.exitcode == 0)

    def _stop_mediators(self):
        '''
        Sets the shutdown flag. Mediators should notice and go into
        graceful shutdown.
        '''
        if ((not self._clients and not self._server)
                or self._mediators_stopped()):
            return

        lumberjack = log.get_logger(self.NAME_MAIN)

        log.debug("Asking mediators to end gracefully...",
                  veredi_logger=lumberjack)
        # Turn on shutdown flag to do the asking.
        self._shutdown.set()

        # Wait on clients to be done.
        log.debug("Waiting for client mediators to complete "
                  "structured shutdown...",
                  veredi_logger=lumberjack)
        for client in self._clients:
            log.debug(f"  Client {client.name}...",
                      veredi_logger=lumberjack)
            client.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
            log.debug("    Done.",
                      veredi_logger=lumberjack)

        # Wait on server now.
        log.debug("Waiting for server mediator to complete "
                  "structured shutdown...",
                  veredi_logger=lumberjack)
        log.debug(f"  Server {self._server.name}...",
                  veredi_logger=lumberjack)
        self._server.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
        log.debug("    Done.",
                  veredi_logger=lumberjack)

        # Did it all shutdown and gave a good exit code?
        return self._mediators_stopped()

    def _stop_logs(self):
        '''
        Sets the logs_end flag. Logs server should notice and gracefully shut
        down.
        '''
        if not self._log_server or self._log_stopped():
            return

        lumberjack = log.get_logger(self.NAME_LOG)

        # Set the game_end flag. They should notice soon and start doing
        # their shutdown.
        log.debug("Asking logs server to end gracefully...",
                  veredi_logger=lumberjack)
        self._shutdown_log.set()

        # Wait for log server to be done.
        log.debug("Waiting for logs server to complete structured shutdown...",
                  veredi_logger=lumberjack)
        self._log_server.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)

        # # Make sure it shutdown and gave a good exit code.
        # self.assertEqual(self._log_server.exitcode, 0)
        return (self._log_server.process.exitcode == 0)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def do_test_nothing(self):
        # This really doesn't do much other than bring up the processes and
        # then kill them, but it's something.
        self.wait(0.1)

    # def test_nothing(self):
    #     # No checks for this, really. Just "does it properly not explode"?
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_nothing))

    # ------------------------------
    # Test cliets pinging server.
    # ------------------------------

    def do_test_ping(self, client):
        mid = self._msg_id.next()
        msg = Message(mid, MsgType.PING, None)
        client.pipe.send(msg)
        recv = client.pipe.recv()
        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertEqual(mid, recv.id)
        self.assertEqual(msg.id, recv.id)
        self.assertEqual(msg.type, recv.type)

        # I really hope the ping is between negative nothingish and
        # positive five seconds.
        self.assertIsInstance(recv.message, float)
        self.assertGreater(recv.message, -0.0000001)
        self.assertLess(recv.message, 5)

    # def test_ping(self):
    #     # No other checks for ping outside do_test_ping.
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_ping, *self._clients))

    # ------------------------------
    # Test Clients sending an echo message.
    # ------------------------------

    def do_test_echo(self, client):
        mid = self._msg_id.next()
        send_msg = f"Hello from {client.name}"
        expected = send_msg
        msg = Message(mid, MsgType.ECHO, send_msg)
        # self.debugging = True
        with log.LoggingManager.on_or_off(self.debugging, True):
            client.pipe.send(msg)
            recv = client.pipe.recv()
        # Make sure we got a message back and it has the same
        # message as we sent.
        self.assertTrue(recv)
        self.assertEqual(mid, recv.id)
        self.assertEqual(msg.id, recv.id)
        self.assertEqual(msg.type, recv.type)
        self.assertIsInstance(recv.message, str)
        self.assertEqual(recv.message, expected)

    # def test_echo(self):
    #     self.assert_test_ran(
    #         self.runner_of_test(self.do_test_echo, *self._clients))

    # ------------------------------
    # Test Clients sending text messages to server.
    # ------------------------------

    def do_test_text(self, client):
        mid = self._msg_id.next()
        self.debugging = True

        # ---
        # Client -> Server: TEXT
        # ---
        print(f"\n\ntest_text: client to server...")

        send_txt = f"Hello from {client.name}?"
        client_send = Message(mid, MsgType.TEXT, send_txt)

        client_recv = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Have client send, then receive from server.
            client.pipe.send(client_send)

            # Server automatically sent an ACK_ID, need to check client.
            client_recv = client.pipe.recv()

        print(f"\n\ntest_text: client send msg: {client_send}")
        print(f"\n\ntest_text: client recv ack: {client_recv}")
        # Make sure that the client received their ACK_ID.
        self.assertIsNotNone(client_recv)
        self.assertIsInstance(client_recv, Message)
        self.assertEqual(mid, client_recv.id)
        self.assertEqual(client_send.id, client_recv.id)
        self.assertEqual(client_recv.type, MsgType.ACK_ID)
        ack_id = mid.decode(client_recv.message)
        self.assertIsInstance(ack_id, type(mid))

        # ---
        # Check: Client -> Server: TEXT
        # ---
        print(f"\n\ntest_text: server to game...")
        server_recv = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Our server should have put the client's packet in its pipe for
            # us... I hope.
            print(f"\n\ntest_text: game recv from server...")
            server_recv = self._server.pipe.recv()

        print(f"\n\ntest_text: client_sent/server_recv: {server_recv}")
        # Make sure that the server received the correct thing.
        self.assertIsNotNone(server_recv)
        self.assertIsInstance(server_recv, tuple)
        self.assertEqual(len(server_recv), 2)  # Make sure next line is sane...
        server_recv_msg, server_recv_ctx = server_recv
        # Check the Message.
        self.assertEqual(mid, server_recv_msg.id)
        self.assertEqual(client_send.id, server_recv_msg.id)
        self.assertEqual(client_send.type, server_recv_msg.type)
        self.assertIsInstance(server_recv_msg.message, str)
        self.assertEqual(server_recv_msg.message, send_txt)
        # Check the Context.
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(server_recv_ctx.id, ack_id)

        # ---
        # Server -> Client: TEXT
        # ---

        print(f"\n\ntest_text: server_send/client_recv...")
        # Tell our server to send a reply to the client's text.
        recv_txt = f"Hello from {self._server.name}!"
        server_send = Message(server_recv_ctx.id, MsgType.TEXT, recv_txt)
        client_recv = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Make something for server to send and client to recvive.
            print(f"\n\ntest_text: server_send...")
            self._server.pipe.send((server_send, server_recv_ctx))
            print(f"\n\ntest_text: client_recv...")
            client_recv = client.pipe.recv()

        print(f"\n\ntest_text: server_sent/client_recv: {client_recv}")
        # Make sure the client got the correct message back.
        self.assertIsNotNone(client_recv)
        self.assertIsInstance(client_recv, Message)
        self.assertEqual(ack_id, client_recv.id)
        self.assertEqual(server_send.id, client_recv.id)
        self.assertEqual(server_send.type, client_recv.type)
        self.assertIsInstance(client_recv.message, str)
        self.assertEqual(client_recv.message, recv_txt)



        # recv_txt = f"Hello from {server.name}!"
        # server_send = Message(mid, MsgType.TEXT, recv_txt)


        #    # client_recv = client.pipe.recv()



        # self.debugging = True

        # print(f"\n\ntest_text: server_sent/client_recv: {client_recv}")
        # # Make sure the client got the correct message back.
        # self.assertIsNotNone(client_recv)
        # self.assertIsInstance(client_recv, Message)
        # self.assertEqual(mid, client_recv.id)
        # self.assertEqual(server_send.id, client_recv.id)
        # self.assertEqual(server_send.type, client_recv.type)
        # self.assertIsInstance(client_recv.message, str)
        # self.assertEqual(client_recv.message, recv_txt)

    def test_text(self):
        self.assert_test_ran(
            self.runner_of_test(self.do_test_text, *self._clients))
