# coding: utf-8

'''
Some command(s) for background data and possibly other data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


from veredi.logger                      import log
from veredi.data                        import background

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg import (CommandRegistrationBroadcast,
                                                CommandRegisterReply,
                                                CommandPermission,
                                                CommandStatus)
from veredi.interface.input.context     import InputContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.debug.background'

_LOG_TITLE = 'Veredi Background Context:'

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
    entity = background.system.meeting.entity.get(
        InputContext.source_id(context))
    # TODO: entity name?

    from veredi.logger import pretty
    output = pretty.indented(background._CONTEXT,
                             sort=True)
    # TODO [2020-06-28]: Log function for 'always log this' that isn't
    # "CRITICAL ERROR OMG!!!"?
    log.critical(f'{_LOG_TITLE}\n' + output)

    return CommandStatus.successful(context)
