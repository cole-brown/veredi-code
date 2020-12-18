# coding: utf-8

'''
Integration Test for input -> command -> command invokee -> SkillResult.

Start with the data "saved" and "in the repository" (i.e. a file on disk).
Create a DataLoadedEvent and kick it off, then sit back and wait for our
DataManager to do Stuff and make Things happen.

Do the CommandRegistrationBroadcast, let SkillSystem register its command(s).

Make an Entity and a from-data SkillComponent, then test the skill command.

This Integration Test avoids using the game Engine. All this is event-driven
and doesn't really need the engine.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.integrate import ZestIntegrateEcs

from veredi.base.null                     import Null
from veredi.base.context                  import UnitTestContext
from veredi.data.context                  import (DataGameContext,
                                                  DataLoadContext)
from veredi.data.exceptions               import LoadError

from veredi.game.ecs.base.identity        import ComponentId

from veredi.game.data.event               import (DataLoadRequest,
                                                  DataLoadedEvent)

from veredi.interface.input.event         import CommandInputEvent

from veredi.rules.d20.pf2.skill.system    import SkillSystem
from veredi.rules.d20.pf2.skill.event     import SkillResult
from veredi.rules.d20.pf2.skill.component import SkillComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_InputCmd_SkillCheck(ZestIntegrateEcs):

    def set_up(self):
        super().set_up()
        self.init_one_system(SkillSystem)

    def sub_events(self) -> None:
        self.manager.event.subscribe(SkillResult, self.event_skill_res)

    def event_skill_res(self, event):
        self.events.append(event)

    def load_request(self, eid, type):
        ctx = DataLoadContext('unit-testing',
                              type,
                              'test-campaign')
        if type == DataGameContext.DataType.NPC:
            ctx.sub['family'] = 'Townville'
            ctx.sub['npc'] = 'Skill Guy'
        else:
            raise LoadError(
                f"No DataGameContext.DataType to ID conversion for: {type}",
                None,
                ctx)

        event = DataLoadRequest(
            eid,
            ctx.type,
            ctx)

        return event

    # -------------------------------------------------------------------------
    # Entity/Component Test Set-Up
    # -------------------------------------------------------------------------

    def per_test_set_up(self):
        self.set_up_events()
        entity = self.create_entity()

        # Make our request event.
        request = self.load_request(entity.id, DataGameContext.DataType.NPC)
        self.assertFalse(self.events)

        # Ask for our Skill Guy data to be loaded.
        self.trigger_events(request)
        self.assertTrue(self.events)
        self.assertEqual(len(self.events), 1)

        # And we have a DataLoadedEvent!
        loaded_event = self.events[0]
        self.assertIsInstance(loaded_event, DataLoadedEvent)

        # Did it make a thing?
        self.assertNotEqual(loaded_event.component_id, ComponentId.INVALID)

        # Get the thing and check it.
        component = self.manager.component.get(loaded_event.component_id)
        self.assertIsNot(component, Null())
        self.assertEqual(loaded_event.component_id,
                         component.id)
        self.assertIsInstance(component, SkillComponent)

        # Make sure component and entity are enabled...
        self.force_alive(entity, component)

        # Not on entity because we don't have anyone hanging on them where they
        # belong yet...
        self.assertIs(entity.get(SkillComponent), Null())

        # Now stuff it in there.
        self.manager.entity.attach(entity.id, component)
        ent_comp = entity.get(SkillComponent)
        self.assertIsNot(ent_comp, Null())
        self.assertIs(ent_comp, component)

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

    def test_ent_set_up(self):
        # Just make sure we did the set_up successfully...
        self.per_test_set_up()

    def test_skill_cmd(self):
        # Set up entity with skill data
        entity = self.per_test_set_up()

        # Let the commands register
        self.allow_registration()

        # Ok... test the skill command.
        context = UnitTestContext(
            self.__class__.__name__,
            'input-event',
            {})  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/skill $perception + 4")
        self.trigger_events(event, expected_events=0)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.zest.integration.interface.zest_input_cmd_skill_check

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
