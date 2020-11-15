# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, NewType, Callable, Tuple

import enum
import signal
import time as py_time
import multiprocessing
from multiprocessing.connection import Connection as mp_conn
from ctypes                     import c_int
from collections                import namedtuple
from datetime                   import datetime


import veredi.time.machine

from veredi.base.enum            import FlagCheckMixin
from veredi.base.const           import VerediHealth
from veredi.game.ecs.base.system import SystemLifeCycle
from veredi.logger               import log, log_client
from veredi.base.context         import VerediContext
from veredi.data.config.config   import Configuration
from veredi.data.config.context  import ConfigContext
from veredi.debug.const          import DebugFlag

from .exceptions                 import MultiProcError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

StartProcFn = NewType('StartProcFn',
                      Callable[['SubToProcComm', VerediContext], None])
'''
The function called to start a process should have signature:

Parameters:
  - VerediContext: Should probably have called `ConfigContext.set_subproc()`
                   so that sub-proc can `ConfigContext.subproc()` to get their
                   sub-process data/objects.

Return:
  - None
'''

FinalizeInitFn = NewType('FinalizeInitFn',
                         Callable[['ProcToSubComm', 'SubToProcComm'], None])
'''
The function called to do any final initialization to the ProcToSubComm or
the SubToProcComm objects before set_up() is complete.
'''


WAIT_SLEEP_TIME_SEC = 0.1
'''Main process will wait/sleep on the game_over flag for this long each go.'''


GRACEFUL_SHUTDOWN_TIME_SEC = 15.0
'''
Main process will give the game/mediator this long to gracefully shutdown.
If they take longer, it will just terminate them.
'''


ExitCodeTuple = namedtuple('ExitCodeTuple', ['name', 'exitcode'])
'''
Name and exitcode tuple.
'''


@enum.unique
class ProcTest(FlagCheckMixin, enum.Flag):
    NONE = 0
    '''No process testing flag.'''

    DNE = enum.auto()
    '''
    Do not start/end/etc this process.
    Make it not exist as much as possible.
    '''


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
# Process Info Tuple-ish Class
# -----------------------------------------------------------------------------

class ProcToSubComm:
    '''
    A collection of info and communication objects for the process to talk to
    its sub-process.
    '''

    def __init__(self,
                 name:       str,
                 process:    multiprocessing.Process,
                 pipe:       mp_conn,
                 shutdown:   multiprocessing.Event,
                 ut_pipe:    Optional[mp_conn] = None) -> None:
        self.name:       str                     = name
        self.process:    multiprocessing.Process = process
        self.pipe:       mp_conn                 = pipe
        self.shutdown:   multiprocessing.Event   = shutdown
        self.ut_pipe:    Optional[mp_conn]       = ut_pipe

        self.timer_val:  Optional[float]         = None
        '''
        We don't (currently) manage this, but do hold on to it for
        encapusulation's sake. It can be optionally set in start() and stop().
        '''

        self.time_start: Optional[datetime]      = None
        '''Time we asked process to start.'''

        self.time_end:   Optional[datetime]      = None
        '''Time that the process ended.'''

    # -------------------------------------------------------------------------
    # Process Control
    # -------------------------------------------------------------------------

    def start(self,
              time_sec: Optional[float] = None) -> None:
        '''
        Runs the sub-process.

        Sets `self.timer_val` based on optional param `time_sec`.
        Also sets `self.time_start` to current time.
        '''
        self.timer_val = time_sec
        self.time_start = veredi.time.machine.utcnow()
        self.process.start()

    def stop(self,
             wait_timeout: float = GRACEFUL_SHUTDOWN_TIME_SEC,
             time_sec:  Optional[float]    = None) -> None:
        '''
        Asks this sub-process to stop/shutdown.

        Will first ask for a graceful shutdown via shutdown flag. This waits
        for a result until timed out (a `wait_timeout` of None will never time
        out).

        If graceful shutdown times out, this will kill the process.

        Sets `self.timer_val` based on optional params `time_sec`.

        Only sets `self.time_end` if this function stops the process. If it was
        already non-existant or stopped it will not be set.
        '''
        if not self.process:
            # Not sure this should be an exception. Have as a log for now.
            # raise log.exception(
            #     None,
            #     MultiProcError,
            #     "ProcToSubComm.process is null for {self.name};"
            #     "cannot stop process.")
            log.error("ProcToSubComm.process is null for {self.name};"
                      "cannot stop process. Returning successful exit.")
            # Could return fail code if appropriate.
            return ExitCodeTuple(self.name, 0)

        if self.process.exitcode == 0:
            log.debug(f"{self.name} already stopped.")
            return ExitCodeTuple(self.name, self.process.exitcode)

        # Set our process's shutdown flag. It should notice soon and start
        # doing its shutdown.
        log.debug(f"Asking {self.name} to end gracefully...")
        self.shutdown.set()

        # Wait for our process to be done.
        if self.process.is_alive():
            log.debug(f"Waiting for {self.name} to complete "
                      "structured shutdown...")
            self.process.join(wait_timeout)
            log.debug(f"    {self.name} exit: "
                      f"{str(self.process.exitcode)}")
        else:
            log.debug(f"    {self.name} isn't alive; "
                      "skip shutdown...")

        # Make sure it shut down and gave a good exit code.
        if (self.process.is_alive()
                and self.process.exitcode is None):
            # Still not exited; terminate it.
            self.process.terminate()

        # We stopped it so we know what time_end to set.
        self.time_end = veredi.time.machine.utcnow()
        return ExitCodeTuple(self.name, self.process.exitcode)

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def exitcode_healthy(self,
                         healthy_return: VerediHealth,
                         unhealthy_return: VerediHealth) -> VerediHealth:
        '''
        NOTE: If process is alive, returns VerediHealth.FATAL!!!

        Returns VerediHealth.HEALTHY for good exitcode (0).
        Returns VerediHealth.UNHEALTHY for bad exitcodes.
        '''
        if self.process.is_alive():
            return VerediHealth.FATAL

        return (healthy_return
                if self.process.exitcode == 0 else
                unhealthy_return)

    def healthy(self, life_cycle: SystemLifeCycle) -> VerediHealth:
        '''
        Returns a health value based on sub-process's status.

        If `life_cycle` is SystemLifeCycle.APOPTOSIS, this will return
        APOPTOSIS_FAILURE, APOPTOSIS_SUCCESSFUL, etc instead of FATAL, HEALTHY,
        DYING, etc.
        '''
        # ------------------------------
        # Process DNE.
        # ------------------------------
        if not self.process:
            # If trying to die and have no process... uh...
            # You should have a process.
            if life_cycle == SystemLifeCycle.APOPTOSIS:
                return VerediHealth.APOPTOSIS_FAILURE

            # No process is pretty bad for a multiprocess thing.
            return VerediHealth.FATAL

        # ------------------------------
        # Process Exists.
        # ------------------------------

        # ---
        # Shutdown?
        # ---
        # Did we tell it to shut down?
        if self.shutdown.is_set():
            # Do we want it to shut down?
            if life_cycle != VerediHealth.APOPTOSIS:
                # Let's indicate something that says we want to let the
                # shutdown continue, but that it's also during the wrong
                # SystemLifeCycle...
                return VerediHealth.DYING

            # Ok: SystemLifeCycle is apoptosis. A nice structured death.
            if self.process.is_alive():
                # We're still in apoptosis?
                # TODO: time-out at system manager and/or game engine level.
                return VerediHealth.APOPTOSIS

            # Healthy Exit Code == A Good Death
            elif self.process.exitcode == 0:
                return VerediHealth.APOPTOSIS_SUCCESSFUL

            # Unhealthy Exit Code == Not So Good of a Death
            return VerediHealth.APOPTOSIS_FAILURE

        # ---
        # Not Running but not Shutdown?!
        # ---
        if not self.process.is_alive():
            if life_cycle == VerediHealth.APOPTOSIS:
                log.error("Process '{}' is in "
                          "SystemLifeCycle.APOPTOSIS and "
                          "process is not alive, but shutdown flag isn't set "
                          "and it should be.",
                          self.name)
                # Might be a successful apoptosis from the multiproc standpoint
                # but we don't know. Someone changed the shutdown flag we want
                # to check.
                return VerediHealth.APOPTOSIS_FAILURE

            # Not running and not in apoptosis life-cycle... Dunno but not
            # healthy.
            return VerediHealth.UNHEALTHY

        # ---
        # Running and should be, so... Healthy.
        # ---
        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # IPC Helpers
    # -------------------------------------------------------------------------

    def send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC pipe.
        Waits/blocks until it receives something.
        '''
        self.pipe.send((package, context))

    def has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if pipe has data to recv().
        '''
        return self.pipe.poll()

    def recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC pipe.
        '''
        package, context = self.pipe.recv()
        return (package, context)

    def _ut_send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC unit-testing pipe.
        Waits/blocks until it receives something.
        '''
        self.ut_pipe.send((package, context))

    def _ut_has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if unit-testing pipe has data to recv().
        '''
        return self.pipe.poll()

    def _ut_recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC unit-testing pipe.
        '''
        package, context = self.ut_pipe.recv()
        return (package, context)

    # -------------------------------------------------------------------------
    # Strings
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"


class SubToProcComm:
    '''
    A collection of info and communication objects for the sub-process to talk
    to its parent.
    '''

    def __init__(self,
                 name:        str,
                 config:      Optional[Configuration],
                 entry_fn:    StartProcFn,
                 pipe:        mp_conn,
                 shutdown:    multiprocessing.Event,
                 debug_flags: Optional[DebugFlag] = None,
                 ut_pipe:     Optional[mp_conn]   = None) -> None:
        self.name        = name
        self.config      = config
        self.pipe        = pipe
        self.shutdown    = shutdown
        self.debug_flags = debug_flags
        self.ut_pipe     = ut_pipe
        self._entry_fn   = entry_fn

    # -------------------------------------------------------------------------
    # Process Control
    # -------------------------------------------------------------------------

    def start(self, context: VerediContext) -> None:
        '''
        Runs the entry function.
        '''
        self._entry_fn(self, context)

    # -------------------------------------------------------------------------
    # IPC Helpers
    # -------------------------------------------------------------------------

    def send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC pipe.
        '''
        self.pipe.send((package, context))

    def recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC pipe.
        '''
        package, context = self.pipe.recv()
        return (package, context)

    def _ut_send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC unit-testing pipe.
        '''
        self.ut_pipe.send((package, context))

    def _ut_recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC unit-testing pipe.
        '''
        package, context = self.ut_pipe.recv()
        return (package, context)

    # -------------------------------------------------------------------------
    # Strings
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"


# -----------------------------------------------------------------------------
# Multiprocess Start
# -----------------------------------------------------------------------------

def set_up(proc_name:         str,
           config:            Configuration,
           context:           VerediContext,
           entry_fn:          StartProcFn,
           t_proc_to_sub:     Type['ProcToSubComm']           = ProcToSubComm,
           t_sub_to_proc:     Type['SubToProcComm']           = SubToProcComm,
           finalize_fn:       FinalizeInitFn                  = None,
           initial_log_level: Optional[log.Level]             = None,
           debug_flags:       Optional[DebugFlag]             = None,
           unit_testing:      Optional[bool]                  = False,
           proc_test:         Optional[ProcTest]              = None,
           shutdown:          Optional[multiprocessing.Event] = None
           ) -> Optional[ProcToSubComm]:
    '''
    Get a process ready for _run_proc().

    If `t_proc_to_sub` and/or `t_sub_to_proc` are not default, those classes
    will be instantiated instead of ProcToSubComm / SubToProcComm.

    If `unit_testing`, creates the ut_pipe side-channel.

    If `finalize_fn`, sends both ProcToSubComm and SubToProcComm objects in to
    be processed just before set-up is complete.

    `shutdown` is an optional param in case caller wants multiple sub-processes
    to share the same shutdown flag.

    Returns a `t_proc_to_sub` (default: ProcToSubComm) object. When ready to
    start/run the subprocess, call start() on it.
    '''
    lumberjack = log.get_logger(proc_name,
                                min_log_level=initial_log_level)

    if proc_test and proc_test.has(ProcTest.DNE):
        # This process 'Does Not Exist' right now.
        # Should we downgrade this to debug, or error out more heavily?
        # (i.e. exception?)
        lumberjack.error(f"'{proc_name}' has {proc_test}. "
                         "Skipping creation.")
        return None

    # ------------------------------
    # Create multiproc IPC stuff.
    # ------------------------------
    lumberjack.debug(f"'{proc_name}': Creating inter-process communication...")

    # The official us<->them IPC pipe.
    child_pipe, parent_pipe = multiprocessing.Pipe()

    # The side-channel/unit-test us<->them IPC pipe.
    ut_child_pipe, ut_parent_pipe = None, None
    if unit_testing:
        ut_child_pipe, ut_parent_pipe = multiprocessing.Pipe()

    # multiproc shutdown flag
    if not shutdown:
        shutdown = multiprocessing.Event()

    # ------------------------------
    # Create the process's private info.
    # ------------------------------
    lumberjack.debug(f"'{proc_name}': Creating process comms objects...")

    # Info for the proc itself to own.
    comms = t_sub_to_proc(name=proc_name,
                          config=config,
                          entry_fn=entry_fn,
                          pipe=child_pipe,
                          shutdown=shutdown,
                          debug_flags=debug_flags,
                          ut_pipe=ut_child_pipe)

    # ---
    # Updated Context w/ start-up info (SubToProcComm, etc).
    # ---
    ConfigContext.set_log_level(context, initial_log_level)
    ConfigContext.set_subproc(context, comms)

    # ------------------------------
    # Create the Process, ProcToSubComm
    # ------------------------------
    subp_args = [context]
    subp_kwargs = {}

    # Create the process object (doesn't start the process).
    subprocess = multiprocessing.Process(
        # _subproc_entry() is always the target; it will do some setup and then
        # call the actual target: `entry_fn`.
        target=_subproc_entry,
        name=proc_name,
        args=subp_args,
        kwargs=subp_kwargs)

    # Info for the caller about the proc and how to talk to.
    proc = t_proc_to_sub(name=proc_name,
                         process=subprocess,
                         pipe=parent_pipe,
                         shutdown=shutdown,
                         ut_pipe=ut_parent_pipe)

    # ------------------------------
    # Use Finalize Callback, if supplied.
    # ------------------------------
    if finalize_fn:
        lumberjack.debug(f"'{proc_name}': Finalize function supplied. "
                         f"Calling {finalize_fn}...")
        finalize_fn(proc, comms)

    # ------------------------------
    # Return ProcToSubComm for caller to use to communicate to sub-proc.
    # ------------------------------
    lumberjack.debug(f"'{proc_name}': Set-up complete.")
    return proc


def _subproc_entry(context: VerediContext) -> None:
    '''
    Init and run a multiprocessing process.
    '''

    # ------------------------------
    # Basic Sanity
    # ------------------------------
    if not context:
        raise log.exception(
            None,
            MultiProcError,
            "Require a context to run sub-process. Got nothing.")

    proc = ConfigContext.subproc(context)
    if not proc:
        raise log.exception(
            None,
            MultiProcError,
            "Require SubToProcComm to run sub-process. Got nothing.",
            context=context)

    # ------------------------------
    # Set-Up Logger & Signals
    # ------------------------------
    initial_log_level = ConfigContext.log_level(context)
    # TODO [2020-08-10]: Logging init should take care of level... Try to
    # get rid of this setLevel().
    proc_log = log.get_logger(proc.name)
    proc_log.setLevel(initial_log_level)

    # Sub-proc will ignore sig-int; primarily pay attention to shutdown flag.
    _sigint_ignore()

    # Start up the logging client
    log_is_server = ConfigContext.log_is_server(context)
    if not log_is_server:
        proc_log.debug(f"log_client: '{proc.name}' "
                       f"log_client.init({initial_log_level}).")
        log_client.init(initial_log_level)

    # ------------------------------
    # More Sanity
    # ------------------------------
    if not proc.pipe:
        raise log.exception(
            None,
            MultiProcError,
            "Process '{}' requires a pipe procection; has None.",
            proc.name,
            veredi_logger=proc_log)
    # Not all procs will require a config, maybe? Require until that's true
    # though.
    if not proc.config:
        raise log.exception(
            None,
            MultiProcError,
            "Process '{}' requires a configuration; has None.",
            proc.name,
            veredi_logger=proc_log)
    # If no log level, allow it to be default?
    # if not initial_log_level:
    #     raise log.exception(
    #         None,
    #         MultiProcError,
    #         "Process '{}' requires a default log level (int); "
    #         "received None.",
    #         proc.name,
    #         veredi_logger=proc_log)
    if not proc.shutdown:
        raise log.exception(
            None,
            MultiProcError,
            "Process '{}' requires a shutdown flag; has None.",
            proc.name,
            veredi_logger=proc_log)

    # ------------------------------
    # Actually run the thing...
    # ------------------------------
    proc_log.debug(f"Process '{proc.name}' starting...")
    proc.start(context)

    # ------------------------------
    # Won't reach here until sub-proc is shutdown or dies.
    # ------------------------------
    if not log_is_server:
        proc_log.debug(f"log_client: '{proc.name}' log_client.close().")
        log_client.close()
    proc_log.debug(f"Process '{proc.name}' done.")


# -----------------------------------------------------------------------------
# Multiprocess End
# -----------------------------------------------------------------------------

def blocking_tear_down(proc: ProcToSubComm,
                       graceful_wait: Optional[float] = -1) -> ExitCodeTuple:
    '''
    Stops process. First tries to ask it to stop (i.e. stop gracefully). If
    that takes too long, terminates the process.

    If `graceful_wait` is set to:
      - positive number: This will block for that many seconds for the
        multiprocessing.join() call to finish.
      - `None`: This will block forever until the process stops gracefully.
      - negative number: It will block for `GRACEFUL_SHUTDOWN_TIME_SEC` by
        default.

    Returns an ExitCodeTuple (the proc name and its exit code).
    '''
    if isinstance(graceful_wait, (int, float)) and graceful_wait < 0:
        graceful_wait = GRACEFUL_SHUTDOWN_TIME_SEC

    lumberjack = log.get_logger(proc.name)

    # ------------------------------
    # Sanity Check, Early Out.
    # ------------------------------
    result = _tear_down_check(proc, lumberjack)
    if result:
        return result

    # ------------------------------
    # Kick off tear-down.
    # ------------------------------
    result = _tear_down_start(proc, lumberjack)
    if result:
        return result

    # ------------------------------
    # Wait for tear-down.
    # ------------------------------
    result = _tear_down_wait(proc, lumberjack, graceful_wait,
                             log_enter=True,
                             log_wait_timeout=True,
                             log_exit=True)
    if result:
        return result

    # ------------------------------
    # Finish tear-down.
    # ------------------------------
    result = _tear_down_end(proc, lumberjack)
    return result


def nonblocking_tear_down_start(proc: ProcToSubComm
                                ) -> Optional[ExitCodeTuple]:
    '''
    Kicks off tear-down. Caller will have to loop calling
    `nonblocking_tear_down_wait` for however long they want to wait for a clean
    shutdown, then call `nonblocking_tear_down_end` to finish.
    '''
    lumberjack = log.get_logger(proc.name)

    # ------------------------------
    # Sanity Check, Early Out.
    # ------------------------------
    result = _tear_down_check(proc, lumberjack)
    if result:
        return result

    # ------------------------------
    # Kick off tear-down.
    # ------------------------------
    result = _tear_down_start(proc, lumberjack)
    if result:
        return result


def nonblocking_tear_down_wait(proc:             ProcToSubComm,
                               graceful_wait:    float = 0.1,
                               log_enter:        bool            = False,
                               log_wait_timeout: bool            = False,
                               log_exit:         bool            = False
                               ) -> Optional[ExitCodeTuple]:
    '''
    Wait for `graceful_wait` seconds for process to end gracefully.

    `log_<something>` flags are for help when looping for a small wait so other
    systems can do things. Logs are guarded by `log_<something>`, so a caller
    can have enter logged once, then just loop logging exit (for example).
    '''
    lumberjack = log.get_logger(proc.name)

    # ------------------------------
    # Wait for tear-down.
    # ------------------------------
    result = _tear_down_wait(proc, lumberjack, graceful_wait,
                             log_enter=log_enter,
                             log_wait_timeout=log_wait_timeout,
                             log_exit=log_exit)
    if result:
        return result


def nonblocking_tear_down_end(proc: ProcToSubComm
                              ) -> Optional[ExitCodeTuple]:
    '''
    Finishes tear-down. Checks that process finished shutdown. If not, we
    terminate it immediately.

    In any case, we return its exit code.
    '''
    lumberjack = log.get_logger(proc.name)

    # ------------------------------
    # Finish tear-down.
    # ------------------------------
    result = _tear_down_end(proc, lumberjack)
    return result


def _tear_down_check(proc: ProcToSubComm,
                     lumberjack: Optional[log.PyLogType]
                     ) -> Optional[ExitCodeTuple]:
    '''
    Checks that process exists, then if process has good exit code.
    '''

    if not proc or not proc.process:
        if proc:
            lumberjack.debug(f"No {proc.name} to stop.")
        else:
            lumberjack.debug(f"Cannot stop None/Null: {proc}")
        # Pretend it exited with good exit code?
        return ExitCodeTuple(proc.name, 0)

    if proc.process.exitcode == 0:
        lumberjack.debug(f"{proc.name}: Already stopped.")
        return ExitCodeTuple(proc.name, proc.process.exitcode)

    return None


def _tear_down_start(proc: ProcToSubComm,
                     lumberjack: Optional[log.PyLogType],
                     ) -> Optional[ExitCodeTuple]:
    '''
    Set shutdown flag. Proc should notice soon (not immediately) and start its
    shutdown.
    '''
    lumberjack.debug(f"{proc.name}: Asking it to end gracefully...")
    proc.shutdown.set()


def _tear_down_wait(proc:             ProcToSubComm,
                    lumberjack:       Optional[log.PyLogType],
                    graceful_wait:    Optional[float] = -1,
                    log_enter:        bool            = True,
                    log_wait_timeout: bool            = True,
                    log_exit:         bool            = True
                    ) -> Optional[ExitCodeTuple]:
    '''
    Waits for process to stop gracefully.

    If `graceful_wait` is set to:
      - positive number: This will block for that many seconds for the
        multiprocessing.join() call to finish.
      - `None`: This will block forever until the process stops gracefully.
      - negative number: It will block for `GRACEFUL_SHUTDOWN_TIME_SEC` by
        default.

    `log_<something>` flags are for help when looping for a small wait so other
    systems can do things. Logs are guarded by `log_<something>`, so a caller
    can have enter logged once, then just loop logging exit (for example).

    Returns an ExitCodeTuple (the proc name and its exit code).
    '''
    if isinstance(graceful_wait, (int, float)) and graceful_wait < 0:
        graceful_wait = GRACEFUL_SHUTDOWN_TIME_SEC

    # Wait for process to be done.
    if proc.process.is_alive():
        if log_enter:
            lumberjack.debug(f"{proc.name}: Waiting for completion of "
                             "structured shutdown...")
        proc.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
        if log_wait_timeout and proc.process.exitcode is None:
            lumberjack.debug(f"{proc.name} exit timeout: "
                             f"{str(proc.process.exitcode)}")
        elif log_exit and proc.process.exitcode is not None:
            lumberjack.debug(f"{proc.name} exit: "
                             f"{str(proc.process.exitcode)}")
            return ExitCodeTuple(proc.name, proc.process.exitcode)
    else:
        if log_enter:
            lumberjack.debug(f"{proc.name}: didn't run; skip shutdown...")

    return None


def _tear_down_end(proc: ProcToSubComm,
                   lumberjack: Optional[log.PyLogType]
                   ) -> ExitCodeTuple:
    '''
    Checks that process finished shutdown. If not, we terminate it immediately.

    In any case, we return its exit code.
    '''
    # Make sure it shut down and gave a good exit code.
    if (proc.process
            and proc.process.is_alive()
            and proc.process.exitcode is None):
        # Still not exited; terminate it.
        lumberjack.debug(f"{proc.name}: Still not exited; terminate it... "
                         "Immediately.")
        proc.process.terminate()

    exitcode = (proc.process.exitcode if (proc and proc.process) else None)
    lumberjack.debug(f"{proc.name}: Exited with code: {exitcode}")
    return ExitCodeTuple(proc.name, exitcode)
