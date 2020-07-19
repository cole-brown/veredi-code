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
from veredi.base.identity import SerializableId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

class CombatEvent(Event):
    def __init__(self,
                 source_id:    EntityId,
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 target_id:    EntityId) -> None:
        self.set(source_id, type, context, target_id)

    def set(self,
            source_id:    EntityId,
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            target_id:    EntityId) -> None:
        super().set(source_id, type, context)
        self.target_id = target_id

    def reset(self) -> None:
        super().reset()
        self.target_id = EntityId.INVALID

    @property
    def source(self) -> EntityId:
        return self.id

    @property
    def target(self) -> EntityId:
        return self.target_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},src:{self.target}]"

    def __repr_name__(self):
        return "CmbtEvent"


# TODO [2020-06-03]: put in health, not combat
class HealthEvent(Event):
    pass


# -----------------------------------------------------------------------------
# General Combat Events
# -----------------------------------------------------------------------------

class AttackRequest(CombatEvent):
    '''
    An entity wants to attack another entity. This is the info about that.
    '''

    def __init__(self,
                 source_id:    EntityId,
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 target_id:    EntityId,
                 attack_id:    SerializableId) -> None:
        self.set(source_id, type, context, target_id, attack_id)

    def set(self,
            source_id:    EntityId,
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            target_id:    EntityId,
            attack_id:    SerializableId) -> None:
        super().set(source_id, type, context, target_id)
        self.attack_id = attack_id

    def reset(self) -> None:
        super().reset()
        self.target_id = EntityId.INVALID

    @property
    def attack(self) -> SerializableId:
        return self.attack_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "AtkReqEvent"


class AttackResult(CombatEvent):
    '''
    An entity has attacked attack another entity. This is the info about that
    and how the attacker did on their parts of the attack math.
    '''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "AtkResEvent"


class DefenseRequest(CombatEvent):
    '''
    An entity wants to do something defensive? This is the info about that.
    '''

    def __init__(self,
                 source_id:    EntityId,
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 target_id:    EntityId,
                 defense_id:   SerializableId) -> None:
        self.set(source_id, type, context, target_id, defense_id)

    def set(self,
            source_id:    EntityId,
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            target_id:    EntityId,
            defense_id:   SerializableId) -> None:
        super().set(source_id, type, context, target_id)
        self.defense_id = defense_id

    def reset(self) -> None:
        super().reset()
        self.target_id = EntityId.INVALID

    @property
    def defense(self) -> SerializableId:
        return self.defense_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "DfnsReq"


class DefenseResult(CombatEvent):
    '''
    An entity did something defensive? This is the info about that and how the
    entity did on their parts of the defense math.
    '''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "DfnsRes"


# TODO [2020-06-03]: put in health, not combat
class HealedEvent(HealthEvent):
    pass


# TODO [2020-06-03]: put in health, not combat
class DamagedEvent(HealthEvent):
    pass
