# coding: utf-8

'''
Custom Formatters for Logging.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing           import Optional, Callable, List
from veredi.base.null import Null

import logging


from .. import const as const_l
from . import const as const_f

# ------------------------------
# Formats
# ------------------------------

from . import time
from . import yaml


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------
    'init_handler',
    'remove_handler',

    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Namespaced
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
]


# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

_handlers: List[logging.Handler] = []
'''Our main/default logger's main/default handler(s).'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def init_handler(logger: logging.Logger,
                 handler:     Optional[logging.Handler]   = None,
                 formatter:   Optional[logging.Formatter] = None
                 ) -> None:
    '''
    Initializes the handler/formatter and adds them to the logger.

    If provided a handler, use that.
    If provided a formatter, set it in handler.

    If not provided a formatter or handler, will create a default of:
      - logging.StreamHandler
        - with time.BestTimeFmt TODO: change default to yaml.LogYaml
    '''
    # ------------------------------
    # Init Handler / Formatter as Needed.
    # ------------------------------

    # Create a default if nothing provided.
    if not handler:
        # Console Handler, same level.
        handler = logging.StreamHandler()
        # leave as NOTSET - this will let logger control log level
        # handler.setLevel(Level.to_logging(level))

        # Set up our default formatter, but only if handler was not specified.
        # For e.g. log client/server, we don't want a formatter on this
        # (client) side.
        #
        # Docs: "Don't bother with a formatter, since a socket handler sends
        # the event as an unformatted pickle."
        #   - https://docs.python.org/3/howto/logging-cookbook.html#network-logging
        #   - [2020-07-19]
        if not formatter:
            formatter = time.BestTimeFmt(fmt=const_f._FMT_LINE_HUMAN,
                                         datefmt=time.FMT_DATETIME,
                                         style=const_f._STYLE)

    # Set formatter if we have one now.
    if formatter:
        handler.setFormatter(formatter)

    # ------------------------------
    # Orginize our handlers.
    # ------------------------------

    # Either got supplied a handler or we'll be making one. Either way, we want
    # to get rid of any of ours it has.
    global _handlers
    if _handlers:
        for handle in _handlers:
            logger.removeHandler(handle)
        _handlers = []

    # Get rid of any of its own handlers if we've got ones to give it.
    if handler is not None:
        for handle in list(logger.handlers):
            logger.removeHandler(handler)

    # Save it into our collection and on the logger.
    _handlers.append(handler)
    logger.addHandler(handler)

    # Debug it.
    name_handler = (handler.__class__.__name__
                    if handler else
                    'default')
    name_formatter = (formatter.__class__.__name__
                      if formatter else
                      'default')
    logger.debug(f"Logger '{logger.name}' set up with handler "
                 f"'{name_handler}' and formatter '{name_formatter}'.")


def remove_handler(handler:     logging.Handler,
                   logger:      Optional[logging.Logger] = None,
                   logger_name: Optional[str]            = None) -> None:
    '''
    Look in log.__handlers for `handler`. If it finds a match, removes it from
    log.__handlers.

    Calls `removeHandler()` on supplied (or default) logger regardless.
    '''
    global _handlers
    if _handlers and handler in _handlers:
        _handlers.remove(handler)

    if logger:
        logger.removeHandler(handler)

    if logger_name:
        logging.getLogger(logger_name).removeHandler(handler)
