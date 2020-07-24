# coding: utf-8

'''
Timing info for game.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import time as py_time


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Timer
# -----------------------------------------------------------------------------

class MonotonicTimer:
    '''
    Uses time.monotonic() to track elapsed time.
    '''

    TIME_FMT = '%H:%M:%S'
    ELAPSED_STR_FMT = '{time_fmt}.{fractional}'

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._start: float = self._current
        self._end:   float = None

    @property
    def _current(self) -> float:
        return py_time.monotonic()

    def start(self) -> None:
        '''Saves current monotonic time as the start time.'''
        self._start = self._current

    def stop(self) -> None:
        '''Saves current monotonic time as the end time.'''
        self._end = self._current

    @property
    def timing(self) -> bool:
        '''
        Not stopped and have a start time means probably timing something.
        '''
        return (self._start and not self._end)

    @property
    def elapsed(self) -> float:
        '''
        If timer has been stopped, returns elapsed from start to end.

        Otherwise, returns elapsed from start to now.
        '''
        elapsed = 0
        if self._end:
            elapsed = self._end - self._start
        else:
            elapsed = self._current - self._start
        return elapsed

    @property
    def elapsed_str(self) -> str:
        '''
        Returns self.elapsed, formatted as HH:MM:SS.fff...
        '''
        elapsed = self.elapsed
        fraction = elapsed % 1
        return self.ELAPSED_STR_FMT.format(
            time_fmt=py_time.strftime(self.TIME_FMT, py_time.gmtime(elapsed)),
            fractional=fraction)

    def timed_out(self, seconds: float) -> bool:
        '''
        If elapsed time is more than `seconds`, returns true.
        '''
        return self.elapsed > seconds
