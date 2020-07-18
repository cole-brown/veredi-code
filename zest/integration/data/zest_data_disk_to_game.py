# coding: utf-8

'''
Integration Test for data load path.

Start with the data "saved" and "in the repository" (i.e. a file on disk).
Create a DataLoadedEvent and kick it off, then sit back and wait for our
DataSystem, Repository, Codec, DataEvents, etc. to do Stuff and make Things
happen.

We will end up with a Component and verify its data.

This Integration Test avoids using the game Engine. All this is event-driven
and doesn't really need the engine.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from ..integrate import IntegrationTest

from veredi.data.context                    import (DataGameContext,
                                                    DataLoadContext)
from veredi.data.exceptions                 import LoadError

from veredi.game.ecs.base.identity          import ComponentId
from veredi.game.data.component             import DataComponent

from veredi.game.data.event                 import (DataLoadRequest,
                                                    DataLoadedEvent)

from veredi.rules.d20.pf2.health.component  import HealthComponent
from veredi.rules.d20.pf2.ability.component import AbilityComponent
from veredi.game.data.identity.component    import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_DataLoad_DiskToGame(IntegrationTest):

    # ---
    # Set-Up & Tear-Down
    # Leaving here even though only calling super(). So I remember about them
    # when next I stumble in here.
    # ---

    def setUp(self):
        super().setUp()
        self.init_required(False)
        # self.init_many_systems(...)
        # self.whatever = self.init_a_system(...)

        self.expected_components = {IdentityComponent,
                                    AbilityComponent,
                                    HealthComponent}

    def tearDown(self):
        super().tearDown()
        self.expected_components = None

    def apoptosis(self):
        super().apoptosis()

    # ---
    # Events
    # ---

    def _sub_events_test(self) -> None:
        self.sub_loaded()

    def load_request(self, type):
        ctx = DataLoadContext('unit-testing',
                              type,
                              'test-campaign')
        if type == DataGameContext.DataType.MONSTER:
            ctx.sub['family'] = 'dragon'
            ctx.sub['monster'] = 'aluminum dragon'
        else:
            raise LoadError(
                f"No DataGameContext.DataType to ID conversion for: {type}",
                None,
                ctx)

        event = DataLoadRequest(
            42,
            ctx.type,
            ctx)

        return event

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager)
        self.assertTrue(self.manager.time)
        self.assertTrue(self.manager.event)
        self.assertTrue(self.manager.component)
        self.assertTrue(self.manager.entity)
        self.assertTrue(self.manager.system)

    def test_set_up(self):
        self.event_set_up()

        # Make our request event.
        request = self.load_request(DataGameContext.DataType.MONSTER)
        self.assertFalse(self.events)

        # Ask for our aluminum_dragon to be loaded. Expect 1 event for
        # each component in its data file.
        expected_events = len(self.expected_components)
        self.trigger_events(request,
                            expected_events=expected_events)
        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

        # And we have DataLoadedEvents! Check 'em all; save the health one
        # for more checks.
        health_comp = None
        for loaded_event in self.events:
            self.assertIsInstance(loaded_event, DataLoadedEvent)

            # Did it make a thing?
            self.assertNotEqual(loaded_event.component_id, ComponentId.INVALID)

            # Get the thing and check it.
            component = self.manager.component.get(loaded_event.component_id)
            self.assertIsNotNone(component)
            self.assertEqual(loaded_event.component_id,
                             component.id)
            self.assertIsInstance(component, DataComponent)

            if isinstance(component, HealthComponent):
                health_comp = component

        self.assertIsNotNone(health_comp)

        health_data = health_comp.persistent
        self.assertEqual(health_data['health']['current']['permanent'],
                         200)
        self.assertEqual(health_data['health']['maximum']['hit-points'],
                         200)
        self.assertEqual(health_data['health']['death']['hit-points'],
                         -50)
        self.assertEqual(health_data['health']['resistance']['slashing'],
                         10)
        self.assertEqual(health_data['health']['resistance']['cold'],
                         3)
        self.assertEqual(health_data['health']['immunity']['bludgeoning'],
                         True)
