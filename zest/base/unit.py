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

from typing import Optional, Union, Any, Type, List, Tuple, Dict
from veredi.base.null import Null


import sys
import unittest
from abc import ABC, abstractmethod


from veredi.logs               import log
from veredi.base               import paths
from veredi.data               import background

from veredi.zest               import zinit, zmake, zpath
from veredi.zest.zpath         import TestType
from veredi.zest.timing        import ZestTiming
from veredi.debug.const        import DebugFlag
from veredi.base.strings       import label
from veredi.data.config.config import Configuration
from veredi.base.context       import VerediContext, UnitTestContext


# -----------------------------------------------------------------------------
# Auto-Generate '.dotted' for a ZestBase class
# -----------------------------------------------------------------------------

class ZestDottedDescriptor:
    '''
    Veredi label.DotStr provided via descriptor - usually named `dotted`.
    '''

    def __init__(self,
                 path_or_dotted: Union[str, paths.Path, Null, None],
                 name:           Optional[str] = None) -> None:
        self.name: str = name
        self.dotted: label.DotStr = None
        if path_or_dotted:
            self.dotted = label.from_something(path_or_dotted)

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the dotted label value.
        '''
        return self.dotted

    def __set__(self,
                instance:       Optional[Any],
                path_or_dotted: Optional[str]) -> None:
        '''
        Set dotted label to DotStr created from file path.
        '''
        if path_or_dotted:
            self.dotted = label.from_something(path_or_dotted)
        else:
            self.dotted = None

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name

# -----------------------------------------------------------------------------
# Descriptor for TestType
# -----------------------------------------------------------------------------

class TestTypeDescriptor:
    '''
    Veredi TestType provided via descriptor.
    '''

    def __init__(self,
                 type: TestType,
                 name: Optional[str] = None) -> None:
        self.name: str = name
        self.type: TestType = type

    def __get__(self,
                instance: Optional[Any],
                owner:    Type[Any]) -> label.DotStr:
        '''
        Returns the TestType value.
        '''
        return self.type

    def __set__(self,
                instance: Optional[Any],
                type:     Optional[TestType]) -> None:
        '''
        Set the TestType value.
        '''
        self.type = type

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        '''
        Save our descriptor variable's name in its owner's class.
        '''
        self.name = name


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

    type: TestTypeDescriptor = TestTypeDescriptor(TestType.UNIT)
    '''
    TestType descriptor. Set to something else as needed.
    '''

    dotted: ZestDottedDescriptor = ZestDottedDescriptor(
        'veredi.zest.base.unit.TODO.give-your-test-a-dotted'
    )

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
        # Configuration & Registration
        # ------------------------------
        self.context: VerediContext = None
        '''
        If class uses a set-up/config context, it should go here.
        zload.set_up_ecs() can provide this.
        '''

        self.config_path: Optional[paths.Path] = None
        '''
        If not None, used as the path to the config file.
        If None, self.type is used to figure out the path to the config file.
        '''

        self.config_rules: Optional[label.LabelInput] = None
        '''
        Ruleset to use for this instance of Veredi.
        '''

        self.config_game_id: Optional[Any] = None
        '''
        Game ID to use for this instance of Veredi.
        '''

        self.config: Configuration = None
        '''
        If class uses a special config, it should be saved here so set-up(s)
        can use it.
        '''
    def set_dotted(self,
                   filename: Union[str, paths.Path],
                   *dotted:  label.LabelInput) -> None:
        '''
        Set test class's `dotted` class-level descriptor based on `filename`
        and `dotted`.
        '''
        filename = paths.cast(filename)
        self.dotted = (filename, *dotted)

    def set_type(self, type: TestType) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        # Choose your +weapon+ test-type!
        # self.type = TestType.UNIT
        # self.type = TestType.INTEGRATION
        # self.type = TestType.FUNCTIONAL
        self.type = type

    def pre_set_up(self,
                   filename:  Union[str, paths.Path]  = None,
                   extra:     label.LabelLaxInputIter = (),
                   test_type: Optional[TestType]      = TestType.UNIT
                   ) -> None:
        '''
        NOTE: All tests are expected to have these inputs resolved to a
        meaningful default!
          - `filename` must be `__file__`.
          - `extra` is available for tests that want to add more to their
            auto-generated `self.dotted`.
          - `test_type` is often already at the correct setting based on what
            zest.base class you derived from.

        Called in `self.setUp()` after `self._define_vars()` and before
        anything happens.

        Use it to do any prep-work needed (like defining a different path for
        the config file, or setting up special logging needs before actual
        `set_up()`).
        '''
        self.set_type(test_type)
        self.set_dotted(filename, *extra)

    def assert_pre_set_up(self) -> None:
        '''
        Make sure `self.dotted`, `self.type`, and whatever else needs to be
        set_up (before the rest of set up is run) is ready.

        E.g.: Logging should be ready to go after this if any special logging
        is happening in this test.
        '''
        if not self.dotted:
            self.fail(f"{self.__class__.__name__}.dotted is not set! Call "
                      "`self.set_dotted(__file__)` in `self.pre_set_up()`! Or "
                      "`self.set_dotted(__file__, 'jeff', 'test', ...)`.")

        if not self.type:
            self.fail(f"{self.__class__.__name__}.type is not set! Call "
                      "`self.set_type(TestType.UNIT)` in `self.pre_set_up()`! "
                      "Or `self.set_type(TestType.INTEGRATION)`. "
                      "Or `self.set_type(TestType.FUNCTIONAL)`...")

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
        # ---
        # Sanity and init.
        # ---
        self._verify_clean_environment()
        self._define_vars()

        # Assume the test has resolved all the keyword args to
        # a meaningful default...
        self.pre_set_up()
        # ...and now make sure of it.
        self.assert_pre_set_up()

        # ---
        # Our Set-Up.
        # ---
        self._set_up_config(test_type=self.type,
                            rules=self.config_rules,
                            game_id=self.config_game_id,
                            config_path=self.config_path)
        self._set_up_registries()
        self._set_up_background()

        # ---
        # Our Unit Test'S Specific Set-Up.
        # ---
        self.set_up()

        # except:
        #     # Try to clean up a bit for next test suite.
        #     self.tearDown()

    # ------------------------------
    # Background / Registry Set-Up
    # ------------------------------

    def _assert_config(self) -> None:
        '''
        Uses `fail()` to indicate when a Configuration already exists.
        '''
        existing_bg = background.config.link(background.Link.CONFIG)
        existing_test = self.config

        if existing_bg:
            self.fail("A configuration has already been created and "
                      "is in the background context. Only one config can "
                      "exist. Pre-existing Config: "
                      f"{existing_bg}")
        elif existing_test:
            self.fail("A configuration has already been created and "
                      "is /not/ in the background context but is in the test. "
                      "Please find out which one you want - "
                      "only one config can exist. Pre-existing Config: "
                      f"{existing_test}")

    def _set_up_config(self,
                       test_type:   Optional[zpath.TestType]   = None,
                       rules:       Optional[label.LabelInput] = None,
                       game_id:     Optional[Any]              = None,
                       config_path: Optional[paths.PathsInput] = None) -> None:
        '''
        Create the Configuration object for setting up Veredi.
        '''
        # Do we already have one?
        self._assert_config()

        # Ok; no config yet. Let's make one.
        self.config = zmake.config(test_type=test_type,
                                   rules=rules,
                                   game_id=game_id,
                                   config_path=config_path)

    def _set_up_background(self) -> None:
        '''
        Set-up nukes background, so call this before anything is created.
        '''
        zinit.set_up_background()

    def _set_up_registries(self) -> None:
        '''
        Nukes all entries in various registries.
        '''
        if self.config is None:
            log.warning("No configuration created?! Test should have created "
                        f"it during `{self.__class__.__name__}"
                        "._set_up_config`. Creating one for now, but "
                        "this should be fixed.")
            self.config = zmake.config(self.type)
        zinit.set_up_registries(self.config)

    def _verify_clean_environment(self):
        # ---
        # Is the Background Clean?
        # ---
        # If not, it probably has a pre-existing Configuration which is a
        # no-go.
        clean, dirty_reason = background.testing.is_clean()
        if not clean:
            self.skipTest(f"Background is not clean! {dirty_reason}")

        # ---
        # Other Things to Check?
        # ---
        # ...they would go here.

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
        try:
            self.tear_down()
        finally:
            self._tear_down_base()

    def _tear_down_base(self) -> None:
        '''
        Do all the base class tear-down.
        '''
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
        # Chain these in finally blocks so they all try to get called?
        try:
            log.ut_tear_down()
        finally:
            # ---
            # Nuke registries and background context.
            # ---
            try:
                self._tear_down_registries()
            finally:
                self._tear_down_background()

    def _tear_down_registries(self) -> None:
        '''
        Nukes all entries in various registries.
        '''
        # ---
        # Nuke  data so it all can remake itself.
        # ---
        zinit.tear_down_registries()

    def _tear_down_background(self) -> None:
        '''
        Tear-down nukes background, so call this after you don't care about
        getting any bg context info.
        '''

        # ---
        # Nuke background data so it all can remake itself.
        # ---
        zinit.tear_down_background()

    # -------------------------------------------------------------------------
    # Log Capture
    # -------------------------------------------------------------------------

    def clear_logs(self) -> None:
        '''
        Drop all captured logs from `self.logs` list.
        '''
        self.logs.clear()

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
        if self._ut_is_verbose:
            print(f'{self.__class__.__name__}._receive_log: '
                  'log allowed through because verbose flag is set.')
        return not self._ut_is_verbose
