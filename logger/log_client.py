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

from . import const
from . import formats
from . import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO [2020-08-10]: Make log_client the only way to init veredi's log?
#   - Would have avoided the double-init issue I had/have in
#     zest_client_server_websocket.py...

_socket_handler: logging.Handler = None

_client_name: str = None


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def init(client_name: str,
         level:       Union[const.Level, int, None] = const.DEFAULT_LEVEL) -> None:
    '''
    Initialize log.py for non-local logging.
    '''
    global _client_name
    _client_name = client_name

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
    log.debug(f"log_client init: {_client_name}")

def close():
    '''
    Close out our _socket_handler if we have one.
    '''
    global _socket_handler

    if not _socket_handler:
        log.debug(f"log_client close: {_client_name} - no _socket_handler")
        return

    log.debug(f"log_client close: {_client_name} - closing _socket_handler...")
    _socket_handler.close()
    formats.remove_handler(_socket_handler)
    log.debug(f"log_client close: {_client_name} - done.")
