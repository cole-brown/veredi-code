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


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------


def init(level: Union[log.Level, int] = log.DEFAULT_LEVEL) -> None:
    '''
    Initialize log.py for non-local logging.
    '''
    # We'll use a socket handler to send out the logs.
    socketHandler = logging.handlers.SocketHandler(
        'localhost',
        logging.handlers.DEFAULT_TCP_LOGGING_PORT)

    # Don't bother with a formatter, since a socket handler sends the event as
    # an unformatted pickle.
    log.init(level=level,
             handler=socketHandler,
             formatter=None)
