# coding: utf-8

'''
Events related to input from user. All input from user should be either
packaged up into an event or perhaps fed directly/firstly into InputSystem.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
import enum

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import MonotonicId
from veredi.game.ecs.event         import Event

from .command.args import CommandStatus
from .context import InputContext


# -----------------------------------------------------------------------------
# Base Input Event
# -----------------------------------------------------------------------------

class InputEvent(Event):
    # def __init__(self,
    #              id:           Union[int, MonotonicId],
    #              type:         Union[int, enum.Enum],
    #              context:      VerediContext,
    #              skill:        str) -> None:
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
    # Input Things
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "InEvent"


class UserInputEvent(Event):
    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "UsrInEvent"


# What other base kinds? Is GM different from User? Don't think so...

# -----------------------------------------------------------------------------
# Command Event
# -----------------------------------------------------------------------------

class CommandInputEvent(UserInputEvent):
    def __init__(self,
                 id:          Union[int, MonotonicId],
                 type:        Union[int, enum.Enum],
                 context:     VerediContext,
                 string_user: str) -> None:
        self.set(id, type, context, string_user)

    def set(self,
            id:          Union[int, MonotonicId],
            type:        Union[int, enum.Enum],
            context:     VerediContext,
            string_user: str) -> None:
        super().set(id, type, context)
        self.string_unsafe = string_user

    def reset(self) -> None:
        super().reset()
        self.string_unsafe = None

    # -------------------------------------------------------------------------
    # Input Things
    # -------------------------------------------------------------------------

    # self.string_unsafe

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "CmdEvent"

    def __str__(self):
        return (f"{self._str_name()}: cmd-len:{len(self.string_unsafe)} :: "
                f"context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                "{len(self.string_unsafe)} :: {repr(self._context)}>")


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

    # -------------------------------------------------------------------------
    # Class Method Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def command(klass: 'OutputEvent',
                status: CommandStatus,
                context: InputContext) -> 'OutputEvent':
        '''
        Create an OutputEvent from the command status.
        '''
        # TODO [2020-06-17]: OutputEvent from actual output, not from
        # CommandStatus? Or should it be both?
        retval = OutputEvent(
            InputContext.source_id(context),
            InputContext.type(context),
        )
        return retval

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
