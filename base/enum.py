# coding: utf-8

'''
Mixins and/or Base/Basic Enum Things
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class FlagCheckMixin:
    '''
    Helper functions for checking if an instance of a enum.Flag has specific
    enum.Flag flags set.
    '''

    def has(self, flag: 'FlagCheckMixin'):
        '''
        Returns true if this OutputType has all the flags specified.
        '''
        return ((self & flag) == flag)

    def any(self, *flags: 'FlagCheckMixin') -> bool:
        '''
        Returns true if this instance has any of the flags specified.

        Can still require multiple by OR'ing e.g.:
          type.any(JeffFlag.JEFF | JeffFlag.JEFFORY, JeffFlag.GEOFF)

        That will look for either a JEFF that is a JEFFORY, or a GEOFF.
        '''
        for each in flags:
            if self.has(each):
                return True
        return False


class FlagSetMixin:
    '''
    Helper functions for setting, unsetting flags in an enum.Flag instance.
    '''

    def set(self, flag: 'FlagSetMixin') -> bool:
        '''
        Returns an instance of this enum.Flag with `flag` added
        (OR'd into self).
        '''
        return self | flag

    def unset(self, flag: 'FlagSetMixin') -> bool:
        '''
        Returns an instance of this enum.Flag with `flag` removed
        (NOT-AND'd out of self).
        '''
        return self & ~flag
