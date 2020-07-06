# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union
import enum

from veredi.game.ecs.event         import Event

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import MonotonicId
from veredi.base.identity import SerializableId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class OutputType(enum.Enum):
    AUTO = enum.auto()


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
                 source_id:   Union[int, MonotonicId],
                 source_type: Union[int, enum.Enum],
                 context:     VerediContext,
                 serial_id:   SerializableId,
                 output_type: 'OutputType') -> None:
        self.set(source_id, source_type, context,
                 serial_id, output_type)

    def set(self,
            source_id:   Union[int, MonotonicId],
            source_type: Union[int, enum.Enum],
            context:     VerediContext,
            serial_id:   SerializableId,
            output_type: 'OutputType') -> None:
        super().set(id, type, context)
        self.serial_id = serial_id
        self.output_type = output_type

    def reset(self) -> None:
        super().reset()
        self.serial_id = None
        self.output_type = None

    # -------------------------------------------------------------------------
    # Class Method Helpers
    # -------------------------------------------------------------------------

    # @classmethod
    # def command(klass: 'OutputEvent',
    #             status: CommandStatus,
    #             context: InputContext) -> 'OutputEvent':
    #     '''
    #     Create an OutputEvent from the command status.
    #     '''
    #     # TODO [2020-06-17]: OutputEvent from actual output, not from
    #     # CommandStatus? Or should it be both?
    #     retval = OutputEvent(
    #         InputContext.source_id(context),
    #         InputContext.type(context),
    #         context
    #     )
    #     return retval

    # def __init__(self,
    #              id:           Union[int, MonotonicId],
    #              type:         Union[int, enum.Enum],
    #              context:      VerediContext) -> None:
    #     self.set(id, type, context, skill)

    # def set(self,
    #         id:           Union[int, MonotonicId],
    #         type:         Union[int, enum.Enum],
    #         context:      VerediContext,
    #         skill:        str) -> None:
    #     super().set(id, type, context)
    #     self.skill        = skill

    # def reset(self) -> None:
    #     super().reset()
    #     self.skill = None

    # -------------------------------------------------------------------------
    # Output Things
    # -------------------------------------------------------------------------

    # ???

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "OutEvent"


# TODO [2020-06-10]: Eventually, more events. When I have a UI or
# something and can send more than just text...
