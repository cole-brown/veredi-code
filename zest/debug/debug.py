# coding: utf-8

'''
Some command(s) for background data and possibly other data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
                                                CommandRegisterReply,
                                                CommandPermission,
                                                CommandArgType,
                                                CommandStatus)
from veredi.interface.input.context     import InputContext


from .                                  import background as dbg_bg


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
    if sub_cmd == 'background':
        return dbg_bg.command(context)

    return CommandStatus.parsing(
        sub_cmd + ' ' + arg_str,
        "Don't know what to do with '{} {}'".format(sub_cmd, arg_str),
        "'/debug' command doesn't have anything set up for "
        "sub-command '{}'".format(sub_cmd))
