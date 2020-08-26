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

from typing import List, Tuple

import sys
import unittest

from veredi.logger                      import log
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

        self.debug_flags:    DebugFlag     = None
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

        # ---------------------------------------------------------------------
        # Actual Set-Up Functions
        # ---------------------------------------------------------------------

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
        # Reset or unset our variables for fastidiousness's sake.
        # ---
        self._ut_is_verbose = False
        self.debugging      = False
        self.debug_flags    = None
        self.logs           = []

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
