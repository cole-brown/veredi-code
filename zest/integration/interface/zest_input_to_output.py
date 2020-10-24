# coding: utf-8

'''
Integration Test for input -> ..?.. -> output.

Start with the data "saved" and "in the repository" (i.e. a file on disk).
Create a DataLoadedEvent and kick it off, then sit back and wait for our
DataSystem, Repository, Codec, DataEvents, etc. to do Stuff and make Things
happen.

Do the CommandRegistrationBroadcast, let AbilitySystem register its command(s).

Make an Entity and a from-data AbilityComponent, then test an ability command.

Make sure output meets expectations.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import re
from itertools import zip_longest

from veredi.zest.base.integrate import ZestIntegrateEngine

from veredi.logger                          import log
from veredi.base.null                       import Null
from veredi.data                            import background
from veredi.base.context                    import UnitTestContext
from veredi.data.context                    import (DataGameContext,
                                                    DataLoadContext)
from veredi.data.exceptions                 import LoadError
from veredi.data.identity                   import UserId, UserKey

from veredi.debug.const                     import DebugFlag
from veredi.game.ecs.base.identity          import ComponentId
from veredi.game.data.component             import DataComponent
from veredi.game.ecs.base.entity            import Entity

from veredi.game.data.event                 import (DataLoadRequest,
                                                    DataLoadedEvent)

from veredi.interface.user                  import User
from veredi.interface.input.event           import CommandInputEvent
from veredi.interface.input.context         import InputContext
from veredi.interface.output.system         import OutputSystem
from veredi.interface.output.envelope       import Envelope
from veredi.interface.output.event          import Recipient

from veredi.rules.d20.pf2.ability.system    import AbilitySystem
from veredi.rules.d20.pf2.ability.event     import AbilityResult
from veredi.rules.d20.pf2.ability.component import AbilityComponent

from veredi.math.system                     import MathSystem
from veredi.math.parser                     import MathTree
from veredi.game.data.identity.system       import IdentitySystem
from veredi.game.data.identity.component    import IdentityComponent
from veredi.rules.d20.pf2.health.component  import HealthComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_InputToOutput_AbilityCheck(ZestIntegrateEngine):

    def set_up(self):
        self.debug_flags = DebugFlag.GAME_ALL
        super().set_up()

        self.output_recvd = None
        self.recipients = Recipient.INVALID
        self.expected_components = {IdentityComponent,
                                    AbilityComponent,
                                    HealthComponent}

        self.init_many_systems(IdentitySystem, MathSystem, AbilitySystem)

        self._uid_gen = UserId.generator()
        self._ukey_gen = UserKey.generator()
        self.make_users()

    def tear_down(self):
        super().tear_down()
        self.expected_components = None
        self.output_recvd = None
        self.recipients = Recipient.INVALID

    def sub_events(self) -> None:
        self.manager.event.subscribe(AbilityResult, self.event_ability_res)

    def event_ability_res(self, event):
        self.events.append(event)

    def load_request(self, entity_id, type):
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
            entity_id,
            ctx.type,
            ctx)

        return event

    def recv_output(self, envelope, recipients):
        '''
        Unit testing callback for OutputSystem.
        '''
        self.output_recvd = envelope
        self.output_recipients = recipients

    def make_users(self):
        '''
        Stuff some fake users into background.
        '''
        uid  = self._uid_gen.next("jeff")
        ukey = self._ukey_gen.next("jeff")
        background.users.add_connected(User(uid, ukey))

    # -------------------------------------------------------------------------
    # Entity/Component Test Set-Up
    # -------------------------------------------------------------------------

    def per_test_set_up(self):
        self.start_engine_and_events()
        entity = self.create_entity()

        # import veredi.zest.debug.background
        # veredi.zest.debug.background.to_log('zest_input_to_output')

        # Make our request event.
        request = self.load_request(entity.id,
                                    DataGameContext.DataType.MONSTER)

        # print("per_test_set_up")
        # from veredi.zest.debug import background
        # background.to_log("unit-testing")

        # Trigger load with our request event.
        # Ask for our aluminum_dragon to be loaded. Expect 1 event for
        # each component in its data file.
        expected_events = len(self.expected_components)
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request,
                                expected_events=expected_events)
        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

        # And we have DataLoadedEvents! Check 'em all; save the health one
        # for more checks.
        loaded_types = set()
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
            comp_type = type(component)
            loaded_types.add(comp_type)

            # Make sure component and entity are enabled...
            self.force_alive(entity, component)

            # Not on entity because we don't have anyone hanging on them where
            # they belong yet...
            self.assertIs(entity.get(comp_type), Null())

            # Now stuff it in there.
            self.manager.entity.attach(entity.id, component)
            ent_comp = entity.get(comp_type)
            self.assertIsNot(ent_comp, Null())
            self.assertIs(ent_comp, component)

        # Now we have a set of all types - check against our expectations.
        self.assertEqual(loaded_types,
                         self.expected_components)

        self.clear_events()
        return entity

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
        self.assertTrue(self.engine)
        self.assertTrue(self.input_system)
        self.assertTrue(self.output_system)

    def test_per_test_set_up(self):
        # Just make sure we did the set up successfully...
        entity = self.per_test_set_up()
        self.assertIsNotNone(entity)
        self.assertIsInstance(entity, Entity)
        self.assertIsNotNone(entity.id)

        self.assertIsNotNone(self.reg_open)

        ability = self.manager.system.get(AbilitySystem)
        self.assertIsNotNone(ability)
        self.assertEqual(ability._subscribed, True)

    def test_input_to_output(self):
        # Set up entity with ability data
        entity = self.per_test_set_up()
        self.manager.system.get(OutputSystem)._unit_test(self.recv_output)

        # Ok... test the ability command.
        context = UnitTestContext(
            self.__class__.__name__,
            'input-event',
            {})  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/ability $dex.mod + 4")
        self.trigger_events(event, expected_events=0)

        with log.LoggingManager.on_or_off(self.debugging):
            self.engine_tick(1)

        self.assertTrue(self.output_recvd)
        self.assertIsInstance(self.output_recvd, Envelope)
        self.assertEqual(self.output_recvd.desired_recipients,
                         Recipient.BROADCAST)
        self.assertEqual(self.output_recvd.valid_recipients,
                         Recipient.BROADCAST)
        # Should be EntityId:001
        self.assertEqual(self.output_recvd.source_id.value, 1)

        # Envelope's data is the math tree results. Make sure they're what we
        # expect.
        self.assertIsInstance(self.output_recvd.data, MathTree)
        # Aluminum Dragon's data is:
        #   veredi/zest/zata/integration/repository/file-tree/game/test-campaign/monsters/dragon/aluminum_dragon.yaml
        # Aluminum Dragon's Dex is: 10 (mod == 0)
        #   dex.mod + 4 = 4
        self.assertEqual(self.output_recvd.data.value, 4)

        self.manager.system.get(OutputSystem)._unit_test()


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.integration.interface.zest_input_to_output

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
