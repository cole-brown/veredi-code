# coding: utf-8

'''
Tests for the Input system, events, and components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.zystem                  import BaseSystemTest

from veredi.base.context                 import UnitTestContext

from veredi.game.data.identity.system    import IdentitySystem
from veredi.game.data.identity.component import IdentityComponent
from veredi.game.data.identity.event     import CodeIdentityRequest
from veredi.game.ecs.base.entity         import Entity

from .system                             import InputSystem
from .identity                           import InputId
from .event                              import CommandInputEvent
# from .component                        import InputComponent

from veredi.interface.input.command.reg  import (CommandRegisterReply,
                                                 CommandPermission,
                                                 CommandArgType,
                                                 CommandStatus)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_InputSystem(BaseSystemTest):
    '''
    Test our InputSystem with some on-disk data.
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

    def setUp(self):
        super().setUp()
        self.init_managers()
        self.init_system_self(InputSystem)
        self.init_system_others(IdentitySystem)
        self.test_cmd_recv = None
        self.test_cmd_ctx = None

    def tearDown(self):
        super().tearDown()
        self.test_cmd_recv = None
        self.test_cmd_ctx = None

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    def _make_cmd(self, event):
        reply = CommandRegisterReply(event,
                                     'veredi.interface.input.zest_system',
                                     'test',
                                     CommandPermission.UNRESTRICTED,
                                     self.trigger_test_cmd)
        reply.add_arg('var name', CommandArgType.VARIABLE)
        reply.add_arg('additional math', CommandArgType.MATH,
                      optional=True)

        self.trigger_events(reply,
                            expected_events=0)

    def trigger_test_cmd(self, math, context):
        self.test_cmd_recv = math
        self.test_cmd_ctx = context
        return CommandStatus.successful(context)

    # -------------------------------------------------------------------------
    # Identity Component
    # -------------------------------------------------------------------------

    def create_entity(self,
                      id_data=ID_DATA,
                      clear_event_queue=True) -> Entity:
        '''
        Add IdentityComponent to each entity our parent makes for us.
        '''
        entity = super().create_entity()
        self.assertTrue(entity)

        self.manager.entity.creation(self.manager.time)

        context = UnitTestContext(
            self.__class__.__name__,
            'identity_request',
            {})  # no initial sub-context

        # Request our dude get an identity assigned via code.
        event = CodeIdentityRequest(
            entity.id,
            entity.type_id,
            context,
            id_data)

        # We aren't registered to receive the reply, so don't expect anything.
        self.trigger_events(event, expected_events=0)
        # But clear it out just in cases and to be a good helper function.
        if clear_event_queue:
            self.clear_events()

        self.manager.component.creation(self.manager.time)

        return entity

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    def test_init(self):
        # with log.LoggingManager.on_or_off(True):
        #     self.init_system_self(InputSystem)
        self.assertTrue(self.system)

    def test_input_cmd(self):
        self.event_setup()
        self.allow_registration()

        entity = self.create_entity()
        self.assertTrue(entity)
        self.assertTrue(IdentityComponent in entity)

        context = UnitTestContext(
            self.__class__.__name__,
            'input-event',
            {})  # no initial sub-context

        # Do the test command event.
        event = CommandInputEvent(
            entity.id,
            entity.type_id,
            context,
            "/test $varname + 4")
        self.trigger_events(event, expected_events=0)

        # Now, no output events or anything right now... So just test that
        # historian has an entry for this and a valid ID.
        self.assertEqual(len(self.system._historian._global), 1)
        history = self.system._historian._global[0]
        self.assertIsNotNone(history)
        self.assertIsNotNone(history.input_id)
        self.assertNotEqual(history.input_id, InputId.INVALID)
        self.assertEqual(history.entity_id, entity.id)

        # Also, like, maybe we should check to see that our command receiver
        # got invoked...

        self.assertTrue(self.test_cmd_recv)
        self.assertTrue(self.test_cmd_ctx)
