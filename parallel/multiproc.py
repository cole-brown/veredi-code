# coding: utf-8

'''
Integration Test for a server and clients talking to each other over
websockets.

Only really tests the websockets and Mediator.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, NewType, Callable

import multiprocessing
from multiprocessing.connection import Connection as mp_conn
from ctypes import c_int
import signal
from collections import namedtuple
import time as py_time
from datetime import datetime, time as dt_time
import enum


from veredi.base.enum                           import FlagCheckMixin
from veredi.logger                       import log, log_client
from veredi.base.context       import VerediContext
from veredi.data.config.config import Configuration
from veredi.data.config.context         import ConfigContext
from veredi.debug.const                         import DebugFlag

from .exceptions import MultiProcError


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
        self.name       = name
        self.process    = process
        self.pipe       = pipe
        self.shutdown   = shutdown
        self.ut_pipe    = ut_pipe

    # -------------------------------------------------------------------------
    # Process Control
    # -------------------------------------------------------------------------

    def start(self) -> None:
        '''
        Runs the sub-process.
        '''
        self.process.start()

    def stop(self,
             wait_timeout: float = GRACEFUL_SHUTDOWN_TIME_SEC) -> None:
        '''
        Asks this sub-process to stop/shutdown.

        Will first ask for a graceful shutdown via shutdown flag. This waits
        for a result until timed out (a `wait_timeout` of None will never time
        out).

        If graceful shutdown times out, this will kill the process.
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

        return ExitCodeTuple(self.name, self.process.exitcode)

    # -------------------------------------------------------------------------
    # IPC Helpers
    # -------------------------------------------------------------------------

    def send(self) -> None:
        '''
        TODO
        '''
        pass

    def recv(self) -> None:
        '''
        TODO
        '''
        pass

    def _ut_send(self) -> None:
        '''
        TODO
        '''
        pass

    def _ut_recv(self) -> None:
        '''
        TODO
        '''
        pass

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
                 name:       str,
                 config:     Optional[Configuration],
                 entry_fn:   StartProcFn,
                 pipe:       mp_conn,
                 shutdown:   multiprocessing.Event,
                 debug_flag: Optional[DebugFlag] = None,
                 ut_pipe:    Optional[mp_conn]   = None) -> None:
        self.name       = name
        self.config     = config
        self.pipe       = pipe
        self.shutdown   = shutdown
        self.debug_flag = debug_flag
        self.ut_pipe    = ut_pipe
        self._entry_fn  = entry_fn

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

    def send(self) -> None:
        '''
        TODO
        '''
        pass

    def recv(self) -> None:
        '''
        TODO
        '''
        pass

    def _ut_send(self) -> None:
        '''
        TODO
        '''
        pass

    def _ut_recv(self) -> None:
        '''
        TODO
        '''
        pass

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
           debug_flag:        Optional[DebugFlag]             = None,
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
    # TODO [2020-08-10]: Logging init should take care of level... Try to
    # get rid of this setLevel(). Add level to get_logger()?
    lumberjack = log.get_logger(proc_name)
    lumberjack.setLevel(int(initial_log_level))

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
                          debug_flag=debug_flag,
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
    proc_log.setLevel(int(initial_log_level))

    # Sub-proc will ignore sig-int; primarily pay attention to shutdown flag.
    _sigint_ignore()
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
    log_client.close()
    proc_log.debug(f"Process '{proc.name}' done.")


# -----------------------------------------------------------------------------
# Multiprocess End
# -----------------------------------------------------------------------------

def tear_down(proc: ProcToSubComm) -> ExitCodeTuple:
    '''
    Stops process. First tries to ask it to stop (i.e. stop gracefully). If
    that takes too long, terminates the process.

    Returns an ExitCodeTuple (the proc name and its exit code).
    '''
    lumberjack = log.get_logger(proc.name)

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

    # Set process's shutdown flag. It should notice soon and start doing
    # its shutdown.
    lumberjack.debug(f"{proc.name}: Asking it to end gracefully...")
    proc.shutdown.set()

    # Wait for process to be done.
    if proc.process.is_alive():
        lumberjack.debug(f"{proc.name}: Waiting for completion of "
                         "structured shutdown...")
        proc.process.join(GRACEFUL_SHUTDOWN_TIME_SEC)
        lumberjack.debug(f"{proc.name} exit: "
                         f"{str(proc.process.exitcode)}")
    else:
        lumberjack.debug(f"{proc.name}: didn't run; skip shutdown...")

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
