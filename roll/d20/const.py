# coding: utf-8

'''
Constants, Enums, and Stuff for roll.d20 module.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import enum


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class FormatOptions(enum.Flag):
    NONE         = 0
    INITIAL      = enum.auto()
    INTERMEDIATE = enum.auto()
    FINAL        = enum.auto()
    ALL = INITIAL | INTERMEDIATE | FINAL

    def all(self, flag):
        return ((self & flag) == flag)

    def any(self, *flags):
        for each in flags:
            if (self & each) == each:
                return True
        return False


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------
