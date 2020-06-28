# coding: utf-8

'''
Tests for the Skill system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zload
from veredi.base.context import UnitTestContext
from veredi.data.exceptions import LoadError
from veredi.logger import log

from veredi.game.ecs.base.identity import ComponentId, EntityId
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.event import DataLoadedEvent, DataLoadRequest
from veredi.game.data.component import DataComponent
from veredi.data.context import DataGameContext, DataLoadContext

from .system import SkillSystem
from .event import SkillRequest, SkillResult
from .component import SkillComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_SkillSystem(unittest.TestCase):
    '''
    Test our SkillSystem with some on-disk data.
    '''

    def setUp(self):
        self.debugging    = False

        (self.manager, _,
         self.context, _) = zload.set_up(self.__class__.__name__,
                                         'setUp',
                                         self.debugging)
        sid               = zload.create_system(self.manager.system,
                                                self.context,
                                                SkillSystem)
        self.skill        = self.manager.system.get(sid)
        self.events       = []

    def tearDown(self):
        self.debugging      = False
        self.manager        = None
        self.context        = None
        self.skill          = None
        self.events         = None

    def sub_events(self):
        self.manager.event.subscribe(DataLoadedEvent, self.event_loaded)
        self.manager.event.subscribe(SkillResult, self.event_skill_res)

    def set_up_subs(self):
        self.sub_events()
        self.manager.system.subscribe(self.manager.event)

    def event_loaded(self, event):
        self.events.append(event)

    def event_skill_res(self, event):
        self.events.append(event)

    def clear_events(self):
        self.events.clear()

    def create_entity(self):
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

    def make_it_so(self, event, num_publishes=3):
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event. So we publish() in order to get
        that one sent out. Which /should/ cause something to process that and
        queue up another. So we'll publish as many times as asked. Then assert
        we ended up with an event in our self.events list.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            self.manager.event.notify(event, True)

            for each in range(num_publishes):
                self.manager.event.publish()

        self.assertTrue(self.events)

    def trigger_events(self, event, num_publishes=3, expected_events=1):
        self.assertTrue(event)
        self.assertTrue(num_publishes > 0)
        self.assertTrue(expected_events >= 0)

        with log.LoggingManager.on_or_off(self.debugging):
            self.make_it_so(event, num_publishes)

        if expected_events == 0:
            self.assertFalse(self.events)
            self.assertEqual(len(self.events), 0)
            return

        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

    def load_request(self, entity_id, type):
        ctx = DataLoadContext('unit-testing', None,
                              type,
                              'test-campaign')
        if type == DataGameContext.Type.NPC:
            ctx.sub['family'] = 'Townville'
            ctx.sub['npc'] = 'Skill Guy'
        else:
            raise LoadError(
                f"No DataGameContext.Type to ID conversion for: {type}",
                None,
                ctx)

        event = DataLoadRequest(
            id,
            ctx.type,
            ctx)

        return event

    def load(self, entity):
        # Make the load request event for our entity.
        request = self.load_request(entity.id,
                                    DataGameContext.Type.NPC)
        self.assertFalse(self.events)

        # Ask for our Skill Guy data to be loaded.
        with log.LoggingManager.on_or_off(self.debugging):
            self.make_it_so(request)
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
            self.__class__.__name__,
            'skill_request',
            {})  # no initial sub-context
        # ctx = self.context.spawn(EphemerealContext,
        #                          'unit-testing', None)

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
        self.assertTrue(self.skill)

    def test_load(self):
        self.set_up_subs()
        entity = self.create_entity()
        self.assertTrue(entity)
        component = self.load(entity)
        self.assertTrue(component)

    def test_skill_req_standard(self):
        self.set_up_subs()
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
        self.set_up_subs()
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

    def test_todo(self):
        log.debug("TODO: Convert to zystem base class like Test_InputSystem")
        self.assertTrue(True)
