# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Callable, List

import unittest
import sys

import multiprocessing
import multiprocessing.connection
from ctypes import c_int
import signal
from collections import namedtuple
import time
import enum

from veredi.zest                                import zmake, zpath
from veredi.logger                              import (log,
                                                        log_server,
                                                        log_client)
from veredi.debug.const                         import DebugFlag
from veredi.base.identity                       import (MonotonicId,
                                                        MonotonicIdGenerator)
from veredi.base.enum                           import (FlagCheckMixin,
                                                        FlagSetMixin)
from veredi.time.timer                          import MonotonicTimer
from veredi.data.identity                       import (UserId,
                                                        UserIdGenerator)


# ---
# Need these to register...
# ---
from veredi.data.codec.json                     import codec


# ---
# Mediation
# ---
from veredi.interface.mediator.message          import Message, MsgType
from veredi.interface.mediator.websocket.server import WebSocketServer
from veredi.interface.mediator.websocket.client import WebSocketClient
from veredi.interface.mediator.context          import MessageContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

WAIT_SLEEP_TIME_SEC = 0.1
'''Main process will wait/sleep on the game_over flag for this long each go.'''

GRACEFUL_SHUTDOWN_TIME_SEC = 15.0
'''
Main process will give the game/mediator this long to gracefully shutdown.
If they take longer, it will just terminate them.
'''

LOG_LEVEL = log.Level.INFO
'''Test should set this to desired during setUp()'''

StopRetVal = namedtuple('StopRetVal',
                        ['mediator_grace', 'log_grace',
                         'mediator_terminate', 'log_terminate'])


@enum.unique
class Disabled(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    Use the actual test function names so that the disabled property works
    right.
    '''
    NONE             = 0

    test_nothing     = enum.auto()
    test_connect     = enum.auto()
    test_ping        = enum.auto()
    test_echo        = enum.auto()
    test_text        = enum.auto()
    test_logs_ignore = enum.auto()
    test_logging     = enum.auto()

    def disabled(self, test_method_name: str) -> bool:
        '''
        Returns true if this enum has a flag set for the
        `test_method_name`.
        '''
        # This will throw KeyError if the test method isn't in our enum
        # (yet). Let it so the programmer wanders in here and finds this
        # and adds their enum value.
        method = self.__class__[test_method_name]

        # Now it's just a check to see if that method name is flagged as
        # disabled.
        return self.has(method)


@enum.unique
class ProcTest(FlagCheckMixin, enum.Flag):
    NONE = 0
    '''No process testing flag.'''

    DNE = enum.auto()
    '''
    Do not start/end/etc this process.
    Make it not exist as much as possible.
    '''


class TestProc:
    '''
    Tuple, basically. Holds on to a collection of stuff about our test
    processes.
    '''

    def __init__(self,
                 name:       str                                   = None,
                 process:    multiprocessing.Process               = None,
                 pipe:       multiprocessing.connection.Connection = None,
                 shutdown:   multiprocessing.Event                 = None,
                 proc_debug: ProcTest                              = None
                 ) -> None:
        self.name = name
        self.process = process
        self.pipe = pipe
        self.shutdown = shutdown
        self.debug = proc_debug


class TestLog(TestProc):
    '''
    Tuple, basically. Holds on to a collection of stuff about our logging
    server test processes.
    '''

    def __init__(self,
                 name:            str                                   = None,
                 process:         multiprocessing.Process               = None,
                 pipe:            multiprocessing.connection.Connection = None,
                 shutdown:        multiprocessing.Event                 = None,
                 ignore_logs:     multiprocessing.Event                 = None,
                 ignored_counter: multiprocessing.Value                 = None,
                 proc_debug:      ProcTest                              = None
                 ) -> None:
        self.name = name
        self.process = process
        self.pipe = pipe
        self.shutdown = shutdown
        self.ignore_logs = ignore_logs
        self.ignored_counter = ignored_counter
        self.debug = proc_debug


class Processes:
    '''
    Named tuple, basically, for the client/server/log_server processes TestProc
    objects.
    '''

    def __init__(self):
        self.clients: List[TestProc] = []
        '''List of WebSocket Mediator Client TestProcs.'''

        self.server: TestProc = None
        '''A WebSocket Mediator Server TestProc.'''

        self.log: TestLog = None
        '''A Log Server TestLog.'''

    # Just access directly... it's a test.

    # @property
    # def clients(self):
    #     return self.clients

    # @clients.setter
    # def clients(self, value):
    #     self.clients = value

    # @property
    # def server(self):
    #     return self.server

    # @server.setter
    # def server(self, value):
    #     self.server = value

    # @property
    # def log(self):
    #     return self.log

    # @log.setter
    # def log(self, value):
    #     self.log = value


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

def run_logs(proc_name            = None,
             log_level            = None,
             shutdown_flag        = None,
             ignore_logs_flag     = None,
             ignored_logs_counter = None,
             debug_flag           = None,
             proc_test            = None) -> None:
    '''
    Inits and runs logging server.
    '''

    lumberjack = log.get_logger(proc_name)
    lumberjack.setLevel(int(LOG_LEVEL))

    # lumberjack.debug("'running' log_server...")
    # # sleep on the shutdown flag, keep sleeping until it returns True
    # while not shutdown_flag.wait(timeout=1):
    #     lumberjack.debug("log_server is alive.")
    #     pass
    # lumberjack.debug("log_server is done?")
    # return

    # TODO [2020-08-10]: Logging init should take care of level... Try to
    # get rid of this setLevel().
    lumberjack = log.get_logger(proc_name)
    lumberjack.setLevel(int(LOG_LEVEL))
    if proc_test.has(ProcTest.DNE):
        # Log Server 'Does Not Exist' right now.
        lumberjack.critical(f"BAD: log server start: '{proc_name}' "
                            f"has {proc_test}. Should not have gotten "
                            "into this function.")
        return

    # TODO [2020-08-10]: Use debug_flag in log_server?
    _sigint_ignore()
    server = log_server.init(shutdown_flag,
                             level=log_level,
                             ignore_flag=ignore_logs_flag,
                             ignored_counter=ignored_logs_counter)

    lumberjack.debug(f"Starting log_server '{proc_name}'...")

    # log_server.run() should never return (until shutdown signaled) - it just
    # listens on the socket connection for logs to process forever.
    log_server.run(server, proc_name)
    lumberjack.debug(f"log_server '{proc_name}' done.")


def run_server(proc_name     = None,
               conn          = None,
               config        = None,
               log_level     = None,
               shutdown_flag = None,
               debug_flag    = None,
               proc_test     = None) -> None:
    '''
    Init and run client/engine IO mediator.
    '''
    # TODO [2020-08-10]: Logging init should take care of level... Try to
    # get rid of this setLevel().
    lumberjack = log.get_logger(proc_name)
    lumberjack.setLevel(int(LOG_LEVEL))
    if proc_test.has(ProcTest.DNE):
        # Mediator Server 'Does Not Exist' right now.
        lumberjack.critical(f"BAD: mediator server start: '{proc_name}' "
                            f"has {proc_test}. Should not have gotten "
                            "into this function.")
        return

    _sigint_ignore()
    log_client.init(log_level)

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

    lumberjack.debug(f"Starting WebSocketServer '{proc_name}'...")
    mediator = WebSocketServer(config, conn, shutdown_flag,
                               debug=debug_flag)
    mediator.start()
    log_client.close()
    lumberjack.debug(f"mediator server '{proc_name}' done.")


def run_client(proc_name     = None,
               conn          = None,
               config        = None,
               log_level     = None,
               shutdown_flag = None,
               debug_flag    = None,
               proc_test     = None,
               user_key      = None) -> None:
    '''
    Init and run client/engine IO mediator.
    '''
    # TODO [2020-08-10]: Logging init should take care of level... Try to
    # get rid of this setLevel().
    lumberjack = log.get_logger(proc_name)
    lumberjack.setLevel(int(LOG_LEVEL))
    if proc_test.has(ProcTest.DNE):
        # Mediator Server 'Does Not Exist' right now.
        lumberjack.critical(f"BAD: mediator client start: '{proc_name}' "
                            f"has {proc_test}. Should not have gotten "
                            "into this function.")
        return

    _sigint_ignore()
    log_client.init(log_level)

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

    lumberjack.debug(f"Starting WebSocketClient '{proc_name}'...")
    mediator = WebSocketClient(config, conn, shutdown_flag,
                               user_key=user_key,
                               debug=debug_flag,
                               unit_testing=True)
    mediator.start()
    log_client.close()
    lumberjack.debug(f"mediator client '{proc_name}' done.")


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_WebSockets(unittest.TestCase):

    PER_TEST_TIMEOUT = 5  # seconds

    # TODO [2020-07-25]: 2 or 4 or something?
    NUM_CLIENTS = 1

    NAME_LOG = 'veredi.test.websockets.log'
    NAME_SERVER = 'veredi.test.websockets.server'
    NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'
    NAME_MAIN = 'veredi.test.websockets.tester'

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def setUp(self):
        self._ut_is_verbose = ('-v' in sys.argv) or ('--verbose' in sys.argv)
        if self._ut_is_verbose and LOG_LEVEL == log.Level.DEBUG:
            # Hope this is enough for log_server to finish printing from
            # previous test...
            time.sleep(0.1)
            # Give ourself a visible output split.
            print('\n\n' + 'v' * 60)
            print('v' * 60 + '\n')

        self.debug_flag = DebugFlag.MEDIATOR_ALL
        self.debugging = False
        self.disabled_tests = (
            # Only this, ideally.
            Disabled.NONE

            # ---
            # Simplest test.
            # ---
            | Disabled.test_nothing

            # ---
            # More complex tests.
            # ---
            # | Disabled.test_connect
            | Disabled.test_ping
            | Disabled.test_echo
            | Disabled.test_text

            # ---
            # Not ready yet.
            # ---
            | Disabled.test_logs_ignore
            | Disabled.test_logging
        )

        self._msg_id: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._user_key: UserIdGenerator = UserId.generator()
        '''For these, just make up user ids.'''

        self.proc: Processes = Processes()
        '''Our test processes.'''

        config = zmake.config(zpath.TestType.INTEGRATION,
                              'config.websocket.yaml')

        default = ProcTest.NONE
        self._set_up_log(config, default)
        self._set_up_server(config, default)  # ProcTest.DNE)
        self._set_up_clients(config, default)  # ProcTest.DNE)

    def tearDown(self):
        self._stop_mediators()
        self._tear_down_server()
        self._tear_down_clients()

        self._stop_logs()
        self._tear_down_log()

        self.debug_flag = None
        self.debugging = False
        self._msg_id = None
        self._user_key = None
        self.proc = None

        if self._ut_is_verbose and LOG_LEVEL == log.Level.DEBUG:
            # Hope this is enough for log_server to finish printing from
            # previous test...
            time.sleep(0.1)
            # Give ourself a visible output split.
            print('\n\n' + '^' * 60)
            print('^' * 60 + '\n')

    # ---
    # Log Set-Up / Tear-Down
    # ---

    def _set_up_log(self, config, proc_test):
        if proc_test.has(ProcTest.DNE):
            # Log Server 'Does Not Exist' right now.
            log.critical(f"Log server set up has {ProcTest.DNE}. "
                         f"Skipping creation/set-up.")
            return

        log.debug(f"Set up log server... {proc_test}")
        # Stuff that both log process and we need.
        name = self.NAME_LOG
        ignore_logs = multiprocessing.Event()
        shutdown = multiprocessing.Event()
        ignored_logs_counter = multiprocessing.Value(c_int, 0)

        # Create our log server Process.
        log_server = TestLog(
            name=name,
            process=multiprocessing.Process(
                target=run_logs,
                name=name,
                kwargs={
                    'proc_name':     name,
                    'log_level':     LOG_LEVEL,
                    'shutdown_flag': shutdown,
                    'ignore_logs_flag': ignore_logs,
                    'ignored_logs_counter': ignored_logs_counter,
                    'debug_flag': self.debug_flag,
                    'proc_test': proc_test,
                }),
            pipe=None,
            shutdown=shutdown,
            ignore_logs=ignore_logs,
            ignored_counter=ignored_logs_counter,
            proc_debug=proc_test)

        # Assign!
        self.proc.log = log_server

    def _tear_down_log(self):
        if not self.proc.log:
            # Log Server 'Does Not Exist' right now.
            log.critical("No log server exists. Skipping tear-down.")
            return

        log.debug("Tear down log server...")

        # Ask log server to stop if we haven't already...
        if not self.proc.log.shutdown.is_set():
            self._stop_logs()

        self.proc.log = None

    # ---
    # Server Set-Up / Tear-Down
    # ---

    def _set_up_server(self, config, proc_test):
        if proc_test.has(ProcTest.DNE):
            # Mediator Server 'Does Not Exist' right now.
            log.critical(f"Mediator server set up has {ProcTest.DNE}. "
                         f"Skipping creation/set-up.")
            return

        log.debug(f"Set up mediator server... {proc_test}")
        # Stuff server and us both need.
        name = self.NAME_SERVER
        mediator_conn, test_conn = multiprocessing.Pipe()
        shutdown = multiprocessing.Event()

        # Create server process.
        server = TestProc(
            name=name,
            process=multiprocessing.Process(
                target=run_server,
                name=name,
                kwargs={
                    'proc_name':     name,
                    'conn':          mediator_conn,
                    'config':        config,
                    'log_level':     LOG_LEVEL,
                    'shutdown_flag': shutdown,
                    'debug_flag':    self.debug_flag,
                    'proc_test': proc_test,
                }),
            pipe=test_conn,
            shutdown=shutdown,
            proc_debug=proc_test)

        # Assign!
        self.proc.server = server

    def _tear_down_server(self):
        if not self.proc.server:
            # Mediator Server 'Does Not Exist' right now.
            log.critical("No mediator server exists. Skipping tear-down.")
            return

        log.debug("Tear down mediator server...")
        # Ask all mediators to stop if we haven't already...
        if not self.proc.server.shutdown.is_set():
            self._stop_mediators()

        self.proc.server = None

    # ---
    # Clients Set-Up / Tear-Down
    # ---

    def _set_up_clients(self, config, proc_test):
        if proc_test.has(ProcTest.DNE):
            # Mediator Clients 'Do Not Exist' right now.
            log.critical(f"Mediator client(s) set up has {ProcTest.DNE}. "
                         f"Skipping creation/set-up.")
            return

        log.debug(f"Set up mediator client(s)... {proc_test}")
        # Shared with all clients.
        shutdown = multiprocessing.Event()

        # Init the clients to an empty list.
        self.proc.clients = []
        # And make as many as we want...
        for i in range(self.NUM_CLIENTS):
            # Stuff clients and us both need.
            mediator_conn, test_conn = multiprocessing.Pipe()
            name = self.NAME_CLIENT_FMT.format(i=i)
            user_key = self._user_key.next(name)

            # Create this client.
            client = TestProc(
                name=name,
                process=multiprocessing.Process(
                    target=run_client,
                    name=name,
                    kwargs={
                        'proc_name':     name,
                        'conn':          mediator_conn,
                        'config':        config,
                        'log_level':     LOG_LEVEL,
                        'shutdown_flag': shutdown,
                        'debug_flag':    self.debug_flag,
                        'proc_test':     proc_test,
                        'user_key':      user_key,
                    }),
                pipe=test_conn,
                shutdown=shutdown,
                proc_debug=proc_test)

            # Append to the list of clients!
            self.proc.clients.append(client)

    def _tear_down_clients(self):
        if not self.proc.clients:
            # Mediator Clients 'Do Not Exist' right now.
            log.critical("No mediator client(s) exist. Skipping tear-down.")
            return

        log.debug("Tear down mediator client(s)...")
        # Ask all mediators to stop if we haven't already... Checking each
        # client even though clients all share a shutdown event currently, just
        # in case that changes later.
        for each in self.proc.clients:
            if not each.shutdown.is_set():
                self._stop_mediators()
                break

        self.proc.clients = None

    # -------------------------------------------------------------------------
    # Stop / Clean-Up Tests Functions
    # -------------------------------------------------------------------------
    # This is before actual tear down. Could even be more self.assert*(...)
    # to do... But the actual client/server should be stopped and such.

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
        # # Close this test's connection to log server.
        # log_client.close()

        mediators_ok = self._stop_mediators()
        log_ok = self._stop_logs()
        log.debug(f"Mediators stopped gracefully? {mediators_ok}")
        log.debug(f"Logs stopped gracefully? {log_ok}")

        # Give up and ask for the terminator... If necessary.
        mediator_terminator = False
        log_terminator = False
        if self.proc.server and self.proc.server.process.exitcode is None:
            # Still not exited; terminate it.
            self.proc.server.process.terminate()
            mediator_terminator = True
        for client in self.proc.clients:
            if client.process.exitcode is None:
                # Still not exited; terminate it.
                client.process.terminate()
                mediator_terminator = True
        if self.proc.log and self.proc.log.process.exitcode is None:
            # Still not exited; terminate it.
            self.proc.log.process.terminate()
            log_terminator = True
        log.debug(f"Mediators terminated? {mediator_terminator}")
        log.debug(f"Logs terminated? {log_terminator}")

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
        if self.proc.server:
            if self.proc.server.process.exitcode is None:
                exitcode = None
                return exitcode
            elif self.proc.server.process.exitcode == 0:
                pass
            else:
                exitcode = self.proc.server.process.exitcode

        # ---
        # Check Clients:
        # ---
        for client in self.proc.clients:
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
        if self.proc.log.process.exitcode is None:
            exitcode = None
            return exitcode
        elif self.proc.log.process.exitcode == 0:
            pass
        else:
            exitcode = self.proc.log.process.exitcode

        return exitcode

    def _mediators_stopped(self):
        '''
        Did it all shutdown and gave a good exit code?
        '''
        all_good = True
        for client in self.proc.clients:
            all_good = all_good and (client.process.exitcode == 0)
        if self.proc.server:
            all_good = all_good and (self.proc.server.process.exitcode == 0)
        return all_good

    def _log_stopped(self):
        '''
        Did log server shutdown and gave a good exit code?
        '''
        all_good = True
        if self.proc.log:
            all_good = (self.proc.log.process.exitcode == 0)
        return all_good

    def _stop_mediators(self):
        '''
        Sets the shutdown flag. Mediators should notice and go into
        graceful shutdown.
        '''
        lumberjack = log.get_logger(self.NAME_MAIN)

        if (not self.proc.clients and not self.proc.server):
            log.debug("No mediators to stop.",
                      veredi_logger=lumberjack)
            return True
        if self._mediators_stopped():
            log.debug("Mediators already stopped.",
                      veredi_logger=lumberjack)
            return True

        log.debug("Asking mediators to end gracefully...",
                  veredi_logger=lumberjack)
        # Turn on shutdown flag(s) to do the asking.
        if self.proc.server:
            self.proc.server.shutdown.set()
        for client in self.proc.clients:
            client.shutdown.set()

        # Wait on clients to be done.
        if self.proc.clients:
            log.debug("Waiting for client mediators to complete "
                      "structured shutdown...",
                      veredi_logger=lumberjack)
            for client in self.proc.clients:
                if client.process and client.process.is_alive():
                    log.debug(f"    Client {client.name}...",
                              veredi_logger=lumberjack)
                    client.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
                    log.debug("    Client {client.name}: Done.",
                              veredi_logger=lumberjack)
                else:
                    log.debug(f"    Client {client.name} didn't run; "
                              "skip shutdown...",
                              veredi_logger=lumberjack)
        else:
            log.debug("No client mediators to shutdown. Skipping.",
                      veredi_logger=lumberjack)

        # Wait on server now.
        if self.proc.server:
            if self.proc.server and self.proc.server.process.is_alive():
                log.debug("Waiting for server mediator to complete "
                          "structured shutdown...",
                          veredi_logger=lumberjack)
                log.debug(f"    Server {self.proc.server.name}...",
                          veredi_logger=lumberjack)
                self.proc.server.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
                log.debug("    Server {self.proc.server.name}: Done.",
                          veredi_logger=lumberjack)
            else:
                log.debug(f"    Server {self.proc.server.name} didn't run; "
                          "skip shutdown...",
                          veredi_logger=lumberjack)
        else:
            log.debug("No server mediator to shutdown. Skipping.",
                      veredi_logger=lumberjack)

        # Did it all shutdown and gave a good exit code?
        return self._mediators_stopped()

    def _stop_logs(self):
        '''
        Sets the logs_end flag. Logs server should notice and gracefully shut
        down.
        '''
        lumberjack = log.get_logger(self.NAME_MAIN)
        if not self.proc.log:
            log.debug("No log server to stop.",
                      veredi_logger=lumberjack)
            return
        if self._log_stopped():
            log.debug("Log server already stopped.",
                      veredi_logger=lumberjack)
            return True

        # Set the game_end flag. They should notice soon and start doing
        # their shutdown.
        log.debug("Asking log server to end gracefully...",
                  veredi_logger=lumberjack)
        self.proc.log.shutdown.set()

        # Wait for log server to be done.
        if self.proc.log and self.proc.log.process.is_alive():
            log.debug("Waiting for log server to complete "
                      "structured shutdown...",
                      veredi_logger=lumberjack)
            self.proc.log.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
            log.debug("log_server exit: "
                      f"{str(self.proc.log.process.exitcode)}")
        else:
            log.debug(f"    Log server {self.proc.log.name} didn't run; "
                      "skip shutdown...",
                      veredi_logger=lumberjack)

        # # Make sure it shutdown and gave a good exit code.
        # self.assertEqual(self.proc.log.exitcode, 0)
        return self._log_stopped()

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def method_name(self, stacklevel: int = 1) -> str:
        '''
        Returns caller method's name.
        Or caller's caller, if `stacklevel` == 2, etc...
        '''
        import inspect
        # Current frame's back-a-frame's code's name.
        frame = inspect.currentframe()
        for i in range(stacklevel):
            if not frame:
                break
            frame = frame.f_back

        if not frame:
            return None
        return frame.f_code.co_name

    # TODO [2020-08-12]: Switch to using @unittest.skipIf(disabled())...
    # somehow?
    def disabled(self) -> bool:
        '''
        Uses magic shenanigans to:

        Return true if caller method is disabled by self.disabled_tests flag.
        Return false if test should run.
        '''
        name = self.method_name(stacklevel=2)
        self.assertIsNotNone(name)

        # Got name, so now we can check if flagged.
        # Could raise a KeyError, and we'll let it bubble up.
        return self.disabled_tests.disabled(name)

    def msg_context(self,
                    msg_ctx_id: Optional[MonotonicId] = None
                    ) -> MessageContext:
        '''
        Some simple context to pass with messages.

        Makes up an id if none supplied.
        '''
        msg_id = msg_ctx_id or MonotonicId(7731, allow=True)
        ctx = MessageContext(
            'veredi.zest.integration.communication.'
            'zest_client_server_websocket',
            msg_id)
        return ctx

    # -------------------------------------------------------------------------
    # Once "Per-Test" Helpers
    # -------------------------------------------------------------------------

    def per_test_timeout(self, sig_triggered, frame):
        '''
        Stop our processes and fail test due to timeout.
        '''
        _sigalrm_end()
        self.per_test_tear_down()
        self.fail(f'Test failure due to timeout. '
                  f'Signal: {sig_triggered} '
                  f'"{signal.strsignal(sig_triggered)}". '
                  f'Frame: {frame}')

    def per_test_set_up(self):
        # Let it all run and wait for the game to end...
        _sigalrm_start(self.PER_TEST_TIMEOUT, self.per_test_timeout)

        self.proc.log.process.start()
        self.proc.server.process.start()
        for client in self.proc.clients:
            client.process.start()

        # Can't figure out how to get this to not make log_server unable to die
        # gracefully...
        # # Hook this test itself into the log server.
        # log_client.init(LOG_LEVEL)
        # log.set_level(LOG_LEVEL)

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

    # -------------------------------------------------------------------------
    # Do-Something-During-A-Test Functions
    # -------------------------------------------------------------------------
    # (Or Do-Nothing,-Really in wait()'s case...)

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
            # Check shutdown flag... Prefer checking server, fall back to first
            # client, fall back to log server.
            shutdown_flag = None
            if self.proc.server:
                shutdown_flag = self.proc.server.shutdown
            elif self.proc.clients and len(self.proc.clients) > 0:
                for client in self.proc.clients:
                    if client.shutdown:
                        shutdown_flag = client.shutdown
                        break
            elif self.proc.log:
                shutdown_flag = self.proc.log.shutdown
            else:
                log.critical("Nothing is running so... "
                             "no shutdown flag to check?!")

            running = not shutdown_flag.wait(timeout=WAIT_SLEEP_TIME_SEC)
            # if log.will_output(log.Level.DEBUG):
            #     time_ok = not timer.timed_out(wait_timeout)
            #     log.debug(f"{self.__class__.__name__}: waited "
            #               f"{timer.elapsed_str}; wait more? "
            #               f"({running} and {time_ok} "
            #               f"== {running and time_ok}")
            while running and not timer.timed_out(wait_timeout):
                # log.debug(f"{self.__class__.__name__}: waited "
                #           f"{timer.elapsed_str}; wait more.")

                # Do nothing and take naps forever until SIGINT received or
                # game finished.
                running = not shutdown_flag.wait(timeout=WAIT_SLEEP_TIME_SEC)

        except KeyboardInterrupt:
            # First, ask for a gentle, graceful shutdown...
            log.debug("Received SIGINT.",
                      veredi_logger=lumberjack)

        else:
            log.debug("Wait finished normally.")

    # =========================================================================
    # =--------------------------------Tests----------------------------------=
    # =--                        Real Actual Tests                          --=
    # =---------------------...after so much prep work.-----------------------=
    # =========================================================================

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    def test_ignored_tests(self):

        # ---
        # First, test for specifics for nicer error messages.
        # ---

        self.assertNotIn(Disabled.test_nothing,     self.disabled_tests)
        self.assertNotIn(Disabled.test_ping,        self.disabled_tests)
        self.assertNotIn(Disabled.test_echo,        self.disabled_tests)
        self.assertNotIn(Disabled.test_text,        self.disabled_tests)
        self.assertNotIn(Disabled.test_logs_ignore, self.disabled_tests)
        self.assertNotIn(Disabled.test_logging,     self.disabled_tests)
        self.assertNotIn(Disabled.test_connect,     self.disabled_tests)

        # ---
        # Last, just check for anything set. Catches all the new flags.
        # ---
        self.assertEqual(self.disabled_tests, Disabled.NONE)

    # ------------------------------
    # Test doing nothing and cleaning up.
    # ------------------------------

    def do_test_nothing(self):
        # This really doesn't do much other than bring up the processes and
        # then kill them, but it's something.
        self.wait(0.1)

        # Make sure we don't have anything in the queues... Allow for having
        # neither client nor server. We've had to regress all the way back to
        # trying to get this running a few times already. Multiprocessing with
        # multiple threads and multiple asyncios is... fun.
        for client in self.proc.clients:
            self.assertFalse(client.pipe.poll())
        if self.proc.server:
            self.assertFalse(self.proc.server.pipe.poll())

    def test_nothing(self):
        if self.disabled():
            return

        # No checks for this, really. Just "does it properly not explode"?
        self.assert_test_ran(
            self.runner_of_test(self.do_test_nothing))

    # ------------------------------
    # Test Client Requesting Connection to Server.
    # ------------------------------

    def do_test_connect(self, client):
        # Send something... Currently client doesn't care and tries to connect
        # on any message it gets when it has no connection. But it may change
        # later.
        mid = Message.SpecialId.CONNECT
        msg = Message(mid, MsgType.IGNORE, payload=None)
        client.pipe.send((msg, self.msg_context(mid)))

        # Received "you're connected now" back?
        recv, ctx = client.pipe.recv()

        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        self.assertIsInstance(recv.id, Message.SpecialId)
        self.assertEqual(mid, recv.id)

        # Translation from stored int to enum or id class instance borks this
        # check up. `msg.id` will be MonotonicId, `recv.id` will be SpecialId,
        # and they won't equal.
        # self.assertEqual(msg.id, recv.id)

        # Don't check this either. Duh. We create it as IGNORE, we're testing
        # CONNECT, and we're expecting ACK_CONNECT back.
        # self.assertEqual(msg.type, recv.type)
        # Can do this though.
        self.assertEqual(recv.type, MsgType.ACK_CONNECT)
        self.assertIsInstance(recv.payload, dict)
        self.assertIn('code', recv.payload)
        self.assertIn('text', recv.payload)
        # Did we connect successfully?
        self.assertTrue(recv.payload['code'])

        # This should be... something.
        self.assertIsNotNone(recv.key)
        self.assertIsInstance(recv.key, UserId)
        # Not sure what it should be, currently, so can't really test that?

        # TODO [2020-08-13]: Server should know what key client will have
        # before client connects.

    def test_connect(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_connect, *self.proc.clients))

    # ------------------------------
    # Test cliets pinging server.
    # ------------------------------

    def do_test_ping(self, client):
        mid = self._msg_id.next()
        msg = Message(mid, MsgType.PING, payload=None)
        client.pipe.send((msg, self.msg_context(mid)))
        recv, ctx = client.pipe.recv()
        # Make sure we got a message back and it has the ping time in it.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        self.assertEqual(msg.id, ctx.id)
        self.assertEqual(mid, recv.id)
        self.assertEqual(msg.id, recv.id)
        self.assertEqual(msg.type, recv.type)

        # I really hope the local ping is between negative nothingish and
        # positive five seconds.
        self.assertIsInstance(recv.payload, float)
        self.assertGreater(recv.payload, -0.0000001)
        self.assertLess(recv.payload, 5)

        # Make sure we don't have anything in the queues...
        self.assertFalse(client.pipe.poll())
        self.assertFalse(self.proc.server.pipe.poll())

    def test_ping(self):
        if self.disabled():
            return

        # No other checks for ping outside do_test_ping.
        self.assert_test_ran(
            self.runner_of_test(self.do_test_ping, *self.proc.clients))

    # ------------------------------
    # Test Clients sending an echo message.
    # ------------------------------

    def do_test_echo(self, client):
        mid = self._msg_id.next()
        send_msg = f"Hello from {client.name}"
        expected = send_msg
        msg = Message(mid, MsgType.ECHO, payload=send_msg)
        ctx = self.msg_context(mid)
        # self.debugging = True
        with log.LoggingManager.on_or_off(self.debugging, True):
            client.pipe.send((msg, ctx))
            recv, ctx = client.pipe.recv()
        # Make sure we got a message back and it has the same
        # message as we sent.
        self.assertTrue(recv)
        self.assertTrue(ctx)
        self.assertIsInstance(recv, Message)
        self.assertTrue(ctx, MessageContext)
        # IDs made it around intact.
        self.assertEqual(msg.id, ctx.id)
        self.assertEqual(mid, recv.id)
        self.assertEqual(msg.id, recv.id)
        # Sent echo, got echo-back.
        self.assertEqual(msg.type, MsgType.ECHO)
        self.assertEqual(recv.type, MsgType.ECHO_ECHO)
        # Got what we sent.
        self.assertIsInstance(recv.payload, str)
        self.assertEqual(recv.payload, expected)

        # Make sure we don't have anything in the queues...
        self.assertFalse(client.pipe.poll())
        self.assertFalse(self.proc.server.pipe.poll())

    def test_echo(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_echo, *self.proc.clients))

    # ------------------------------
    # Test Clients sending text messages to server.
    # ------------------------------

    def do_test_text(self, client):
        mid = self._msg_id.next()

        # ---
        # Client -> Server: TEXT
        # ---
        log.debug("client to server...")

        send_txt = f"Hello from {client.name}?"
        client_send = Message(mid, MsgType.TEXT, payload=send_txt)
        client_send_ctx = self.msg_context(mid)

        client_recv = None
        client_recv_ctx = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Have client send, then receive from server.
            client.pipe.send((client_send, client_send_ctx))

            # Server automatically sent an ACK_ID, need to check client.
            client_recv = client.pipe.recv()

        log.debug(f"client send msg: {client_send}")
        log.debug(f"client recv ack: {client_recv}")
        # Make sure that the client received the correct thing.
        self.assertIsNotNone(client_recv)
        self.assertIsInstance(client_recv, tuple)
        self.assertEqual(len(client_recv), 2)  # Make sure next line is sane...
        client_recv_msg, client_recv_ctx = client_recv
        # Make sure that the client received their ACK_ID.
        self.assertIsNotNone(client_recv_msg)
        self.assertIsInstance(client_recv_msg, Message)
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)
        self.assertEqual(mid, client_recv_msg.id)
        self.assertEqual(client_send.id, client_recv_msg.id)
        self.assertEqual(client_recv_msg.type, MsgType.ACK_ID)
        ack_id = mid.decode(client_recv_msg.payload)
        self.assertIsInstance(ack_id, type(mid))

        # ---
        # Check: Client -> Server: TEXT
        # ---
        log.debug("test_text: server to game...")
        server_recv = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Our server should have put the client's packet in its pipe for
            # us... I hope.
            log.debug("test_text: game recv from server...")
            server_recv = self.proc.server.pipe.recv()

        log.debug(f"client_sent/server_recv: {server_recv}")
        # Make sure that the server received the correct thing.
        self.assertIsNotNone(server_recv)
        self.assertIsInstance(server_recv, tuple)
        self.assertEqual(len(server_recv), 2)  # Make sure next line is sane...
        server_recv_msg, server_recv_ctx = server_recv
        # Check the Message.
        self.assertEqual(mid, server_recv_msg.id)
        self.assertEqual(client_send.id, server_recv_msg.id)
        self.assertEqual(client_send.type, server_recv_msg.type)
        self.assertIsInstance(server_recv_msg.payload, str)
        self.assertEqual(server_recv_msg.payload, send_txt)
        # Check the Context.
        self.assertIsInstance(server_recv_ctx, MessageContext)
        self.assertEqual(server_recv_ctx.id, ack_id)

        # ---
        # Server -> Client: TEXT
        # ---

        log.debug("test_text: server_send/client_recv...")
        # Tell our server to send a reply to the client's text.
        recv_txt = f"Hello from {self.proc.server.name}!"
        server_send = Message(server_recv_ctx.id, MsgType.TEXT,
                              payload=recv_txt)
        client_recv = None
        with log.LoggingManager.on_or_off(self.debugging, True):
            # Make something for server to send and client to recvive.
            log.debug("test_text: server_send...")
            log.debug(f"test_text: pipe to game: {server_send}")
            self.proc.server.pipe.send((server_send, server_recv_ctx))
            log.debug("test_text: client_recv...")
            client_recv = client.pipe.recv()

        log.debug(f"server_sent/client_recv: {client_recv}")
        # Make sure the client got the correct message back.
        self.assertIsNotNone(client_recv)
        self.assertIsInstance(client_recv, tuple)
        self.assertEqual(len(client_recv), 2)  # Make sure next line is sane...
        client_recv_msg, client_recv_ctx = client_recv
        self.assertIsNotNone(client_recv_ctx)
        self.assertIsInstance(client_recv_ctx, MessageContext)

        self.assertIsInstance(client_recv_msg, Message)
        self.assertEqual(ack_id, client_recv_msg.id)
        self.assertEqual(server_send.id, client_recv_msg.id)
        self.assertEqual(server_send.type, client_recv_msg.type)
        self.assertIsInstance(client_recv_msg.payload, str)
        self.assertEqual(client_recv_msg.payload, recv_txt)

        # ---
        # Server -> Client: ACK
        # ---

        # Client automatically sent an ACK_ID, need to check server for it.
        server_recv = self.proc.server.pipe.recv()

        log.debug(f"server sent msg: {server_send}")
        log.debug(f"server recv ack: {server_recv}")
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
        self.assertEqual(mid, server_recv_msg.id)
        self.assertEqual(server_send.id, server_recv_msg.id)
        self.assertEqual(server_recv_msg.type, MsgType.ACK_ID)
        ack_id = mid.decode(server_recv_msg.payload)
        self.assertIsInstance(ack_id, type(mid))

        # Make sure we don't have anything in the queues...
        self.assertFalse(client.pipe.poll())
        self.assertFalse(self.proc.server.pipe.poll())

    def test_text(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_text, *self.proc.clients))

    # ------------------------------
    # Test Ignoring Logs...
    # ------------------------------

    def do_test_logs_ignore(self):
        self.assertIsNotNone(self.proc.log)

        self.assertEqual(self.proc.log.ignored_counter.value, 0)

        self.proc.log.ignore_logs.set()

        # Does this not get printed and does this increment our counter?
        self.assertEqual(self.proc.log.ignored_counter.value, 0)

        # Connect this process to the log server, do a long that should be
        # ignored, and then disconnect.
        log_client.init()
        log.critical("You should not see this.")
        log_client.close()
        # Gotta wait a bit for the counter to sync back to this process,
        # I guess.
        self.wait(1)  # 0.1)
        self.assertEqual(self.proc.log.ignored_counter.value, 1)

    def test_logs_ignore(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_logs_ignore))

    # ------------------------------
    # Test Server sending LOGGING to client.
    # ------------------------------

    def do_test_logging(self, client):

        self.assertEqual(self.proc.log.ignored_counter.value, 0)
        self.assertFalse(self.proc.log.ignore_logs.is_set())

        self.proc.log.ignore_logs.set()

        self.assertEqual(self.proc.log.ignored_counter.value, 0)

        # # Have a client connect to server so we can then tell it to do a
        # # logging thing.
        # self.connect_client(client)

        # TODO:
        # TODO:
        # TODO: Time for UserIds?
        # TODO:
        # TODO:
        # TODO:

        # Have a client adjust its log level to debug. Should spit out a lot of
        # logs then.
        mid = self._msg_id.next()
        msg = Message.log(mid, log.Level.DEBUG)
        ctx = self.msg_context(mid)
        with log.LoggingManager.on_or_off(self.debugging, True):
            # server -> client
            self.proc.server.pipe.send((msg, ctx))
            # client ack
            ack_msg, ack_ctx = self.proc.server.pipe.recv()

        self.wait(0.1)
        # We ignored something, at least, right?
        self.assertGreater(self.proc.log.ignored_counter.value, 2)

        # Make sure we got a message back and it has the same
        # message as we sent.
        self.assertTrue(ack_msg)
        self.assertTrue(ack_ctx)
        self.assertIsInstance(ack_msg, Message)
        self.assertTrue(ack_ctx, MessageContext)
        # Sent logging... right?
        self.assertEqual(msg.type, MsgType.LOGGING)

        # Make sure we don't have anything in the queues...
        self.assertFalse(client.pipe.poll())
        self.assertFalse(self.proc.server.pipe.poll())

    def test_logging(self):
        if self.disabled():
            return

        self.assert_test_ran(
            self.runner_of_test(self.do_test_logging, *self.proc.clients))
