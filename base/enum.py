# coding: utf-8

'''
Mixins and/or Base/Basic Enum Things
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum

from veredi.logger import log


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
        Returns true if this enum has all the flags specified.
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

    @property
    def is_solo(flag: 'FlagCheckMixin') -> bool:
        '''
        Returns True if this instance is exactly one flag bit.
        Returns False if this instance has:
          - More than one bit set.
          - Zero bits set.
          - Invalid `flag` value (e.g. None).
        '''
        # ---
        # Simple Cases
        # ---

        if not isinstance(flag, enum.Flag):
            msg = (f"FlagCheckMixin.is_solo: '{flag}' is not an "
                   "enum.Flag derived type.")
            error = ValueError(msg, flag)
            raise log.exception(error,
                                None,
                                msg)

        # A nice clean-looking way of doing, but could miss some cases. For
        # example, if a flag mask exists as a value in the enum and the flag
        # value passed in happens to be equal to that mask.
        if flag not in flag.__class__:
            return False

        # ---
        # Not As Simple Case
        # ---

        # Count the bits set to get a sure answer. Apparently this ridiculous
        # "decimal number -> binary string -> count characters" is fast for
        # small, non-parallel/vectorizable things.
        #   https://stackoverflow.com/a/9831671/425816
        bits_set = bin(flag.value).count("1")
        return bits_set == 1


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
