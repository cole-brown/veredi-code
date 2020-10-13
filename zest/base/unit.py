# coding: utf-8

'''
Base Veredi Class for Tests.
  - Helpful functions.
  - Set-up / Tear-down for global Veredi stuff.
    - config registry
    - yaml codec tag registry
    - etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, List, Tuple

import sys
import unittest

# Veredi has time too, so three 'time' modules to deal with...
# Veredi's gets to reserve 'time' so actual tests can do as they please.
# Python's time gets 'py_time' and datetime.time gets 'py_dttime'.
import time as py_time
from datetime import (datetime,
                      timezone,
                      tzinfo,
                      timedelta,
                      time as py_dttime)

from veredi.logger                      import log
from veredi.zest.zpath                  import TestType
from veredi.zest                        import zload
from veredi.debug.const                 import DebugFlag
from veredi.base                        import dotted

from veredi.data.config                 import registry as config_registry
from veredi.data.codec.yaml             import registry as yaml_registry


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODOs:
#   - Name functions based on what should be called by actual unit tests.
#     -  [a-z_][a-zA-Z_]*: called by subclasses for actual unit tests.
#     - _[a-z_][a-zA-Z_]*: Just used by this internally, most likely.


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
                 timezone:        tzinfo = None,
                 elapsed_str_fmt: str    = None) -> None:
        '''
        Creates the timing info class for a test run and saves the current
        time as the start time for the test.

        `_elapsed_str_fmt` will be set to `ZestTiming.DEFAULT_ELAPSED_FMT`
        if left as default/None.
        '''
        self._tz:              tzinfo    = timezone
        self._start:           datetime  = datetime.now(tz=self._tz)
        self._end:             datetime  = None
        self._td_elapsed:      timedelta = None
        self._dt_elapsed:      py_dttime = None
        self._elapsed_str_fmt: str       = (elapsed_str_fmt
                                            or ZestTiming.DEFAULT_ELAPSED_FMT)

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

    # ------------------------------
    # Funcs
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
    # Elapsed Time Getters
    # ------------------------------

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


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestBase(unittest.TestCase):
    '''
    Base Veredi Class for Tests.
      - Helpful functions.
      - Set-up / Tear-down for global Veredi stuff.
        - config registry
        - yaml codec tag registry
        - etc.

    Internal (probably) helpers/functions/variables - that is ones subclasses
    probably won't need to use directly - are prefixed with '_'. The
    helpers/functions/variables useddirectly are not prefixed.

    Or in regex terms:
      -  r'[a-z][a-zA-Z_]*[a-z]': Called by subclasses for actual unit tests.
      - r'_[a-z_][a-zA-Z_]*[a-z]': Just used by this internally, most likely.
    '''

    _TEST_TYPE = TestType.UNIT

    def dotted(self, uufileuu: str) -> None:
        '''
        If class or instance has a _DOTTED, returns that.

        Else tries to build something from `uufileuu`, which should probably
        just be:
          __file__
        '''
        try:
            return self._DOTTED
        except AttributeError:
            pass

        # Didja know this exists?
        return dotted.from_path(uufileuu)

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp(), before ZestBase.set_up().
        '''
        # ---------------------------------------------------------------------
        # Create self vars.
        # ---------------------------------------------------------------------

        # -
        # ---
        # Just define the variables here for name, type hinting, and docstr.
        # Set to empty/None/False/default. Actual setup of the variables is
        # either done by sub-class or a set-up function.
        # ---
        # -

        # ------------------------------
        # Debugging
        # ------------------------------

        self._ut_is_verbose = ('-v' in sys.argv) or ('--verbose' in sys.argv)
        '''
        True if unit tests were run with the 'verbose' flag from
        command line/whatever.

        Pretty stupid hack to get at verbosity since unittest doesn't provide
        it anywhere. :(
        '''

        self.debugging:      bool          = False
        '''
        Use as a flag for turning on/off extra debugging stuff.
        Mainly used with log.LoggingManager.on_or_off() context manager.
        '''

        self.debug_flags:    DebugFlag     = DebugFlag.GAME_ALL
        '''
        Debug flags to pass on to things that use them, like:
        Engine, Systems, Mediators, etc.
        '''

        # ------------------------------
        # Logging
        # ------------------------------

        self.logs:          List[Tuple[log.Level, str]] = []
        '''
        Logs get captured into this list when self.capture_logs(True) is
        in effect.
        '''

        # ------------------------------
        # Time (logging/debug help)
        # ------------------------------
        testing_timezone = timezone(timedelta(hours=-7))
        self._timing: ZestTiming = ZestTiming(testing_timezone)
        '''
        Timing info helper. Auto-starts timer when created, or can restart with
        self._timing.test_start(). Call self._timing.test_end() and check it
        whenever you want to see timing info.
        '''

    def set_up(self) -> None:
        '''
        Use this!

        Called at the end of self.setUp(), when instance vars are defined but
        no actual set-up has been done yet.
        '''
        ...

    def setUp(self) -> None:
        '''
        unittest.TestCase setUp function. Make one for your test class, and
        call stuff like so:

        super().setUp()
        <your stuff here>
        '''
        self._define_vars()

        self._set_up_background()

        self.set_up()

    # ------------------------------
    # Background Context Set-Up
    # ------------------------------

    def _set_up_background(self) -> None:
        '''
        Set-up nukes background, so call this before anything is created.
        '''

        # ---
        # Nuke background data so it all can remake itself.
        # ---
        zload.set_up_background()

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Use this!

        Called at the beginning of self.tearDown().
        '''
        ...

    def tearDown(self) -> None:
        '''
        unittest.TestCase tearDown function.

        Use tear_down(). This calls tear_down() before any of the base class
        tear-down happens.
        '''

        # ---
        # Do test's tear down first in case they rely on vars we control.
        # ---
        self.tear_down()

        # ---
        # Reset or unset our variables for fastidiousness's sake.
        # ---
        self._ut_is_verbose = False
        self.debugging      = False
        self.debug_flags    = None
        self.logs           = []

        # ---
        # Other tear-downs.
        # ---
        log.ut_tear_down()

        # ---
        # Nuke registries and background context.
        # ---
        self._tear_down_registries()
        self._tear_down_background()

    def _tear_down_registries(self) -> None:
        '''
        Nukes all entries into various registries.
          - config.registry
          - codec.yaml.registry
        '''
        config_registry._ut_unregister()
        yaml_registry._ut_unregister()

    def _tear_down_background(self) -> None:
        '''
        Tear-down nukes background, so call this after you don't care about
        getting any bg context info.
        '''

        # ---
        # Nuke background data so it all can remake itself.
        # ---
        zload.tear_down_background()

    # -------------------------------------------------------------------------
    # Log Capture
    # -------------------------------------------------------------------------

    def capture_logs(self, enabled: bool) -> None:
        '''
        Divert logs from being output to being received by self.receive_log()
        instead.
        '''
        if enabled:
            log.ut_set_up(self._receive_log)
        else:
            log.ut_tear_down()

    def _receive_log(self,
                     level: log.Level,
                     output: str) -> None:
        '''
        Logs will come to this callback when self.capture_logs(True) is
        in effect.

        They get appended to self.logs as (level, log output str) tuples.
        '''
        self.logs.append((level, output))

        # I want to eat the logs and not let them into the output.
        # ...unless verbose tests, then let it go through.
        return not self._ut_is_verbose
