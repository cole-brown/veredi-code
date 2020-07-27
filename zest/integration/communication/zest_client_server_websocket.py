# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Iterable

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
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ---
# TODO: put these in config?
# -start-
WAIT_SLEEP_TIME_SEC = 5.0
'''Main process will wait/sleep on the game_over flag for this long each go.'''

GRACEFUL_SHUTDOWN_TIME_SEC = 15.0
'''
Main process will give the game/mediator this long to gracefully shutdown.
If they take longer, it will just terminate them.
'''
# -end-
# TODO
# ---

LOG_LEVEL = log.Level.NOTSET
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
        global LOG_LEVEL
        LOG_LEVEL = log.Level.DEBUG

        self._shutdown = multiprocessing.Event()
        self._shutdown_log = multiprocessing.Event()

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

    def per_test_set_up(self):
        # Let it all run and wait for the game to end...
        self._log_server.process.start()
        self._server.process.start()
        for client in self._clients:
            client.process.start()

    def wait(self) -> None:
        '''
        Waits forever. Kills server on Ctrl-C/SIGINT.

        Returns 0 if all exitcodes are 0.
        Returns None or some int if all exitcodes are not 0.
        '''
        lumberjack = log.get_logger(self.NAME_MAIN)
        log.info("Waiting for processes to finish...",
                 veredi_logger=lumberjack)

        try:
            # check shutdown flag...
            running = not self._shutdown.wait(timeout=WAIT_SLEEP_TIME_SEC)
            while running:
                # Do nothing and take naps forever until SIGINT received or
                # game finished.
                running = not self._shutdown.wait(timeout=WAIT_SLEEP_TIME_SEC)

        except KeyboardInterrupt:
            # First, ask for a gentle, graceful shutdown...
            log.debug("Received SIGINT.",
                      veredi_logger=lumberjack)

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

        log.info("Asking mediators to end gracefully...",
                 veredi_logger=lumberjack)
        # Turn on shutdown flag to do the asking.
        self._shutdown.set()

        # Wait on clients to be done.
        log.info("Waiting for client mediators to complete "
                 "structured shutdown...",
                 veredi_logger=lumberjack)
        for client in self._clients:
            log.debug(f"  Client {client.name}...",
                      veredi_logger=lumberjack)
            client.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
            log.debug("    Done.",
                      veredi_logger=lumberjack)

        # Wait on server now.
        log.info("Waiting for server mediator to complete "
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
        log.info("Asking logs server to end gracefully...",
                 veredi_logger=lumberjack)
        self._shutdown_log.set()

        # Wait for log server to be done.
        log.info("Waiting for logs server to complete structured shutdown...",
                 veredi_logger=lumberjack)
        self._log_server.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)

        # # Make sure it shutdown and gave a good exit code.
        # self.assertEqual(self._log_server.exitcode, 0)
        return (self._log_server.process.exitcode == 0)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_basic(self):
        self.per_test_set_up()

        self.wait()
