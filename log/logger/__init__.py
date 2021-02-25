# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Type, Callable,
                    Mapping, MutableMapping, Iterable, Dict, List)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext


import logging


from .. import const

# -----------------------------------------------------------------------------
# Logger Helpers
# -----------------------------------------------------------------------------

def init(logger_name: str,
         level:       const.LogLvlConversion      = const.DEFAULT_LEVEL,
         handler:     Optional[logging.Handler]   = None,
         formatter:   Optional[logging.Formatter] = None
         ) -> logging.Logger:
    '''
    Initializes and returns a logger with the supplied name.
    '''
    # Create our logger at our default output level.
    logger = logging.getLogger(logger_name)
    logger.setLevel(const.Level.to_logging(level))
    logger.debug(f"Logger '{logger_name}' initialized at level {level}")

    # ---
    # Handlers & Formatters
    # ---

    # Get rid of any of its own handlers if we've got ones to give it.
    if handler:
        for handle in list(logger.handlers):
            logger.removeHandler(handler)

    if not handler:
        # Console Handler, same level.
        handler = logging.StreamHandler()
        # leave as NOTSET - this will let logger control log level
        # handler.setLevel(Level.to_logging(level))

        # Set up our formatter, but only if handler was not specified. For e.g.
        # log client/server, we don't want a formatter on this (client) side.
        #
        # Docs: "Don't bother with a formatter, since a socket handler sends
        # the event as an unformatted pickle."
        #   - https://docs.python.org/3/howto/logging-cookbook.html#network-logging
        #   - [2020-07-19]
        formatter = BestTimeFmt(fmt=_FMT_LINE_HUMAN,
                                datefmt=_FMT_DATETIME,
                                style=_STYLE)
        handler.setFormatter(formatter)

    # Now set it in our collection and on the logger.
    __handlers.append(handler)
    logger.addHandler(handler)


    return logger
