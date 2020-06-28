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
                                            CommandArgType,
                                            CommandStatus)
from veredi.input.context           import InputContext


from . import background as dbg_bg


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.debug.debug'


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

def register(event: CommandRegistrationBroadcast) -> None:
    '''
    Build the 'debug' command.
    '''
    cmd = CommandRegisterReply(
        event,
        DOTTED_NAME,
        'debug',
        CommandPermission.DEBUG,
        command,
        description='Debug command with various sub-commands')

    cmd.add_arg('sub-cmd', CommandArgType.WORD)
    cmd.add_arg('args', CommandArgType.STRING)

    return cmd


# -----------------------------------------------------------------------------
# Command Handlers
# -----------------------------------------------------------------------------

def command(sub_cmd: str,
            arg_str: str,
            context: Optional[InputContext] = None) -> CommandStatus:
    '''
    Debug command invocation handler.
    '''
    print("\nHello there from cmd_debug!", sub_cmd, arg_str)
    print(context)
    return CommandStatus.successful(context)

    if sub_cmd == 'background':
        dbg_bg.command(context)
