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
    '''Base exception type for all command errors.'''

    def __init__(self, message, cause, context):
        '''With user context data.'''
        super().__init__(message, cause, context)


# ---
# Specifics
# ---

class CommandRegisterError(CommandError):
    '''Error happened while registering a command.'''

    def __init__(self, message, cause, context):
        '''With user context data.'''
        super().__init__(message, cause, context)


class CommandPermissionError(CommandError):
    '''Command or Entity failed authz/permission check.'''

    def __init__(self, message, cause, context):
        '''With user context data.'''
        super().__init__(message, cause, context)


class CommandExecutionError(CommandError):
    '''Command sub-system encountered an error during execution of a
    command.'''

    def __init__(self, message, cause, context):
        '''With user context data.'''
        super().__init__(message, cause, context)
