# coding: utf-8

'''
Easy include for the minimum required to receive and register for events.

That is, do this:
from veredi.interface.input.command.reg import *
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Only import what's needed.
from .event      import CommandRegistrationBroadcast, CommandRegisterReply
from .exceptions import CommandRegisterError, CommandExecutionError
from .const      import CommandPermission
from .args       import CommandArgType, CommandStatus, CommandInvoke


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Explicitly export those pieces to make pycodestyle happy, and to make
# slightly more future/idiot proof.
__all__ = [
    # ---
    # Events
    CommandRegistrationBroadcast,
    CommandRegisterReply,
    # ---

    # ---
    # Exceptions
    CommandRegisterError,
    CommandExecutionError,
    # ---

    # ---
    # Constants
    CommandPermission,
    # ---

    # ---
    # Args & Such
    CommandArgType,
    CommandStatus,
    CommandInvoke,
    # ---
]
