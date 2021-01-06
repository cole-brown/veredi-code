# coding: utf-8

'''
A D20 Game Rules Base Class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Type, Union, Tuple)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from veredi.base.context import VerediContext
    from ..meeting           import Meeting

from abc import abstractmethod


from veredi.logger                         import log
from veredi.base.const                     import VerediHealth
from veredi.base                           import label
from veredi.debug.const                    import DebugFlag
from veredi.data                           import background
from veredi.data.serdes.adapter.definition import Definition
from veredi.data.serdes.adapter.record     import Record
from veredi.data.milieu                    import ValueMilieu
from veredi.data.config.config             import Configuration

# Game / ECS Stuff
from veredi.game.ecs.event                 import EventManager

from veredi.game.ecs.base.identity         import EntityId, SystemId
from veredi.game.ecs.base.system           import System
from veredi.game.ecs.base.component        import Component

# Commands
from veredi.interface.input.command.reg    import CommandRegistrationBroadcast


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Should eventually derive from veredi.rules.game.RulesGame or something...
class D20RulesGame:

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

    def __init__(self,
                 context:  Optional['VerediContext'],
                 managers: 'Meeting') -> None:
        '''
        Initializes the D20 Game Rules from config/context/repo data.
        '''

        self._definition: Definition = None
        '''Game's Definition data for our D20 Rules-based game.'''

        self._data: Record = None
        '''Game's saved data Record.'''

        self._configure(context)

    def _configure(self,
                   context: 'VerediContext') -> None:
        '''
        Get rules definition file and configure it for use.

        Set ourself into the background for anything that needs us.
        '''
        # ---
        # Sanity
        # ---
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # ---
        # Get game definition data.
        # ---

        # Ask config for our definition to be deserialized and given to us
        # right now.
        self._definition = Definition(
            'game',
            config.definition(self.dotted(), context))

        if not self._definition:
            raise background.config.exception(
                context,
                "Cannot configure {} without its game definition data.",
                self.__class__.__name__)

        # ---
        # Get game saved data?
        # ---
        self._data = Record('game.record',  # TODO: get str from somewhere else?
                            config.game())

        # Complain if we don't have the saved game data, unless DebugFlagged to
        # be quiet.
        if (not self._definition
                and not background.manager.flagged(DebugFlag.NO_SAVE_FILES)):
            raise background.config.exception(
                context,
                "Cannot configure {} without its game saved data.",
                self.__class__.__name__)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    def dotted(self) -> str:
        '''
        Veredi dotted label string.
        '''
        return 'veredi.rules.d20.pf2.game'
