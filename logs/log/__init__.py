# coding: utf-8

'''
Veredi's Log is layered on top of Python's 'logging' module.

If you have a class, inherit the 'mixin.LogMixin' class and make sure to call
`_log_config()` during init or configuration. This will give you a logger named
with your class's dotted string, which is a sub-logger of the veredi root
logger.

For more basic needs, use the `log.<level>()` or other functions to log out via
the root veredi logger.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ------------------------------
# Types (External)
# ------------------------------

from logging import Logger as PyLogType  # noqa


# ------------------------------
# Types, Enums, Consts
# ------------------------------

from .const import (
    # Constants
    DEFAULT_LEVEL,

    # Types
    LogLvlConversion, LoggerInput, SuccessInput,

    # Enums
    MessageType, SuccessType, Level, Group, GroupResolve
)


# ------------------------------
# LogName To Root Veredi Logger
# ------------------------------

from .log import (
    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    init,
    init_logger,

    get_logger,
    get_level,
    set_level,

    will_output,
    incr_stack_level,

    ultra_mega_debug,
    ultra_hyper_debug,

    debug,
    info,
    warning,
    error,
    exception,
    critical,
    at_level,

    group,
    set_group_level,
    group_multi,
    security,
    start_up,
    data_processing,


    # ------------------------------
    # 'with' context manager
    # ------------------------------
    LoggingManager,

    # ------------------------------
    # Unit Testing Support
    # ------------------------------
    ut_call,
    ut_set_up,
    ut_tear_down,
)


# ------------------------------
# Log Formatters & Handlers
# ------------------------------

from .formats import (
    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    init_handler,
    remove_handler,
)

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # -------------------------------------------------------------------------
    # const.py
    # -------------------------------------------------------------------------

    # ------------------------------
    # Constants
    # ------------------------------
    'DEFAULT_LEVEL',

    # ------------------------------
    # Types
    # ------------------------------
    'LogLvlConversion',
    'LoggerInput',
    'SuccessInput',

    # ------------------------------
    # Enums
    # ------------------------------
    'MessageType',
    'SuccessType',
    'Level',
    'Group',
    'GroupResolve',


    # -------------------------------------------------------------------------
    # log.py
    # -------------------------------------------------------------------------

    # ------------------------------
    # Types & Consts
    # ------------------------------

    # ------------------------------
    # Functions
    # ------------------------------
    'init',
    'init_logger',

    'get_logger',
    'get_level',
    'set_level',

    'will_output',
    'incr_stack_level',

    'ultra_mega_debug',
    'ultra_hyper_debug',

    'debug',
    'info',
    'warning',
    'error',
    'exception',
    'critical',
    'at_level',

    'group',
    'set_group_level',
    'group_multi',
    'security',
    'start_up',
    'data_processing',


    # ------------------------------
    # 'with' context manager
    # ------------------------------
    'LoggingManager',

    # ------------------------------
    # Unit Testing Support
    # ------------------------------
    'ut_call',
    'ut_set_up',
    'ut_tear_down',


    # -------------------------------------------------------------------------
    # non-log.py
    # -------------------------------------------------------------------------

    # ------------------------------
    # Log Formatters & Handlers
    # ------------------------------
    'init_handler',
    'remove_handler',

    # ------------------------------
    # External Types
    # ------------------------------
    'PyLogType',

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
# Code
# -----------------------------------------------------------------------------
