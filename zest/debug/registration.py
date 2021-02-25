# coding: utf-8

'''
Some command(s) for background data and possibly other data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi                             import log
from veredi.data                        import background

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg import CommandRegistrationBroadcast


# debug commands to register:
from .                                  import background as dbg_bg
from .                                  import debug


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DOTTED_NAME = 'veredi.debug.background'


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

def register(event: CommandRegistrationBroadcast) -> None:
    '''
    Our event handler for the registration broadcast.
    '''
    if not background.manager.event:
        log.warning(f"'{DOTTED_NAME}' cannot register its commands as there "
                    "is no EventManager in the background meeting.")
        return

    # Get our debug commands' registration events sent out.
    background.manager.event.notify(
        debug.register(event))
    background.manager.event.notify(
        dbg_bg.register(event))
