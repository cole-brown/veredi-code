# coding: utf-8

'''
Unit-Testing-Only Exceptions.

All others will be towed at owner's expense.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.base.exceptions import VerediError


# -----------------------------------------------------------------------------
# Unit Test Exceptions
# -----------------------------------------------------------------------------

class UnitTestError(VerediError):
    '''
    Generic unit-test error.
    '''
    ...
