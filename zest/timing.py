# coding: utf-8

'''
Base Veredi Class for Tests.
  - Helpful functions.
  - Set-up / Tear-down for global Veredi stuff.
    - config registry
    - yaml serdes tag registry
    - etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union

from datetime import (datetime,
                      timezone,
                      tzinfo,
                      timedelta,
                      time as py_dttime)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Time/Timing Info Helper Class
# -----------------------------------------------------------------------------

class ZestTiming:
    '''
    A timing info class for test runs. Holds start, end time (w/ timezone),
    elapsed time. Helpers for printing this out if wanted for info or
    debugging.
    '''

    DEFAULT_ELAPSED_FMT = '%H:%M:%S.%f'

    def __init__(self,
                 tz:          Union[tzinfo, int, bool, None] = None,
                 elapsed_fmt: str                            = None
                 ) -> None:
        '''
        Creates the timing info class for a test run and saves the current
        time as the start time for the test.

        `tz` can be:
          - an integer offset from UTC (e.g. -8 for Pacific Standard Time)
          - a tzinfo object
          - True (for local machine time)
          - None/False (for UTC)

        `_elapsed_str_fmt` will be set to `ZestTiming.DEFAULT_ELAPSED_FMT`
        if left as default/None.
        '''
        # ---
        # Figure out Timezone.
        # ---
        zone = None

        # No timezone provided - use UTC.
        if not tz:
            zone = timezone.utc

        # True == use local time.
        elif tz is True:
            zone = datetime.now().astimezone().tzinfo

        # NOTE: MUST BE BELOW 'is True'! True is an int, apparently...
        # Integer offset provided - convert to Timezone.
        elif isinstance(tz, int):
            zone = timezone(timedelta(tz))

        # Else, we have a tzinfo already.
        else:
            zone = tz

        # ---
        # Initialize
        # ---
        self._tz:              tzinfo    = zone
        self._start:           datetime  = datetime.now(tz=self._tz)
        self._end:             datetime  = None
        self._td_elapsed:      timedelta = None
        self._dt_elapsed:      py_dttime = None
        self._elapsed_str_fmt: str       = (elapsed_fmt
                                            or ZestTiming.DEFAULT_ELAPSED_FMT)

    # ------------------------------
    # Stopwatch Functions
    # ------------------------------

    def test_start(self) -> None:
        '''
        Sets start time. Start is already set when instance is created, so this
        is just if a different start is desired.
        '''
        self._start = datetime.now(tz=self._tz)

    def test_end(self) -> None:
        '''
        Sets end time, elapsed time of test.
        '''
        self._end = datetime.now(tz=self._tz)

        self._td_elapsed = self._end - self._start
        self._dt_elapsed = py_dttime(second=self._td_elapsed.seconds,
                                     microsecond=self._td_elapsed.microseconds)

    # ------------------------------
    # Properties / Setters
    # ------------------------------

    @property
    def timezone(self) -> Optional[tzinfo]:
        '''Returns timezone (tzinfo object).'''
        return self._tz

    @timezone.setter
    def timezone(self, value: tzinfo) -> None:
        '''
        Setter for timezone. Only sets self var; doesn't change other vars to
        be based on new tz.
        '''
        self._tz = value

    @property
    def start_dt(self) -> Optional[datetime]:
        '''Returns start time (datetime object).'''
        return self._start

    @start_dt.setter
    def start_dt(self, value: datetime) -> Optional[datetime]:
        '''Setter for start time (datetime object).'''
        self._start = value

    @property
    def start_str(self,
                  sep=' ',
                  timespec='seconds') -> Optional[str]:
        '''
        `sep` and `timespec` are fed into datetime.isoformat().

        Returns start time as formatted string.
        '''
        return self._start.isoformat(sep=' ', timespec='seconds')

    @property
    def end_dt(self) -> Optional[datetime]:
        '''Returns end time (datetime object).'''
        return self._end

    @end_dt.setter
    def end_dt(self, value: datetime) -> Optional[datetime]:
        '''Setter for end time (datetime object).'''
        self._end = value

    @property
    def end_str(self,
                sep=' ',
                timespec='seconds') -> Optional[str]:
        '''
        `sep` and `timespec` are fed into datetime.isoformat().

        Returns end time as formatted string.
        '''
        return self._end.isoformat(sep=' ', timespec='seconds')

    @property
    def elapsed_td(self) -> Optional[timedelta]:
        '''Returns elapsed timedelta.'''
        return self._td_elapsed

    @property
    def elapsed_dt(self) -> Optional[datetime]:
        '''Returns elapsed timedelta as a datetime.'''
        return self._dt_elapsed

    @property
    def elapsed_str(self) -> Optional[datetime]:
        '''Returns elapsed timedelta as a formatted string.'''
        return self._dt_elapsed.strftime(self._elapsed_str_fmt)
