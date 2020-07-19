# coding: utf-8

'''
Events related to combat.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
import enum

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import (MonotonicId,
                                           ComponentId)
from veredi.game.ecs.event         import Event


# -----------------------------------------------------------------------------
# Base Skill Event
# -----------------------------------------------------------------------------

class SkillEvent(Event):
    def __init__(self,
                 id:           Union[int, MonotonicId],
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 skill:        str) -> None:
        self.set(id, type, context, skill)

    def set(self,
            id:           Union[int, MonotonicId],
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            skill:        str) -> None:
        super().set(id, type, context)
        self.skill        = skill

    def reset(self) -> None:
        super().reset()
        self.skill = None

    # -------------------------------------------------------------------------
    # Skill Things
    # -------------------------------------------------------------------------

    # self.skill

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "SkEvent"


# -----------------------------------------------------------------------------
# Skill Request Event -> Skill Output Events
# -----------------------------------------------------------------------------

class SkillRequest(SkillEvent):

    # -------------------------------------------------------------------------
    # Skill Things
    # -------------------------------------------------------------------------

    # self.skill

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "SkReq"

    def __str__(self):
        return (f"{self._str_name()}: {self.skill} :: "
                f"context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                "{self.skill} :: {repr(self._context)}>")


class SkillResult(SkillEvent):
    def __init__(self,
                 id:           Union[int, MonotonicId],
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 component_id: Union[int, ComponentId],
                 skill:        str,
                 amount:       int) -> None:
        self.set(id, type, context, component_id, skill, amount)

    def set(self,
            id:           Union[int, MonotonicId],
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            component_id: Union[int, ComponentId],
            skill:        str,
            amount:       int) -> None:
        super().set(id, type, context, skill)
        self.component_id = component_id
        self.amount       = amount

    def reset(self) -> None:
        super().reset()
        self.component_id = ComponentId.INVALID
        self.amount       = None

    # -------------------------------------------------------------------------
    # Skill Things
    # -------------------------------------------------------------------------

    # self.skill
    # self.amount
    # self.component_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "SkRes"

    def __str__(self):
        return (f"{self._str_name()}: {self.skill} = {self.amount} "
                f":: context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"{self.skill}={self.amount} :: {repr(self._context)}>")


# SkillAssistRequest/Event?
