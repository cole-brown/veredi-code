# coding: utf-8

'''
Integration Test Base Class for multiple process tests like client/server
mediator testing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any, Callable, Generator,
                    Tuple, List, Literal)


import signal
import time as py_time
import enum


from veredi.zest          import zmake, zontext
from veredi.logs          import log, log_server

from veredi.base.strings  import label
from veredi.base.enum     import FlagCheckMixin
from veredi.base.context  import UnitTestContext

from veredi.parallel      import multiproc
from veredi.time.timer    import MonotonicTimer
from veredi.data.identity import UserId, UserKey

from .integrate           import ZestIntegrateEngine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# ------------------------------
# Test Processes
# ------------------------------

@enum.unique
class ProcTest(FlagCheckMixin, enum.Flag):
    NONE = 0
    '''No process testing flag.'''

    DNE = enum.auto()
    '''
    Do not start/end/etc this process.
    Make it not exist as much as possible.
    '''


# ------------------------------
# Client Proc Info
# ------------------------------

class ClientProcToSubComm(multiproc.ProcToSubComm):
    '''
    ProcToSubComm with UserId and UserKey added for testing purposes.
    '''

    def __init__(self,
                 *args:    Any,
                 **kwargs: Any):
        super().__init__(*args, **kwargs)

        self._user_id:  Optional[UserId]  = None
        self._user_key: Optional[UserKey] = None

    def set_user(self,
                 id:  Optional[UserId],
                 key: Optional[UserKey]) -> None:
        self._user_id  = id
        self._user_key = key

    @property
    def user_id(self) -> Optional[UserId]:
        return self._user_id

    @property
    def user_key(self) -> Optional[UserKey]:
        return self._user_key


# ------------------------------
# All Processes Collection
# ------------------------------

class Processes:
    '''
    Named tuple, basically, for the client/server/log_server processes TestProc
    objects.
    '''

    @enum.unique
    class Direction(enum.Enum):
        SET_UP = enum.auto()
        TEAR_DOWN = enum.auto()

    def __init__(self):
        self.clients: List[ClientProcToSubComm] = []
        '''List of WebSocket Mediator Client TestProcs.'''

        self.server: multiproc.ProcToSubComm = None
        '''A WebSocket Mediator Server TestProc.'''

        self.log: log_server.LogServerComm = None
        '''A Log Server TestLog.'''

    # ------------------------------
    # Properties
    # ------------------------------
    # Just access directly... it's a test.

    # ------------------------------
    # Iterators / Generators
    # ------------------------------

    def all(self,
            direction: 'Processes.Direction' = Direction.SET_UP
            ) -> Generator['multiproc.ProcToSubComm', None, None]:
        '''
        Generator for iterating over all Processes.
        '''

        if direction == Processes.Direction.SET_UP:
            return self._all_forward()

        elif direction == Processes.Direction.TEAR_DOWN:
            return self._all_reversed()

        else:
            raise ValueError("Don't have a way of iterating over "
                             f"clients in this direction: {direction}")

    def _all_forward(self) -> Generator['multiproc.ProcToSubComm', None, None]:
        '''
        Generator for iterating over all Processes in a 'forwardsly' manner.
        '''
        # Log goes first so it can be set up for whatever comes after.
        if self.log:
            yield self.log

        # Server next so it can be set up before clients...
        if self.server:
            yield self.server

        for client in self.all_clients(Processes.Direction.SET_UP):
            yield client

    def _all_reversed(self
                      ) -> Generator['multiproc.ProcToSubComm', None, None]:
        '''
        Generator for iterating over all Processes in a 'forwardsly' manner.
        '''
        for client in self.all_clients(Processes.Direction.TEAR_DOWN):
            yield client

        if self.server:
            yield self.server

        # Return log last specifically for shutting down all processes.
        # Want to shut it down after everyone has disconnected from it.
        if self.log:
            yield self.log

    def all_clients(self,
                    direction: 'Processes.Direction' = Direction.SET_UP
                    ) -> Generator['multiproc.ProcToSubComm', None, None]:
        '''
        Generator for iterating over all client processes.
        '''
        if not self.clients:
            return

        clients = None
        if direction == Processes.Direction.SET_UP:
            clients = self.clients
        elif direction == Processes.Direction.TEAR_DOWN:
            clients = reversed(self.clients)
        else:
            raise ValueError("Don't have a way of iterating over "
                             f"clients in this direction: {direction}")

        for each in clients:
            yield each


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class ZestIntegrateMultiproc(ZestIntegrateEngine):

    PER_TEST_TIMEOUT = 15  # seconds

    NAME_LOG = 'veredi.test.multiproc.log'
    NAME_MAIN = 'veredi.test.multiproc.tester'
    # NAME_SERVER = 'veredi.test.websockets.server'
    # NAME_CLIENT_FMT = 'veredi.test.websockets.client.{i:02d}'

    DISABLED_TESTS = set()

    # -------------------------------------------------------------------------
    # Set-Up & Tear-Down
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines ZestSystem's instance variables with type hinting, docstrs.
        '''
        super()._define_vars()

        self.proc: Processes = Processes()
        '''Our test processes.'''

    def pre_set_up(self,
                   config_path: str,
                   rules:       Optional[label.LabelInput] = None,
                   game_id:     Optional[Any]              = None
                   ) -> None:
        # ---
        # Save these config args.
        # ---
        self.config_path = config_path
        self.config_rules = rules
        self.config_game_id = game_id

    def set_up(self,
               log_level:  log.Level,
               proc_flags: ProcTest) -> None:
        # ---
        # Print out start of new test debuging separator lines.
        # ---
        if self._ut_is_verbose and log_level == log.Level.DEBUG:
            # Hope this is enough for log_server to finish printing from
            # previous test...
            py_time.sleep(0.1)

            # Give ourself a visible output split.
            print('\n\n' + 'v' * 60)
            print('v' * 60)
            print('start:  ', self._timing.start_str)
            print('\n')

        # ---
        # Wanted ASAP.
        # ---
        log.set_level(log_level)
        self.lumberjack = log.get_logger(self.NAME_MAIN)


        # ------------------------------
        # Let parent do stuff.
        # ------------------------------
        super().set_up()

        # ---
        # Finish our things.
        # ---
        self._set_up_log(proc_flags, log_level)

    def tear_down(self, log_level: log.Level) -> None:
        self._tear_down_log()
        super().tear_down()

        self._timing.test_end()

        self.proc = None

        if self._ut_is_verbose and log_level == log.Level.DEBUG:
            # Hope this is enough for log_server to finish printing from
            # previous test...
            py_time.sleep(0.1)

            # Give ourself a visible output split w/ end time and duration
            print('\n')
            print('end:    ', self._timing.end_str)
            print('elapsed:', self._timing.elapsed_str)
            print('^' * 60)
            print('^' * 60 + '\n')

    # ---
    # Log Set-Up / Tear-Down
    # ---

    def _set_up_log(self,
                    proc_test: ProcTest,
                    log_level: log.Level) -> None:
        if proc_test.has(ProcTest.DNE):
            # Log Server 'Does Not Exist' right now.
            self.log_critical(f"Log server set up has {ProcTest.DNE}. "
                              f"Skipping creation/set-up.")
            return

        # Create our log server Process.
        self.log_debug(f"Set up log server... {proc_test}")
        name = self.NAME_LOG
        context = zontext.empty(__file__,
                                self,
                                '_set_up_log',
                                UnitTestContext)
        self.proc.log = log_server.init(process_name=name,
                                        initial_log_level=log_level,
                                        context=context,
                                        config=self.config,
                                        debug_flags=self.debug_flags)

    def _tear_down_log(self) -> None:
        if not self.proc.log:
            # Log Server 'Does Not Exist' right now.
            self.log_critical("No log server exists. Skipping tear-down.")
            return

        self.log_debug("Tear down log server...")

        # Ask log server to stop if we haven't already...
        if not self.proc.log.shutdown.is_set():
            self._stop(self.proc.log)

        self.proc.log = None

    # -------------------------------------------------------------------------
    # Stop / Clean-Up Tests Functions
    # -------------------------------------------------------------------------
    # This is before actual tear down. Could even be more self.assert*(...)
    # to do... But the actual client/server should be stopped and such.

    def _stop(self, proc: multiproc.ProcToSubComm) -> multiproc.ExitCodeTuple:
        '''
        Stops process. First tries to ask it to stop (i.e. stop gracefully). If
        that takes too long, terminates the process.

        Returns an ExitCodeTuple (the proc name and its exit code).
        '''
        return multiproc.blocking_tear_down(proc)

    def stop_processes(self) -> None:
        '''
        Stops all processes.

        First asks for a graceful stop via self._stop(self.proc.<blank>).
        If that fails, asks for a less graceful stop via Process.terminate().

        Asserts that each has successfully stopped (exitcode == 0).
        '''
        stop_codes = []
        for each in self.proc.all(Processes.Direction.TEAR_DOWN):
            # Let log be taken care of in _tear_down_log.
            if each == self.proc.log:
                continue
            # Stop the process, add its exit code to the list.
            stop_codes.append(self._stop(each))

        # Check our exit codes.
        for name, code in stop_codes:
            self.assertEqual(code, 0,
                             msg=f"{name} had exit code of {code} != 0.")
            # -15 is -SIGTERM, fyi...
            #   https://man7.org/linux/man-pages/man7/signal.7.html

    # -------------------------------------------------------------------------
    # Log Helpers
    # -------------------------------------------------------------------------

    def log(self,
            level: log.Level,
            msg: str,
            *args: Any,
            **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        log.at_level(level, msg, *args, **kwargs,
                     veredi_logger=self.lumberjack)

    def log_ultra_mega_debug(self,
                             msg: str,
                             *args: Any,
                             **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        log.ultra_mega_debug(msg, *args, **kwargs,
                             veredi_logger=self.lumberjack)

    def log_ultra_hyper_debug(self,
                              msg: str,
                              *args: Any,
                              **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        log.ultra_hyper_debug(msg, *args, **kwargs,
                              veredi_logger=self.lumberjack)

    def log_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        self.log(log.Level.DEBUG, msg, *args, **kwargs)

    def log_info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        self.log(log.Level.INFO, msg, *args, **kwargs)

    def log_warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        self.log(log.Level.WARNING, msg, *args, **kwargs)

    def log_critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        '''
        Log with self.lumberjack (has self.NAME_MAIN as its name).
        '''
        self.log(log.Level.CRITICAL, msg, *args, **kwargs)

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

    def disabled(self, stacklevel: int = 2) -> bool:
        '''
        Figures out if a test should be skipped based on some centralized flag
        or thing.

        Redefine if you need to. By default, checks for test's method name
        (as per `self.method_name()`) in `self.DISABLED_TESTS`).

        Make sure `stacklevel` is correct as it is fed into
        `self.method_name()` in order to get the actual test's method name.

        Return True if test should be skipped.
        Return False if test should run.
        '''
        name = self.method_name(stacklevel=stacklevel)
        self.assertIsNotNone(name)

        # Got name, so now we can check if flagged.
        # Could raise a KeyError, and we'll let it bubble up.
        return name in self.DISABLED_TESTS

    # -------------------------------------------------------------------------
    # Once "Per-Test" Helpers
    # -------------------------------------------------------------------------

    def per_test_timeout(self, sig_triggered, frame) -> None:
        '''
        Stop our processes and fail test due to timeout.
        '''
        multiproc._sigalrm_end()
        self.per_test_tear_down()
        self.fail(f'Test failure due to timeout. '
                  f'Signal: {sig_triggered} '
                  f'"{signal.strsignal(sig_triggered)}". '
                  f'Frame: {frame}')

    def per_test_set_up(self, wait_sec: float = 1) -> None:
        '''
        Sets timeout alarm, starts each process, and then waits for `wait_sec`
        for start-up of processes to settle out.
        '''
        # Let it all run and wait for the game to end...
        multiproc._sigalrm_start(self.PER_TEST_TIMEOUT, self.per_test_timeout)

        for each in self.proc.all(Processes.Direction.SET_UP):
            each.process.start()

        # Can't figure out how to get this to not make log_server unable to die
        # gracefully...
        #   - This may have been solved at some point and maybe should be
        #     re-attempted.
        # # Hook this test itself into the log server.
        # log_client.init(self.__class__.__name__, LOG_LEVEL)
        # log.set_level(LOG_LEVEL)

        # Wait for clients, server to settle out.
        self.wait(wait_sec)
        multiproc._sigalrm_end()

    def per_test_tear_down(self) -> None:
        '''
        Stops our processes.
        '''
        self.stop_processes()

    def runner_of_test(self, body: Callable, *args: Any) -> None:
        '''
        Runs `per_test_set_up`, then runs function `body` with catch for
        KeyboardInterrupt (aka SIGINT), then finishes off with
        `per_test_tear_down`.

        If `args`, will run `body` with each arg entry (unpacked if tuple).
        '''
        if self.disabled(3):
            # stack '3' is: disabled(), this, actual test.
            self.skipTest("Test currently disabled as per self.disabled().")

        self.per_test_set_up()

        error = False
        sig_int = False

        multiproc._sigalrm_start(self.PER_TEST_TIMEOUT, self.per_test_timeout)
        try:
            if args:
                for test_arg in args:
                    # If we have args, call body for each one. Unpack its args
                    # for call if it is a (normal) tuple.
                    if (not isinstance(test_arg, multiproc.ProcToSubComm)
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
            # Let interrupt through like this.
            # We'll fail on it in assert_test_ran().

        except AssertionError:
            # Reraise these - should be unittest assertions.
            raise

        except Exception as err:
            error = err

            # [2020-09-03] Wasn't reraising - but the error loses its stack
            # trace and then you just have no idea where the thing that hates
            # you is. Trying out reraising now instead.
            raise

        finally:
            multiproc._sigalrm_end()
            self.per_test_tear_down()

        return (sig_int, error)

    def assert_test_ran(
            self,
            *test_runner_ret_vals: Tuple[int, Union[Literal[False], Exception]]
    ) -> None:
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

    def assert_empty_pipes(self) -> None:
        # ------------------------------
        # Check All Clients - Normal and Test Pipes.
        # ------------------------------
        for client in self.proc.clients:
            # ---
            # Normal Pipe
            # ---
            client_pipe_data = client.has_data()
            if client_pipe_data:
                # Print out what's in the pipe?
                log.critical("Client IPC pipe is not empty!")
                data = client.recv()
                log.ultra_hyper_debug(data)
            self.assertFalse(client_pipe_data)

            # ---
            # Test Pipe
            # ---
            client_test_pipe_data = client._ut_has_data()
            if client_test_pipe_data:
                # Print out what's in the pipe?
                log.critical("Client IPC /test/ pipe is not empty!")
                data = client._ut_recv()
                log.ultra_hyper_debug(data)
            self.assertFalse(client_test_pipe_data)

        # ------------------------------
        # Check Server Pipes
        # ------------------------------
        if self.proc.server:
            # ---
            # Normal Pipe
            # ---
            server_pipe_data = self.proc.server.has_data()
            if server_pipe_data:
                # Print out what's in the pipe?
                log.critical("Server IPC pipe is not empty!")
                data = self.proc.server.recv()
                log.ultra_hyper_debug(data)
            self.assertFalse(server_pipe_data)

            # ---
            # Test Pipe
            # ---
            server_test_pipe_data = self.proc.server.ut_pipe.poll()
            if server_test_pipe_data:
                # Print out what's in the pipe?
                log.critical("Server IPC /test/ pipe is not empty!")
                data = self.proc.server._ut_recv()
                log.ultra_hyper_debug(data)
            self.assertFalse(server_test_pipe_data)

    # -------------------------------------------------------------------------
    # Do-Something-During-A-Test Functions
    # -------------------------------------------------------------------------
    # (Or Do-Nothing,-Really in wait()'s case...)

    def wait_on_nothing(self, wait_timeout) -> None:
        '''
        Sleeps for the wait_timeout. Doesn't care about shutdown flags or
        anything.
        '''
        # Force timeout into range.
        wait_timeout = wait_timeout or 0
        if (wait_timeout < 0.000001
                or wait_timeout > 5):
            # This is a unit test, so we waint to time out and we want to do it
            # soonish... So timeout between quite soonish to 5 sec.
            wait_timeout = min(max(0.000001, wait_timeout), 5)

        # Sleep for either 0.1 sec, or who duration if that's shorter.
        sleep_time = min(wait_timeout, 0.1)
        timer = MonotonicTimer()  # Timer starts timing on creation.
        try:
            self.log_debug("wait_on_nothing: Received SIGINT.")
            while not timer.timed_out(wait_timeout):
                py_time.sleep(sleep_time)

        except KeyboardInterrupt:
            # First, ask for a gentle, graceful shutdown...
            self.log_debug("wait_on_nothing: Received SIGINT.")

        else:
            self.log_debug("wait_on_nothing: Wait finished normally.")

        self.log_debug(f"wait_on_nothing: Waited for {timer.elapsed_sec} sec.")

    def wait(self,
             wait_timeout,
             loop_timeout=multiproc.WAIT_SLEEP_TIME_SEC) -> None:
        '''
        Loops waiting on `self._shutdown` flag or Ctrl-C/SIGINT. Each loop it
        will sleep/await the shutdown flag for `loop_timeout` seconds. The
        maximum amount this will wait is `wait_timeout` seconds.

        Does not call self.stop() or do any clean up after waiting.
        '''
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
                self.log_critical("Nothing is running so... "
                                  "no shutdown flag to check?!")

            running = not shutdown_flag.wait(
                timeout=multiproc.WAIT_SLEEP_TIME_SEC)
            # if log.will_output(log.Level.DEBUG):
            #     time_ok = not timer.timed_out(wait_timeout)
            #     self.log_debug(f"{self.__class__.__name__}: waited "
            #                    f"{timer.elapsed_str}; wait more? "
            #                    f"({running} and {time_ok} "
            #                    f"== {running and time_ok}")
            while running and not timer.timed_out(wait_timeout):
                # self.log_debug(f"{self.__class__.__name__}: waited "
                #                f"{timer.elapsed_str}; wait more.")

                # Do nothing and take naps forever until SIGINT received or
                # wait finished.
                running = not shutdown_flag.wait(
                    timeout=multiproc.WAIT_SLEEP_TIME_SEC)

        except KeyboardInterrupt:
            # First, ask for a gentle, graceful shutdown...
            self.log_debug("Received SIGINT.")

        else:
            self.log_debug("Wait finished normally.")

    # =========================================================================
    # =--------------------------------Tests----------------------------------=
    # =--                        Real Actual Tests                          --=
    # =---------------------...after so much prep work.-----------------------=
    # =========================================================================

    # ------------------------------
    # Check to see if we're blatently ignoring anything...
    # ------------------------------

    # def test_ignored_tests(self):
    #     '''You may want to copy/paste this into your test class.'''
    #     self.assertFalse(self.disabled_tests,
    #                      "Expected no disabled tests, "
    #                      f"got: {self.disabled_tests}")
