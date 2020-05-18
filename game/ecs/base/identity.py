# coding: utf-8

'''
IDs for Entities, Components, and Systems.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
# import datetime

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base
# -----------------------------------------------------------------------------

class MonotonicIdGenerator:
    '''
    Class that generates monotonically increasing IDs. Not random, not UUID...
    just monotonically increasing.
    '''

    def __init__(self, id_class):
        self._id_class = id_class
        self._last_id = id_class.INVALID

    def next(self):
        self._last_id += 1
        return self._id_class(self._last_id, allow=True)

    def peek(self):
        return self._last_id


class MonotonicId(int):
    INVALID = 0
    _format = '{:03d}'

    def __new__(klass, value, *args, allow=False, **kwargs):
        if not allow:
            # Just make all constructed return INVALID.
            return super().__new__(klass, klass.INVALID)
        return super().__new__(klass, value)

    def __add__(self, other):
        raise NotImplementedError(f"{str(self)} cannot be added.")

    def __sub__(self, other):
        raise NotImplementedError(f"{str(self)} cannot be subtracted.")

    def __mul__(self, other):
        raise NotImplementedError(f"{str(self)} cannot be multiplied.")

    def __div__(self, other):
        raise NotImplementedError(f"{str(self)} cannot be divided.")

    def __str__(self):
        return (f'{self.__class__.__name__}:' + self._format).format(int(self))

    def __repr__(self):
        return ('id:' + self._format).format(int(self))


# ------------------------------------------------------------------------------
# ECS ID Types
# ------------------------------------------------------------------------------

class ComponentId(MonotonicId):
    pass

class EntityId(MonotonicId):
    pass

class SystemId(MonotonicId):
    pass
