# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, List

import unittest

from veredi.logger                      import log
from .                                  import zload
from .zpath                             import TestType
from veredi.base.context                import UnitTestContext

from veredi.game.ecs.base.system        import System
from veredi.game.ecs.event              import Event
from veredi.base.context                import VerediContext
from veredi.game.ecs.base.identity      import EntityId
from veredi.game.ecs.base.entity        import Entity
from veredi.game.ecs.meeting            import Meeting
from veredi.interface.input.system      import InputSystem

from veredi.interface.input.command.reg import CommandRegistrationBroadcast


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Class for Testing Systems
# -----------------------------------------------------------------------------

class BaseSystemTest(unittest.TestCase):
    '''
    Base testing class with some setup and helpers.

    For testing classes where EcsManagers and events are needed.
    '''

    def setUp(self) -> None:
        '''
        unittest.TestCase setUp function. Make one for your test class, and
        call stuff like so, possibly with more stuff:

        super().setUp()
        self.init_managers(...)
        self.init_system(...)
        '''
        self.debugging:      bool                         = False
        self.events:         List[Event]                  = []
        self.manager:        Meeting                      = None
        self.context:        VerediContext                = None

        self.reg_open:       CommandRegistrationBroadcast = None
        '''
        Reg broadcast event if it has happened and been received by the unit
        test.
        '''

        self.system:         System                       = None
        '''The system being tested.'''

    def init_managers(self,
                      test_type: Optional[TestType] = TestType.UNIT) -> None:
        '''
        Calls zload.set_up to create Meeting of EcsManagers, a context from a
        config file, and a manager.system.
        '''
        (self.manager, _,
         self.context, _) = zload.set_up(self.__class__.__name__,
                                         'setUp',
                                         self.debugging,
                                         test_type=test_type)

    def init_system_others(self, *sys_types: System) -> None:
        '''
        Initializes other systems you need that aren't covered by
        init_system_self() or init_managers().

        init_managers() calls zload.set_up() which can optionally take a
        `desired_systems` kwarg.
        '''
        sids = zload.create_systems(self.manager.system,
                                    self.context,
                                    *sys_types)
        return sids

    def init_system_self(self, sys_type: System) -> System:
        '''
        Initializes, returns your test's system.
        '''
        sid = zload.create_system(self.manager.system,
                                  self.context,
                                  sys_type)
        self.system = self.manager.system.get(sid)

    def tearDown(self) -> None:
        '''
        unittest.TestCase tearDown function. Make one for your test class.

        Here's a start:

        super().tearDown()
        self.jeff = None  # <- or wherever you put your system in setUp().
        '''
        self.debugging = False
        self.events    = None
        self.manager   = None
        self.context   = None
        self.system    = None
        self.reg_open  = None

    # -------------------------------------------------------------------------
    # Event Helpers / Handlers
    # -------------------------------------------------------------------------

    def _sub_events_test(self) -> None:
        '''
        Subscribe to the events your want to be the (or just a)
        receiver/handler for here. Called from event_set_up() for tests that
        want to do events.

        e.g.:
        self.event_manager.subscribe(CommandRegistrationBroadcast,
                                     self.event_cmd_reg)
        '''
        pass

    def _sub_events_systems(self) -> None:
        '''
        This has all systems that SystemManager knows about (which /should/ be
        every single one) get their subscribe() call.
        '''
        self.manager.system.subscribe(self.manager.event)

    def _sub_events_commands(self) -> None:
        '''
        Subscribes our event_cmd_reg() function to the
        CommandRegistrationBroadcast.
        '''
        self.manager.event.subscribe(CommandRegistrationBroadcast,
                                     self.event_cmd_reg)

    def event_set_up(self) -> None:
        '''
        Rolls _sub_events_* into one call.
        '''
        self._sub_events_test()
        self._sub_events_systems()
        self._sub_events_commands()

    def clear_events(self) -> None:
        '''
        Clears out the `self.events` queue.
        '''
        self.events.clear()

    def event_now(self,
                  event:         Event,
                  num_publishes: int = 3) -> None:
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event? So we publish() in order to get
        that one sent out. Which /may/ cause something to process that and
        queue up another. So we'll publish as many times as asked in
        `num_publishes`.

        NOTE: This has a LoggingManager in it, so set self.debugging to true if
        you need to output all the logs during events.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            self.manager.event.notify(event, True)

            for each in range(num_publishes):
                self.manager.event.publish()

    def trigger_events(self,
                       event:           Event,
                       num_publishes:   int = 3,
                       expected_events: int = 1) -> None:
        '''
        Sanity asserts on inputs, then we call event_now() to immediately
        trigger event and response. Then we check our events queue against
        `expected_events` (set to zero if you don't expect any).

        NOTE: This has a LoggingManager in it, so set self.debugging to true if
        you need to output all the logs during events.
        '''
        self.assertTrue(event)
        self.assertTrue(num_publishes > 0)
        self.assertTrue(expected_events >= 0)

        # This has a LoggingManager in it, so set self.debugging to true if you
        # need to output all the logs during events.
        self.event_now(event, num_publishes)

        if expected_events == 0:
            self.assertFalse(self.events)
            self.assertEqual(len(self.events), 0)
            return

        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

    def event_cmd_reg(self, event):
        self.assertIsInstance(event,
                              CommandRegistrationBroadcast)
        self.reg_open = event

        self._make_cmd(event)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def _make_cmd(self, event):
        '''
        Called from event_cmd_reg() when broadcast comes in.
        Make CommandRegisterReply() events for each command you want to
        register.
        '''
        pass

    def allow_registration(self):
        if self.reg_open:
            return

        input_system = self.manager.system.get(InputSystem)
        self.assertTrue(input_system)

        event = input_system._commander.registration(self.system.id,
                                                     None)
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)
        # Now registration is open.
        self.assertTrue(self.reg_open)

    # -------------------------------------------------------------------------
    # Create Things for Tests
    # -------------------------------------------------------------------------

    def create_entity(self) -> Entity:
        '''
        Creates an empty entity of type _TYPE_DONT_CARE.
        '''
        _TYPE_DONT_CARE = 1

        # TODO [2020-06-01]: When we get to Entities-For-Realsies,
        # probably change to an EntityContext or something...
        context = UnitTestContext(
            self.__class__.__name__,
            'test_create',
            {})  # no initial sub-context

        # Set up an entity to load the component on to.
        eid = self.manager.entity.create(_TYPE_DONT_CARE,
                                         context)
        self.assertNotEqual(eid, EntityId.INVALID)
        entity = self.manager.entity.get(eid)
        self.assertTrue(entity)

        return entity

    # -------------------------------------------------------------------------
    # Test Functions
    # -------------------------------------------------------------------------

    # def test_init(self):
    #     self.assertTrue(self.system)
