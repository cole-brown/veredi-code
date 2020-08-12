# coding: utf-8

'''
This is the server-side of a multiprocess/thread safe logger.

It will actually log out the logs it receives from log clients. So that all
logs from one game/server are well-formatted and in one place.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union

import multiprocessing
import pickle
import logging
import logging.handlers
import socketserver
import struct
import select
from datetime import datetime

from . import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
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
            host:    str = 'localhost',
            port:    int = logging.handlers.DEFAULT_TCP_LOGGING_PORT,
            handler: logging.Handler = LogRecordStreamHandler) -> None:
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.timeout = 1
        self.logname = None
        self.shutdown_flag = shutdown_flag
        self.ignore_flag = ignore_flag
        self.ignored_counter = ignored_counter

    def verify_request(self, request, client_address):
        '''
        Verifies the request.

        Return True if we should proceed with this request.
        '''
        # Black hole it if we're set to ignore.
        if self.ignore_flag and self.ignore_flag.is_set():
            if self.ignored_counter:
                # If we have a counter, increment it for this ignored log.
                with self.ignored_counter.get_lock():
                    self.ignored_counter.value += 1

            return False

        return super().verify_request(request, client_address)

    def serve_until_stopped(self) -> None:
        while not self.shutdown_flag.is_set():
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()

        # Shutdown flag was set so we're done.


# ---------------------------------Log Server----------------------------------
# --                           Main Logging Loop                             --
# ----------------------------Log Til You're Dead.-----------------------------

def init(shutdown_flag:   multiprocessing.Event,
         level:           Union[log.Level, int]           = log.DEFAULT_LEVEL,
         ignore_flag:     Optional[multiprocessing.Event] = None,
         ignored_counter: Optional[multiprocessing.Array] = None) -> None:
    '''
    Prepare the logging server.
    Returns the logging server. Pass it back into run() to run it.
    '''
    log.init(level=level)
    log.set_level(level)

    log_server = LogRecordSocketReceiver(shutdown_flag,
                                         ignore_flag=ignore_flag,
                                         ignored_counter=ignored_counter)
    return log_server


def run(log_server:    LogRecordSocketReceiver,
        log_name:      str) -> None:
    '''
    Run the logging server til death do you part.
    '''
    time_utc   = datetime.utcnow().isoformat(timespec='seconds', sep=' ')
    time_local = datetime.now().isoformat(timespec='seconds', sep=' ')
    log.get_logger(log_name).debug(
        'Started Logging Server at time: '
        f'{time_local} '
        f'(utc: {time_utc})')

    log_server.serve_until_stopped()
    log.get_logger(log_name).debug(
        'Logging Server stopped. Closing...')
    # This gets our sockets closed and quiets this message:
    #   /usr/local/lib/python3.8/multiprocessing/process.py:108:
    #   ResourceWarning: unclosed <socket.socket fd=10,
    #     family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0,
    #     laddr=('127.0.0.1', 9020)> self._target(*self._args, **self._kwargs)
    #   ResourceWarning: Enable tracemalloc to get the object allocation
    #     traceback
    log_server.server_close()

    # # Fake 'run log server' do-nothing loop waiting on shutdown_flag:
    # # sleep on the shutdown flag, keep sleeping until it returns True
    # while not log_server.shutdown_flag.wait(timeout=1):
    #     pass

    log.get_logger(log_name).debug(
        'Ending Logging Server.')


# if __name__ == '__main__':
#     server = init()
#     print('TODO: The run step.')
#     # Null() should run it forever, I think?
#     # run(server, '__main__.log_server', Null())
