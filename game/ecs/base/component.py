# coding: utf-8

'''
Everything that makes up players, monsters, items, etc. should be a Component
subclass...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Type
import enum

from veredi.base.context import VerediContext
from veredi.data.config.context import ConfigContext
from .identity import ComponentId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

CompIdOrType = Union[ComponentId, Type['Component']]


@enum.unique
class ComponentLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()
    DEAD       = enum.auto()

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self._name_}"
        )

    def __repr__(self):
        return (
            f"ELC.{self._name_}"
        )


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Component:
    '''
    A component does not track its EntityId. This is so we can have entities
    that actually share the same exact component.
    '''

    def __init__(self,
                 context: Optional[VerediContext],
                 cid:     ComponentId) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''
        self._comp_id = cid
        self._life_cycle = ComponentLifeCycle.INVALID

        self._configure(context)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        pass

    @property
    def id(self) -> ComponentId:
        return ComponentId.INVALID if self._comp_id is None else self._comp_id

    @property
    def enabled(self):
        return self._life_cycle == ComponentLifeCycle.ALIVE

    @property
    def life_cycle(self):
        return self._life_cycle

    def _life_cycled(self, new_state: ComponentLifeCycle):
        '''
        ComponentManager calls this to update life cycle. Will be called on:
          - INVALID  -> CREATING   : During ComponentManager.create().
          - CREATING -> ALIVE      : During ComponentManager.creation()
          - ALIVE    -> DESTROYING : During ComponentManager.destroy().
          - DESTROYING -> DEAD     : During ComponentManager.destruction()
        '''
        self._life_cycle = new_state

    def __str__(self):
        return (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{str(self.life_cycle)}]"
        )

    def __repr__(self):
        return (
            '<v.comp:'
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"{str(self.life_cycle)}]>"
        )
