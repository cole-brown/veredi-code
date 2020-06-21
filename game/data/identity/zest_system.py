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
from veredi.logger import log

from veredi.game.ecs.base.identity import ComponentId, EntityId
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.component import DataComponent

from .system import IdentitySystem
from .event import CodeIdentityRequest, IdentityResult
from .component import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_IdentitySystem(unittest.TestCase):
    '''
    Test our IdentitySystem with some on-disk data.
    '''

    ID_DATA = {
        'identity': {
            'name': 'test-jeff',
            'group': 'u/jeffe',

            'display-name': 'Test Jeff',
            'user': 'u/jeffe',
            'player': 'Test Jeff',
            'title': 'Titular',
        },
    }

    def setUp(self):
        self.debug               = False

        (self.managers,
         self.context,
         self.system_manager, _) = zload.set_up(self.__class__.__name__,
                                                'setUp',
                                                self.debug)
        sid                      = zload.create_system(self.system_manager,
                                                       self.context,
                                                       IdentitySystem)
        self.identity               = self.system_manager.get(sid)
        self.events              = []

    def tearDown(self):
        self.debug          = False
        self.managers       = None
        self.context        = None
        self.system_manager = None
        self.identity       = None
        self.events         = None

    def sub_events(self):
        self.managers.event.subscribe(IdentityResult, self.event_identity_res)

    def set_up_subs(self):
        self.sub_events()
        self.system_manager.subscribe(self.managers.event)

    def event_loaded(self, event):
        self.events.append(event)

    def event_identity_res(self, event):
        self.events.append(event)

    def clear_events(self):
        self.events.clear()

    def create_entity(self):
        _TYPE_DONT_CARE = 1
        # Â§-TODO-Â§ [2020-06-01]: When we get to Entities-For-Realsies,
        # probably change to an EntityContext or something...
        context = UnitTestContext(
            self.__class__.__name__,
            'test_create',
            {})  # no initial sub-context

        # Set up an entity to load the component on to.
        eid = self.managers.entity.create(_TYPE_DONT_CARE,
                                          context)
        self.assertNotEqual(eid, EntityId.INVALID)
        entity = self.managers.entity.get(eid)
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
        with log.LoggingManager.on_or_off(self.debug):
            self.managers.event.notify(event, True)

            for each in range(num_publishes):
                self.managers.event.publish()

        self.assertTrue(self.events)

    def trigger_events(self, event, num_publishes=3, expected_events=1):
        self.assertTrue(event)
        self.assertTrue(num_publishes > 0)
        self.assertTrue(expected_events >= 0)

        with log.LoggingManager.on_or_off(self.debug):
            self.make_it_so(event, num_publishes)

        if expected_events == 0:
            self.assertFalse(self.events)
            self.assertEqual(len(self.events), 0)
            return

        self.assertTrue(self.events)
        self.assertEqual(len(self.events), expected_events)

    # def load_request(self, entity_id, type):
    #     ctx = self.context.spawn(DataLoadContext,
    #                              'unit-testing', None,
    #                              type,
    #                              'test-campaign')
    #     if type == DataGameContext.Type.NPC:
    #         ctx.sub['family'] = 'Townville'
    #         ctx.sub['npc'] = 'Identity Guy'
    #     else:
    #         raise LoadError(
    #             f"No DataGameContext.Type to ID conversion for: {type}",
    #             None,
    #             ctx)

    #     event = DataLoadRequest(
    #         id,
    #         ctx.type,
    #         ctx)

    #     return event

    # def load(self, entity):
    #     # Make the load request event for our entity.
    #     request = self.load_request(entity.id,
    #                                 DataGameContext.Type.NPC)
    #     self.assertFalse(self.events)

    #     # Ask for our Identity Guy data to be loaded.
    #     with log.LoggingManager.on_or_off(self.debug):
    #         self.make_it_so(request)
    #     self.assertTrue(self.events)
    #     self.assertEqual(len(self.events), 1)

    #     # We should get an event for load finished.
    #     self.assertEqual(len(self.events), 1)
    #     self.assertIsInstance(self.events[0], DataLoadedEvent)
    #     event = self.events[0]
    #     cid = event.component_id
    #     self.assertNotEqual(cid, ComponentId.INVALID)
    #     component = self.managers.component.get(cid)
    #     self.assertIsInstance(component, DataComponent)
    #     self.assertIsInstance(component, IdentityComponent)

    #     # Stuff it on our entity
    #     self.managers.entity.add(entity.id, component)
    #     # Make sure component got attached to entity.
    #     self.assertIn(IdentityComponent, entity)

    #     return component

    def identity_request_code(self, entity, id_data):
        context = UnitTestContext(
            self.__class__.__name__,
            'identity_request',
            {})  # no initial sub-context
        # ctx = self.context.spawn(EphemerealContext,
        #                          'unit-testing', None)

        event = CodeIdentityRequest(
            entity.id,
            entity.type_id,
            context,
            id_data)

        return event

    def test_init(self):
        self.assertTrue(self.managers)
        self.assertTrue(self.context)
        self.assertTrue(self.system_manager)
        self.assertTrue(self.identity)

    # def test_load(self):
    #     self.set_up_subs()
    #     entity = self.create_entity()
    #     self.assertTrue(entity)
    #     component = self.load(entity)
    #     self.assertTrue(component)

    def test_identity_req_code(self):
        self.set_up_subs()
        entity = self.create_entity()
        # Throw away loading events.
        self.clear_events()

        request = self.identity_request_code(entity, self.ID_DATA)
        with log.LoggingManager.on_or_off(self.debug):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, IdentityResult)
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Check out the component.
        cid_event = result.component_id
        self.assertNotEqual(cid_event, ComponentId.INVALID)
        component_event = self.managers.component.get(cid_event)
        self.assertIsInstance(component_event, DataComponent)
        self.assertIsInstance(component_event, IdentityComponent)
        component_event._life_cycle = ComponentLifeCycle.ALIVE

        with log.LoggingManager.on_or_off(self.debug):
            component_entity = entity.get(IdentityComponent)
        self.assertIsInstance(component_entity, DataComponent)
        self.assertIsInstance(component_entity, IdentityComponent)
        self.assertEqual(component_event.id, component_entity.id)
        self.assertIs(component_event, component_entity)

        # Now our guy should have his name?
        self.assertTrue(component_entity.name, 'test-jeff')
        self.assertTrue(component_entity.display, 'Test Jeff')

    # def test_identity_req_load(self):
    #     self.set_up_subs()
    #     entity = self.create_entity()
    #     self.load(entity)
    #     # Throw away loading events.
    #     self.clear_events()

    #     request = self.identity_request(entity, "knowledge (nature)")
    #     with log.LoggingManager.on_or_off(self.debug):
    #         self.trigger_events(request)

    #     result = self.events[0]
    #     self.assertIsInstance(result, IdentityResult)
    #     self.assertEqual(result.identity.lower(), request.identity.lower())
    #     # request and result should be both for our entity
    #     self.assertEqual(result.id, request.id)
    #     self.assertEqual(result.id, entity.id)

    #     # Identity Guy should have Four Nature Knowledges.
    #     self.assertEqual(result.amount, 4)

    def test_todo(self):
        log.debug("TODO: Convert to zystem base class like Test_InputSystem")
        self.assertTrue(True)
