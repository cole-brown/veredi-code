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
    '''
    Time format string for output.
    '''

    ELAPSED_STR_SEC_PRECISION = 10 ** 3
    '''
    Fractional seconds precision for string output.
    '''

    ELAPSED_STR_FMT = '{time_fmt}.{fractional:d}'
    '''
    Full string format for stirng output.
    '''

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
    def elapsed(self) -> int:
        '''
        If timer has been stopped, returns elapsed nanoseconds from start to
        end.

        Otherwise, returns elapsed from start to now.
        '''
        elapsed = 0
        if self._end:
            elapsed = self._end - self._start
        else:
            elapsed = self._current - self._start
        return elapsed

    @property
    def elapsed_sec(self) -> float:
        '''
        Converts `self.elapsed` property value (nanoseconds int) into seconds
        float.
        '''
        return self.elapsed * 10.0**9

    @property
    def elapsed_str(self) -> str:
        '''
        Returns `self.elapsed`, formatted as HH:MM:SS.fff...
        '''
        elapsed = self.elapsed
        # Multiply by precision to get our relevant fractional second:
        #       from:    0.123456789
        #         to: 1234.56789
        #   truncate: 1234
        fraction = int((elapsed % 1)
                       * self.ELAPSED_STR_SEC_PRECISION)
        return self.ELAPSED_STR_FMT.format(
            time_fmt=py_time.strftime(self.TIME_FMT, py_time.gmtime(elapsed)),
            fractional=fraction)

    def timed_out(self, seconds: float) -> bool:
        '''
        If elapsed time is more than `seconds`, returns true.
        '''
        return self.elapsed > seconds
