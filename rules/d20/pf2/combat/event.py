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

class CombatEvent(Event,
                  name_dotted='veredi.rules.d20.pf2.combat.event',
                  name_string='combat.event'):
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

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.klass
        return f"{name}[id:{self.id},t:{self.type},src:{self.target}]"

    def __repr_name__(self):
        return "CmbtEvent"


# TODO [2020-06-03]: put in health, not combat
class HealthEvent(Event,
                  name_dotted='veredi.rules.d20.pf2.health.event',
                  name_string='health.event'):
    pass


# -----------------------------------------------------------------------------
# General Combat Events
# -----------------------------------------------------------------------------

class AttackRequest(CombatEvent,
                    name_dotted='veredi.rules.d20.pf2.combat.request.attack',
                    name_string='combat.request.attack'):
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


class AttackResult(CombatEvent,
                   name_dotted='veredi.rules.d20.pf2.combat.result.attack',
                   name_string='combat.result.attack'):
    '''
    An entity has attacked attack another entity. This is the info about that
    and how the attacker did on their parts of the attack math.
    '''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "AtkResEvent"


class DefenseRequest(CombatEvent,
                     name_dotted='veredi.rules.d20.pf2.combat.request.defense',
                     name_string='combat.request.defense'):
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


class DefenseResult(CombatEvent,
                    name_dotted='veredi.rules.d20.pf2.combat.result.defense',
                    name_string='combat.result.defense'):
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
class HealedEvent(HealthEvent,
                  name_dotted='veredi.rules.d20.pf2.health.result',
                  name_string='health.result'):
    pass


# TODO [2020-06-03]: put in health, not combat
class DamagedEvent(HealthEvent,
                   name_dotted='veredi.rules.d20.pf2.combat.damage',
                   name_string='combat.damage'):
    pass
