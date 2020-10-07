# coding: utf-8

'''
This is the client-side of a multiprocess/thread safe logger.

It will set up log.py so that logs get routed to a log server instead of output
through this process/thread/whatever.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union

import logging
import logging.handlers

from . import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-10]: Make log_client the only way to init veredi's log?
#   - Would have avoided the double-init issue I had/have in
#     zest_client_server_websocket.py...

_socket_handler = None

# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def init(level: Union[log.Level, int, None] = log.DEFAULT_LEVEL) -> None:
    '''
    Initialize log.py for non-local logging.
    '''
    # We'll use a socket handler to send out the logs.
    global _socket_handler
    _socket_handler = logging.handlers.SocketHandler(
        'localhost',
        logging.handlers.DEFAULT_TCP_LOGGING_PORT)

    # Don't bother with a formatter, since a socket handler sends the event as
    # an unformatted pickle.
    log.init(level=level,
             handler=_socket_handler,
             formatter=None,
             reinitialize=True)
    # log.set_level(level)


def close():
    '''
    Close out our _socket_handler if we have one.
    '''
    global _socket_handler

    if not _socket_handler:
        return

    _socket_handler.close()
    log.remove_handler(_socket_handler)
