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

from ..integrate                            import IntegrationTest

from veredi.logger                          import log
from veredi.base.null                       import Null
from veredi.base.context                    import UnitTestContext
from veredi.data.context                    import (DataGameContext,
                                                    DataLoadContext)
from veredi.data.exceptions                 import LoadError

from veredi.debug.const                     import DebugFlag
from veredi.game.ecs.base.identity          import ComponentId
from veredi.game.data.component             import DataComponent

from veredi.game.data.event                 import (DataLoadRequest,
                                                    DataLoadedEvent)

from veredi.interface.input.event           import CommandInputEvent
from veredi.interface.input.context         import InputContext
from veredi.interface.output.system         import OutputSystem
from veredi.interface.output.event          import OutputType

from veredi.rules.d20.pf2.ability.system    import AbilitySystem
from veredi.rules.d20.pf2.ability.event     import AbilityResult
from veredi.rules.d20.pf2.ability.component import AbilityComponent

from veredi.math.system                     import MathSystem
from veredi.game.data.identity.system       import IdentitySystem
from veredi.game.data.identity.component    import IdentityComponent
from veredi.rules.d20.pf2.health.component  import HealthComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# # regex is:
# #   "iid:"
# #   hexadecimal string with dash separators:
# #   word boundry
# # This works for InputIds like:
# #   iid:53a296bb-4240-5e84-a5ce-b7293b648138
# IID_RE_STR = r'iid:[0-9A-Fa-f-]*\b'
# Currently encode IIDs to dict via Encodable.encode(), so currently id value
# is an int:
IID_RE_STR = r'iid:\s?[0-9]*\b'
IID_REPLACEMENT = '<input-id>'

EXPECTED_OUTPUT = '''!effect.math
title: {caption: Fake Subtitle, name: Fake Title}
input: ability $dex.mod + 4
id: {_encodable: InputId, <input-id>}
type: veredi.math.event.output
output:
  children:
  - children:
    - children:
      - {name: dexterity.score, type: variable, value: 10}
      - {name: '10', type: constant, value: 10}
      name: "\\u2212"
      type: operator
      value: 0
    - {name: '2', type: constant, value: 2}
    name: "\\xF7\\xF7"
    type: operator
    value: 0
  - {name: '4', type: constant, value: 4}
  name: +
  type: operator
  value: 4
names: {'EntityId:001': aluminum dragon}
'''


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_InputToOutput_AbilityCheck(IntegrationTest):

    # ---
    # Set-Up & Tear-Down
    # --
    # Leaving here even if only calling super(). So I remember about them
    # when next I stumble in here.
    # ---

    def setUp(self):
        super().setUp()
        self.debug_flags = DebugFlag.GAME_ALL
        self.output_recvd = None

        self.init_required(True)
        self.init_input()
        self.init_many_systems(IdentitySystem, MathSystem, AbilitySystem)
        self.init_output()
        # self.whatever = self.init_a_system(...)

        self.expected_components = {IdentityComponent,
                                    AbilityComponent,
                                    HealthComponent}

    def tearDown(self):
        super().tearDown()
        self.expected_components = None
        self.output_recvd = None

    def apoptosis(self):
        super().apoptosis()

    # ---
    # Events
    # ---

    def _sub_events_test(self) -> None:
        self.sub_loaded()
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

    def recv_output(self, send_entry):
        self.output_recvd = send_entry

    # -------------------------------------------------------------------------
    # Entity/Component Test Set-Up
    # -------------------------------------------------------------------------

    def per_test_set_up(self):
        self.engine_set_up()
        self.event_set_up()
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

    def test_ent_set_up(self):
        # Just make sure we did the set up successfully...
        self.per_test_set_up()

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
        self.assertEqual(self.output_recvd.target_type,
                         OutputType.BROADCAST)
        self.assertEqual(self.output_recvd.payload_type,
                         OutputType.BROADCAST)

        # Replace payload's input id with placeholder via regex. Then compare
        # line by line with a nice error message so it's not just all...:
        #
        #   AssertionError: '!eff[532 chars]ator\n value: 4\nnames:
        #   {\'EntityId:001\': aluminum dragon}\n' != '!eff[532 chars]ator\n
        #   value: 4\nnames: {\'EntityId:001\': aluminum dragon}'
        #   Diff is 697 characters long. Set self.maxDiff to None to see it.

        regex = re.compile(IID_RE_STR, re.IGNORECASE)
        payload = regex.sub(IID_REPLACEMENT, self.output_recvd.payload)
        i = 0
        for line, check in zip_longest(payload.split('\n'),
                                       EXPECTED_OUTPUT.split('\n')):
            # 'this' shouldn't be in the output anywhere.
            self.assertEqual(line.find('this'), -1,
                             f"line #{i} failed 'this'-lessness check: "
                             f"\noutput: '{line}'")
            self.assertEqual(line, check,
                             "line #{i} failed equality check: \noutput: "
                             f"'{line}'\n check: '{check}'")
            i += 1

        self.manager.system.get(OutputSystem)._unit_test()
