# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Type, NewType, Callable, Tuple, List

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
from veredi.base.strings         import label
from veredi.base.strings.mixin   import NamesMixin
from veredi.game.ecs.base.system import SystemLifeCycle
from veredi.logs                 import log, log_client
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
    NONE = enum.auto()
    '''No process testing flag.'''

    DNE = enum.auto()
    '''
    Do not start/end/etc this process.
    Make it not exist as much as possible.
    '''

    LOG_LEVEL_DELAY = enum.auto()
    '''
    Delay setting log level until late in initialization/set-up.
    '''


_LOG_INIT: List[log.Group] = [
    log.Group.START_UP,
    log.Group.PARALLEL,
]
'''
Group of logs we use a lot for log.group_multi().
'''


_LOG_KILL: List[log.Group] = [
    log.Group.SHUTDOWN,
    log.Group.PARALLEL,
]
'''
Group of logs we use a lot for log.group_multi().
'''


_DOTTED_FUNCS: label.DotStr = 'veredi.parallel.multiproc'
'''Veredi dotted label for multiproc functions.'''


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

class ProcToSubComm(NamesMixin,
                    name_dotted='veredi.parallel.multiproc.process',
                    # Name replaced in __init__()
                    name_string='multiproc.p2sc'):
    '''
    A collection of info and communication objects for the process to talk to
    its sub-process.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 name:       str,
                 process:    multiprocessing.Process,
                 pipe:       mp_conn,
                 shutdown:   multiprocessing.Event,
                 ut_pipe:    Optional[mp_conn] = None) -> None:
        # Updated name descriptor to parameter.
        self.name = name

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

    def started(self) -> Optional[bool]:
        '''
        Returns None if `start()` has not been called.
        Returns False if `start()` has been called but we are not alive yet.
        Returns True if we are alive.
        '''
        if not self.time_start:
            return None
        return self.process.is_alive()

    def start_time(self) -> Optional[datetime]:
        '''
        Returns None or the datetime that `start()` was called.
        '''
        return self.time_start

    def start(self,
              time_sec: Optional[float] = None) -> None:
        '''
        Runs the sub-process.

        Sets `self.timer_val` based on optional param `time_sec`.
        Also sets `self.time_start` to current time.
        '''
        log.group_multi(_LOG_INIT,
                        self.dotted,
                        f"{self.__class__.__name__}: "
                        f"Starting {self.name} sub-process...")
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
            #     MultiProcError,
            #     "ProcToSubComm.process is null for {self.name};"
            #     "cannot stop process.")
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            "process is null for {self.name}; "
                            "cannot stop process. Returning successful "
                            "exit anyways.",
                            log_minimum=log.Level.WARNING,
                            log_success=False)
            # Could return fail code if appropriate.
            return ExitCodeTuple(self.name, 0)

        if self.process.exitcode == 0:
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            "{self.name} process already stopped.")
            return ExitCodeTuple(self.name, self.process.exitcode)

        # Set our process's shutdown flag. It should notice soon and start
        # doing its shutdown.
        log.group_multi(_LOG_KILL,
                        self.dotted,
                        f"{self.__class__.__name__}: "
                        f"Asking {self.name} to end gracefully...")
        self.shutdown.set()

        # Wait for our process to be done.
        if self.process.is_alive():
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            f"Waiting for {self.name} to complete "
                            "structured shutdown...")
            self.process.join(wait_timeout)
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            f"{self.name} exit code: "
                            f"{str(self.process.exitcode)}")
        else:
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            f"{self.name} isn't alive; "
                            "skip shutdown...")

        # Make sure it shut down and gave a good exit code.
        if (self.process.is_alive()
                and self.process.exitcode is None):
            # Still not exited; terminate it.
            log.group_multi(_LOG_KILL,
                            self.dotted,
                            f"{self.__class__.__name__}: "
                            f"{self.name} still not exited; terminating...")
            self.process.terminate()

        # We stopped it so we know what time_end to set.
        self.time_end = veredi.time.machine.utcnow()
        log.group_multi(_LOG_KILL,
                        self.dotted,
                        f"{self.__class__.__name__}: "
                        f"{self.name} stopped.")
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

        If `life_cycle` is SystemLifeCycle.AUTOPHAGY, this will return
        AUTOPHAGY_FAILURE, AUTOPHAGY_SUCCESSFUL, etc instead of FATAL, HEALTHY,
        DYING, etc.
        '''
        # ------------------------------
        # Process DNE.
        # ------------------------------
        if not self.process:
            # If trying to die and have no process... uh...
            # You should have a process.
            if life_cycle == SystemLifeCycle.AUTOPHAGY:
                return VerediHealth.AUTOPHAGY_FAILURE

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
            if life_cycle != VerediHealth.AUTOPHAGY:
                # Let's indicate something that says we want to let the
                # shutdown continue, but that it's also during the wrong
                # SystemLifeCycle...
                return VerediHealth.DYING

            # Ok: SystemLifeCycle is autophagy. A nice structured death.
            if self.process.is_alive():
                # We're still in autophagy?
                # TODO: time-out at system manager and/or game engine level.
                return VerediHealth.AUTOPHAGY

            # Healthy Exit Code == A Good Death
            elif self.process.exitcode == 0:
                return VerediHealth.AUTOPHAGY_SUCCESSFUL

            # Unhealthy Exit Code == Not So Good of a Death
            return VerediHealth.AUTOPHAGY_FAILURE

        # ---
        # Not Running but not Shutdown?!
        # ---
        if not self.process.is_alive():
            if life_cycle == VerediHealth.AUTOPHAGY:
                log.error("Process '{}' is in "
                          "SystemLifeCycle.AUTOPHAGY and "
                          "process is not alive, but shutdown flag isn't set "
                          "and it should be.",
                          self.name)
                # Might be a successful autophagy from the multiproc standpoint
                # but we don't know. Someone changed the shutdown flag we want
                # to check.
                return VerediHealth.AUTOPHAGY_FAILURE

            # Not running and not in autophagy life-cycle... Dunno but not
            # healthy.
            return VerediHealth.UNHEALTHY

        # ---
        # Running and should be, so... Healthy.
        # ---
        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # IPC Helpers
    # -------------------------------------------------------------------------

    def has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if pipe has data to recv().
        '''
        contains_data = self.pipe.poll()
        # log.data_processing(self.dotted,
        #                     "{} '{}' pipe has data?: {}",
        #                     self.__class__.__name__, self.name,
        #                     contains_data)
        #                     # log_only_at=log.Level.DEBUG)
        return contains_data

    def send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC pipe.
        Waits/blocks until it receives something.
        '''
        log.data_processing(self.dotted,
                            "{} '{}' send to sub-proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        self.pipe.send((package, context))

    def recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC pipe.
        '''
        package, context = self.pipe.recv()
        log.data_processing(self.dotted,
                            "{} '{}' recv from sub-proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        return (package, context)

    def _ut_exists(self) -> bool:
        '''
        Returns True if self._comms.ut_pipe is truthy.
        '''
        exists = bool(self.ut_pipe)
        # log.data_processing(self.dotted,
        #                     "{} '{}' TESTING pipe exists?: {}",
        #                     self.__class__.__name__, self.name,
        #                     exists)
        return exists

    def _ut_has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if unit-testing pipe has data to recv().
        '''
        contains_data = self.ut_pipe.poll()
        # log.data_processing(self.dotted,
        #                     "{} '{}' TESTING pipe has data?: {}",
        #                     self.__class__.__name__, self.name,
        #                     contains_data)
        return contains_data

    def _ut_send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC unit-testing pipe.
        Waits/blocks until it receives something.
        '''
        log.data_processing(self.dotted,
                            "{} '{}' unit-test send to sub-proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        self.ut_pipe.send((package, context))

    def _ut_recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC unit-testing pipe.
        '''
        package, context = self.ut_pipe.recv()
        log.data_processing(self.dotted,
                            "{} '{}' unit-test recv from sub-proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        return (package, context)

    # -------------------------------------------------------------------------
    # Strings
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"


class SubToProcComm(NamesMixin,
                    name_dotted='veredi.parallel.multiproc.subprocess',
                    # Name replaced in __init__()
                    name_string='multiproc.s2pc'):
    '''
    A collection of info and communication objects for the sub-process to talk
    to its parent.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 name:        str,
                 config:      Optional[Configuration],
                 entry_fn:    StartProcFn,
                 pipe:        mp_conn,
                 shutdown:    multiprocessing.Event,
                 debug_flags: Optional[DebugFlag] = None,
                 ut_pipe:     Optional[mp_conn]   = None) -> None:
        # Updated name descriptor to parameter.
        self.name = name

        self.config:      Optional[Configuration] = config
        self.pipe:        mp_conn                 = pipe
        self.shutdown:    multiprocessing.Event   = shutdown
        self.debug_flags: Optional[DebugFlag]     = debug_flags
        self.ut_pipe:     Optional[mp_conn]       = ut_pipe
        self._entry_fn:   StartProcFn             = entry_fn

    # -------------------------------------------------------------------------
    # Process Control
    # -------------------------------------------------------------------------

    def start(self, context: VerediContext) -> None:
        '''
        Runs the entry function.
        '''
        log.group_multi(_LOG_INIT,
                        self.dotted,
                        f"{self.__class__.__name__}: "
                        f"Starting {self.name}...")
        self._entry_fn(self, context)

    # -------------------------------------------------------------------------
    # IPC Helpers
    # -------------------------------------------------------------------------

    def has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if pipe has data to recv().
        '''
        contains_data = self.pipe.poll()
        # log.data_processing(self.dotted,
        #                     "{} '{}' pipe has data?: {}",
        #                     self.__class__.__name__, self.name,
        #                     contains_data)
        return contains_data

    def send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC pipe.
        Waits/blocks until it receives something.
        '''
        log.data_processing(self.dotted,
                            "{} '{}' pipe send to main proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        self.pipe.send((package, context))

    def recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC pipe.
        '''
        package, context = self.pipe.recv()
        log.data_processing(self.dotted,
                            "{} '{}' pipe recv from main proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        return (package, context)

    def _ut_exists(self) -> bool:
        '''
        Returns True if self._comms.ut_pipe is truthy.
        '''
        exists = bool(self.ut_pipe)
        # log.data_processing(self.dotted,
        #                     "{} '{}' TESTING pipe exists?: {}",
        #                     self.__class__.__name__, self.name,
        #                     exists)
        return exists

    def _ut_has_data(self) -> bool:
        '''
        No wait/block.
        Returns True if unit-testing pipe has data to recv().
        '''
        contains_data = self.ut_pipe.poll()
        # log.data_processing(self.dotted,
        #                     "{} '{}' TESTING pipe has data?: {}",
        #                     self.__class__.__name__, self.name,
        #                     contains_data)
        return contains_data

    def _ut_send(self, package: Any, context: VerediContext) -> None:
        '''
        Push package & context into IPC unit-testing pipe.
        Waits/blocks until it receives something.
        '''
        log.data_processing(self.dotted,
                            "{} '{}' TESTING pipe send to main proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
        self.ut_pipe.send((package, context))

    def _ut_recv(self) -> Tuple[Any, VerediContext]:
        '''
        Pull a package & context from the IPC unit-testing pipe.
        '''
        package, context = self.ut_pipe.recv()
        log.data_processing(self.dotted,
                            "{} '{}' TESTING pipe recv from main proc: {}, {}",
                            self.__class__.__name__, self.name,
                            package, context)
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
    logger = log.get_logger(proc_name,
                            min_log_level=initial_log_level)
    log_dotted = label.normalize(_DOTTED_FUNCS, 'set_up')


    if proc_test and proc_test.has(ProcTest.DNE):
        # This process 'Does Not Exist' right now.
        # Should we downgrade this to debug, or error out more heavily?
        # (i.e. exception?)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "'{}' has {}. Skipping creation.",
                        proc_name, proc_test,
                        veredi_logger=logger,
                        log_minimum=log.Level.ERROR,
                        log_success=False)
        return None

    # ------------------------------
    # Create multiproc IPC stuff.
    # ------------------------------
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "'{}': Creating inter-process communication...",
                    proc_name,
                    veredi_logger=logger)

    # The official us<->them IPC pipe.
    child_pipe, parent_pipe = multiprocessing.Pipe()

    # The side-channel/unit-test us<->them IPC pipe.
    ut_child_pipe, ut_parent_pipe = None, None
    if unit_testing:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "'{}': Creating unit-testing "
                        "inter-process communication...",
                        proc_name,
                        veredi_logger=logger)
        ut_child_pipe, ut_parent_pipe = multiprocessing.Pipe()
        context.add('proc-test', proc_test)

    # multiproc shutdown flag
    if not shutdown:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "'{}': Creating shutdown inter-process "
                        "event flag...",
                        proc_name,
                        veredi_logger=logger)
        shutdown = multiprocessing.Event()

    # ------------------------------
    # Create the process's private info.
    # ------------------------------
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "'{}': Creating process comms objects...",
                    proc_name,
                    veredi_logger=logger)

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
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "'{}': Saving into the ConfigContext...",
                    proc_name,
                    veredi_logger=logger)
    ConfigContext.set_log_level(context, initial_log_level)
    ConfigContext.set_subproc(context, comms)

    # ------------------------------
    # Create the Process, ProcToSubComm
    # ------------------------------
    subp_args = [context]
    subp_kwargs = {}

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "'{}': Creating the sub-process object...",
                    proc_name,
                    veredi_logger=logger)

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
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "'{}': Finalize function supplied. "
                        "Calling {}...",
                        proc_name, finalize_fn,
                        veredi_logger=logger)
        finalize_fn(proc, comms)

    # ------------------------------
    # Return ProcToSubComm for caller to use to communicate to sub-proc.
    # ------------------------------
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "'{}': Set-up complete.",
                    proc_name,
                    veredi_logger=logger)
    return proc


def _subproc_entry(context: VerediContext) -> None:
    '''
    Init and run a multiprocessing process.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, 'entry')

    # ------------------------------
    # Basic Sanity
    # ------------------------------
    if not context:
        log.group_multi(
            _LOG_INIT,
            _log_dotted,
            "_subproc_entry: "
            "Require a context to run sub-process. Got nothing.")
        raise log.exception(
            MultiProcError,
            "Require a context to run sub-process. Got nothing.")

    proc = ConfigContext.subproc(context)
    if not proc:
        log.group_multi(
            _LOG_INIT,
            _log_dotted,
            "_subproc_entry: "
            "Require SubToProcComm to run sub-process. Got nothing.")
        raise log.exception(
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

    log.group_multi(_LOG_INIT,
                    _log_dotted,
                    "Initializing sub-process '{}'",
                    proc.name,
                    veredi_logger=proc_log)

    # Start up the logging client
    log_is_server = ConfigContext.log_is_server(context)
    if not log_is_server:
        log.group_multi(_LOG_INIT,
                        _log_dotted,
                        "Initializing log_client for '{}'",
                        proc.name,
                        veredi_logger=proc_log)
        log_client.init(proc.name, initial_log_level)

    # ------------------------------
    # More Sanity
    # ------------------------------
    if not proc.pipe:
        log.group_multi(
            _LOG_INIT,
            _log_dotted,
            "Process '{}' requires a pipe connection; has None.",
            proc.name,
            veredi_logger=proc_log)
        raise log.exception(
            MultiProcError,
            "Process '{}' requires a pipe connection; has None.",
            proc.name,
            veredi_logger=proc_log)
    # Not all procs will require a config, maybe? Require until that's true
    # though.
    if not proc.config:
        log.group_multi(
            _LOG_INIT,
            _log_dotted,
            "Process '{}' requires a configuration; has None.",
            proc.name,
            veredi_logger=proc_log)
        raise log.exception(
            MultiProcError,
            "Process '{}' requires a configuration; has None.",
            proc.name,
            veredi_logger=proc_log)
    # If no log level, allow it to be default?
    # if not initial_log_level:
    #     raise log.exception(
    #         MultiProcError,
    #         "Process '{}' requires a default log level (int); "
    #         "received None.",
    #         proc.name,
    #         veredi_logger=proc_log)
    if not proc.shutdown:
        log.group_multi(
            _LOG_INIT,
            _log_dotted,
            "Process '{}' requires a shutdown flag; has None.",
            proc.name,
            veredi_logger=proc_log)
        raise log.exception(
            MultiProcError,
            "Process '{}' requires a shutdown flag; has None.",
            proc.name,
            veredi_logger=proc_log)

    # ------------------------------
    # Actually run the thing...
    # ------------------------------
    log.group_multi(_LOG_INIT,
                    _log_dotted,
                    "Process '{}' starting...",
                    proc.name,
                    veredi_logger=proc_log)
    proc.start(context)

    # DONE WITH '_LOG_INIT'; SWITCH TO '_LOG_KILL'!

    # ------------------------------
    # Won't reach here until sub-proc is shutdown or dies.
    # ------------------------------
    if not log_is_server:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "Closing log_client for '{}' log_client.close().",
                        proc.name,
                        veredi_logger=proc_log)
        log_client.close()

    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "Process '{}' done.",
                    proc.name,
                    veredi_logger=proc_log)


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

    _log_dotted = label.normalize(_DOTTED_FUNCS, 'tear_down.blocking.full')
    logger = log.get_logger(proc.name)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "blocking_tear_down({}): "
                    "graceful_wait: {}, shutdown? {}",
                    proc.name, graceful_wait,
                    proc.shutdown.is_set(),
                    veredi_logger=logger)

    # ------------------------------
    # Sanity Check, Early Out.
    # ------------------------------
    result = _tear_down_check(proc, logger)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "blocking_tear_down({}): tear_down_check: {}, "
                    "shutdown? {}",
                    proc.name, result,
                    proc.shutdown.is_set(),
                    veredi_logger=logger)
    if result:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "blocking_tear_down({}): finished with: {}, "
                        "shutdown? {}",
                        proc.name, result,
                        proc.shutdown.is_set(),
                        veredi_logger=logger)
        return result

    # ------------------------------
    # Kick off tear-down.
    # ------------------------------
    _tear_down_start(proc, logger)
    # `_tear_down_start()` doesn't have a return - can't check it.
    # if result:
    #     log.debug(f"blocking_tear_down({proc.name}): finished with: {result}, "
    #               f"shutdown? {proc.shutdown.is_set()}",
    #               veredi_logger=logger)
    #     return result

    # ------------------------------
    # Wait for tear-down.
    # ------------------------------
    result = _tear_down_wait(proc, logger, graceful_wait,
                             log_enter=True,
                             log_wait_timeout=True,
                             log_exit=True)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "blocking_tear_down({}): tear_down_wait: {}, "
                    "shutdown? {}",
                    proc.name, result,
                    proc.shutdown.is_set(),
                    veredi_logger=logger)
    if result:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "blocking_tear_down({}): finished with: {}, "
                        "shutdown? {}",
                        proc.name, result,
                        proc.shutdown.is_set(),
                        veredi_logger=logger)
        return result

    # ------------------------------
    # Finish tear-down.
    # ------------------------------
    result = _tear_down_end(proc, logger)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "blocking_tear_down({}): tear_down_end: {}, "
                    "shutdown? {}",
                    proc.name, result,
                    proc.shutdown.is_set(),
                    veredi_logger=logger)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "blocking_tear_down({}): completed with: {}, "
                    "shutdown? {}",
                    proc.name, result,
                    proc.shutdown.is_set(),
                    veredi_logger=logger)
    return result


def nonblocking_tear_down_start(proc: ProcToSubComm
                                ) -> Optional[ExitCodeTuple]:
    '''
    Kicks off tear-down. Caller will have to loop calling
    `nonblocking_tear_down_wait` for however long they want to wait for a clean
    shutdown, then call `nonblocking_tear_down_end` to finish.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, 'tear_down.nonblocking.start')
    logger = log.get_logger(proc.name)

    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_start({}): Begin.",
                    proc.name,
                    veredi_logger=logger)

    # ------------------------------
    # Sanity Check, Early Out.
    # ------------------------------
    result = _tear_down_check(proc, logger)
    if result:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "nonblocking_tear_down_start({}): ",
                        "Check returned exit code: {}",
                        proc.name, result,
                        veredi_logger=logger)
        return result

    # ------------------------------
    # Kick off tear-down.
    # ------------------------------
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_start({}): ",
                    "Starting tear-down...",
                    proc.name,
                    veredi_logger=logger)
    _tear_down_start(proc, logger)
    # No return value for `_tear_down_start()`; can't check anything.
    # if result:
    #     log.group_multi(_LOG_KILL,
    #                     _log_dotted,
    #                     "nonblocking_tear_down_start({}): ",
    #                     "_tear_down_start returned exit code: {}",
    #                     proc.name, result,
    #                     veredi_logger=logger)
    #     return result

    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_start({}): Done.",
                    proc.name,
                    veredi_logger=logger)


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
    _log_dotted = label.normalize(_DOTTED_FUNCS, 'tear_down.nonblocking.wait')
    logger = log.get_logger(proc.name)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_start({}): Begin.",
                    proc.name,
                    veredi_logger=logger)

    # ------------------------------
    # Wait for tear-down.
    # ------------------------------
    result = _tear_down_wait(proc, logger, graceful_wait,
                             log_enter=log_enter,
                             log_wait_timeout=log_wait_timeout,
                             log_exit=log_exit)
    if result:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "_tear_down_wait({}): Returned exit code: {}",
                        proc.name, result,
                        veredi_logger=logger)
        return result

    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_start({}): No exit yet...",
                    proc.name,
                    veredi_logger=logger)


def nonblocking_tear_down_end(proc: ProcToSubComm
                              ) -> Optional[ExitCodeTuple]:
    '''
    Finishes tear-down. Checks that process finished shutdown. If not, we
    terminate it immediately.

    In any case, we return its exit code.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, 'tear_down.nonblocking.end')
    logger = log.get_logger(proc.name)

    # ------------------------------
    # Finish tear-down.
    # ------------------------------
    result = _tear_down_end(proc, logger)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "nonblocking_tear_down_end({}): "
                    "_tear_down_end returned exit code: {}",
                    proc.name, result,
                    veredi_logger=logger)
    return result


def _tear_down_check(proc: ProcToSubComm,
                     logger: Optional[log.PyLogType]
                     ) -> Optional[ExitCodeTuple]:
    '''
    Checks that process exists, then if process has good exit code.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, '_tear_down.check')

    if not proc or not proc.process:
        if proc:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_check({}): "
                            "No {} to stop.",
                            proc.name, proc.name,
                            veredi_logger=logger)
        else:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_check(): "
                            "Cannot stop None/Null sub-process: {}",
                            proc,
                            veredi_logger=logger)
        # Pretend it exited with good exit code?
        return ExitCodeTuple(proc.name, 0)

    if proc.process.exitcode == 0:
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "_tear_down_check({}): "
                        "Process '{}' is already stopped.",
                        proc.name, proc.name,
                        veredi_logger=logger)
        return ExitCodeTuple(proc.name, proc.process.exitcode)

    return None


def _tear_down_start(proc: ProcToSubComm,
                     logger: Optional[log.PyLogType],
                     ) -> None:
    '''
    Set shutdown flag. Proc should notice soon (not immediately) and start its
    shutdown.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, '_tear_down.start')
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "_tear_down_start({}): "
                    "Asking '{}' to end gracefully...",
                    proc.name, proc.name,
                    veredi_logger=logger)
    proc.shutdown.set()


def _tear_down_wait(proc:             ProcToSubComm,
                    logger:       Optional[log.PyLogType],
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

    _log_dotted = label.normalize(_DOTTED_FUNCS, '_tear_down.wait')

    # Wait for process to be done.
    if proc.process.is_alive():
        if log_enter:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_wait({}): "
                            "Waiting for '{}' to complete "
                            "structured shutdown...",
                            proc.name, proc.name,
                            veredi_logger=logger)
        proc.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
        if log_wait_timeout and proc.process.exitcode is None:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_wait({}): "
                            "'{proc.name}' timed out of this wait; "
                            "not dead yet.",
                            proc.name, proc.name,
                            veredi_logger=logger)
        elif log_exit and proc.process.exitcode is not None:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_wait({}): "
                            "'{}' has exited with exit code: {}",
                            proc.name, proc.name,
                            str(proc.process.exitcode),
                            veredi_logger=logger)
            return ExitCodeTuple(proc.name, proc.process.exitcode)
    else:
        if log_enter:
            log.group_multi(_LOG_KILL,
                            _log_dotted,
                            "_tear_down_wait({}): "
                            "'{}' didn't run; skip shutdown...",
                            proc.name, proc.name,
                            veredi_logger=logger)

    return None


def _tear_down_end(proc: ProcToSubComm,
                   logger: Optional[log.PyLogType]
                   ) -> ExitCodeTuple:
    '''
    Checks that process finished shutdown. If not, we terminate it immediately.

    In any case, we return its exit code.
    '''
    _log_dotted = label.normalize(_DOTTED_FUNCS, '_tear_down.end')

    # Make sure it shut down and gave a good exit code.
    if (proc.process
            and proc.process.is_alive()
            and proc.process.exitcode is None):
        # Still not exited; terminate it.
        log.group_multi(_LOG_KILL,
                        _log_dotted,
                        "_tear_down_end({}): "
                        "'{}' has still not exited; terminate it... "
                        "Immediately.",
                        proc.name, proc.name,
                        veredi_logger=logger)
        proc.process.terminate()

    exitcode = (proc.process.exitcode if (proc and proc.process) else None)
    log.group_multi(_LOG_KILL,
                    _log_dotted,
                    "_tear_down_end({}): "
                    "'{}' has exited with exit code: {}",
                    proc.name, proc.name,
                    str(exitcode),
                    veredi_logger=logger)
    return ExitCodeTuple(proc.name, exitcode)
