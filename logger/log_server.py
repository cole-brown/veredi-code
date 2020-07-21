# coding: utf-8

'''
This is the server-side of a multiprocess/thread safe logger.

It will actually log out the logs it receives from log clients. So that all
logs from one game/server are well-formatted and in one place.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union

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
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data: bytes) -> object:
        return pickle.loads(data)

    def handleLogRecord(self, record: logging.LogRecord) -> None:
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
            host:    str           = 'localhost',
            port:    int           = logging.handlers.DEFAULT_TCP_LOGGING_PORT,
            handler: logging.Handler = LogRecordStreamHandler) -> None:
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


# ---------------------------------Log Server----------------------------------
# --                           Main Logging Loop                             --
# ----------------------------Log Til You're Dead.-----------------------------

def init(level: Union[log.Level, int] = log.DEFAULT_LEVEL) -> None:
    '''
    Prepare the logging server.
    Returns the logging server. Pass it back into run() to run it.
    '''
    log.init(level=level)

    log_server = LogRecordSocketReceiver()
    return log_server


def run(log_server, log_name) -> None:
    '''
    Run the logging server til death do you part.
    '''
    time_utc   = datetime.utcnow().isoformat(timespec='seconds', sep=' ')
    time_local = datetime.now().isoformat(timespec='seconds', sep=' ')

    log.get_logger(log_name).critical(
        '\n'
        'Veredi\n'
        f'  Time: {time_local}\n'
        f'   UTC: {time_utc}\n'
        '------------------\n')

    log.get_logger(log_name).critical(
        'veredi.log.log_server: Starting Logging TCP Server...')
    log_server.serve_until_stopped()


if __name__ == '__main__':
    init()
