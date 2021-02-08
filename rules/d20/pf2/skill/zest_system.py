# coding: utf-8

'''
Tests for the Skill system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import random


from veredi.zest.base.system        import ZestSystem
from veredi.base.context            import UnitTestContext
from veredi.logger                  import log

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.event         import DataLoadedEvent
from veredi.game.data.component     import DataComponent
from veredi.data.context            import DataAction

from veredi.data.records            import DataType
from veredi.rules.d20.pf2.game      import PF2Rank

from .system                        import SkillSystem
from .event                         import SkillRequest, SkillResult
from .component                     import SkillComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_SkillSystem(ZestSystem):
    '''
    Test our SkillSystem with some on-disk data.
    '''

    def set_up(self):
        super().set_up()
        self.set_up_input()
        self.init_self_system(SkillSystem)

    def sub_events(self):
        self.manager.event.subscribe(SkillResult, self.event_skill_res)

    def event_skill_res(self, event):
        self.events.append(event)

    def load(self, entity):
        # Make the load request event for our entity.
        request = self.data_request(entity.id,
                                    PF2Rank.Phylum.NPC,
                                    'Townville',
                                    'Skill Guy')
        self.assertFalse(self.events)

        # Ask for our Skill Guy data to be loaded.
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)
        self.assertTrue(self.events)
        self.assertEqual(len(self.events), 1)

        # We should get an event for load finished.
        self.assertEqual(len(self.events), 1)
        self.assertIsInstance(self.events[0], DataLoadedEvent)
        event = self.events[0]
        cid = event.component_id
        self.assertNotEqual(cid, ComponentId.INVALID)
        component = self.manager.component.get(cid)
        self.assertIsInstance(component, DataComponent)
        self.assertIsInstance(component, SkillComponent)

        # Stuff it on our entity; make it enabled too.
        self.manager.entity.attach(entity.id, component)
        component._life_cycle = ComponentLifeCycle.ALIVE
        # Make sure component got attached to entity.
        self.assertIn(SkillComponent, entity)

        return component

    def skill_request(self, entity, skill):
        context = UnitTestContext(
            __file__,
            self,
            'skill_request')  # no initial sub-context

        event = SkillRequest(
            entity.id,
            entity.type_id,
            context,
            skill)

        return event

    def test_init(self):
        self.assertTrue(self.manager)
        self.assertTrue(self.context)
        self.assertTrue(self.manager.system)
        self.assertTrue(self.system)

    def test_load(self):
        self.set_up_events()
        entity = self.create_entity()
        self.assertTrue(entity)
        component = self.load(entity)
        self.assertTrue(component)

    def test_skill_req_standard(self):
        self.set_up_events()
        entity = self.create_entity()
        self.load(entity)
        # Throw away loading events.
        self.clear_events()

        request = self.skill_request(entity, "Acrobatics")
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, SkillResult)
        self.assertEqual(result.skill.lower(), request.skill.lower())
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Skill Guy should have Nine Acrobatics.
        self.assertEqual(result.amount, 9)

    def test_skill_req_grouped(self):
        self.set_up_events()
        entity = self.create_entity()
        self.load(entity)
        # Throw away loading events.
        self.clear_events()

        request = self.skill_request(entity, "knowledge (nature)")
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, SkillResult)
        self.assertEqual(result.skill.lower(), request.skill.lower())
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Skill Guy should have Four Nature Knowledges.
        self.assertEqual(result.amount, 4)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.rules.d20.pf2.skill.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
