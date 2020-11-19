# coding: utf-8

'''
Some command(s) for background data and possibly other data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional


from veredi.logger                       import log
from veredi.data                         import background

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg  import (CommandRegistrationBroadcast,
                                                 CommandRegisterReply,
                                                 CommandPermission,
                                                 CommandStatus)
from veredi.interface.input.context      import InputContext
from veredi.game.data.identity.component import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.debug.background'

_LOG_TITLE = 'Veredi Background Context'


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

    # Get entity info so we can:
    #   a) Log who called this?
    #        TODO [2020-07-07]: command/history should do this.
    #   b) Send background data back to them.
    entity = background.system.meeting.entity.get(
        InputContext.source_id(context))
    component = entity.get(IdentityComponent)

    # TODO: to_entity()
    # TODO: Figure out what the hell I meant by "TODO: to_entity()"
    to_log(component.log_name)

    return CommandStatus.successful(context)


def to_log(log_name: str) -> None:
    '''
    Log background out at a level that will likely get printed.
    '''
    from veredi.logger import pretty
    output = pretty.indented(background._CONTEXT,
                             sort=True)
    # TODO [2020-06-28]: Log function for 'always log this' that isn't
    # "CRITICAL ERROR OMG!!!"?
    log.critical(f'{_LOG_TITLE} (requested by {log_name}):\n' + output)
