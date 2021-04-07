# coding: utf-8

'''
Tests for the Ability system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import random


from veredi.zest.base.system        import ZestSystem
from veredi.zest.zpath              import TestType

from veredi.base.context            import UnitTestContext
from veredi.data.exceptions         import LoadError
from veredi.logs                    import log

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.entity    import Entity
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.event         import (DataLoadedEvent,
                                                 DataLoadRequest)
from veredi.game.data.component     import DataComponent
from veredi.data.context            import (DataAction,
                                                 DataGameContext,
                                                 DataLoadContext)
from veredi.data.records            import DataType
from veredi.rules.d20.pf2.game      import PF2Rank

from veredi.interface.input.event   import CommandInputEvent

from .system                        import AbilitySystem
from .event                         import AbilityRequest, AbilityResult
from .component                     import AbilityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

# TODO [2020-10-13]: Get, test output!!!

class Test_AbilitySystem(ZestSystem):
    '''
    Test our AbilitySystem with some on-disk data.
    '''

    ID_DATA = {
        'identity': {
            'name': 'aluminum dragon',
            'group': 'monster',
            'owner': 'u/gm_dm',

            'display-name': 'Aluminum Dragon',
            'title': 'Lightweight',
        },
    }

    # Strong aluminum dragon with normal str mod conversion.
    EXPECTED_STR_SCORE = 30
    EXPECTED_STR_MOD   = "(${this.score} - 10) // 2"

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = __file__

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        super().set_up()
        self.set_up_input()
        self.init_self_system(AbilitySystem)
        self.test_cmd_recv = None
        self.test_cmd_ctx = None

    def tear_down(self):
        super().tear_down()
        self.test_cmd_recv = None
        self.test_cmd_ctx = None

    def sub_events(self):
        self.manager.event.subscribe(AbilityResult, self.event_ability_res)

    # -------------------------------------------------------------------------
    # Loading data.
    # -------------------------------------------------------------------------

    def create_entity(self, clear_event_queue=True) -> Entity:
        '''
        Creates entity by:
          - Having parent create_entity()
          - Calling identity() to create/attach IdentityComponent.
          - Calling load() to create/attach our AbilityComponent.
          - Clearing events (if flagged to do so).

          - Returning entity.

        If `clear_event_queue`, drops all events from EventManager's queue
        before returing.
        '''
        entity = super().create_entity()
        self.assertTrue(entity)

        # Create and attach components.
        self.create_identity(entity,
                             data=self.ID_DATA,
                             expected_events=0,
                             clear_event_queue=clear_event_queue)
        self.create_ability(entity)

        # Make the entity alive!
        self.manager.entity.creation(self.manager.time)

        # Throw away loading events?
        if clear_event_queue:
            self.clear_events()

        return entity

    def create_ability(self, entity):
        # Make the load request event for our entity.
        request = self.data_request(entity.id,
                                    PF2Rank.Phylum.MONSTER,
                                    'dragon',
                                    'Aluminum Dragon')
        self.assertFalse(self.events)

        # Ask for our Ability Guy data to be loaded.
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        # Attach the loaded component to our entity.
        self.assertIsInstance(self.events[0], DataLoadedEvent)
        event = self.events[0]
        cid = event.component_id
        self.assertNotEqual(cid, ComponentId.INVALID)
        component = self.manager.component.get(cid)
        self.assertIsInstance(component, DataComponent)
        self.assertIsInstance(component, AbilityComponent)

        self.manager.entity.attach(entity.id, component)
        component._life_cycle = ComponentLifeCycle.ALIVE
        # Make sure component got attached to entity.
        self.assertIn(AbilityComponent, entity)

        return component

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def ability_request(self, entity, ability):
        context = UnitTestContext(
            __file__,
            self,
            'ability_request')  # no initial sub-context
        # ctx = self.context.spawn(EphemerealContext,
        #                          'unit-testing', None)

        event = AbilityRequest(
            entity.id,
            entity.type_id,
            context,
            entity.id,
            ability)

        return event

    def event_ability_res(self, event):
        self.assertIsInstance(event,
                              AbilityResult)
        self.events.append(event)

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.manager)
        self.assertTrue(self.context)
        self.assertTrue(self.manager.system)
        self.assertTrue(self.system)

    def test_ability_req(self):
        self.set_up_events()
        entity = self.create_entity()

        request = self.ability_request(entity, "strength")
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, AbilityResult)
        self.assertEqual(result.ability.lower(), request.ability.lower())
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Aluminum Dragon should have 30 strengths.
        self.assertEqual(result.amount.value,
                         self.EXPECTED_STR_SCORE)
        self.assertEqual(result.amount.milieu,
                         'strength.score')

    def test_ability_req_mod(self):
        self.set_up_events()
        entity = self.create_entity()

        request = self.ability_request(entity, "strength.modifier")
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, AbilityResult)
        self.assertEqual(result.ability.lower(), request.ability.lower())
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Aluminum Dragon should have normal math for str mod.
        self.assertEqual(result.amount.value,
                         self.EXPECTED_STR_MOD)
        self.assertEqual(result.amount.milieu,
                         'strength.modifier')

    def test_ability_req_mod_alias(self):
        self.set_up_events()
        entity = self.create_entity()

        # 'str' is 'strength' alias
        # 'mod' is 'modifier' alias
        request = self.ability_request(entity, "str.mod")
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, AbilityResult)
        self.assertEqual(result.ability.lower(), request.ability.lower())
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Aluminum Dragon should have normal math for str mod.
        self.assertEqual(result.amount.value,
                         self.EXPECTED_STR_MOD)
        self.assertEqual(result.amount.milieu,
                         'strength.modifier')

    # ------------------------------
    # Commands
    # ------------------------------

    def test_cmd_reg(self):
        self.set_up_events()
        self.allow_registration()

        # Nothing exploded?
        #    ...
        # Success!

    def test_cmd_score(self):
        self.set_up_events()
        self.allow_registration()
        entity = self.create_entity()

        context = UnitTestContext(
            __file__,
            self,
            'test_cmd_score')  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/ability $strength.score + 4")
        self.trigger_events(event, expected_events=0)

    def test_cmd_mod(self):
        self.set_up_events()
        self.allow_registration()
        entity = self.create_entity()

        context = UnitTestContext(
            __file__,
            self,
            'test_cmd_mod')  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/ability $strength.modifier + 4")
        self.trigger_events(event, expected_events=0)

    def test_cmd_shortcut(self):
        self.set_up_events()
        self.allow_registration()
        entity = self.create_entity()

        context = UnitTestContext(
            __file__,
            self,
            'test_cmd_shortcut')  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/ability $strength + 4")
        self.trigger_events(event, expected_events=0)

    def test_cmd_alias(self):
        self.set_up_events()
        self.allow_registration()
        entity = self.create_entity()

        context = UnitTestContext(
            __file__,
            self,
            'test_cmd_alias')  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/ability $str.mod + 4")
        self.trigger_events(event, expected_events=0)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.rules.d20.pf2.ability.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
