# coding: utf-8

'''
Tests for the Skill system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.system        import ZestSystem
from veredi.base.context            import UnitTestContext
from veredi.logger                  import log

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.component     import DataComponent

from .system                        import IdentitySystem
from .event                         import CodeIdentityRequest, IdentityResult
from .component                     import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_IdentitySystem(ZestSystem):
    '''
    Test our IdentitySystem with some on-disk data.
    '''

    ID_DATA = {
        'identity': {
            'name': 'test-jeff',
            'group': 'u/jeffe',
            'owner': 'u/jeffe',

            'log-name': 'test-jeff',
            'display-name': 'Test Jeff',
            'allonym': 'u/jill'
        },
    }

    def set_up(self):
        super().set_up()
        self.init_self_system(IdentitySystem)

    def sub_events(self):
        self.manager.event.subscribe(IdentityResult, self.event_identity_res)

    def event_identity_res(self, event):
        self.events.append(event)

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
        self.assertTrue(self.manager)
        self.assertTrue(self.context)
        self.assertTrue(self.manager.system)
        self.assertTrue(self.system)

    def test_identity_req_code(self):
        self.set_up_events()
        entity = self.create_entity()
        # Throw away loading events.
        self.clear_events(clear_manager=True)

        request = self.identity_request_code(entity, self.ID_DATA)
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        result = self.events[0]
        self.assertIsInstance(result, IdentityResult)
        # request and result should be both for our entity
        self.assertEqual(result.id, request.id)
        self.assertEqual(result.id, entity.id)

        # Check out the component.
        cid_event = result.component_id
        self.assertNotEqual(cid_event, ComponentId.INVALID)
        component_event = self.manager.component.get(cid_event)
        self.assertIsInstance(component_event, DataComponent)
        self.assertIsInstance(component_event, IdentityComponent)
        component_event._life_cycle = ComponentLifeCycle.ALIVE

        with log.LoggingManager.on_or_off(self.debugging):
            component_entity = entity.get(IdentityComponent)
        self.assertIsInstance(component_entity, DataComponent)
        self.assertIsInstance(component_entity, IdentityComponent)
        self.assertEqual(component_event.id, component_entity.id)
        self.assertIs(component_event, component_entity)

        # Now our guy should have his name?
        self.assertTrue(component_entity.designation, 'Test Jeff')
        self.assertTrue(component_entity.log_name, 'test-jeff')
        self.assertTrue(component_entity.log_extra, 'u/jill')
        self.assertTrue(component_entity.owner, 'u/jeffe')
        self.assertTrue(component_entity.allonym, 'u/jill')
        self.assertTrue(component_entity.controller, 'u/jill')


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.identity.zest_system

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
