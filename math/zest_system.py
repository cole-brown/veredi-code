# coding: utf-8

'''
Tests for the Math system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.system import ZestSystem

from veredi.zest             import zontext
from veredi.base.const       import VerediHealth
from veredi.data             import background

from .system                 import MathSystem
from .event                  import MathResult
from .parser                 import MathTree
from .d20.parser             import D20Parser

from veredi.interface.input.parse import UTParcel

# from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
#                                                 CommandRegisterReply,
#                                                 CommandPermission,
#                                                 CommandArgType,
#                                                 CommandStatus)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_MathSystem(ZestSystem):
    '''
    Test our MathSystem.
    '''

    def set_up(self):
        super().set_up()
        self.init_self_system(MathSystem)
        self.parser = D20Parser(None)
        self.value_canon = None
        self.value_fill = None

        self.context = zontext.test(self.__class__.__name__,
                                    'set_up')

        # Set up parser in background for MathSystem to grab.
        parcel = UTParcel(self.parser, self.context)
        background.input.set(self.dotted(__file__),
                             parcel,
                             None,
                             background.Ownership.SHARE)

        self.set_up_events(clear_self=True,
                           clear_manager=True)

    def tear_down(self):
        super().tear_down()
        self.value_canon = None
        self.value_fill = None

    def sub_events(self):
        self.manager.event.subscribe(MathResult, self.event_math_res)

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def event_math_res(self, event):
        self.assertIsInstance(event,
                              MathResult)
        self.events.append(event)

    # -------------------------------------------------------------------------
    # Cannons and Fillers
    # -------------------------------------------------------------------------

    def canonicalize(self, input_str, milieu_str):
        return self.value_canon

    def fill(self, entity_id, input_str, context):
        return self.value_fill, input_str

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager)
        self.assertTrue(self.context)
        self.assertTrue(self.manager.system)
        self.assertTrue(self.system)

    def test_math_command_status(self):
        '''
        Just check that whatever happened, we think we succeeded at it.
        '''
        math = self.parser.parse('40 + 2')
        self.assertTrue(math)
        # Not evaluated yet.
        self.assertFalse(math.value)

        status = self.system.command(math,
                                     self.canonicalize,
                                     self.fill,
                                     MathResult(0, 0,
                                                self.context,
                                                math),
                                     self.context)
        self.assertTrue(status.success)

    def test_math_command_result(self):
        '''
        Check to make sure some easy math gets an actual, correct result.
        '''
        math = self.parser.parse('40 + 2')
        self.assertTrue(math)
        # Not evaluated yet.
        self.assertFalse(math.value)

        status = self.system.command(math,
                                     self.canonicalize,
                                     self.fill,
                                     MathResult(0, 0,
                                                self.context,
                                                math),
                                     self.context)
        self.assertTrue(status.success)

        # Not evaluated yet.
        self.assertFalse(math.value)
        # But should be ready to be evaluated after that first pass.
        self.assertEqual(len(self.system._recurse), 0)
        self.assertEqual(len(self.system._finalize), 1)
        self.assertEqual(len(self.events), 0)

        # Tick once should be enough to finalize and get an event ready.
        health = self.system._update(self.manager.time,
                                     self.manager.component,
                                     self.manager.event)
        self.assertEqual(health,
                         VerediHealth.HEALTHY)
        # Should have nothing queued in MathSystem and one event ready for
        # publish but not published quite yet.
        self.assertEqual(len(self.system._recurse), 0)
        self.assertEqual(len(self.system._finalize), 0)
        self.assertEqual(len(self.events), 0)
        self.assertEqual(len(self.manager.event._events), 1)

        # Publish my event to me.
        self.manager.event.publish()
        self.assertEqual(len(self.manager.event._events), 0)
        self.assertEqual(len(self.events), 1)

        # Check my math result.
        result = self.events[0]
        self.assertIsInstance(result, MathResult)
        self.assertEqual(result.total, 42)

    def test_math_replace_var(self):
        '''
        Check to make sure a var gets replaced with more maths.
        '''
        # replace the variable with this:
        self.value_canon = 'jeff.jefferson'
        self.value_fill = '20 * 2'
        math = self.parser.parse('$jeff + 2')
        self.assertTrue(math)
        # Not evaluated yet.
        self.assertFalse(math.value)

        status = self.system.command(math,
                                     self.canonicalize,
                                     self.fill,
                                     MathResult(0, 0,
                                                self.context,
                                                math),
                                     self.context)
        self.assertTrue(status.success)

        # Not evaluated yet.
        self.assertFalse(math.value)
        # And should need to keep going after first pass. First pass should
        # replace $jeff so math is still in flux; not ready for finalization.
        self.assertEqual(len(self.system._recurse), 1)
        self.assertEqual(len(self.system._finalize), 0)
        self.assertEqual(len(self.events), 0)
        self.assertEqual(len(self.manager.event._events), 0)

        # Tick once should find stable math during recurse, put into finalize
        # queue, immediate take from finalize, evaluate it, and send out
        # the event.
        health = self.system._update(self.manager.time,
                                     self.manager.component,
                                     self.manager.event)
        self.assertEqual(health,
                         VerediHealth.HEALTHY)
        self.assertEqual(len(self.system._recurse), 0)
        self.assertEqual(len(self.system._finalize), 0)
        self.assertEqual(len(self.events), 0)
        self.assertEqual(len(self.manager.event._events), 1)

        # Publish my event to me.
        self.manager.event.publish()
        self.assertEqual(len(self.manager.event._events), 0)
        self.assertEqual(len(self.events), 1)

        # Check my math result.
        result = self.events[0]
        self.assertIsInstance(result, MathResult)
        self.assertEqual(result.total, 42)

        # Milieu didn't make it because our replacement was just math.
        # So verify that statement
        for var in result.root.walk(MathTree._predicate_variable_nodes):
            self.fail('No variables should be present in output tree.')

    # def test_math_milieu(self):
    #     '''
    #     Check to make sure our milieu (value parsing contextual name)
    #     is used properly.
    #     '''
    #
    #     # TODO [2020-07-05]: do this test
    #
    #     # Check that my milieu made it.
    #     num_vars = 0
    #     for var in result.root.walk(MathTree._predicate_variable_nodes):
    #         num_vars += 1
    #         self.assertEqual(var.milieu, self.canon)
    #     # Make sure we actually checked a var?
    #     self.assertEqual(num_vars, 1)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------


# Can't just run file from here... Do:
#   doc-veredi python -m veredi.math.d20.zest_tree

if __name__ == '__main__':
    import unittest
    unittest.main()
