# coding: utf-8

'''
Tests for the Commander sub-system, events, components, commands......
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.zest.base.ecs         import ZestEcs
from veredi.zest                  import zonfig
from veredi                       import log

from veredi.data                  import background
from veredi.base.null             import Null
from veredi.game.ecs.event        import EventManager
from veredi.data.config.hierarchy import Document

# Just wanna get this dude registered.
from veredi.math.d20.parser       import MathParser

from ..context                    import InputContext
from ..parse                      import Parcel
from .commander                   import Commander
from .args                        import CommandArgType, CommandStatus
from .event                       import (CommandRegistrationBroadcast,
                                          CommandRegisterReply)
from .                            import const


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_Commander(ZestEcs):
    '''
    Test our Commander with some commands.
    '''

    def set_up(self):
        super().set_up()
        self.config = zonfig.manual(
            self._TEST_TYPE,
            None,
            None,
            {
                Document.CONFIG: {
                    'data': {
                        'game': None,
                        #    # repository:
                        #    #   type: veredi.repository.file-tree
                        #    #   directory: ../repository/file-tree
                        #    #   sanitize: veredi.paths.sanitize.human
                        #    # serdes: veredi.serdes.yaml
                    },
                    'server': {
                        'input': {
                            'parser': {
                                'math': 'veredi.math.d20.parser',
                                'command': 'veredi.interface.input.commander',
                            },
                        },
                    },
                },
            })

        self.event_manager     = EventManager(self.config, self.debug_flags)
        self.parsers           = Parcel(None)
        self.commander         = Commander(None)

        self.cmd_was_triggered = False

        background.input.set('veredi.interface.input.command.zest_commander',
                             self.parsers,
                             None,
                             background.Ownership.SHARE)

        self.set_up_events()

    def tear_down(self):
        super().tear_down()
        self.config            = None
        self.event_manager     = None
        self.parsers           = None
        self.commander         = None
        self.cmd_was_triggered = False

    def sub_events(self):
        self.event_manager.subscribe(CommandRegistrationBroadcast,
                                     self._eventsub_cmd_reg)
        self.event_manager.subscribe(CommandRegisterReply,
                                     self.event_cmd_reply)

    def set_up_events(self):
        self.commander.subscribe(self.event_manager)
        self.sub_events()
        self.clear_events(clear_manager=True)

    def _event_now(self,
                   event,
                   num_publishes=3) -> None:
        '''
        Redefine cuz no self.managers or self.managers.event.
        Just self.event_manager.
        '''
        with log.LoggingManager.on_or_off(self.debugging):
            self.event_manager.notify(event, True)

            for each in range(num_publishes):
                self.event_manager.publish()

    # -------------------------------------------------------------------------
    # Helpers and Events
    # -------------------------------------------------------------------------

    def user_input_ctx(self, input_str, entity_id, entity_name):
        return InputContext(None, input_str, entity_id, entity_name,
                            self.commander.dotted() + '.unit-test')

    def allow_registration(self):
        if self.reg_open:
            return

        event = self.commander.registration(42, None)
        self.trigger_events(event,
                            expected_events=0,
                            num_publishes=1)
        # Now registration is open.
        self.assertTrue(self.reg_open)

    def event_cmd_reply(self, event):
        self.events.append(event)

    def trigger_cmd(self, math, context=None):
        self.cmd_was_triggered = True
        return CommandStatus.successful(context)

    def full_cmd_setup(self):
        self.allow_registration()

        # Reg is open; make a command to register.
        cmd_reg = CommandRegisterReply(
            self.reg_open,
            'veredi.interface.input.command.zest_commander',
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

    def test_cmd_broadcast(self):
        # No registration yet.
        self.assertFalse(self.reg_open)

        event = self.commander.registration(42, None)
        with log.LoggingManager.on_or_off(self.debugging):
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
            'veredi.interface.input.command.zest_commander',
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
                                        self.user_input_ctx(cmd_str,
                                                            Null(),
                                                            None))

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


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi python -m veredi.interface.input.command.zest_commander

if __name__ == '__main__':
    import unittest
    # log.set_level(log.Level.DEBUG)
    unittest.main()
