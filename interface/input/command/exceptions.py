# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Our Stuff
from veredi.base.exceptions import VerediError


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

# ---
# Base
# ---

class CommandError(VerediError):
    '''
    Base exception type for all command errors.
    '''
    ...


# ---
# Specifics
# ---

class CommandRegisterError(CommandError):
    '''
    Error happened while registering a command.
    '''
    ...


class CommandPermissionError(CommandError):
    '''
    Command or Entity failed authz/permission check.
    '''
    ...


class CommandExecutionError(CommandError):
    '''
    Command sub-system encountered an error during execution of a
    command.
    '''
    ...
