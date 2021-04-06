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

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import MonotonicId
from veredi.game.ecs.event         import Event


# -----------------------------------------------------------------------------
# Base Input Event
# -----------------------------------------------------------------------------

class InputEvent(Event,
                 name_dotted='veredi.interface.input.event',
                 name_string='input'):
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

    def __repr_name__(self) -> str:
        return "InEvent"


class UserInputEvent(Event,
                     name_dotted='veredi.interface.input.event.user',
                     name_string='input.user'):
    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self) -> str:
        return "UsrInEvent"


# What other base kinds? Is GM different from User? Don't think so...

# -----------------------------------------------------------------------------
# Command Event
# -----------------------------------------------------------------------------

class CommandInputEvent(UserInputEvent,
                        name_dotted='veredi.interface.input.event.command',
                        name_string='input.command'):
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

    def __repr_name__(self) -> str:
        return "CmdEvent"

    def __str__(self) -> str:
        return (f"{self.__str_name__()}: cmd-len:{len(self.string_unsafe)} :: "
                f"context: {str(self._context)}")

    def __repr__(self) -> str:
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                "{len(self.string_unsafe)} :: {repr(self._context)}>")

