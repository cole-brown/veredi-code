# coding: utf-8

'''
This is the server-side of a multiprocess/thread safe logger.

It will actually log out the logs it receives from log clients. So that all
logs from one game/server are well-formatted and in one place.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

import multiprocessing
from multiprocessing.connection import Connection as mp_conn
from ctypes import c_int
import pickle
import logging
import logging.handlers
import socketserver
import struct
import select
from datetime import datetime


from . import log
from veredi.parallel import multiproc
from veredi.debug.const                         import DebugFlag
from veredi.data                         import background
from veredi.data.config.config import Configuration
from veredi.base.context       import VerediContext
from veredi.data.config.context         import ConfigContext


# -----------------------------------------------------------------------------
# Log Server's multiproc Sub-Classes
# -----------------------------------------------------------------------------

class LogServerComm(multiproc.ProcToSubComm):
    '''
    The parent process's object for communicating to the LogServer sub-process.
    '''

    def __init__(self,
                 name:            str                                   = None,
                 process:         multiprocessing.Process               = None,
                 pipe:            mp_conn = None,
                 shutdown:        multiprocessing.Event                 = None,
                 ignore_logs:     multiprocessing.Event                 = None,
                 ignored_counter: multiprocessing.Value                 = None,
                 ut_pipe:            mp_conn = None
                 ) -> None:
        super().__init__(name=name,
                         process=process,
                         pipe=pipe,
                         shutdown=shutdown,
                         ut_pipe=ut_pipe)
        self.ignore_logs = ignore_logs
        self.ignored_counter = ignored_counter

    def finalize_init(self,
                      ignore_logs:     multiprocessing.Event,
                      ignored_counter: multiprocessing.Value) -> None:
        '''
        Set vars specific to log process comms.
        '''
        self.ignore_logs = ignore_logs
        self.ignored_counter = ignored_counter


class LogServerSub(multiproc.SubToProcComm):
    '''
    The child process's object for communicating with the parent.
    '''

    def __init__(self,
                 name:            str,
                 config:          Optional[Configuration],
                 entry_fn:        multiproc.StartProcFn,
                 pipe:            mp_conn,
                 shutdown:        multiprocessing.Event,
                 ignore_logs:     multiprocessing.Event = None,
                 ignored_counter: multiprocessing.Value = None,
                 debug_flags:     Optional[DebugFlag]   = None,
                 ut_pipe:         Optional[mp_conn]     = None) -> None:
        super().__init__(name=name,
                         config=config,
                         entry_fn=entry_fn,
                         pipe=pipe,
                         shutdown=shutdown,
                         debug_flags=debug_flags,
                         ut_pipe=ut_pipe)
        self.ignore_logs = ignore_logs
        self.ignored_counter = ignored_counter

    def finalize_init(self,
                      ignore_logs:     multiprocessing.Event,
                      ignored_counter: multiprocessing.Value) -> None:
        '''
        Set vars specific to log process comms.
        '''
        self.ignore_logs = ignore_logs
        self.ignored_counter = ignored_counter


# -----------------------------------------------------------------------------
# Log Server Implementation
# -----------------------------------------------------------------------------

class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    '''
    Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.

    https://docs.python.org/3/howto/logging-cookbook.html#network-logging
      - [2020-07-19]
    '''

    def handle(self) -> None:
        '''
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        '''
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unpickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handle_log_record(record)

    def unpickle(self, data: bytes) -> object:
        return pickle.loads(data)

    def handle_log_record(self, record: logging.LogRecord) -> None:
        # Check if we should be ignoring log records (unit testing).
        if (isinstance(self.server, LogRecordSocketReceiver)
                and self.server.should_ignore_record()):
            # Tell our server we're ignoring this one.
            self.server.ignored_record()
            # Black hole it if we're set to ignore.
            return

        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name

        logger = logging.getLogger(name)

        # NOTE!: /EVERY/ record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    '''
    Simple TCP socket-based logging receiver suitable for testing.

    https://docs.python.org/3/howto/logging-cookbook.html#network-logging
      - [2020-07-19]
    '''

    allow_reuse_address = True

    def __init__(
            self,
            shutdown_flag:   multiprocessing.Event,
            ignore_flag:     Optional[multiprocessing.Event] = None,
            ignored_counter: Optional[multiprocessing.Value] = None,
            host:            str = 'localhost',
            port:            int = logging.handlers.DEFAULT_TCP_LOGGING_PORT,
            handler:         logging.Handler = LogRecordStreamHandler
    ) -> None:
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.timeout = 0.5
        self.logname = None
        self.shutdown_flag = shutdown_flag
        self.ignore_flag = ignore_flag
        self.ignored_counter = ignored_counter

    def should_ignore_record(self):
        '''
        Returns whether a log record should be ignored based
        on `self.ignore_flag`.
        '''
        ignore = self.ignore_flag and self.ignore_flag.is_set()
        return ignore

    def ignored_record(self):
        '''
        Called when a handler ignores a log record. Increments
        `self.ignored_counter` if possible.
        '''
        if not self.ignored_counter:
            return

        # If we have a counter, increment it for this ignored log.
        with self.ignored_counter.get_lock():
            self.ignored_counter.value += 1

    def serve_until_stopped(self) -> None:
        while not self.shutdown_flag.is_set():
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                # New client connection to handle. Will keep open and running
                # on its own thread after this.
                self.handle_request()

        # Shutdown flag was set so we're done.
        log.debug("log_server's LogRecordSocketReceiver stopped serving "
                  "in preparation for shutdown.")


# ---------------------------------Log Server----------------------------------
# --                           Main Logging Loop                             --
# ----------------------------Log Til You're Dead.-----------------------------

# ------------------------------
# Init / Create
# ------------------------------

def init(process_name: str = 'veredi.log.server',
         initial_log_level: Optional[log.Level] = None,
         context: VerediContext = None,
         config: Configuration = None,
         debug_flags: DebugFlag = None) -> LogServerComm:
    '''
    Create / Set-Up the Log Server according to context/config data.
    '''
    # ---
    # Prep Work
    # ---

    # Grab ut flag from background?
    ut_flagged = background.testing.get_unit_testing()

    # We are the log_server, so... tell the multiproc code that.
    ConfigContext.set_log_is_server(context, True)

    # ---
    # Init
    # ---

    # ...And get ready for running our sub-proc.
    server = multiproc.set_up(
        # Override types with our subtypes.
        t_proc_to_sub=LogServerComm,
        t_sub_to_proc=LogServerSub,
        # Add finalize so we can give 'em the ignore_logs stuff.
        finalize_fn=_finalize_proc,
        # Normal params:
        proc_name=process_name,
        config=config,
        context=context,
        entry_fn=run,
        initial_log_level=initial_log_level,
        debug_flags=debug_flags,
        unit_testing=ut_flagged)

    return server


def _finalize_proc(proc: multiproc.ProcToSubComm,
                   sub:  multiproc.SubToProcComm) -> None:
    '''
    Finalize the ProcToSubComm and SubToProcComm objects before init finishes.
    '''

    # LogServer-specific multiprocessing stuff.
    ignore_logs = multiprocessing.Event()
    ignored_logs_counter = multiprocessing.Value(c_int, 0)

    proc.finalize_init(ignore_logs, ignored_logs_counter)
    sub.finalize_init(ignore_logs, ignored_logs_counter)


def run(comms: multiproc.SubToProcComm, context: VerediContext = None) -> None:
    '''
    Run the logging server til death do you part.
    '''

    # ------------------------------
    # Set Up Logging, Init Server
    # ------------------------------
    log_level = ConfigContext.log_level(context)
    log.init(level=log_level)
    # TODO [2020-09-12]: Ideally init would stick the level but that wasn't
    # the case back when I started doing the multiproc stuff... Check
    # again/fix.
    log.set_level(log_level)

    log_server = LogRecordSocketReceiver(comms.shutdown,
                                         ignore_flag=comms.ignore_logs,
                                         ignored_counter=comms.ignored_counter)

    # ---
    # Announce thyself, Mr. Lumberjack.
    # ---
    time_utc   = datetime.utcnow().isoformat(timespec='seconds', sep=' ')
    time_local = datetime.now().isoformat(timespec='seconds', sep=' ')
    log.get_logger(comms.name).debug(
        'Started Logging Server at time: '
        f'{time_local} '
        f'(utc: {time_utc})')

    # ------------------------------
    # Run Logging Server!
    # ------------------------------
    log_server.serve_until_stopped()

    # ------------------------------
    # Clean-Up / Tear-Down Server
    # ------------------------------
    log.get_logger(comms.name).debug(
        'Logging Server stopped. Closing...')
    # This gets our sockets closed and quiets this message:
    #   /usr/local/lib/python3.8/multiprocessing/process.py:108:
    #   ResourceWarning: unclosed <socket.socket fd=10,
    #     family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0,
    #     laddr=('127.0.0.1', 9020)> self._target(*self._args, **self._kwargs)
    #   ResourceWarning: Enable tracemalloc to get the object allocation
    #     traceback
    log_server.server_close()

    log.get_logger(comms.name).debug(
        'Ending Logging Server.')


# if __name__ == '__main__':
#     server = init()
#     print('TODO: The run step.')
#     # Null() should run it forever, I think?
#     # run(server, '__main__.log_server', Null())
