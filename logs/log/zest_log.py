# coding: utf-8

'''
Test our logging and formatting.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Union, List, Tuple, Mapping


from io import StringIO
import logging

from veredi.zest.base.unit  import ZestBase
from veredi.zest.zpath      import TestType


from veredi.base            import yaml
from veredi.base.context    import UnitTestContext
from veredi.base.strings    import label
from veredi.data            import background


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

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'log', 'base')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

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

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'log', 'message')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_critical_at_default(self) -> None:
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

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'log', 'format')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self) -> None:
        '''
        Set up our logging to be unit-testable.
        '''
        # Initialize our Formatter...
        self.formatter = formats.yaml.FormatYaml()

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
    # Log Capture
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

    def deserialize(self) -> None:
        '''
        Gets string from `self.stream`, deserializes it via YAML, clears the
        stream, and returns the deserialized data.

        Calls `assertStream` and `assertNoStream`.
        '''
        # Get data from stream, deserialize it.
        self.assertStream()
        self.stream.seek(0)
        data = yaml.safe_load_all(self.stream)
        # Convert from lazy iterator to actual data.
        data = list(data)

        # Clean up stream while we're at this...
        self.stream.truncate(0)
        self.stream.seek(0)
        # Need both of these! `truncate()` deletes the current data and
        # `seek()` resets stream position back to zero, which we check for.
        self.assertNoStream()

        # Return the deserialized data.
        return data

    def capture(self) -> None:
        '''
        Reads all from our log stream and saves as log entries in `self.logs`.

        Clears stream after reading from it.

        Returns number of logs read from stream.
        '''
        # Deserialize whatever's in our stream buffer
        logs = self.deserialize()
        # (and make sure we got something).
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)

        # Capture the logs to our `self.logs` list.
        self.logs.extend(logs)
        self.assertLogs()

        return len(logs)

    # -------------------------------------------------------------------------
    # Asserts for Log / Stream
    # -------------------------------------------------------------------------

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
    # Longer asserts for help in testing.
    # -------------------------------------------------------------------------

    def verify_message(self, record: Mapping, expected: str) -> None:
        '''
        Verify that `record` has the message in the expected spot and that it
        matches the `expected` string.
        '''
        self.assertTrue(record)
        self.assertEqual(record['message'], expected)

    def verify_context(self,
                       record:          Mapping,
                       expected_data:   Mapping,
                       expected_func:   str,
                       expected_type:   str = 'UnitTestContext',
                       expected_dotted: str = None,
                       expected_class:  str = None,
                       ) -> None:
        '''
        Verify that `record` has the message in the expected spot and that it
        matches the `expected` string.
        '''
        if not expected_func:
            self.fail("verify_context requires an `expected_func`; "
                      f"got: {expected_func}")
        if not expected_dotted:
            expected_dotted = self.dotted
        if not expected_class:
            expected_class = f'{self.__class__.__name__}'
        expected_method = f'{expected_class}.{expected_func}'

        # Record has a context of correct type?
        self.assertIn('context', record)
        context_data = record['context']
        self.assertIn(expected_type, context_data)
        context_data = context_data[expected_type]

        # Context has expected `dotted` and has data?
        self.assertIn('dotted', context_data)
        self.assertEqual(context_data['dotted'], expected_dotted)
        self.assertIn('unit-testing', context_data)

        # Now we can check the expected_data...
        data = context_data['unit-testing']
        # Slight detour: data has "test_case.test_name" in it, so pop that out
        # and check it before comparing the rest of the dictionaries.
        method = data.pop('dotted')
        self.assertEqual(method, expected_method)
        # Ok; now we can check the data; should equal expected_data.
        self.assertEqual(data, expected_data)

    def verify_group(self,
                     record: Mapping,
                     group: const.Group,
                     dotted: str = None) -> None:
        '''
        Verify that `record` has group fields as expected.
        '''
        if not dotted:
            dotted = self.dotted

        self.assertIn('group', record)
        data_group = record['group']

        self.assertIn('name', data_group)
        self.assertEqual(data_group['name'], group.value)

        self.assertIn('dotted', data_group)
        self.assertEqual(data_group['dotted'], dotted)

    def verify_success(self,
                       record:  Mapping,
                       success: const.SuccessType,
                       dry_run: bool,
                       dotted:  str = None) -> None:
        '''
        Verify that `record` has or does not have group fields as expected.
        '''
        if not dotted:
            dotted = self.dotted
        normalized = const.SuccessType.normalize(success, dry_run)

        # If no fields expected, verify success dict is not present
        # and be done.
        if success is const.SuccessType.IGNORE and not dry_run:
            self.assertNotIn('success', record)
            return

        self.assertIn('success', record)
        data_success = record['success']

        if success is not const.SuccessType.IGNORE:
            self.assertIn('normalized', data_success)
            self.assertEqual(data_success['normalized'], str(normalized))

            self.assertIn('verbatim', data_success)
            self.assertEqual(data_success['verbatim'], str(success))
        else:
            self.assertNotIn('normalized', data_success)
            self.assertNotIn('verbatim', data_success)

        if dry_run:
            self.assertIn('dry-run', data_success)
            self.assertEqual(data_success['dry-run'], dry_run)
        else:
            self.assertNotIn('dry-run', data_success)

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    def make_context(self,
                     test_func: str,
                     data:      Mapping = None
                     ) -> Tuple[Mapping, UnitTestContext]:
        '''
        Creates a UnitTestContext with either supplied data or a default.

        Returns a tuple of (<context data used>, <context created>).
        '''
        if not data:
            data = {
                'field': 'value',
                'here':  'there',
                42:      '?',
            }
        context = UnitTestContext(self,
                                  data=data)
        return (data, context)

    def log_success(self,
                    message: str,
                    group:   const.Group,
                    success: const.SuccessType,
                    dry_run: bool,
                    context: UnitTestContext) -> Mapping:
        '''
        Log a message to a group with success data.

        Returns the captured log record.
        '''
        # ---
        # Log to the group!
        # ---
        log.group(group,
                  self.dotted,
                  message,
                  context=context,
                  log_success=success,
                  log_dry_run=dry_run)
        # No logs yet but should have stream data.
        self.assertNoLogs()
        self.assertStream()

        # ---
        # Check the log!
        # ---
        # Convert back from yaml and check fields and such.
        self.capture()
        self.assertLogs(exact=1)
        record = self.logs[0]

        # ---
        # Return the log!
        # ---
        return record

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_critical_at_default(self) -> None:
        self.assertNothing()

        message = 'test'
        log.critical(message)
        # No logs yet but should have stream data.
        self.assertNoLogs()
        self.assertStream()

        # Convert back from yaml and check fields and such.
        self.capture()
        self.assertLogs(exact=1)
        record = self.logs[0]
        self.assertTrue(record)
        self.verify_message(record, message)

    def test_context(self) -> None:
        func = 'test_context'
        self.assertNothing()

        message = 'test'
        ctx_data, context = self.make_context(func)

        log.critical(message, context=context)
        # No logs yet but should have stream data.
        self.assertNoLogs()
        self.assertStream()

        # Convert back from yaml and check fields and such.
        self.capture()
        self.assertLogs(exact=1)
        record = self.logs[0]

        # Check record fields.
        self.verify_message(record, message)
        self.verify_context(record, ctx_data, func)

    def test_group(self) -> None:
        func = 'test_group'
        self.assertNothing()

        # Make sure our group will log.
        group = const.Group.SECURITY
        level = const.Level.WARNING
        log.set_group_level(group, level)

        # Get some stuff to log.
        message = 'test'
        ctx_data, context = self.make_context(func)

        # ---
        # Log to the group!
        # ---
        log.security(self.dotted,
                     message,
                     context=context)
        # No logs yet but should have stream data.
        self.assertNoLogs()
        self.assertStream()

        # ---
        # Check the log!
        # ---
        # Convert back from yaml and check fields and such.
        self.capture()
        self.assertLogs(exact=1)
        record = self.logs[0]

        # Check record fields.
        self.verify_message(record, message)
        self.verify_context(record, ctx_data, func)
        self.verify_group(record, group)

    def test_success(self) -> None:
        func = 'test_success'
        self.assertNothing()

        # Make sure our group will log.
        group = const.Group.SECURITY
        level = const.Level.WARNING
        log.set_group_level(group, level)

        # Get some stuff to log.
        message = 'test'
        ctx_data, context = self.make_context(func)

        # ------------------------------
        # This should not have a success field.
        # ------------------------------
        # Ignore and not dry-run - no success field.
        success = const.SuccessType.IGNORE
        dry_run = False
        with self.subTest(success=success,
                          dry_run=dry_run):
            record = self.log_success(message,
                                      group,
                                      success,
                                      dry_run,
                                      context)
            self.verify_success(record, success, dry_run)
            self.assertNotIn('success', record)

        # ------------------------------
        # This should have a partial success field.
        # ------------------------------
        # Ignore and dry-run==True - only dry-run in output.
        self.clear_logs()
        success = const.SuccessType.IGNORE
        dry_run = True
        with self.subTest(success=success,
                          dry_run=dry_run):
            record = self.log_success(message,
                                      group,
                                      success,
                                      dry_run,
                                      context)
            self.verify_success(record, success, dry_run)
            self.assertIn('success', record)
            rec_success = record['success']
            self.assertNotIn('normalized', rec_success)
            self.assertNotIn('verbatim', rec_success)
            self.assertIn('dry-run', rec_success)

        # ------------------------------
        # Now test some more expected use-cases.
        # ------------------------------
        self.clear_logs()
        success = const.SuccessType.BLANK
        dry_run = True
        with self.subTest(success=success,
                          dry_run=dry_run):
            record = self.log_success(message,
                                      group,
                                      success,
                                      dry_run,
                                      context)
            self.verify_success(record, success, dry_run)

        self.clear_logs()
        success = const.SuccessType.FAILURE
        dry_run = False
        with self.subTest(success=success,
                          dry_run=dry_run):
            record = self.log_success(message,
                                      group,
                                      success,
                                      dry_run,
                                      context)
            self.verify_success(record, success, dry_run)

        self.clear_logs()
        success = const.SuccessType.SUCCESS
        dry_run = False
        with self.subTest(success=success,
                          dry_run=dry_run):
            record = self.log_success(message,
                                      group,
                                      success,
                                      dry_run,
                                      context)
            self.verify_success(record, success, dry_run)


# -----------------------------------------------------------------------------
# What is our default log formatter?
# -----------------------------------------------------------------------------

class ZestLogFormatDefault(ZestLogBase):
    '''
    Test veredi.logs.log has the expected default formatter.
    '''

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = (__file__, 'log', 'format', 'default')

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_default_is_yaml(self) -> None:
        self.assertTrue(log.logger)
        self.assertIsInstance(log.logger, logging.Logger)
        self.assertTrue(log.logger.handlers)
        self.assertEqual(len(log.logger.handlers), 1)

        handler = log.logger.handlers[0]
        self.assertTrue(handler)
        formatter = handler.formatter
        self.assertTrue(formatter)
        self.assertIsInstance(formatter, logging.Formatter)
        self.assertIsInstance(formatter, formats.yaml.FormatYaml)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run logs/log/zest_log.py

if __name__ == '__main__':
    import unittest
    # log.set_level(const.Level.DEBUG)
    unittest.main()
