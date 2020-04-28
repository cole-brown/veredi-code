# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python


# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class VerediError(Exception):
    def __init__(self):
        '''No-args ctor.'''
        pass

    def __init__(self, message, cause, context):
        '''Context data included.'''
        self.message = message
        self.cause   = cause
        self.context = context

    def __str__(self):
        output = f"{self.message}"
        if self.cause:
            output += f" from {self.cause}"
        if self.context:
            output += f" with context {self.context}"

        return output
