# coding: utf-8

'''
Some command(s) for background data and possibly other data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


from veredi.data import background

# Everything needed to participate in command registration.
from veredi.input.command.reg       import (CommandRegistrationBroadcast,
                                            CommandRegisterReply,
                                            CommandPermission,
                                            CommandStatus)
from veredi.input.context           import InputContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.debug.background'


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

def register(event: CommandRegistrationBroadcast) -> None:
    '''
    Build the 'background' command.
    '''
    cmd = CommandRegisterReply(
        event,
        background.DOTTED_NAME,
        'background',
        CommandPermission.DEBUG,
        command,
        description='Debug command to show the background context.')

    # No args.

    return cmd


# -----------------------------------------------------------------------------
# Command Handlers
# -----------------------------------------------------------------------------

def command(context: Optional[InputContext] = None) -> CommandStatus:
    '''
    Debug command invocation handler.
    '''
    print("\nHello there from cmd_background!")
    print(context)
    return CommandStatus.successful(context)
