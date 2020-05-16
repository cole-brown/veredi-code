# coding: utf-8

'''
Everything that makes up players, monsters, items, etc. should be a Component
subclass...
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import NewType, Any, Union, Type, Iterable
import enum

from .exceptions import ComponentError

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

ComponentId = NewType('ComponentId', int)
INVALID_COMPONENT_ID = ComponentId(0)

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
                 cid: ComponentId,
                 *args: Any,
                 **kwargs: Any) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''
        self._comp_id = cid
        self._life_cycle = ComponentLifeCycle.INVALID

    @property
    def id(self) -> ComponentId:
        return self._comp_id

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
            f"[id:{self.id:03d}, "
            f"{str(self.life_cycle)}]"
        )

    def __repr__(self):
        return (
            '<v.comp:'
            f"{self.__class__.__name__}"
            f"[id:{self.id:03d}, "
            f"{repr(self.life_cycle)}]>"
        )


    # TODO: __str__
    # TODO: __repr__


#     # --------------------------------------------------------------------------
#     # Set Interface (hashable, equals)
#     # --------------------------------------------------------------------------
#
#     def __hash__(self):
#         '''Set/Dict interface.
#
#         Redefining so that Components are singleton - only one per class
#         allowed. This doesn't prevent an Entity from having, say, HealthClass
#         and HealthSubClass, but at least it's a sanity check.
#         '''
#         # Hash of (sub)class itself, not any instance.
#         # All (sub)class instances will be considered 'equal' this way for
#         # e.g. set, dict operations.
#         return hash(self.__class__)
#
#     def __eq__(self, other: Any):
#         '''Set/Dict interface.
#
#         Redefining so that Components are singleton - only one per class
#         allowed. This doesn't prevent an Entity from having, say, HealthClass
#         and HealthSubClass, but at least it's a sanity check.
#         '''
#         # Hash of (sub)class itself, not any instance.
#         # All (sub)class instances will be considered 'equal' this way for
#         # e.g. set, dict operations.
#         other_hash = None
#         if isinstance(other, Component):
#             other_hash = Component.hashed(other)
#         else:
#             other_hash = hash(other)
#         return hash(self) == other_hash
