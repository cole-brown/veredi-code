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

from typing import List, Tuple, Dict

import sys
import unittest

from veredi.logger                      import log
from veredi.zest                        import zload
from veredi.zest.zpath                  import TestType
from veredi.zest.timing                 import ZestTiming
from veredi.debug.const                 import DebugFlag
from veredi.base.string                 import label


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestBase(unittest.TestCase):
    '''
    Base Veredi Class for Tests.
      - Helpful functions.
      - Set-up / Tear-down for global Veredi stuff.
        - config registry
        - yaml serdes tag registry
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
        return label.from_path(uufileuu)

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
        self._timing: ZestTiming = ZestTiming(tz=True)  # True -> local tz
        '''
        Timing info helper. Auto-starts timer when created, or can restart with
        self._timing.test_start(). Call self._timing.test_end() and check it
        whenever you want to see timing info.
        '''

        # ------------------------------
        # Registries
        # ------------------------------
        self._registry_setup: Dict[str, bool] = {
            'encodables': False,
        }
        '''
        Must be keyword arg names for zload.set_up_registries().
        '''

    def want_registered(self, registry_setup_name: str) -> None:
        '''
        Call in set_up() with a key string for self._registry_setup() to mark
        those for registration.
        '''
        self._registry_setup[registry_setup_name] = True

    def set_up(self) -> None:
        '''
        Use this!

        Called at the end of self.setUp(), when instance vars are defined but
        no actual set-up has been done yet.
        '''
        ...

    def setUp(self) -> None:
        '''
        unittest.TestCase setUp function. Sub-classes should use `set_up()` for
        their test set-up.
        '''
        self._define_vars()

        self._set_up_background()

        self.set_up()

        # Set up registries after custom set_up so they can set flags for what
        # registries to populate/ignore.
        self._set_up_registries()

    # ------------------------------
    # Background / Registry Set-Up
    # ------------------------------

    def _set_up_background(self) -> None:
        '''
        Set-up nukes background, so call this before anything is created.
        '''

        # ---
        # Nuke background data so it all can remake itself.
        # ---
        zload.set_up_background()

    def _set_up_registries(self) -> None:
        '''
        Nukes all entries in various registries.
        '''

        # ---
        # Nuke registries' data so it all can remake itself.
        # ---
        zload.set_up_registries(**self._registry_setup)

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

        Sub-classes should use `tear_down()` for their test tear-down. This
        calls tear_down() before any of the base class tear-down happens.
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
        Nukes all entries in various registries.
        '''
        # ---
        # Nuke  data so it all can remake itself.
        # ---
        zload.tear_down_registries()

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
