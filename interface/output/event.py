# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Any, Mapping
import enum

from veredi.game.ecs.event          import Event

from veredi.base.enum               import FlagCheckMixin, FlagSetMixin
from veredi.base.context            import VerediContext
from veredi.game.ecs.base.identity  import EntityId
from veredi.base.identity           import SerializableId
from veredi.interface.input.context import InputContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Recipient(FlagCheckMixin, FlagSetMixin, enum.Flag):
    '''
    has() and any() provided by FlagCheckMixin.
    '''

    INVALID = 0

    # ------------------------------
    # Output to Users Types:
    # ------------------------------
    GM = enum.auto()
    '''Send this to the GM due to some special GM-only data.'''

    USER = enum.auto()
    '''Send this to the user who is responsible for it.'''

    BROADCAST = enum.auto()
    '''Send this to all users in the game.'''

    # ------------------------------
    # Other Output Types to Flag:
    # ------------------------------
    LOG = enum.auto()
    '''Send this output (formatted as would be for text client) to the log.'''


# -----------------------------------------------------------------------------
# Base Output Event
# -----------------------------------------------------------------------------

class OutputEvent(Event):
    '''
    An event that should be show to the outside world (users?). Something that
    isn't just apparent in some other way.

    E.g. maybe an attack has an OutputEvent with how much damage the attack
    dealt, but how many hit points the target lost is only known via their
    health bar (or not at all if the gm is hiding that info).
    '''

    def __init__(self,
                 source_id:   Union[int, EntityId],
                 source_type: Union[int, enum.Enum],
                 output:      Any,
                 context:     VerediContext,
                 serial_id:   SerializableId,
                 recipients: 'Recipient') -> None:
        self.set(source_id, source_type, output, context,
                 serial_id, recipients)

    def set(self,
            source_id:   Union[int, EntityId],
            source_type: Union[int, enum.Enum],
            output:      Any,
            context:     VerediContext,
            serial_id:   SerializableId,
            recipients: 'Recipient') -> None:
        super().set(source_id, source_type, context)
        self._output = output
        self._serial_id = serial_id
        self._recipients = recipients
        # self._designations = {
        #     str(source_id): InputContext.source_designation(context),
        # }

    def reset(self) -> None:
        super().reset()
        self._output = None
        self._serial_id = None
        self._recipients = None
        # self._designations = None

    # -------------------------------------------------------------------------
    # Output Things
    # -------------------------------------------------------------------------

    @property
    def output(self) -> Any:
        '''
        Returns the event's raw output (string, MathTree, whatever).
        '''
        return self._output

    # @property
    # def designations(self) -> Mapping[str, str]:
    #     '''
    #     Returns a dictionary of identifiers (dotted strs, IDs, etc.) to
    #     designations (entity display names, feat display names, etc).
    #     '''
    #     return self._designations
    #
    # @property
    # def title(self) -> str:
    #     '''
    #     Display Name / Title of this event.
    #
    #     e.g. "Skill Check"
    #     '''
    #     return self._title_main
    #
    # @property
    # def subtitle(self) -> str:
    #     '''
    #     Second Display Name / Sub-Title of this event.
    #
    #     e.g. "Sneakery"
    #     '''
    #     return self._title_sub

    @property
    def serial_id(self) -> SerializableId:
        '''
        SerializableId of this event - likely its InputId.
        '''
        return self._serial_id

    @property
    def source_type(self) -> Union[int, enum.Enum]:
        '''
        EntityTypeId of the entity responsible for this OutputEvent.
        '''
        return self.type

    @property
    def source_id(self) -> Union[int, EntityId]:
        '''
        EntityId of the entity responsible for this OutputEvent.
        '''
        return self.id

    @property
    def desired_recipients(self) -> 'Recipient':
        '''
        Desired recipients of this OutputEvent.
        '''
        return self._recipients

    @property
    def dotted(self) -> str:
        '''
        Veredi dotted name for what type/kind of output this is.
        '''
        return 'veredi.interface.output.event.base'

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "OutEvent"
