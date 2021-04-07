# coding: utf-8

'''
Tests for the Skill system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.ecs           import ZestEcs
from veredi.zest                    import zmake
from veredi.zest.zpath              import TestType

from veredi.base.context            import UnitTestContext
from veredi.logs                    import log

from veredi.game.ecs.event          import EventManager
from veredi.game.ecs.time           import TimeManager
from veredi.game.ecs.component      import ComponentManager
from veredi.game.ecs.entity         import EntityManager
from veredi.game.ecs.system         import SystemManager
from veredi.game.ecs.meeting        import Meeting

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.component import ComponentLifeCycle
from veredi.game.data.component     import DataComponent


from .manager                       import IdentityManager
from .event                         import CodeIdentityRequest, IdentityResult
from .component                     import IdentityComponent


# For registering
from veredi.data.repository.file.tree import FileTreeRepository


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_IdentityManager(ZestEcs):
    '''
    Test our IdentityManager with some on-disk data.

    Using ZestEcs as our base instead of ZestBase (which most other managers
    use) as we are reliant on a lot of the other managers anyways... Time,
    Event, and Entity directly; Component indirectly.
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

    # -------------------------------------------------------------------------
    # Set-Up
    # -------------------------------------------------------------------------

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

        self.identity = self.manager.identity

    # -------------------------------------------------------------------------
    # Tear-Down
    # -------------------------------------------------------------------------

    def tear_down(self):
        super().tear_down()

        self.config      = None
        self.identity    = None
        self.manager     = None

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _sub_data_loaded(self) -> None:
        '''Don't want DataLoadedEvent.'''
        pass

    def sub_events(self) -> None:
        self.manager.event.subscribe(IdentityResult,
                                     self._eventsub_generic_append)

    def identity_request_code(self, entity, id_data):
        context = UnitTestContext(
            __file__,
            self,
            'identity_request_code')  # no initial sub-context

        event = CodeIdentityRequest(
            entity.id,
            entity.type_id,
            context,
            id_data)

        return event

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.identity)
        self.assertTrue(self.manager)
        self.assertTrue(self.manager.identity)

    def test_identity_req_code(self):
        # ---
        # Test Set-Up
        # ---
        self.set_up_events()
        entity = self.create_entity(force_entity_alive=True)
        # Throw away any loading events?
        # self.clear_events(clear_manager=True)
        # Would rather know that nothing I need was created...
        self.assertEqual(len(self.events), 0)
        # ...and nothing anyone else needs is dangling.
        self.assertFalse(self.manager.event.has_queued)

        # ---
        # Request an IdentityComponent be created from our data.
        # ---
        request = self.identity_request_code(entity, self.ID_DATA)
        with log.LoggingManager.on_or_off(self.debugging):
            self.trigger_events(request)

        # ---
        # Verify result.
        # ---
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

    # TODO [2020-10-09]: test user_id and user_key dicts stay synced with
    # games entities.


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.game.data.identity.zest_manager

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
