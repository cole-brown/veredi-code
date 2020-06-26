# coding: utf-8

'''
Events related to combat.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
import enum

from veredi.base.context import VerediContext
# is there a CombatContext?
# from .context import CombatContext
from veredi.game.ecs.event import Event
from veredi.game.ecs.base.identity import EntityId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class CombatEvent(Event):
    pass


# §-TODO-§ [2020-06-03]: put in health, not combat
class HealthEvent(Event):
    pass


# -----------------------------------------------------------------------------
# General Data Events
# -----------------------------------------------------------------------------

class AttackedEvent(CombatEvent):
    def __init__(self,
                 target_id:    EntityId,
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 source_id:    EntityId) -> None:
        self.set(target_id, type, context, source_id)

    def set(self,
            target_id:    EntityId,
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            source_id:    EntityId) -> None:
        super().set(target_id, type, context)
        self.source_id = source_id

    def reset(self) -> None:
        super().reset()
        self.source_id = EntityId.INVALID

    @property
    def target(self) -> EntityId:
        return self.id

    @property
    def source(self) -> EntityId:
        return self.source_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},src:{self.source}]"

    def __repr_name__(self):
        return "AtkEvent"


# §-TODO-§ [2020-06-03]: put in health, not combat
class HealedEvent(HealthEvent):
    pass


# §-TODO-§ [2020-06-03]: put in health, not combat
class DamagedEvent(HealthEvent):
    pass
