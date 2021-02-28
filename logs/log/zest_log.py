# coding: utf-8

'''
Test our logging and formatting.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Union, List, Tuple


from io import StringIO
import logging

from veredi.zest.base.unit import ZestBase

from veredi.base.strings       import label
from veredi.data               import background


# ------------------------------
# What we're testing:
# ------------------------------
from . import log
from . import const
from . import formats

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class ZestLogBase(ZestBase):
    '''
    Test the veredi.logs.log module layered on top of Python's logging module.
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp().
        '''
        # ------------------------------
        # Parent!
        # ------------------------------
        super()._define_vars()

        # ------------------------------
        # Debugging
        # ------------------------------

    def set_up(self) -> None:
        '''
        Set up our logging to be unit-testable.
        '''

        # ------------------------------
        # Enable capture as final thing.
        # ------------------------------
        self.capture_logs(True)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Do any of our own clean-up.
        '''
        # ------------------------------
        # Disable capture as soon as possible.
        # ------------------------------
        self.capture_logs(False)

        # ------------------------------
        # Tear down the rest.
        # ------------------------------
        # This is actually part of disabling `capture_logs()`.
        # log.ut_tear_down()

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def assertLogs(self,
                   exact:   Optional[int] = None,
                   minimum: Optional[int] = None,
                   maximum: Optional[int] = None) -> None:
        '''
        Assert that we have any captured (i.e. at least one) logs.

        Will also assert the following if the param is not None:
          - 'exact': Exactly this number of logs received.
            ==
          - 'minimum': At least this number of logs received.
            >=
          - 'maximum': At most this number of logs received.
            <=
        '''
        # ---
        # Any?
        # ---
        self.assertTrue(self.logs)

        # ---
        # Numerical Comparisons?
        # ---
        if exact is not None:
            self.assertEqual(len(self.logs), exact)
        if minimum is not None:
            self.assertGreaterEqual(len(self.logs), minimum)
        if maximum is not None:
            self.assertLessEqual(len(self.logs), maximum)

    def assertNoLogs(self) -> None:
        '''
        Asserts that we have no captured logs.
        '''
        self.assertFalse(self.logs)

    def assertMessage(self,
                      log_output:     Union[str, Tuple[const.Level, str]],
                      substring:      Optional[str]       = None,
                      regex:          Optional[str]       = None,
                      expected_level: Optional[const.Level] = None) -> None:
        '''
        Asserts that log_output matches a regex.

        Can optionally assert that it was at the correct level, if the
        `log_output` is a `log.ut_call()` captured log from `self.logs`.

        If `substring` is provided, builds a simple regex to match anything
        before/after.

        If `regex` is provided, uses that directly in the assert.
        '''
        if not substring and not regex:
            self.fail("Received nothing to check log message for. "
                      f"substring: '{substring}', regex: '{regex}', "
                      f"log: '{log_output}'")
        if not log_output:
            self.fail("Empty log."
                      f"substring: '{substring}', regex: '{regex}', "
                      f"log: '{log_output}'")

        # ---
        # log.ut_call() check...
        # ---
        # `log.ut_call()` saves off a tuple of (Level, message)
        # before the Formatter gets a go at the log.
        log_message = log_output
        log_level = None
        if isinstance(log_output, tuple):
            log_level = log_output[0]
            log_message = log_output[1]

        if expected_level:
            if log_level:
                self.assertEqual(log_level, expected_level)
            else:
                self.fail("No level known for log; cannot verify level. "
                          f"expected_level: {expected_level}, "
                          f"log: '{log_output}'")

        if substring:
            self.assertRegex(log_message, r'^.*' + substring + r'.*$')

        if regex:
            self.assertRegex(log_message, regex)


# -----------------------------------------------------------------------------
# Class for Veredi Log layer.
# -----------------------------------------------------------------------------

class ZestLogMessage(ZestLogBase):
    '''
    Test veredi.logs.log messages/levels are acting in an expected manner.

    Does not test formatting.
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp().
        '''
        # ------------------------------
        # Parent!
        # ------------------------------
        super()._define_vars()

        # ------------------------------
        # Debugging
        # ------------------------------

    def set_up(self) -> None:
        '''
        Set up our logging to be unit-testable.
        '''

        # ------------------------------
        # Enable capture as final thing.
        # ------------------------------
        self.capture_logs(True)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Do any of our own clean-up.
        '''
        # ------------------------------
        # Disable capture as soon as possible.
        # ------------------------------
        self.capture_logs(False)

        # ------------------------------
        # Tear down the rest.
        # ------------------------------
        # This is actually part of disabling `capture_logs()`.
        # log.ut_tear_down()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_critical_at_default(self) -> None:
        '''
        A basic test. Critical should always print out at whatever the default
        level is.
        '''
        self.assertNoLogs()

        message = 'test'
        log.critical(message)
        self.assertLogs(exact=1)
        self.assertMessage(self.logs[0], substring=message)


    def test_critical_at_default(self) -> None:
        '''
        A basic test. Critical should always print out at whatever the default
        level is.
        '''
        self.assertNoLogs()

        message = 'test'
        log.critical(message)
        self.assertLogs(exact=1)
        self.assertMessage(self.logs[0], substring=message)


# -----------------------------------------------------------------------------
# Class for Veredi Log Format layer.
# -----------------------------------------------------------------------------

class ZestLogFormat(ZestLogBase):
    '''
    Test veredi.logs.log.formats are acting in an expected manner.
    '''

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Defines any instance variables with type hinting, docstrs.
        Happens ASAP during unittest.setUp().
        '''
        # ------------------------------
        # Parent!
        # ------------------------------
        super()._define_vars()

        # ------------------------------
        # Our log capturer.
        # ------------------------------
        self.stream: StringIO = StringIO()

        # ------------------------------
        # Our log formatter.
        # ------------------------------
        self.formatter: logging.Formatter = None

    def set_up(self) -> None:
        '''
        Set up our logging to be unit-testable.
        '''
        # Initialize our Formatter...
        self.formatter = formats.yaml.LogYaml()

        # ------------------------------
        # Enable capture as final thing.
        # ------------------------------
        self.capture_logs(True)

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self) -> None:
        '''
        Do any of our own clean-up.
        '''
        # ------------------------------
        # Disable capture as soon as possible.
        # ------------------------------
        self.capture_logs(False)

        # ------------------------------
        # Tear down the rest.
        # ------------------------------
        # This is actually part of disabling `capture_logs()`.
        # log.ut_tear_down()
        self.stream = None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def capture_logs(self, enabled: bool) -> None:
        '''
        This test, instead of diverting at veredi layer, we are going to swap
        handlers to a stream handler using our string stream.

        This lets us get fully formatted logs.
        '''
        if enabled:
            formats.ut_set_up(self.stream,
                              log.logger,
                              self.formatter)
        else:
            formats.ut_tear_down(log.logger)

    def capture(self) -> None:
        '''
        Reads all from our log stream and saves as a log entry in `self.logs`.
        '''
        # Bit of sanity checking...
        self.assertTrue(self.stream)
        self.assertFalse(self.stream.closed)
        self.assertTrue(self.stream.readable)
        self.assertTrue(self.stream.seekable)

        # ...and capture the string.
        message = self.stream.getvalue()
        # No known log level so just put str in, not (level, str)
        self.logs.append(message)

        # And reset for next log.
        self.stream.truncate(0)
        self.stream.seek(0)
        # Need both of these! `truncate()` deletes the current data and
        # `seek()` resets stream position back to zero, which we check for.

    def assertStream(self) -> None:
        '''Asserts that stream exists, has data.'''
        # Ensure it exists with some expected states.
        self.assertTrue(self.stream)
        self.assertFalse(self.stream.closed)
        self.assertTrue(self.stream.readable)
        self.assertTrue(self.stream.seekable)

        # Assert it has data.
        self.assertGreater(self.stream.tell(), 0)

    def assertNoStream(self) -> None:
        '''Asserts that stream exists, but has no.'''
        # Ensure it exists with some expected states.
        self.assertTrue(self.stream)
        self.assertFalse(self.stream.closed)
        self.assertTrue(self.stream.readable)
        self.assertTrue(self.stream.seekable)

        # Assert it has data.
        self.assertEqual(self.stream.tell(), 0)

    def assertNothing(self) -> None:
        '''Assert stream and logs are empty.'''
        self.assertNoStream()
        self.assertNoLogs()

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_critical_at_default(self) -> None:
        '''
        A basic test. Critical should always print out at whatever the default
        level is.
        '''
        self.assertNothing()

        message = 'test'
        log.critical(message)
        # No logs yet but should have stream data.
        self.assertNoLogs()
        self.assertStream()
        # TODO HERE
        print(self.stream.getvalue())


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run logs/log/zest_log.py

if __name__ == '__main__':
    import unittest
    # log.set_level(const.Level.DEBUG)
    unittest.main()
