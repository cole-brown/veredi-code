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

class EcsComponentError(VerediError):
    '''
    Some sort of component-related error.
    '''
    ...


class EcsEntityError(VerediError):
    '''
    Some sort of entity-related error.
    '''
    ...


class EcsSystemError(VerediError):
    '''
    A Veredi System, or SystemManager, had a system-related error.

    Didn't name 'SystemError' because Python built-in has that name and I
    didn't want to accidentally forget an include to use Veredi's when
    intended...

    ...Stupid python built-in SystemError...

    ...Definitely not my fault for not namespacing exceptions to their modules
    or anything...
    '''
    ...
