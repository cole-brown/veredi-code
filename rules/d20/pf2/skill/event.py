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

class SkillEvent(Event,
                 name_dotted='veredi.rules.d20.pf2.skill.event',
                 name_string='skill.event'):
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

class SkillRequest(SkillEvent,
                   name_dotted='veredi.rules.d20.pf2.skill.request',
                   name_string='skill.request'):

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
        return (f"{self.__str_name__()}: {self.skill} :: "
                f"context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                "{self.skill} :: {repr(self._context)}>")


class SkillResult(SkillEvent,
                  name_dotted='veredi.rules.d20.pf2.skill.result',
                  name_string='skill.result'):
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

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.klass
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "SkRes"

    def __str__(self):
        return (f"{self.__str_name__()}: {self.skill} = {self.amount} "
                f":: context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                f"{self.skill}={self.amount} :: {repr(self._context)}>")


# SkillAssistRequest/Event?
