# coding: utf-8

'''
Machine Time (Computer Time (OS Time)) for logs, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type

from datetime import datetime, timezone
import time as py_time
from decimal import Decimal

from veredi.base.strings.mixin import NamesMixin


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Bare Funcs?
# -----------------------------------------------------------------------------


def stamp() -> datetime:
    '''
    A datetime timestamp. Use stamp_to_str() if/when it will be serialized.
    '''
    return datetime.now(timezone.utc)


def stamp_to_str(dt_stamp: Optional[datetime] = None) -> str:
    '''
    A datetime timestamp in a format we approve of for parsing. If no `stamp`
    provided, will use `stamp` property.
    '''
    if not dt_stamp:
        dt_stamp = stamp()
    # Use the full percision to get a normalized string width.
    return dt_stamp.isoformat(timespec='microseconds')


def utcnow() -> datetime:
    '''Current UTC datetime.'''
    return datetime.utcnow()


def monotonic_ns() -> int:
    '''Python.time.monotonic_ns() -> int'''
    return py_time.monotonic_ns()


def unique() -> str:
    '''Ugly, but unique. Maybe hash it before serving...'''
    # Ignore the fractional seconds in datetime because monotonic_ns should
    # cover us...
    return (utcnow().isoformat(timespec='seconds')
            + '.'
            + str(monotonic_ns()))


# -----------------------------------------------------------------------------
# Class?
# -----------------------------------------------------------------------------


class MachineTime(NamesMixin,
                  name_dotted='veredi.time.machine',
                  name_string='time.machine'):
    '''
    Time functions for non-game times.
    '''

    SEC_TO_NS = 1_000_000_000

    @classmethod
    def sec_to_ns(klass:  Type['MachineTime'],
                  seconds: Union[int, float, Decimal]) -> int:
        '''
        Convert seconds to a nanoseconds value compatible with
        self.monotonic_ns.
        '''
        nano = seconds * klass.SEC_TO_NS
        # Our monotonic_ns property returns an int, and we don't care about any
        # precision below nanoseconds anyways.
        return int(nano)

    @property
    def stamp(self) -> datetime:
        '''A datetime timestamp. Use stamp_to_str() if/when it will
        be serialized.'''
        return datetime.now(timezone.utc)

    def stamp_to_str(self, dt_stamp: Optional[datetime] = None) -> str:
        '''A datetime timestamp in a format we approve of for parsing. If no
        `stamp` provided, will use MachineTime.stamp property.'''
        if not dt_stamp:
            dt_stamp = self.stamp
        # Use the full percision to get a normalized string width.
        return dt_stamp.isoformat(timespec='microseconds')

    @property
    def utcnow(self) -> datetime:
        '''Current UTC datetime.'''
        return datetime.utcnow()

    @property
    def monotonic_ns(self) -> int:
        '''Python.time.monotonic_ns() -> int'''
        return py_time.monotonic_ns()

    @property
    def unique(self) -> str:
        '''Ugly, but unique. Maybe hash it before serving...'''
        # Ignore the fractional seconds in datetime because monotonic_ns should
        # cover us...
        return (self.utcnow.isoformat(timespec='seconds')
                + '.'
                + str(self.monotonic_ns))
