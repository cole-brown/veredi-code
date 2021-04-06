# coding: utf-8

'''
Events related to combat.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union)
from veredi.base.null import Nullable, Null
if TYPE_CHECKING:
    from veredi.math.parser import MathTree


import enum

from veredi.base.context import VerediContext
from veredi.game.ecs.event import Event
from veredi.game.ecs.base.identity import EntityId


# -----------------------------------------------------------------------------
# Base Event
# -----------------------------------------------------------------------------

class AbilityEvent(Event,
                   name_dotted='veredi.rules.d20.pf2.ability.event',
                   name_string='ability.event'):
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
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},src:{self.target}]"

    def __repr_name__(self):
        return "AbilEvent"


# -----------------------------------------------------------------------------
# Ability Request Event
# -----------------------------------------------------------------------------

class AbilityRequest(AbilityEvent,
                     name_dotted='veredi.rules.d20.pf2.ability.request',
                     name_string='ability.request'):
    '''
    An entity wants to do an ability check. This is the info about that.
    '''

    def __init__(self,
                 source_id:    EntityId,
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 target_id:    EntityId,
                 ability:      Union[str, 'MathTree']) -> None:
        self.set(source_id, type, context, target_id, ability)

    def set(self,
            source_id:    EntityId,
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            target_id:    EntityId,
            ability:      Union[str, 'MathTree']) -> None:
        super().set(source_id, type, context, target_id)
        self._ability = ability

    def reset(self) -> None:
        super().reset()
        self._ability = None

    @property
    def source(self) -> EntityId:
        return self.id

    @property
    def target(self) -> EntityId:
        return self.target_id

    @property
    def ability(self) -> Nullable[Union[str, 'MathTree']]:
        return self._ability or Null()

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "AbilReq"


class AbilityResult(AbilityEvent,
                    name_dotted='veredi.rules.d20.pf2.ability.result',
                    name_string='ability.result'):
    '''
    An entity has done an ability check. This is the info about that.
    '''

    def __init__(self,
                 request:   'AbilityRequest',
                 amount:    Nullable[int]) -> None:
        self.set(request.source, request.type,
                 request.context, request.target_id,
                 request.ability,
                 amount)

    def set(self,
            source_id: EntityId,
            type:      Union[int, enum.Enum],
            context:   VerediContext,
            target_id: EntityId,
            ability:   Union[str, 'MathTree'],
            amount:    Nullable[Union[int, 'MathTree']]) -> None:
        super().set(source_id, type, context, target_id)
        self._ability = ability
        self._amount = amount

    def reset(self) -> None:
        super().reset()
        self._ability = None
        self._amount = None

    @property
    def source(self) -> EntityId:
        return self.id

    @property
    def target(self) -> EntityId:
        return self.target_id

    @property
    def ability(self) -> Nullable[str]:
        return self._ability or Null()

    @property
    def amount(self) -> Nullable[Union[int, 'MathTree']]:
        return self._amount or Null()

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "AbilRes"
