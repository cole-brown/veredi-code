# coding: utf-8

'''
Tests for the Commander sub-system, events, components, commands......
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest

from veredi.zest import zonfig
from veredi.logger import log

from veredi.base.null import Null
from veredi.game.ecs.event import EventManager
from veredi.data.config.hierarchy import Document

# Just wanna get this dude registered.
from veredi.math.d20.parser import MathParser

from ..context import InputSystemContext
from ..parse import Parcel
from .commander import Commander
from .args import CommandArgType, CommandStatus
from .event import CommandRegistrationBroadcast, CommandRegisterReply
from . import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Commander(unittest.TestCase):
    '''
    Test our Commander with some commands.
    '''

    def setUp(self):
        self.debugging = False

        self.config = zonfig.manual({
            Document.CONFIG: {
                'data': {
                    'game': None,
                    #    # repository:
                    #    #   type: veredi.repository.file-tree
                    #    #   directory: ../repository/file-tree
                    #    #   sanitize: veredi.sanitize.human.path-safe
                    #    # codec: veredi.codec.yaml
                },
                'input': {
                    'parser': {
                        'math': 'veredi.math.d20.parser',
                        'command': 'veredi.input.commander',
                    },
                },
            },
        })

        self.event_manager     = EventManager(self.config)
        self.parsers           = Parcel(self.config.context)
        self._context          = InputSystemContext(self.parsers, None)
        self.commander         = Commander(self._context)

        self.reg_open          = False
        self.events            = []
        self.cmd_was_triggered = False
        self._set_up_subs()

    def tearDown(self):
        self.debugging         = False
        self.config            = None
        self.event_manager     = None
        self.commander         = None
        self.parsers           = None
        self._context          = None
        self.reg_open          = False
        self.cmd_was_triggered = False
        self.events            = None

    def _sub_events(self):
        self.event_manager.subscribe(CommandRegistrationBroadcast,
                                     self.event_cmd_reg)
        self.event_manager.subscribe(CommandRegisterReply,
                                     self.event_cmd_reply)

    def _set_up_subs(self):
        self._sub_events()
        self.commander.subscribe(self.event_manager)

    # -------------------------------------------------------------------------
    # Helpers and Events
    # -------------------------------------------------------------------------

    def user_input_ctx(self, input_str, entity_id):
        return self._context.clone(None, input_str, entity_id)

    def allow_registration(self):
        if self.reg_open:
            return

        event = self.commander.registration(42, self._context)
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)
        # Now registration is open.
        self.assertTrue(self.reg_open)

    def event_cmd_reg(self, event):
        self.assertIsInstance(event, CommandRegistrationBroadcast)
        self.reg_open = event

    def event_cmd_reply(self, event):
        self.events.append(event)

    def clear_events(self):
        self.events.clear()

    def make_it_so(self, event, num_publishes=1):
        '''
        Notifies the event for immediate action. Which /should/ cause something
        to process it and queue up an event. So we publish() in order to get
        that one sent out. Which /should/ cause something to process that?

        Adjust num_publishes if you need to keep going from there.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            self.event_manager.notify(event, True)

            for each in range(num_publishes):
                self.event_manager.publish()

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

    def trigger_cmd(self, math, context=None):
        self.cmd_was_triggered = True
        return CommandStatus.successful(context)

    def full_cmd_setup(self):
        self.allow_registration()

        # Reg is open; make a command to register.
        cmd_reg = CommandRegisterReply(
            self.reg_open,
            'unit-test',
            # I'm not testing perms here.
            const.CommandPermission.UNRESTRICTED,
            self.trigger_cmd,
            description='This is a unit testing thing.')

        cmd_reg.add_arg('var name', CommandArgType.VARIABLE)
        cmd_reg.add_arg('more math', CommandArgType.MATH,
                        optional=True)

        # No commands yet.
        self.assertEqual(len(self.commander._commands), 0)
        # Register our command.
        self.trigger_events(cmd_reg, num_publishes=1, expected_events=1)
        # Was command registered?
        self.assertIsInstance(self.events[0], CommandRegisterReply)
        self.assertEqual(len(self.commander._commands), 1)
        self.clear_events()

    # -------------------------------------------------------------------------
    # Unit Tests!
    # -------------------------------------------------------------------------

    def test_init(self):
        self.assertTrue(self.commander)
        self.assertTrue(self.parsers)
        self.assertTrue(self._context)

    def test_cmd_broadcast(self):
        # No registration yet.
        self.assertFalse(self.reg_open)

        event = self.commander.registration(42, self._context)
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)

        # Now registration is open.
        self.assertTrue(self.reg_open)
        self.assertIsInstance(self.reg_open, CommandRegistrationBroadcast)
        # And we don't bother saving the broadcast event in event queue.
        self.assertEqual(len(self.events), 0)

    def test_cmd_registered(self):
        self.allow_registration()

        # Reg is open; make a command to register.
        cmd_reg = CommandRegisterReply(
            self.reg_open,
            'unit-test',
            # I'm not testing perms here.
            const.CommandPermission.UNRESTRICTED,
            self.trigger_cmd,
            description='This is a unit testing thing.')

        cmd_reg.add_arg('var name', CommandArgType.VARIABLE)
        cmd_reg.add_arg('more math', CommandArgType.MATH,
                        optional=True)

        # No commands yet.
        self.assertEqual(len(self.commander._commands), 0)
        # Register our command.
        self.trigger_events(cmd_reg, num_publishes=1, expected_events=1)
        # Was command registered?
        self.assertIsInstance(self.events[0], CommandRegisterReply)
        self.assertEqual(len(self.commander._commands), 1)

    def test_command_execution(self):
        self.full_cmd_setup()

        cmd_str = 'unit-test 2 + 3'

        # Now ask for this to be executed. Should be a clean/valid input,
        # should have command name, should not have command prefix.
        status = self.commander.execute(None,
                                        cmd_str,
                                        self.user_input_ctx(cmd_str, Null()))

        # In normal usage, we may need EventManager to publish() once or thrice
        # (or not), depending on the command. Here we're unit testing so we
        # don't care about all that and our command is done now.
        #
        # It rudely did everything during execution/invocation instead of
        # holding back any heavy-weight lifting for its turn in the update
        # tick... probably. I may have walked back this assumption since then.
        # These are unit tests and tend to get ignored until they fail...
        #
        # So, hi. Sorry this is failing for you. :(
        self.assertTrue(self.cmd_was_triggered)

        # We get status back immediately. Should be a success.
        self.assertIsInstance(status, CommandStatus)
        self.assertTrue(status.success)
        self.assertEqual(status.command_safe, cmd_str)
