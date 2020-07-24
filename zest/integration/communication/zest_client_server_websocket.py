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
import namedtuple
import time

from veredi.zest import zmake, zpath
from veredi.logger                      import log, log_server, log_client

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
             shutdown_flag = None) -> None:
    '''
    Inits and runs logging server.
    '''
    _sigint_ignore()
    server = log_server.init()

    # log_server.run() should never return - it just listens on the socket
    # connection for logs to process forever.
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

    lumberjack.critical("todo... server/mediator")
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

    lumberjack.critical("todo... client/mediator")
    mediator = WebSocketClient(config, conn, shutdown_flag)
    mediator.start()


# -----------------------------------------------------------------------------
# Multiprocessing Stoppers
# -----------------------------------------------------------------------------

def stop_server(
        processes: Mapping[str, multiprocessing.Process]) -> bool:
    '''
    Sets the game_end flag. Engine and Mediator should notice and go into
    graceful shutdown.
    '''
    lumberjack = log.get_logger(ProcessType.MAIN.value)

    # Set the game_end flag. They should notice soon and start doing
    # their shutdown.
    log.info("Asking engine/mediator to end the game gracefully...",
             veredi_logger=lumberjack)
    processes.game_end.set()

    # Wait on engine and mediator processes to be done.
    # Wait on mediator first, since I think it'll take less long?
    log.info("Waiting for mediator to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.MEDIATOR].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.MEDIATOR].exitcode is None:
        log.error("Mediator did not shut down in time. Data may be lost...",
                  veredi_logger=lumberjack)
    else:
        log.info("Mediator shut down complete.",
                 veredi_logger=lumberjack)

    # Now wait on the engine.
    log.info("Waiting for engine to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.ENGINE].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.ENGINE].exitcode is None:
        log.error("Engine did not shut down in time. Data may be lost...",
                  veredi_logger=lumberjack)
    else:
        log.info("Engine shut down complete.",
                 veredi_logger=lumberjack)


def _logs_over(
        processes: Mapping[str, multiprocessing.Process]) -> bool:
    '''
    Sets the logs_end flag. Logs server should notice and gracefully shut down.
    '''
    lumberjack = log.get_logger(ProcessType.MAIN.value)

    # Set the game_end flag. They should notice soon and start doing
    # their shutdown.
    log.info("Asking logs server to end gracefully...",
             veredi_logger=lumberjack)
    processes.logs_end.set()

    # Wait on engine and mediator processes to be done.
    # Wait on mediator first, since I think it'll take less long?
    log.info("Waiting for logs server to complete structured shutdown...",
             veredi_logger=lumberjack)
    processes.proc[ProcessType.LOGS].join(GRACEFUL_SHUTDOWN_TIME_SEC)
    if processes.proc[ProcessType.LOGS].exitcode is None:
        log.error("Logs server did not shut down in time. "
                  "Logs may be lost? IDK...",
                  veredi_logger=lumberjack)
    else:
        log.info("Logs server shut down complete.",
                 veredi_logger=lumberjack)



# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets(unittest.TestCase):

    NUM_CLIENTS = 2

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

        self._clients: Iterable[TestProc] = None
        '''Our WebSocket Client processes and pipes in an indexable list.'''

        config = zmake.config(zpath.TestType.INTEGRATION,
                              'config.websocket.yaml')

        self._set_up_log()
        self._set_up_server(config)
        self._set_up_clients(config)

    def tearDown(self):
        self._tear_down_log()
        self._tear_down_server()
        self._tear_down_clients()

        self.debug_flags = None
        self._shutdown = None

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
                    'shutdown_flag': self._shutdown_log,
                }),
            None)

    def _tear_down_log(self):
        # TODO: ask log server to shut down, wait on it to die.

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
        # TODO: ask server to shut down, wait on it to die.

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
        # TODO: ask each client to shut down, wait on them to die.

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

    def wait(self,) -> None:
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
            log.warning("Received SIGINT.",
                        veredi_logger=lumberjack)

        # Finally, stop the processes.
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

        # Figure out our exitcode return value.
        time.sleep(0.1)  # Short nap for our kids to clean up...
        exitcode = 0
        if self._server.process.exitcode is None:
            exitcode = None
        elif self._server.process.exitcode == 0:
            pass
        else:
            exitcode = self._server.process.exitcode
        for client in self._clients:
            if client.process.exitcode is None:
                exitcode = None
            elif client.process.exitcode == 0:
                pass
            else:
                exitcode = client.process.exitcode
        if self._log_server.process.exitcode is None:
            exitcode = None
        elif self._log_server.process.exitcode == 0:
            pass
        else:
            exitcode = self._log_server.process.exitcode

        # ---
        # Ok... Now assert stuff.
        # Tried to kill the procs a few ways and gave them some time to die, so
        # assert what we remember about that.
        # ---

        # I really want them to all have died ok.
        self.assertEqual(exitcode, 0)

        # I don't want to have to had to resorted to terminators.
        self.assertFalse(mediator_terminator)
        self.assertFalse(log_terminator)

        # I do want the processes to have ended gracefully with their shutdown
        # flag.
        self.assertTrue(mediators_ok)
        self.assertTrue(log_ok)

    def _stop_mediators(self):
        '''
        Sets the shutdown flag. Mediators should notice and go into
        graceful shutdown.
        '''
        lumberjack = log.get_logger(self.NAME_MAIN)

        log.info("Asking mediators to end gracefully...",
                 veredi_logger=lumberjack)
        # Turn on shutdown flag to do the asking.
        self._shutdown.set()

        # Wait on mediators to be done.
        log.info("Waiting for client mediators to complete "
                 "structured shutdown...",
                 veredi_logger=lumberjack)
        for client in self._clients:
            log.debug(f"  Client {client.name}...",
                      veredi_logger=lumberjack)
            client.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
            log.debug("    Done.",
                      veredi_logger=lumberjack)
            # self.assertEqual(client.process.exitcode, 0)

        log.info("Waiting for server mediator to complete "
                 "structured shutdown...",
                 veredi_logger=lumberjack)
        log.debug(f"  Server {self._server.name}...",
                  veredi_logger=lumberjack)
        self._server.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
        log.debug("    Done.",
                  veredi_logger=lumberjack)
        # self.assertEqual(self._server.exitcode, 0)

        # Did it all shutdown and gave a good exit code?
        all_good = True
        for client in self._clients:
            all_good = all_good and (client.process.exitcode == 0)
        all_good = all_good and (self._server.process.exitcode == 0)
        return all_good

    def _stop_logs(self):
        '''
        Sets the logs_end flag. Logs server should notice and gracefully shut
        down.
        '''
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
