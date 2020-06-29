# coding: utf-8

'''
Machine Time (Computer Time (OS Time)) for logs, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

from datetime import datetime, timezone
import time as py_time


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Machine / OS Time
# -----------------------------------------------------------------------------

class MachineTime:
    '''
    Time functions for non-game times.
    '''

    @property
    def stamp(self) -> datetime:
        '''A datetime timestamp. Use stamp_to_str() if/when it will
        be serialized.'''
        return datetime.now(timezone.utc)

    def stamp_to_str(self, stamp: Optional[datetime] = None) -> str:
        '''A datetime timestamp in a format we approve of for parsing. If no
        `stamp` provided, will use MachineTime.stamp property.'''
        stamp = stamp or self.stamp
        # Use the full percision to get a normalized string width.
        return stamp.isoformat(timespec='microseconds')

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
